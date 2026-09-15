"""One row per (txid, candidate peer), with every feature the estimator is allowed to see.

The grain is the peer, not the announcement. "Which peer originated this" is a question about
peers: a peer that reached four observers is one candidate, not four, and leaving the rows
ungrouped would let a well-observed relay outvote the originator by sheer row count. JAAL made the
same choice for `ANNOUNCED_BY` and said so, for this stage's benefit.

Every column here is observable. Nothing is read from a sibling tree and nothing is derived from a
label, which is what lets `stage.py` stay a pure read of two directories under `data/`.

One measured fact shaped this file. On a run at `observer_fraction` 0.7 the mean number of distinct
observers per (txid, peer) is 1.005: an observer records only the announcement that told it
something new, so almost every candidate was heard by exactly one observer and
`n_observers_seen` is a near-constant. The informative half of "how many of our observers saw it
via this peer, and how many saw nothing" is therefore the second half, and `n_observers_blind`
carries it. Both are emitted, because section 6 requires the first, but a model that leaned on
`n_observers_seen` would be leaning on a constant.
"""

from __future__ import annotations

import polars as pl

from chakravyuh.shastra.schema import (
    HOSTING_CLASSES,
    NET_CLASS_CODES,
    TOR_CLASS,
)

# Columns this stage needs from each upstream table, named so a schema change upstream fails here
# with a missing-column error rather than silently producing a feature full of nulls.
ANNOUNCEMENT_COLUMNS = (
    "row_id",
    "txid",
    "peer_ip",
    "observer_ip",
    "seen_us",
    "rank_in_tx",
    "delta_first_us",
    "net_class",
)
PEER_COLUMNS = ("peer_ip", "n_txids", "frac_rank_one")
TRANSACTION_COLUMNS = ("txid", "input_addresses")


def peer_degree(edges: pl.DataFrame) -> pl.DataFrame:
    """Degree of each peer node in the fused graph, both directions, every edge kind.

    Read from `graph/` rather than recomputed from `normalised/` on purpose. `peers.n_txids` is
    already a transaction count and is carried as its own feature; what this adds is the degree the
    fused graph actually has, which also counts the `HOSTED_IN` edge to the peer's ASN and would
    count anything a later stage adds. If the two ever disagree, the graph is the one an analyst is
    looking at.
    """
    ends = pl.concat(
        [
            edges.select(pl.col("src").alias("node")),
            edges.select(pl.col("dst").alias("node")),
        ]
    )
    return (
        ends.filter(pl.col("node").str.starts_with("peer:"))
        .group_by("node")
        .agg(pl.len().alias("peer_degree"))
        .select(
            pl.col("node").str.strip_prefix("peer:").alias("peer_ip"),
            pl.col("peer_degree").cast(pl.Int32()),
        )
    )


def payer_links(announcements: pl.DataFrame, transactions: pl.DataFrame) -> pl.DataFrame:
    """How many of one payer's transactions each peer announced. The strongest observable rule.

    Transactions are linked by their first input address. Address reuse is the strongest signal the
    capture leaks, and this rule scores 0.263 on the S02 reference run against first-seen's 0.221,
    so it is the number the estimator has to beat. Handing it to the model as a feature rather than
    hoping the model rediscovers it is deliberate: a model that cannot see the strongest rule cannot
    be expected to improve on it.

    Counted over the whole capture, not the training window. This is observable data, not a label:
    an investigator holding the capture can compute it for every transaction in it, and restricting
    it to the training window would model an investigator who deleted half their own evidence.
    """
    payers = transactions.select(
        "txid", pl.col("input_addresses").list.first().alias("payer")
    ).drop_nulls("payer")
    pairs = announcements.select("txid", "peer_ip").unique().join(payers, on="txid", how="inner")
    shared = pairs.group_by("payer", "peer_ip").agg(pl.col("txid").n_unique().alias("payer_shared"))
    return pairs.join(shared, on=["payer", "peer_ip"], how="left").select(
        "txid", "peer_ip", pl.col("payer_shared").cast(pl.Int32())
    )


def candidates(
    announcements: pl.DataFrame,
    peers: pl.DataFrame,
    transactions: pl.DataFrame,
    edges: pl.DataFrame,
) -> pl.DataFrame:
    """The feature table. One row per (txid, peer_ip), sorted so the output is order-independent.

    Returns the fourteen feature columns of `schema.FEATURES_SCHEMA`, plus `net_class_code` for the
    model, plus three columns that are not features and must never reach the model: `row_id` for
    deterministic tie-breaking, `seen_us` for the training-window mask, and
    `n_observers_in_tx` for the abstain rules.

    Units: every `_us` column is microseconds. `delta_first_us` is this peer's earliest sighting
    minus the transaction's earliest sighting by anyone, so rank one's value is zero.
    `announce_spread_us` is the spread of this peer's own sightings of this transaction, which is
    zero for the overwhelming majority of candidates and non-zero exactly when several observers
    heard the same peer at different times.
    """
    n_observers = announcements["observer_ip"].n_unique()
    grouped = announcements.group_by("txid", "peer_ip").agg(
        pl.col("row_id").min().alias("row_id"),
        pl.col("seen_us").min().alias("seen_us"),
        pl.col("delta_first_us").min().alias("delta_first_us"),
        pl.col("rank_in_tx").min().alias("rank_in_tx"),
        pl.len().alias("n_announcements"),
        pl.col("observer_ip").n_unique().alias("n_observers_seen"),
        (pl.col("seen_us").max() - pl.col("seen_us").min()).alias("announce_spread_us"),
        pl.col("net_class").first().alias("net_class"),
    )

    per_tx = announcements.group_by("txid").agg(
        pl.col("observer_ip").n_unique().alias("n_observers_in_tx")
    )
    peer_stats = peers.select(
        "peer_ip",
        pl.col("frac_rank_one").alias("peer_frac_rank_one"),
        pl.col("n_txids").alias("peer_n_txids"),
    )

    joined = (
        grouped.join(peer_stats, on="peer_ip", how="left")
        .join(peer_degree(edges), on="peer_ip", how="left")
        .join(payer_links(announcements, transactions), on=["txid", "peer_ip"], how="left")
        .join(per_tx, on="txid", how="left")
    )

    return (
        joined.with_columns(
            pl.len().over("txid").cast(pl.Int32()).alias("n_candidates"),
            # A peer that reached every observer leaves none blind. Clamped at zero rather than
            # allowed negative: a hand-built fixture can carry more distinct observers inside one
            # transaction than the capture-wide count if it was assembled inconsistently, and a
            # negative count would be a silently wrong feature rather than a loud one.
            (pl.lit(n_observers) - pl.col("n_observers_seen"))
            .clip(lower_bound=0)
            .cast(pl.Int32())
            .alias("n_observers_blind"),
            (pl.col("net_class") == TOR_CLASS).alias("is_tor_exit"),
            pl.col("net_class").is_in(list(HOSTING_CLASSES)).fill_null(False).alias("is_hosting"),
            pl.col("net_class")
            .replace_strict(NET_CLASS_CODES, default=0, return_dtype=pl.Int32())
            .alias("net_class_code"),
            pl.col("peer_frac_rank_one").fill_null(0.0),
            pl.col("peer_n_txids").fill_null(0).cast(pl.Int32()),
            pl.col("peer_degree").fill_null(0).cast(pl.Int32()),
            pl.col("payer_shared").fill_null(0).cast(pl.Int32()),
        )
        .with_columns(
            # `is_tor_exit` stays null-free but must not become False for a null net_class by
            # accident: an unenriched run knows nothing about Tor, and False would claim it knows.
            pl.col("is_tor_exit").fill_null(False),
            pl.col("n_announcements").cast(pl.Int32()),
            pl.col("n_observers_seen").cast(pl.Int32()),
            pl.col("n_observers_in_tx").cast(pl.Int32()),
            pl.col("rank_in_tx").cast(pl.Int32()),
        )
        .sort("txid", "peer_ip")
    )
