"""MAYAJAAL-SPEC Layer 2: the block clock, coinbase, coin selection and the transactions.

One function builds one transaction against the live ledger, and `generate` is the loop that
calls it. The shape of a transaction is where the detectors downstream get their signal, so the
awkward cases are produced here on purpose rather than left to chance: change that sits at a
random output index, change that is sometimes a reused address, payments that are sometimes
round numbers, spends that sometimes pool inputs from two different entities.

Money is `int` satoshis end to end. Floats appear only inside a distribution draw and are cast
before they are stored, which is why every draw goes through `_draw_sats` or `_fee_rate`.
Conservation is not asserted here, it is arithmetic: the change output is defined as whatever
is left after the payments and the fee, and when that remainder is below dust it becomes fee.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from chakravyuh.mayajaal import entities, ledger
from chakravyuh.mayajaal.config import Config
from chakravyuh.mayajaal.entities import Population
from chakravyuh.mayajaal.ledger import Ledger, Outpoint, Utxo


@dataclass(frozen=True, slots=True)
class Tx:
    """One transaction. The trailing fields are ground truth and never reach observable output."""

    txid: str
    height: int
    time_us: int
    is_coinbase: bool
    inputs: tuple[Outpoint, ...]
    input_addresses: tuple[str, ...]
    input_sats: tuple[int, ...]
    output_addresses: tuple[str, ...]
    output_sats: tuple[int, ...]
    output_kinds: tuple[str, ...]
    fee_sats: int
    fee_rate: int
    vsize_vb: int
    sender: int
    input_owners: tuple[int, ...]
    change_index: int
    violations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Seed:
    """One prehistory output. The ledger starts mid-chain, so the first spend has something
    to spend. Written out so the invariant test can replay the UTXO set from files alone."""

    txid: str
    vout: int
    address: str
    script_type: str
    sats: int
    height: int


@dataclass(slots=True)
class Counters:
    """Run bookkeeping. `attempts`/`built`/`dropped` feed section 10's counts, which must
    satisfy `in == out + dropped`, so every attempt lands in exactly one of the last two."""

    attempts: int = 0
    built: int = 0
    drops: dict[str, int] = field(default_factory=dict)

    def drop(self, reason: str) -> None:
        self.drops[reason] = self.drops.get(reason, 0) + 1


@dataclass(slots=True)
class MultiInput:
    """Holds the multi-input rate near its target without pinning it to a constant.

    Whether a transaction *can* have two inputs depends on what its sender happens to hold, so
    a plain Bernoulli draw lands wherever the UTXO set allows, which for this population is well
    under the configured rate. This nudges the probability by the error seen so far.

    ponytail: proportional control, no integral term. The measured rate is asserted within a
    configured tolerance, and if that ever needs tightening the fix is a second term here.
    """

    target: float
    gain: float
    multi: int = 0
    total: int = 0

    def p(self) -> float:
        if self.total == 0:
            return self.target
        error = self.target - self.multi / self.total
        return min(1.0, max(0.0, self.target + self.gain * error))

    def observe(self, n_inputs: int) -> None:
        self.total += 1
        if n_inputs > 1:
            self.multi += 1


def _vsize(cfg: Config, in_kinds: list[str], out_kinds: list[str]) -> int:
    """Estimated virtual size in vbytes, from the per-script-type table in run_config.json.

    An estimate is the honest model: a real wallet also pays a fee computed from an estimate,
    which is why real fee rates are not exactly the round numbers users typed.
    """
    chain = cfg.chain
    return (
        chain.vsize_overhead_vb
        + sum(chain.input_vb[kind] for kind in in_kinds)
        + sum(chain.output_vb[kind] for kind in out_kinds)
    )


def _fee_rate(cfg: Config, rng: random.Random) -> int:
    """Whole sat/vB, lognormal and clamped. Whole because that is what wallets let you set."""
    chain = cfg.chain
    drawn = int(rng.lognormvariate(chain.fee_mu, chain.fee_sigma))
    return min(chain.fee_max_sat_per_vb, max(chain.fee_min_sat_per_vb, drawn))


def _draw_sats(rng: random.Random, mu: float, sigma: float, floor: int) -> int:
    """The only place a value becomes money. Cast happens here, so nothing downstream is float."""
    return max(floor, int(rng.lognormvariate(mu, sigma)))


def endow(cfg: Config, pop: Population, book: Ledger, rng: random.Random) -> list[Seed]:
    """Give every entity its opening balance as real UTXOs, one prehistory transaction each.

    MAYAJAAL-SPEC starts the capture at height 880000, not at the genesis block, so the coins
    being spent in the first block were mined by someone the capture never saw. Modelling that
    as an endowment is the alternative to generating sixteen years of history to spend from.
    Amounts are the entity type's own value distribution shifted up by `endowment.mu_offset`,
    because an opening balance has to outlast several payments drawn from that same
    distribution or the first spend empties the wallet.
    """
    chain = cfg.chain
    height = chain.start_height - 1
    low, high = chain.endow_utxos
    seeds: list[Seed] = []
    for index, entity in enumerate(pop.entities):
        spec = cfg.type_of(entity.entity_type)
        # Outputs are drawn before the txid exists, because the txid is a hash of them. The
        # entity index is the nonce: an endowment has no inputs, so nothing else separates two
        # entities that happen to draw one output of the same size to the same script type.
        drawn: list[tuple[str, str, int]] = []
        for _ in range(rng.randint(low, high)):
            address, kind = entity.receive_address(rng, pop.factory)
            sats = _draw_sats(rng, spec.value_mu + chain.endow_mu_offset, chain.endow_sigma, 1)
            drawn.append((address, kind, sats))
        txid = ledger.txid_for((), drawn, nonce=f"endowment:{index}")
        for vout, (address, kind, sats) in enumerate(drawn):
            book.create(
                (txid, vout),
                Utxo(
                    address=address,
                    kind=kind,
                    sats=sats,
                    height=height,
                    owner=index,
                    coinbase=False,
                ),
            )
            seeds.append(Seed(txid, vout, address, kind, sats, height))
    return seeds


def _select(
    cfg: Config,
    cands: list[tuple[Outpoint, Utxo]],
    need: int,
    min_inputs: int,
    out_kinds: list[str],
    fee_rate: int,
) -> list[tuple[Outpoint, Utxo]] | None:
    """Choose inputs covering `need` plus the fee the choice itself implies, or None.

    The fee depends on the number of inputs and the fee depends on the selection, so the two
    are resolved together: after each candidate the fee is recomputed for the selection as it
    now stands, including the change output, whose script type is the first input's by policy.

    One input is preferred when the caller asks for one, and the smallest coin that covers the
    payment on its own is taken, which is the best-fit rule most wallets ship. When the caller
    wants a multi-input spend, or when no single coin is large enough, small coins are
    accumulated instead, which is what consolidation looks like on a real chain.
    """
    ordered = sorted(cands, key=lambda kv: kv[1].sats)
    if min_inputs == 1:
        for item in ordered:
            kind = item[1].kind
            if item[1].sats >= need + fee_rate * _vsize(cfg, [kind], [*out_kinds, kind]):
                return [item]
    chosen: list[tuple[Outpoint, Utxo]] = []
    total = 0
    for item in ordered:
        chosen.append(item)
        total += item[1].sats
        if len(chosen) < max(2, min_inputs):
            continue
        kinds = [utxo.kind for _, utxo in chosen]
        if total >= need + fee_rate * _vsize(cfg, kinds, [*out_kinds, kinds[0]]):
            return chosen
    return None


def _cosigner(
    cfg: Config,
    pop: Population,
    book: Ledger,
    rng: random.Random,
    height: int,
    avoid: int,
    fee_rate: int,
) -> tuple[Outpoint, Utxo, str, str, int] | None:
    """A second entity's input plus the output paying it back, or None if nobody can join.

    This is the case that makes common-input-ownership wrong. The joiner brings one coin and
    takes back its value less the vsize its own input and output add, so it pays its own way
    and the transaction still balances without the initiator subsidising it.
    """
    chain = cfg.chain
    for _ in range(chain.max_pick_attempts):
        other = pop.receivers.pick(rng)
        if other == avoid:
            continue
        held = book.spendable(other, height, chain.coin_select_window)
        if not held:
            continue
        outpoint, utxo = min(held, key=lambda kv: kv[1].sats)
        address, kind = pop.entities[other].receive_address(rng, pop.factory)
        # Costed against the output type actually minted above, not the input's type. The two
        # differ often enough, and the difference is what would otherwise make the initiator's
        # change absorb the joiner's fee and break the exactness the fee arithmetic relies on.
        cost = fee_rate * (chain.input_vb[utxo.kind] + chain.output_vb[kind])
        refund = utxo.sats - cost
        if refund < chain.dust_threshold_sats:
            continue
        return outpoint, utxo, address, kind, refund
    return None


@dataclass(frozen=True, slots=True)
class Intent:
    """What one campaign move wants from one transaction. None means "use the type's policy".

    A move describes its shape and lets `payment` build it against the live ledger, rather than
    writing a transaction of its own. That is the difference between an agent and an injected
    pattern: a peel that cannot be funded does not happen, and the campaign has to react.
    """

    to: int | None = None
    outputs: tuple[int, int] | None = None
    equal: bool | None = None
    sats: int | None = None
    min_inputs: int | None = None


_NO_INTENT = Intent()


def payment(
    cfg: Config,
    pop: Population,
    book: Ledger,
    rng: random.Random,
    *,
    sender_index: int,
    height: int,
    time_us: int,
    control: MultiInput,
    intent: Intent | None = None,
) -> Tx | None:
    """One spend by `sender_index`, or None when the sender cannot afford one.

    Returning None rather than shrinking the payment to fit is deliberate: the payment amount
    comes from the entity type's value distribution, and quietly clamping it to the balance
    would replace that distribution with a picture of who happens to be rich. A wallet that
    cannot cover a payment does not make it, and the caller tries a different sender.
    """
    chain = cfg.chain
    plan = _NO_INTENT if intent is None else intent
    sender = pop.entities[sender_index]
    spec = cfg.type_of(sender.entity_type)
    cands = book.spendable(sender_index, height, chain.coin_select_window)
    if not cands:
        return None

    low, high = spec.outputs if plan.outputs is None else plan.outputs
    n_pay = rng.randint(low, high)
    equal = spec.equal_outputs if plan.equal is None else plan.equal
    if plan.sats is not None:
        # A move naming an amount is moving one specific pot on, so the pot is divided rather
        # than redrawn: a peel that redrew its value would not be peeling anything.
        each, extra = divmod(plan.sats, n_pay)
        amounts = [each + (1 if index < extra else 0) for index in range(n_pay)]
        if amounts[-1] < chain.min_payment_sats:
            return None
    elif equal:
        # A mixer's outputs are equal by design, which is what defeats amount matching.
        each = _draw_sats(rng, spec.value_mu, spec.value_sigma, chain.min_payment_sats)
        amounts = [each] * n_pay
    else:
        amounts = [
            _draw_sats(rng, spec.value_mu, spec.value_sigma, chain.min_payment_sats)
            for _ in range(n_pay)
        ]
    # Drawn either way so an intent cannot shift the draw sequence of the traffic around it.
    rounding = rng.random() < chain.round_payment_rate
    if rounding and plan.sats is None:
        amounts[0] = max(chain.round_to_sats, amounts[0] - amounts[0] % chain.round_to_sats)

    addresses: list[str] = []
    kinds: list[str] = []
    owners: list[int] = []
    for _ in range(n_pay):
        who = pop.receivers.pick(rng) if plan.to is None else plan.to
        address, kind = pop.entities[who].receive_address(rng, pop.factory)
        addresses.append(address)
        kinds.append(kind)
        owners.append(who)

    fee_rate = _fee_rate(cfg, rng)
    want_multi = rng.random() < control.p()
    min_inputs = (2 if want_multi else 1) if plan.min_inputs is None else plan.min_inputs
    chosen = _select(cfg, cands, sum(amounts), min_inputs, kinds, fee_rate)
    if chosen is None and min_inputs > 1:
        chosen = _select(cfg, cands, sum(amounts), 1, kinds, fee_rate)
    if chosen is None:
        return None

    violations: list[str] = []
    if rng.random() < chain.collaborative_multi_input_rate:
        joined = _cosigner(cfg, pop, book, rng, height, sender_index, fee_rate)
        if joined is not None:
            outpoint, utxo, address, kind, refund = joined
            chosen.append((outpoint, utxo))
            amounts.append(refund)
            addresses.append(address)
            kinds.append(kind)
            owners.append(utxo.owner)
            violations.append("common_input_ownership")

    in_kinds = [utxo.kind for _, utxo in chosen]
    total_in = sum(utxo.sats for _, utxo in chosen)
    paid = sum(amounts)
    change_kind = in_kinds[0]
    fee = fee_rate * _vsize(cfg, in_kinds, [*kinds, change_kind])
    change = total_in - paid - fee
    change_index = -1
    if change >= chain.dust_threshold_sats:
        address, reused = sender.change_address(rng, pop.factory, change_kind)
        change_index = len(amounts)
        amounts.append(change)
        addresses.append(address)
        kinds.append(change_kind)
        owners.append(sender_index)
        if reused:
            violations.append("change_address_reuse")
    else:
        # The remainder is not worth an output, so it goes to the miner instead. Handing over
        # the whole remainder rather than the estimated fee is what keeps the identity
        # inputs == outputs + fee exact once the change output disappears.
        fee = total_in - paid
    if sender_index in owners[:n_pay]:
        violations.append("self_payment")

    order = list(range(len(amounts)))
    rng.shuffle(order)
    if change_index >= 0:
        change_index = order.index(change_index)
    amounts = [amounts[i] for i in order]
    addresses = [addresses[i] for i in order]
    kinds = [kinds[i] for i in order]
    owners = [owners[i] for i in order]

    for outpoint, _ in chosen:
        book.spend(outpoint)
    # The txid is derived here rather than handed in, because it is a hash of exactly these
    # inputs and outputs and they are only final now. No nonce: an outpoint can be spent once,
    # so the input set already separates this transaction from every other one in the run.
    inputs = tuple(outpoint for outpoint, _ in chosen)
    txid = ledger.txid_for(inputs, list(zip(addresses, kinds, amounts, strict=True)))
    for vout, sats in enumerate(amounts):
        book.create(
            (txid, vout),
            Utxo(
                address=addresses[vout],
                kind=kinds[vout],
                sats=sats,
                height=height,
                owner=owners[vout],
                coinbase=False,
            ),
        )

    control.observe(len(chosen))
    return Tx(
        txid=txid,
        height=height,
        time_us=time_us,
        is_coinbase=False,
        inputs=inputs,
        input_addresses=tuple(utxo.address for _, utxo in chosen),
        input_sats=tuple(utxo.sats for _, utxo in chosen),
        output_addresses=tuple(addresses),
        output_sats=tuple(amounts),
        output_kinds=tuple(kinds),
        fee_sats=fee,
        fee_rate=fee_rate,
        vsize_vb=_vsize(cfg, in_kinds, kinds),
        sender=sender_index,
        input_owners=tuple(utxo.owner for _, utxo in chosen),
        change_index=change_index,
        violations=tuple(violations),
    )


def _coinbase(
    cfg: Config,
    pop: Population,
    book: Ledger,
    rng: random.Random,
    *,
    height: int,
    time_us: int,
    fees: int,
) -> Tx:
    """The block reward, paid to one pool chosen in proportion to its hashrate."""
    pool = pop.hashrate.pick(rng)
    address, kind = pop.entities[pool].payout_address(rng, pop.factory)
    sats = cfg.chain.coinbase_subsidy_sats + fees
    # BIP34 puts the block height in the coinbase, and this is why: a coinbase has no inputs,
    # so without the height two blocks paying the same pool the same subsidy would serialise
    # identically and share a txid.
    txid = ledger.txid_for((), [(address, kind, sats)], nonce=f"height:{height}")
    book.create(
        (txid, 0),
        Utxo(address=address, kind=kind, sats=sats, height=height, owner=pool, coinbase=True),
    )
    return Tx(
        txid=txid,
        height=height,
        time_us=time_us,
        is_coinbase=True,
        inputs=(),
        input_addresses=(),
        input_sats=(),
        output_addresses=(address,),
        output_sats=(sats,),
        output_kinds=(kind,),
        fee_sats=0,
        fee_rate=0,
        vsize_vb=_vsize(cfg, [], [kind]),
        sender=pool,
        input_owners=(),
        change_index=-1,
        violations=(),
    )


@dataclass(frozen=True, slots=True)
class Block:
    height: int
    time_us: int
    n_txs: int
    coinbase_txid: str
    subsidy_sats: int
    fees_sats: int


@dataclass(frozen=True, slots=True)
class Run:
    """Everything one run produced. `writers` decides which halves are observable."""

    population: Population
    seeds: tuple[Seed, ...]
    blocks: tuple[Block, ...]
    txs: tuple[Tx, ...]
    counters: Counters
    multi_input_rate: float


def _quota(n_txs: int, n_blocks: int) -> list[int]:
    """Spread the requested payment count over the blocks, remainder to the earliest blocks."""
    base, extra = divmod(n_txs, n_blocks)
    return [base + 1 if index < extra else base for index in range(n_blocks)]


@dataclass(frozen=True, slots=True)
class Context:
    """One block, handed to an actor so it can spend inside the run rather than beside it.

    `generate` owns the ledger, the clock and the txid counter, so an actor is given them
    instead of building a chain of its own. A campaign transaction therefore competes for the
    same coins as ordinary traffic and lands in the same block, which is what stops the
    adversary's output from being separable by anything other than its behaviour.
    """

    cfg: Config
    pop: Population
    book: Ledger
    rng: random.Random
    control: MultiInput
    counters: Counters
    height: int
    time_us: int


# Called once per block, after ordinary traffic. Returns the transactions it managed to build,
# which may be none: an actor that could not fund a move has not moved.
Actor = Callable[[Context], list[Tx]]

# Handed the population once it exists and asked for the per-block hook. A factory rather than a
# ready-made actor because the population is built inside `generate` from the run's one random
# stream: an actor built beforehand would have to be given a population that does not exist yet.
ActorPlan = Callable[[Population], Actor]


def generate(cfg: Config, rng: random.Random, plan: ActorPlan | None = None) -> Run:
    """Build the whole chain. Deterministic given `rng`, which is the only source of randomness.

    `cfg.n_txs` counts payments, not rows: each block also carries a coinbase, and the pools fan
    out a payout every `pool_payout_interval_blocks`, so the transaction file holds more rows
    than were asked for. The requested count is what section 10's `counts.in` records, against
    which the payments actually built and the attempts dropped have to add up.

    The `plan` argument is the adversary's way in. Its transactions compete for the same coins,
    land in the same blocks and are counted in the same totals as ordinary traffic, which is what
    stops them from being separable by anything except how they behave.
    """
    chain = cfg.chain
    pop = entities.build(cfg, rng)
    actor = None if plan is None else plan(pop)
    book = Ledger(maturity_blocks=chain.coinbase_maturity_blocks)
    seeds = endow(cfg, pop, book, rng)
    control = MultiInput(target=chain.multi_input_rate, gain=chain.multi_input_controller_gain)
    counters = Counters()
    quota = _quota(cfg.n_txs, cfg.n_blocks)
    txs: list[Tx] = []
    blocks: list[Block] = []

    for index, time_us in enumerate(
        ledger.block_times(rng, chain.genesis_us, chain.block_interval_s, cfg.n_blocks)
    ):
        height = chain.start_height + index
        senders = pop.senders_by_hour[entities.hour_of(time_us)]
        found: list[Tx] = []

        if index % chain.pool_payout_interval_blocks == 0:
            # A pool pays its miners on a cadence, which is the regular, many-output spend the
            # payout-cadence detector in S03 is meant to find. Failures are silent: a pool with
            # nothing matured yet simply does not pay this round.
            for pool in pop.pools:
                payout = payment(
                    cfg,
                    pop,
                    book,
                    rng,
                    sender_index=pool,
                    height=height,
                    time_us=time_us,
                    control=control,
                    intent=Intent(outputs=chain.pool_payout_outputs),
                )
                if payout is not None:
                    found.append(payout)

        for _ in range(quota[index]):
            counters.attempts += 1
            built: Tx | None = None
            # A sender picked by schedule may hold nothing spendable at this height. Trying
            # another sender keeps the requested volume; giving up after a bounded number of
            # tries keeps a drained ledger from turning into an unbounded loop.
            for _ in range(chain.max_pick_attempts):
                built = payment(
                    cfg,
                    pop,
                    book,
                    rng,
                    sender_index=senders.pick(rng),
                    height=height,
                    time_us=time_us,
                    control=control,
                )
                if built is not None:
                    break
            if built is None:
                counters.drop("sender_could_not_fund_a_payment")
                continue
            counters.built += 1
            found.append(built)

        if actor is not None:
            found.extend(
                actor(
                    Context(
                        cfg=cfg,
                        pop=pop,
                        book=book,
                        rng=rng,
                        control=control,
                        counters=counters,
                        height=height,
                        time_us=time_us,
                    )
                )
            )

        fees = sum(tx.fee_sats for tx in found)
        coinbase = _coinbase(
            cfg,
            pop,
            book,
            rng,
            height=height,
            time_us=time_us,
            fees=fees,
        )
        txs.append(coinbase)
        txs.extend(found)
        blocks.append(
            Block(
                height=height,
                time_us=time_us,
                n_txs=1 + len(found),
                coinbase_txid=coinbase.txid,
                subsidy_sats=chain.coinbase_subsidy_sats,
                fees_sats=fees,
            )
        )

    return Run(
        population=pop,
        seeds=tuple(seeds),
        blocks=tuple(blocks),
        txs=tuple(txs),
        counters=counters,
        multi_input_rate=control.multi / control.total if control.total else 0.0,
    )
