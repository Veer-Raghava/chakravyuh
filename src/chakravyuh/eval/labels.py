"""The audited doors labels reach a model through. Law 2 rule 3, as code.

Nothing outside `chakravyuh.eval` may read or construct a label. These functions are how a stage
that needs one asks for it, and every property that makes the resulting number honest is enforced
on this side of the door rather than trusted to the caller:

  one family per door   `origin_labels` returns which peer actually broadcast a transaction, for
                        SHASTRA. `wallet_labels` returns who owns an address and whether they are
                        illicit, for BUDDHI. Neither can return the other's labels, so a stage
                        cannot reach a label family its brief does not entitle it to by passing a
                        different argument.
  training window only  Both filter on the split boundary before returning anything. The caller
                        does not pass the boundary in: it is derived here, from the observable
                        capture's own time span, so a stage cannot widen its training window by
                        claiming the capture is longer than it is.
  no path arguments     A run id, exactly as `metrics.py` and `validate.py` take one. The answer
                        key's location is derived from it and cannot be pointed elsewhere.
  numbers out, or rows  A door returns labels, which is the point. What it never returns is the
                        holdout: `n_withheld` says how many rows the boundary removed, so a caller
                        can tell "the window is empty" from "the answer key is missing", and that
                        count is the only thing it learns about the far side.

Returning None rather than raising when the answer key is absent, for Law 2 rule 6: inference must
complete with `ground_truth/` moved away. A stage that asked for labels it cannot have should warn
and fall back to an unsupervised path, not die.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from chakravyuh.eval.split import boundary_us
from chakravyuh.mayajaal.writers import RUN_ID

GENERATED_ROOT = Path("data") / "generated"
GROUND_TRUTH_ROOT = Path("ground_truth")


@dataclass(frozen=True)
class OriginLabels:
    """Which peer really broadcast each transaction, for the transactions a model may train on.

    `frame` is two columns, `txid` and `origin_peer_ip`, one row per transaction. Not one row per
    announcement: a caller joining this onto its candidate table gets the label attached to every
    candidate row of that transaction, which is what a per-candidate binary target needs.
    """

    boundary_us: int
    train_fraction: float
    frame: pl.DataFrame
    n_labelled: int
    n_withheld: int


@dataclass(frozen=True)
class WalletLabels:
    """Who owns each address, for the addresses a model may train on.

    Cluster-keyed rather than address-keyed in the sense that matters to BUDDHI: `owner_id` is the
    true entity, so a caller can ask whether its predicted cluster agrees with the true one, and
    `is_illicit` is the risk target. Addresses are the join key because that is the only entity
    identifier the observable tree contains.
    """

    boundary_us: int
    train_fraction: float
    frame: pl.DataFrame
    n_labelled: int
    n_withheld: int


def _roots(run_id: str) -> tuple[Path, Path]:
    """The observable and truth trees for `run_id`, validated. Never a path from the caller."""
    if not RUN_ID.match(run_id):
        raise ValueError(f"run_id must match {RUN_ID.pattern}, got {run_id!r}")
    return GENERATED_ROOT / run_id, GROUND_TRUTH_ROOT / run_id


def _boundary(observable: Path, train_fraction: float) -> tuple[int, pl.DataFrame]:
    """The split boundary and the per-transaction first-observed time it was derived from.

    Both come from `normalised/announcements.parquet`, which is observable. The span is over every
    announcement rather than over the transactions being labelled, so the boundary is a property of
    the capture and does not move when a caller labels a subset of it.

    The returned frame is `txid` and `first_seen_us`, and it is what both doors filter on. Filtering
    on the earliest time an *observer* saw a transaction, rather than on the truth column recording
    when it was really broadcast, is the stricter of the two: a transaction is always broadcast at
    or before it is seen, so anything this admits was broadcast inside the window too. It also makes
    the door agree row for row with a caller that masked its own features on `seen_us`, which is the
    only way a parity check between the two can mean anything.
    """
    announcements = pl.read_parquet(
        observable / "normalised" / "announcements.parquet", columns=["txid", "seen_us"]
    )
    if announcements.is_empty():
        raise ValueError(f"{observable}: no announcements, so there is no span to split")
    first = int(announcements["seen_us"].min())  # type: ignore[arg-type]
    last = int(announcements["seen_us"].max())  # type: ignore[arg-type]
    seen = announcements.group_by("txid").agg(pl.col("seen_us").min().alias("first_seen_us"))
    return boundary_us(first, last, train_fraction), seen


def origin_labels(run_id: str, train_fraction: float) -> OriginLabels | None:
    """SHASTRA's door. `(txid, origin_peer_ip)` for training-window transactions only.

    `train_fraction` comes from `run_config.json`'s `eval.train_fraction` and is a share of the
    capture's observed time span, never a timestamp. Returns None when the answer key is absent.

    Transactions no observer ever saw are absent from the returned frame whatever their true
    broadcast time, because they have no observed time to place on either side of the boundary and
    no candidate row for a label to attach to. They are still in the denominator every accuracy in
    `metrics.py` divides by, which is where that shortfall belongs.
    """
    observable, truth = _roots(run_id)
    key = truth / "origins.parquet"
    if not key.is_file():
        return None

    boundary, seen = _boundary(observable, train_fraction)
    origins = pl.read_parquet(key, columns=["txid", "true_origin_ip"])
    joined = origins.join(seen, on="txid", how="inner")
    train = (
        joined.filter(pl.col("first_seen_us") < boundary)
        .select("txid", pl.col("true_origin_ip").alias("origin_peer_ip"))
        .sort("txid")
    )
    return OriginLabels(
        boundary_us=boundary,
        train_fraction=train_fraction,
        frame=train,
        n_labelled=train.height,
        n_withheld=joined.height - train.height,
    )


def wallet_labels(run_id: str, train_fraction: float) -> WalletLabels | None:
    """BUDDHI's door. `(address, owner_id, is_illicit, typologies)` for training-window addresses.

    Exploded from the answer key's per-entity address lists so the frame joins straight onto an
    observable address table, and filtered to addresses first seen before the boundary. An entity
    can therefore appear on both sides of the split, with its early addresses labelled and its late
    ones withheld, which is the honest shape: an investigator learns about a wallet over time and
    does not learn about it retroactively.
    """
    observable, truth = _roots(run_id)
    key = truth / "entities.parquet"
    if not key.is_file():
        return None

    boundary, _ = _boundary(observable, train_fraction)
    addresses = pl.read_parquet(
        observable / "normalised" / "addresses.parquet", columns=["address", "first_seen_us"]
    )
    owned = (
        pl.read_parquet(key, columns=["entity_id", "is_illicit", "typologies", "addresses"])
        .explode("addresses")
        .rename({"addresses": "address", "entity_id": "owner_id"})
        .drop_nulls("address")
    )
    joined = owned.join(addresses, on="address", how="inner")
    train = (
        joined.filter(pl.col("first_seen_us") < boundary)
        .select("address", "owner_id", "is_illicit", "typologies")
        .sort("address")
    )
    return WalletLabels(
        boundary_us=boundary,
        train_fraction=train_fraction,
        frame=train,
        n_labelled=train.height,
        n_withheld=joined.height - train.height,
    )
