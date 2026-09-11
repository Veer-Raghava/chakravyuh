"""The UTXO ledger: `(txid, vout) -> (address, sats, height)`, plus the block clock.

MAYAJAAL-SPEC Layer 2 asks for an actual ledger rather than a random graph with amounts
sprinkled on it, because half the cases the detectors need only exist in the accounting:
change outputs, multi-input spends, consolidation, dust. Value conservation is enforced by
the caller building transactions; this module enforces that a coin cannot be spent twice and
cannot be spent before it exists.

Two rules hold everywhere in here. All money is `int` satoshis, never a float. Nothing
iterates a `set`: the spendable index is a dict used as an ordered set, because set iteration
order depends on PYTHONHASHSEED and would make the same seed produce different bytes in a
different process.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from dataclasses import dataclass, field

Outpoint = tuple[str, int]


def txid_for(
    inputs: Sequence[Outpoint],
    outputs: Sequence[tuple[str, str, int]],
    *,
    nonce: str = "",
) -> str:
    """The transaction id, a SHA-256 over this transaction's own serialised contents.

    `outputs` is one `(address, script_type, sats)` triple per output, in the order they appear
    in the transaction. `inputs` is the outpoints being spent, in the order they are spent.

    A real txid is a hash of the serialised transaction, so a generated one has to be too. The
    previous version hashed the transaction's ordinal and then overwrote the last eight
    characters with zeros, which gave every txid in the run an identical tail. This project
    truncates identifiers to the first eight and last four characters everywhere it renders
    them, so a constant tail meant four of those twelve characters carried no information, and
    a shared tail across every identifier is the first thing a reader spots as synthetic.

    `nonce` exists for the two transaction kinds that have no inputs to be unique through. A
    coinbase passes its block height, which is what BIP34 requires of a real coinbase and is
    what separates two blocks that pay the same pool the same subsidy. An endowment passes its
    entity index. Everything else leaves it empty: an outpoint can be spent only once, so a
    transaction's input set already distinguishes it from every other transaction in the run.

    The domain separator and the NUL delimiters are what make the preimage unambiguous. NUL
    appears in no address, script type or txid, so no two different transactions can serialise
    to the same string. A genuine digest collision would surface immediately rather than
    silently, because `Ledger.create` refuses an outpoint it has already seen.
    """
    body = "\x00".join(
        [nonce]
        + [f"{txid}:{vout}" for txid, vout in inputs]
        + [f"{address}:{kind}:{sats}" for address, kind, sats in outputs]
    )
    return hashlib.sha256(f"chakravyuh-tx\x00{body}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Utxo:
    """One unspent output. `owner` and `kind` are ledger bookkeeping, never observable output."""

    address: str
    kind: str
    sats: int
    height: int
    owner: int
    coinbase: bool


@dataclass(slots=True)
class Ledger:
    """The live UTXO set, with a per-owner index so coin selection is not a full-set scan.

    `by_owner` maps an entity index to its unspent outpoints. The value type is `dict[..., None]`
    rather than `set`, purely for deterministic iteration order.
    """

    maturity_blocks: int
    utxos: dict[Outpoint, Utxo] = field(default_factory=dict)
    by_owner: dict[int, dict[Outpoint, None]] = field(default_factory=dict)

    def create(self, outpoint: Outpoint, utxo: Utxo) -> None:
        if outpoint in self.utxos:
            raise ValueError(f"outpoint {outpoint} created twice")
        self.utxos[outpoint] = utxo
        self.by_owner.setdefault(utxo.owner, {})[outpoint] = None

    def spend(self, outpoint: Outpoint) -> Utxo:
        """Remove and return the output. Raises if it does not exist or is already spent."""
        utxo = self.utxos.pop(outpoint, None)
        if utxo is None:
            raise ValueError(f"outpoint {outpoint} is not in the unspent set")
        del self.by_owner[utxo.owner][outpoint]
        return utxo

    def spendable(self, owner: int, height: int, window: int) -> list[tuple[Outpoint, Utxo]]:
        """The oldest `window` outputs of `owner` that may legally be spent in `height`.

        Oldest-first is FIFO, which is a coin-selection policy real wallets actually ship, and
        the window bounds the hot loop: an exchange holding tens of thousands of outputs must
        not cost a full scan per transaction. Coinbase outputs are withheld until they have
        `maturity_blocks` of confirmations, which is what gives the generated chain a coinbase
        maturity to respect rather than a rule stated in a docstring.
        """
        out: list[tuple[Outpoint, Utxo]] = []
        for outpoint in self.by_owner.get(owner, {}):
            utxo = self.utxos[outpoint]
            if utxo.height > height:
                continue
            if utxo.coinbase and height - utxo.height < self.maturity_blocks:
                continue
            out.append((outpoint, utxo))
            if len(out) == window:
                break
        return out


def block_times(rng: random.Random, genesis_us: int, interval_s: float, n: int) -> list[int]:
    """`n` block timestamps in microseconds, exponential inter-arrival with mean `interval_s`.

    Gaps are rounded to whole microseconds and accumulated as integers, so the timeline cannot
    drift the way a running float sum would, and a gap can never be zero: two blocks sharing a
    timestamp would make the announcement ordering in S02 ambiguous.
    """
    rate = 1.0 / interval_s
    times: list[int] = []
    now = genesis_us
    for _ in range(n):
        now += max(1, round(rng.expovariate(rate) * 1_000_000))
        times.append(now)
    return times
