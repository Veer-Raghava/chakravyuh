"""The mixer detector, and the set-aside that keeps ownership heuristics off a CoinJoin.

Equal-value outputs are the mark of a collaborative transaction: several unrelated parties signed
one transaction together, so its inputs belong to strangers and every ownership claim read off
those inputs is wrong by construction. SETU already flags the shape (`has_equal_outputs`). This
module turns that flag into a decision with a name, so "we did not apply common-input ownership
across this transaction" is a recorded act with a reason rather than a filter nobody wrote down.

A one-input transaction with equal outputs is not a mixer. It is one party splitting their own
coin, and their inputs and outputs do belong to one owner. That is why `n_in >= 2` is part of the
rule and not an optimisation: the plural inputs are what make the inputs strangers.

The output threshold is restated rather than imported from `shastra.typology`, because no stage
reads another stage's internals. It is the same number on purpose — three equal outputs is a
mixing round in both layers, so the two use one word for one shape. JAAL's rule is a strict subset
of SHASTRA's: the same output shape, plus the plural inputs. A run where the two disagree is a
split SHASTRA names `coinjoin_like` and this module refuses to.

Nothing here reads a label. A mixer is a shape in the capture, and this module can be wrong about
it, which is why the mark is a reason attached to a transaction and not a deletion.
"""

from __future__ import annotations

from typing import Final

import polars as pl

# Three or more outputs of one value. Two is a payments-plus-change coincidence; three is a round.
COINJOIN_MIN_OUTPUTS: Final[int] = 3
# Two or more inputs. The bar that separates a mixer from a split, per the module docstring.
MIXER_MIN_INPUTS: Final[int] = 2
# The reason recorded wherever a mixer is set aside. The contract's vocabulary for a set-aside is
# a reason string, and this is the one this stage writes.
SET_ASIDE_REASON: Final[str] = "coinjoin_mixer"


def is_mixer() -> pl.Expr:
    """A boolean expression over `normalised/transactions.parquet`'s own columns.

    An expression rather than a predicate over a frame, so the two heuristics in `cluster.py` and
    the node flag in `stage.py` all ask the same question of the same columns and cannot drift.
    """
    return (
        pl.col("has_equal_outputs")
        & (pl.col("n_out") >= COINJOIN_MIN_OUTPUTS)
        & (pl.col("n_in") >= MIXER_MIN_INPUTS)
    )


def flags(transactions: pl.DataFrame) -> pl.DataFrame:
    """One row per transaction: its `txid` and whether it is a mixer.

    The grain is every transaction, not only the mixers, so a join onto the node table marks the
    non-mixers false rather than leaving them null. `null` and `false` are different claims and
    section 5 keeps them apart everywhere else.
    """
    return transactions.select("txid", is_mixer().alias("coinjoin"))
