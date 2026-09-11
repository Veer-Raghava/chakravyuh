"""MAYAJAAL-SPEC Layer 4: laundering campaigns as agents rather than stamped shapes.

A campaign is a small agent with a disposition, a coin and a current holder. Each block it may
pick one move, weighted by its own risk appetite, and ask the chain layer to build that move
against the live ledger. The move is a request and not a guarantee: a peel whose holder cannot
fund it does not happen, and the campaign carries on from wherever it actually got to.

That is why the typology is derived at the end rather than chosen at the start. A campaign is
named after the moves that actually produced transactions, so `campaigns.parquet` describes what
happened, and `entities.typologies` names only entities a campaign really routed value through.
A label with no transaction behind it would be unscoreable, which is exactly what S01 refused to
write.

The moves split into two families, and the difference is where the coin ends up. `peel` and
`structure` send a slice onward and keep the remainder as change, so the holder does not move:
that trailing change output is what a peel chain is recognised by. `hop`, `split`, `mix` and
`merge` send the pot on, so the holder becomes the recipient. `dwell` produces no transaction at
all, and `cash_out` ends the campaign at an exchange.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from chakravyuh.mayajaal import chain, weighted
from chakravyuh.mayajaal.chain import Actor, Context, Intent, Tx
from chakravyuh.mayajaal.config import Config
from chakravyuh.mayajaal.entities import Population
from chakravyuh.mayajaal.weighted import WeightedIndex

# Each move that names a typology maps to one string in the frozen vocabulary of
# docs/DATA-CONTRACTS.md section 2. `merge`, `dwell` and `cash_out` name none of them: they
# happen inside every typology, so counting them would make every campaign look alike.
# `rapid_hop` is deliberately absent. It is in section 5's detector vocabulary, not section 2's
# label vocabulary, so it is something S03 may claim and not something truth may assert.
TYPOLOGY_OF: dict[str, str] = {
    "peel": "peel_chain",
    "structure": "structuring",
    "split": "fan_out",
    "mix": "coinjoin_like",
    "hop": "pass_through",
}
_ORDER = {move: index for index, move in enumerate(TYPOLOGY_OF)}
FALLBACK_TYPOLOGY = "pass_through"

# Moves that hand the pot to the recipient. The rest keep it.
_FORWARDS = frozenset({"hop", "split", "mix", "merge"})

# One fiftieth of the pot is left behind to cover the fee. Whatever the fee does not take
# becomes a change output, which is the residue a peel chain is followed by. Too small a
# reserve and coin selection cannot cover the fee and the move silently fails; too large and
# the campaign leaks value at every hop.
HEADROOM = 50

# The types that generate criminal proceeds, as opposed to the types that move them on. A
# campaign starts at one of these because a laundering campaign starts with something to launder.
SOURCE_TYPES = frozenset({"darknet_market", "ransomware", "scam"})
RECRUITS = (2, 5)


def _spare(amount: int, dust: int) -> int:
    """`amount` less the fee reserve: what a move may actually ask to send."""
    return amount - max(dust, amount // HEADROOM)


def _largest(ctx: Context, who: int) -> int:
    """The biggest single coin `who` can spend now, which is the coin a campaign is moving.

    One coin rather than the balance, because a campaign follows a pot. Naming an amount that
    needed every coin the holder had would turn every ordinary move into a consolidation and
    make `merge` indistinguishable from the rest.
    """
    held = ctx.book.spendable(who, ctx.height, ctx.cfg.chain.coin_select_window)
    return max((utxo.sats for _, utxo in held), default=0)


def _balance(ctx: Context, who: int) -> int:
    """Everything `who` can spend now. Only `merge` wants this."""
    held = ctx.book.spendable(who, ctx.height, ctx.cfg.chain.coin_select_window)
    return sum(utxo.sats for _, utxo in held)


def _weights(cfg: Config, appetite: float) -> WeightedIndex[str]:
    """Each move's weight interpolated between its cautious and hurried endpoints.

    The move mix is therefore a consequence of the agent's disposition. Two campaigns with the
    same appetite still diverge, because what they can afford differs.
    """
    return weighted.build(
        (move, low + (high - low) * appetite)
        for move, (low, high) in cfg.adversary.move_weights.items()
    )


@dataclass(slots=True)
class Campaign:
    """One agent. Everything after `wait` is the record of what it did, not what it meant to."""

    campaign_id: str
    appetite: float
    moves: WeightedIndex[str]
    budget_moves: int
    start_block: int
    holder: int
    wait: int = 0
    done: bool = False
    # A dict used as an ordered set. Nothing here may iterate a `set`: its order depends on
    # PYTHONHASHSEED and the determinism gate runs two separate interpreters.
    participants: dict[int, None] = field(default_factory=dict)
    ran: dict[str, int] = field(default_factory=dict)
    txids: list[str] = field(default_factory=list)
    start_us: int = 0
    end_us: int = 0
    total_sats: int = 0

    def typology(self) -> str:
        """What this campaign did: its most frequent move that names a typology.

        Ties break on the vocabulary's own order rather than on the order moves happened to be
        counted in, so the label is a function of the campaign's behaviour alone.
        """
        counted = [(n, -_ORDER[m], m) for m, n in self.ran.items() if m in TYPOLOGY_OF]
        if not counted:
            return FALLBACK_TYPOLOGY
        return TYPOLOGY_OF[max(counted)[2]]


@dataclass(slots=True)
class Adversary:
    """Every campaign in the run, and the one method `chain.generate` calls per block.

    Built before the run and planned once the population exists, because the population is
    created inside `generate` from the same generator: planning against a population built
    a second time would either need `entities.build` to run twice or divert the run's only
    random stream, and either one breaks reproducibility from the seed alone.
    """

    cfg: Config
    rng: random.Random
    pop: Population | None = None
    # The world's illicit transaction share, as a hard ceiling on transactions built here. The
    # per-campaign move budget shapes each campaign; this keeps the sum of them honest.
    budget: int = 0
    pending: list[Campaign] = field(default_factory=list)
    live: list[Campaign] = field(default_factory=list)
    finished: list[Campaign] = field(default_factory=list)
    mules: tuple[int, ...] = ()
    mixers: tuple[int, ...] = ()

    def plan(self, pop: Population) -> Actor:
        """Sample the campaigns and return the per-block hook. Called once, by `generate`."""
        if self.pop is not None:
            raise RuntimeError("adversary already planned: a second plan would reuse the stream")
        self.pop = pop
        by_type: dict[str, list[int]] = {}
        for index in pop.illicit:
            by_type.setdefault(pop.entities[index].entity_type, []).append(index)
        sources = [i for name in sorted(SOURCE_TYPES) for i in by_type.get(name, [])]
        self.mules = tuple(by_type.get("mule", ())) or pop.illicit
        self.mixers = tuple(by_type.get("mixer", ())) or self.mules
        self.budget = round(self.cfg.world.illicit_tx_share * self.cfg.n_txs)
        self.pending = self._campaigns(sources)
        return self.act

    def _campaigns(self, sources: list[int]) -> list[Campaign]:
        """Plan as many campaigns as the illicit transaction budget pays for.

        `n_campaigns` is a ceiling rather than a count. The binding constraint is the world's
        illicit share: a campaign costs a transaction per move, so asking for a hundred and
        twenty of them on a run whose whole illicit budget is a dozen transactions would either
        overrun that share or truncate every campaign into a stub. Divided by the mean campaign
        length, the budget says how many campaigns can actually finish.
        """
        adv = self.cfg.adversary
        low, high = adv.moves_per_campaign
        mean_moves = max(1, (low + high) // 2)
        want = min(adv.n_campaigns, self.budget // mean_moves)
        if not sources or want < 1:
            return []
        # Starts are spread over the first three quarters of the run so a campaign planned near
        # the end still has blocks left to move in, and so campaigns overlap: a run in which
        # only one campaign is ever live would let a downstream model separate them by time.
        horizon = max(1, self.cfg.n_blocks * 3 // 4)
        out: list[Campaign] = []
        for index in range(want):
            appetite = self.rng.random()
            holder = self.rng.choice(sources)
            campaign = Campaign(
                campaign_id=f"camp-{index:04d}",
                appetite=appetite,
                moves=_weights(self.cfg, appetite),
                budget_moves=self.rng.randint(low, high),
                start_block=self.rng.randrange(horizon),
                holder=holder,
            )
            campaign.participants[holder] = None
            out.append(campaign)
        # Latest first, so activating the earliest is a pop from the end.
        out.sort(key=lambda c: (-c.start_block, c.campaign_id))
        return out

    def act(self, ctx: Context) -> list[Tx]:
        """One block. Every live campaign gets one chance to move, in start order."""
        index = ctx.height - self.cfg.chain.start_height
        while self.pending and self.pending[-1].start_block <= index:
            self.live.append(self.pending.pop())
        built: list[Tx] = []
        for campaign in self.live:
            if self.budget <= 0:
                break
            tx = self._step(campaign, ctx)
            if tx is not None:
                built.append(tx)
                self.budget -= 1
        still: list[Campaign] = []
        for campaign in self.live:
            (still if not campaign.done else self.finished).append(campaign)
        self.live = still
        return built

    def _step(self, campaign: Campaign, ctx: Context) -> Tx | None:
        if campaign.wait > 0:
            campaign.wait -= 1
            return None
        if len(campaign.txids) >= campaign.budget_moves:
            campaign.done = True
            return None
        adv = self.cfg.adversary
        move = campaign.moves.pick(ctx.rng)
        campaign.wait = ctx.rng.randint(*adv.move_gap_blocks) - 1
        if move == "dwell":
            # Sitting still is a move. A campaign that waits out a monitoring window leaves a
            # gap in the graph, and the gap is a feature S03 measures rather than an absence.
            campaign.wait = ctx.rng.randint(*adv.dwell_blocks)
            campaign.ran["dwell"] = campaign.ran.get("dwell", 0) + 1
            return None
        plan = self._intent(campaign, ctx, move)
        if plan is None:
            return None
        intent, sats = plan
        tx = chain.payment(
            ctx.cfg,
            ctx.pop,
            ctx.book,
            ctx.rng,
            sender_index=campaign.holder,
            height=ctx.height,
            time_us=ctx.time_us,
            control=ctx.control,
            intent=intent,
        )
        if tx is None:
            return None
        self._record(campaign, move, tx, sats, intent.to)
        return tx

    def _record(self, campaign: Campaign, move: str, tx: Tx, sats: int, target: int | None) -> None:
        campaign.ran[move] = campaign.ran.get(move, 0) + 1
        campaign.txids.append(tx.txid)
        # Counted once per hop, which is what volume means on a transaction graph: the same coin
        # moved twice is two transfers. Change returning to the holder is not counted.
        campaign.total_sats += sats
        if not campaign.start_us:
            campaign.start_us = tx.time_us
        campaign.end_us = tx.time_us
        if move == "cash_out":
            # The exchange is where the money lands, not a participant in moving it. Labelling
            # it would put a laundering typology on a victim service, and section 5 exempts
            # exchanges from scoring precisely because they receive what they did not send.
            campaign.done = True
            return
        if target is not None:
            campaign.participants[target] = None
            if move in _FORWARDS:
                campaign.holder = target

    def _intent(self, campaign: Campaign, ctx: Context, move: str) -> tuple[Intent, int] | None:
        """The transaction this move wants, and the sats it moves, or None if it is unaffordable.

        Returning None is the agent reacting to its own balance. Nothing here shrinks a move to
        fit: a campaign that cannot peel this block tries again next block, possibly with a
        different move, which is why the realised move mix is never exactly the configured one.
        """
        adv = self.cfg.adversary
        dust = self.cfg.chain.dust_threshold_sats
        floor = self.cfg.chain.min_payment_sats
        rng = ctx.rng
        pot = _spare(_largest(ctx, campaign.holder), dust)
        if pot < floor:
            return None
        if move == "peel":
            sats = int(pot * rng.uniform(*adv.peel_share))
            target = rng.choice(self.mules)
        elif move == "structure":
            limit = adv.structuring_threshold_sats
            # Just under the reporting threshold, jittered, because a run of identical
            # amounts would be a signature no structurer would leave.
            sats = limit - rng.randrange(max(1, limit // 20))
            target = rng.choice(self.mules)
        elif move == "split":
            sats, target = pot, rng.choice(self.mules)
            return Intent(to=target, outputs=adv.split_outputs, sats=sats), sats
        elif move == "mix":
            sats, target = pot, rng.choice(self.mixers)
            return Intent(to=target, outputs=adv.mix_outputs, equal=True, sats=sats), sats
        elif move == "merge":
            sats = _spare(_balance(ctx, campaign.holder), dust)
            target = rng.choice(self.mules)
            wanted = rng.randint(*adv.merge_inputs)
            return Intent(to=target, outputs=(1, 1), sats=sats, min_inputs=wanted), sats
        elif move == "cash_out":
            sats, target = pot, rng.choice(ctx.pop.exchanges)
        else:
            sats, target = pot, rng.choice(self.mules)
        if sats < floor or sats > pot:
            return None
        return Intent(to=target, outputs=(1, 1), sats=sats), sats

    def records(self) -> list[Campaign]:
        """The campaigns that actually built something, in campaign id order.

        A campaign that never funded a move is dropped rather than written with an empty txid
        list. It planned nothing that happened, and a row describing it would be a typology with
        no transaction behind it.
        """
        live = [c for c in (*self.finished, *self.live, *self.pending) if c.txids]
        return sorted(live, key=lambda c: c.campaign_id)

    def apply_typologies(self, pop: Population) -> None:
        """Label every entity a campaign routed value through, from the campaigns that ran.

        Sorted and de-duplicated, so an entity used by two campaigns of the same shape carries
        the label once and the parquet does not depend on the order campaigns finished in.
        """
        for campaign in self.records():
            name = campaign.typology()
            for index in campaign.participants:
                labels = pop.entities[index].typologies
                if name not in labels:
                    labels.append(name)
        for entity in pop.entities:
            entity.typologies.sort()
