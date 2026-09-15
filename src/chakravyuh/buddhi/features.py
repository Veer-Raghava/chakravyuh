"""One row per wallet subject, with every feature the risk model is allowed to see.

The subject grain, not the address grain. An entity's addresses share an owner and therefore a
risk, and the label door (`chakravyuh.eval.labels.wallet_labels`) is answered per address but
meaningful per owner. A subject is one predicted cluster from `graph/clusters.parquet`, or one
address that no `SAME_OWNER` edge linked to anything: those are still wallets an investigator can
be asked about, and leaving them unscored would silently drop most of the capture.

**The window rule, which is the whole point of this file.** A subject is train if its earliest
activity in the capture is before the split boundary, holdout otherwise. A train subject's
features are computed over pre-boundary transactions only; a holdout subject's, over
post-boundary transactions only. Not one feature is computed over the full time range, because
`normalised/addresses.parquet` already carries whole-capture aggregates and a subject that trains
on its own future is the leak the brief names. Cluster shape is windowed with the same rule: a
cluster's late-arriving members are future information about its early self, so only members
active inside the window count, and `min_edge_confidence` is the weakest link among edges whose
both ends were active in the window.

Every column here is observable. Nothing is read from a sibling tree and nothing is derived from
a label, which is what lets `stage.py` stay a pure read of directories under `data/`.
"""

from __future__ import annotations

from typing import Final

import polars as pl

# Columns this stage needs from each upstream table, named so a schema change upstream fails here
# with a missing-column error rather than silently producing a feature full of nulls.
TRANSACTION_COLUMNS = (
    "txid",
    "first_seen_us",
    "n_out",
    "input_addresses",
    "output_addresses",
    "output_amounts",
    "total_out_sats",
    "fee_rate_sat_vb",
    "is_coinbase",
    "has_equal_outputs",
)
CLUSTER_COLUMNS = ("cluster_id", "addresses")
EDGE_COLUMNS = ("src", "dst", "kind", "confidence", "evidence")
ADDRESS_COLUMNS = ("address", "script_type")
ORIGIN_ESTIMATE_COLUMNS = ("txid", "p_origin", "rank", "margin", "abstain", "features")
# The estimator whose probabilities become features. `first_spy` is also written to signals/ but
# is a trivial rule; the learned ensemble is the one this stage fuses.
ENSEMBLE: Final[str] = "ensemble"

MODEL_FEATURES: tuple[str, ...] = (
    "n_addresses",
    "n_tx_sent",
    "total_sent_sats",
    "mean_sent_sats",
    "n_tx_received",
    "total_received_sats",
    "mean_received_sats",
    "balance_sats",
    "n_counterparties",
    "max_fan_out",
    "n_coinbase_received",
    "frac_equal_outputs",
    "mean_fee_rate",
    "median_dwell_us",
    "min_edge_confidence",
    "n_heuristics",
    "n_script_types",
    "mean_p_origin",
    "mean_origin_margin",
    "frac_origin_abstained",
    "frac_top1_tor",
    "mean_n_announcements",
)

# The vocabulary `top_features` names and `docs/FEATURES.md` glosses, one entry per model feature.
FEATURE_GLOSSES: tuple[tuple[str, str], ...] = (
    ("n_addresses", "how many of its addresses were active in its window"),
    ("n_tx_sent", "transactions it sent in its window"),
    ("total_sent_sats", "satoshis it sent in its window"),
    ("mean_sent_sats", "average size of its sends"),
    ("n_tx_received", "transactions that paid it in its window"),
    ("total_received_sats", "satoshis it received in its window"),
    ("mean_received_sats", "average size of its receipts"),
    ("balance_sats", "received minus sent inside its window"),
    ("n_counterparties", "distinct wallets it transacted with"),
    ("max_fan_out", "most addresses it paid in a single transaction"),
    ("n_coinbase_received", "block rewards it collected; mining pools look like this"),
    ("frac_equal_outputs", "share of its transactions with equal-value outputs, a coinjoin mark"),
    ("mean_fee_rate", "average fee per vbyte its sends paid"),
    ("median_dwell_us", "typical gap between one of its receipts and its next send"),
    ("min_edge_confidence", "confidence of the weakest link holding its cluster together"),
    ("n_heuristics", "how many clustering heuristics contributed to its cluster"),
    ("n_script_types", "distinct address formats its active addresses use"),
    ("mean_p_origin", "average origin confidence on the transactions it sent"),
    ("mean_origin_margin", "how far ahead the top origin candidate usually was"),
    ("frac_origin_abstained", "share of its sends the origin estimator refused to answer"),
    ("frac_top1_tor", "share of its sends whose top origin candidate is a Tor exit"),
    ("mean_n_announcements", "average propagation breadth of its sends"),
)

AGGREGATE_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "n_tx_sent": pl.Int32(),
    "total_sent_sats": pl.Int64(),
    "mean_sent_sats": pl.Float64(),
    "mean_fee_rate": pl.Float64(),
    "frac_equal_outputs": pl.Float64(),
    "max_fan_out": pl.Int32(),
    "n_tx_received": pl.Int32(),
    "total_received_sats": pl.Int64(),
    "mean_received_sats": pl.Float64(),
    "n_coinbase_received": pl.Int32(),
    "balance_sats": pl.Int64(),
    "n_counterparties": pl.Int32(),
    "median_dwell_us": pl.Float64(),
}


def subjects(clusters: pl.DataFrame, addresses: pl.DataFrame) -> pl.DataFrame:
    """One row per (subject_id, address), plus `is_clustered`.

    A cluster's members come from `clusters.addresses` (JAAL stores bare addresses there and
    `addr:` node ids on the edges). An address appearing in no cluster becomes its own singleton
    subject, so the scored population is every address in the capture exactly once.
    """
    clustered = (
        clusters.select("cluster_id", pl.col("addresses").alias("address"))
        .explode("address")
        .with_columns(pl.lit(True).alias("is_clustered"))
    )
    singles = (
        addresses.select("address")
        .filter(~pl.col("address").is_in(clustered["address"]))
        .with_columns(("addr:" + pl.col("address")).alias("subject_id"))
        .with_columns(pl.lit(False).alias("is_clustered"))
    )
    return pl.concat(
        [
            clustered.select("cluster_id", "address", "is_clustered").rename(
                {"cluster_id": "subject_id"}
            ),
            singles.select("subject_id", "address", "is_clustered"),
        ]
    ).sort("subject_id", "address")


def _sides(transactions: pl.DataFrame) -> pl.DataFrame:
    """One row per (txid, address, side) with value and time, from the chain columns.

    A transaction an address both sends and receives contributes to both sides, which is what the
    chain actually says. Coinbase has empty `input_addresses`, so it exists only as a receive —
    and `is_coinbase` travels on the receive row, where the block reward lands.
    """
    sent = transactions.select(
        "txid",
        "first_seen_us",
        pl.col("total_out_sats").alias("sats"),
        "fee_rate_sat_vb",
        "has_equal_outputs",
        pl.lit(False).alias("is_coinbase"),
        pl.col("input_addresses").alias("address"),
        pl.lit("in").alias("side"),
    ).explode("address")
    received = transactions.select(
        "txid",
        "first_seen_us",
        pl.col("output_amounts").list.sum().alias("sats"),
        pl.lit(None, dtype=pl.Float64).alias("fee_rate_sat_vb"),
        pl.lit(False).alias("has_equal_outputs"),
        pl.col("is_coinbase"),
        pl.col("output_addresses").alias("address"),
        pl.lit("out").alias("side"),
    ).explode("address")
    return pl.concat([sent, received])


def _aggregate(sides: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:
    """The activity block per subject, over the side rows this window actually holds.

    `members` is the (subject_id, address) pairs whose window this side of the boundary is. The
    caller has already filtered the transactions to the window, so an aggregate here cannot see a
    transaction the subject's window excludes — that is the no-future guarantee, enforced by the
    shape of the call rather than by a check after the fact.
    """
    joined = sides.join(members, on="address", how="inner")
    if joined.is_empty():
        return pl.DataFrame(schema=AGGREGATE_SCHEMA)

    sent = joined.filter(pl.col("side") == "in")
    received = joined.filter(pl.col("side") == "out")

    sent_block = sent.group_by("subject_id", maintain_order=True).agg(
        pl.col("txid").n_unique().alias("n_tx_sent"),
        pl.col("sats").sum().alias("total_sent_sats"),
        pl.col("sats").mean().alias("mean_sent_sats"),
        pl.col("fee_rate_sat_vb").mean().alias("mean_fee_rate"),
        pl.col("has_equal_outputs").mean().alias("frac_equal_outputs"),
    )
    received_block = received.group_by("subject_id", maintain_order=True).agg(
        pl.col("txid").n_unique().alias("n_tx_received"),
        pl.col("sats").sum().alias("total_received_sats"),
        pl.col("sats").mean().alias("mean_received_sats"),
        pl.col("is_coinbase").sum().alias("n_coinbase_received"),
    )
    # Counterparties: any address sharing a transaction with one of the subject's members, other
    # than the subject's own members. Counted over window rows only.
    others = joined.select("txid", "address").unique()
    counterparties = (
        joined.select("subject_id", "txid", "address")
        .unique()
        .join(others, on="txid", how="left")
        .filter(
            pl.col("address_right").is_not_null() & (pl.col("address") != pl.col("address_right"))
        )
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("address_right").n_unique().alias("n_counterparties"))
    )
    fan_out = (
        sent.select("subject_id", "txid", "address")
        .unique()
        .group_by("subject_id", "txid", maintain_order=True)
        .agg(pl.len().alias("n_receivers"))
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("n_receivers").max().alias("max_fan_out"))
    )
    dwell = _dwell(sides, members)

    block = sent_block.join(received_block, on="subject_id", how="full", coalesce=True)
    block = block.join(counterparties, on="subject_id", how="full", coalesce=True)
    block = block.join(fan_out, on="subject_id", how="full", coalesce=True)
    block = block.join(dwell, on="subject_id", how="full", coalesce=True)
    return (
        block.with_columns(
            (pl.col("total_received_sats") - pl.col("total_sent_sats")).alias("balance_sats")
        )
        .with_columns(
            # The empty-half branch is typed by AGGREGATE_SCHEMA; these casts make the non-empty
            # branch agree with it, so the two halves can concat for any boundary.
            pl.col("n_tx_sent").cast(pl.Int32()),
            pl.col("n_tx_received").cast(pl.Int32()),
            pl.col("n_coinbase_received").cast(pl.Int32()),
            pl.col("n_counterparties").cast(pl.Int32()),
            pl.col("max_fan_out").cast(pl.Int32()),
        )
        .select(list(AGGREGATE_SCHEMA))
    )


def _dwell(sides: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:
    """Median gap between a receipt and that address's next send, per subject.

    Pairing is by order, not by UTXO: normalised/ has no input-output linkage, so "the next thing
    this address did after being paid" is the observable the capture actually holds. Null when the
    address never sent after a receipt, which is most of them and is not an error.
    """
    events = (
        sides.join(members, on="address", how="inner")
        .select(
            "address",
            pl.col("side").alias("event"),
            pl.col("first_seen_us").alias("t"),
        )
        .unique()
    )
    if events.is_empty():
        return pl.DataFrame(schema={"subject_id": pl.String(), "median_dwell_us": pl.Float64()})
    receipts = events.filter(pl.col("event") == "out").sort("t")
    sends = events.filter(pl.col("event") == "in").sort("t")
    paired = receipts.select("address", "t").join_asof(
        sends.select("address", pl.col("t").alias("next_t")),
        left_on="t",
        right_on="next_t",
        by="address",
        strategy="forward",
    )
    subject_of = members.unique(subset=["address"]).select("address", "subject_id")
    return (
        paired.join(subject_of, on="address", how="inner")
        .with_columns((pl.col("next_t") - pl.col("t")).alias("gap"))
        .filter(pl.col("gap").is_not_null())
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("gap").median().cast(pl.Float64).alias("median_dwell_us"))
    )


def cluster_shape(
    clusters: pl.DataFrame,
    edges: pl.DataFrame,
    members: pl.DataFrame,
    active: pl.DataFrame,
) -> pl.DataFrame:
    """Windowed cluster shape: active size, weakest live link, distinct heuristics.

    `active` is one row per address with any window activity. A cluster's full-capture membership
    is deliberately not used: an address that joins after the window is future information about
    the cluster, so `n_addresses` counts only members active in the window and
    `min_edge_confidence` reads only edges whose both ends were active then.
    """
    active_members = members.join(active, on="address", how="semi")
    sizes = active_members.group_by("subject_id", maintain_order=True).agg(
        pl.len().alias("n_addresses")
    )

    same_owner = edges.filter(pl.col("kind") == "SAME_OWNER").select(
        "src", "dst", "confidence", "evidence"
    )
    ends = pl.concat(
        [
            same_owner.select(
                pl.col("src").str.strip_prefix("addr:").alias("a"),
                pl.col("dst").str.strip_prefix("addr:").alias("b"),
                "confidence",
                "evidence",
            ),
            same_owner.select(
                pl.col("dst").str.strip_prefix("addr:").alias("a"),
                pl.col("src").str.strip_prefix("addr:").alias("b"),
                "confidence",
                "evidence",
            ),
        ]
    )
    live_ends = ends.join(active, left_on="a", right_on="address", how="semi")
    pairs = live_ends.select(
        pl.col("a").alias("left"),
        pl.col("b").alias("right"),
        "confidence",
        "evidence",
    )
    member_pairs = active_members.select(
        pl.col("subject_id"), pl.col("address").alias("left")
    ).join(
        active_members.select(pl.col("subject_id"), pl.col("address").alias("right")),
        on="subject_id",
    )
    weakest = (
        pairs.join(member_pairs, on=["left", "right"], how="inner")
        .group_by("subject_id", maintain_order=True)
        .agg(
            pl.col("confidence").min().alias("min_edge_confidence"),
            pl.col("evidence").n_unique().alias("n_heuristics"),
        )
    )
    return sizes.join(weakest, on="subject_id", how="full", coalesce=True)


def script_types(
    addresses: pl.DataFrame, active: pl.DataFrame, members: pl.DataFrame
) -> pl.DataFrame:
    """Distinct address formats among a subject's active members.

    `script_type` is derived from the address's own prefix, so reading it for an active address
    adds no time information; restricting to active members is what keeps the member set windowed.
    """
    return (
        members.join(active, on="address", how="semi")
        .join(addresses.select("address", "script_type"), on="address", how="inner")
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("script_type").n_unique().alias("n_script_types"))
    )


def origin_fusion(origin_estimates: pl.DataFrame, sent: pl.DataFrame) -> pl.DataFrame:
    """The origin estimator's output, as five per-subject features over its own sent txids.

    `sent` is (subject_id, txid) for the sends inside the subject's window, and
    `origin_estimates` is the ensemble rows only. A send whose transaction the estimator refused
    has no rank-1 row — SHASTRA's abstain rule — and counts in `frac_origin_abstained`. Null
    origin features mean the subject sent nothing in its window, which LightGBM treats as its own
    value and not as a default.
    """
    sent_txids = sent.select("subject_id", "txid").unique()
    top1 = origin_estimates.filter(pl.col("rank") == 1).select(
        "txid",
        "p_origin",
        "margin",
        pl.col("features").struct.field("n_announcements").alias("n_announcements"),
        pl.col("features").struct.field("is_tor_exit").alias("is_tor_exit"),
    )
    answered = sent_txids.join(top1, on="txid", how="inner")
    per_subject = answered.group_by("subject_id", maintain_order=True).agg(
        pl.col("p_origin").mean().alias("mean_p_origin"),
        pl.col("margin").mean().alias("mean_origin_margin"),
        pl.col("n_announcements").mean().cast(pl.Float64).alias("mean_n_announcements"),
        pl.col("is_tor_exit").mean().cast(pl.Float64).alias("frac_top1_tor"),
    )
    refused = (
        sent_txids.join(
            answered.select("subject_id", "txid"), on=["subject_id", "txid"], how="anti"
        )
        .group_by("subject_id", maintain_order=True)
        .agg(pl.len().alias("_n_refused"))
    )
    totals = sent_txids.group_by("subject_id", maintain_order=True).agg(pl.len().alias("_n_sent"))
    share = totals.join(refused, on="subject_id", how="full", coalesce=True).with_columns(
        (pl.col("_n_refused").fill_null(0) / pl.col("_n_sent")).alias("frac_origin_abstained")
    )
    return per_subject.join(
        share.select("subject_id", "frac_origin_abstained"),
        on="subject_id",
        how="full",
        coalesce=True,
    )


def build(
    transactions: pl.DataFrame,
    clusters: pl.DataFrame,
    addresses: pl.DataFrame,
    edges: pl.DataFrame,
    origin_estimates: pl.DataFrame,
    boundary_us: int,
) -> pl.DataFrame:
    """The subject table: one row per wallet subject, windowed features, no future data.

    The window rule is applied exactly once, here. A subject whose earliest activity is before
    `boundary_us` is a train subject and is aggregated over pre-boundary transactions; every
    other subject is aggregated over post-boundary transactions. Both halves run through the same
    `_aggregate`, so neither can quietly grow a different definition.
    """
    who = subjects(clusters, addresses)
    sides = _sides(transactions)

    first_activity = sides.group_by("address", maintain_order=True).agg(
        pl.col("first_seen_us").min().alias("first_us")
    )
    placed = who.join(first_activity, on="address", how="inner")
    subject_first = placed.group_by("subject_id", maintain_order=True).agg(
        pl.col("first_us").min().alias("subject_first_us"),
        pl.len().alias("_member_rows"),
    )
    subject_first = subject_first.with_columns(
        (pl.col("subject_first_us") < boundary_us).alias("is_train")
    )

    train_members = (
        placed.join(subject_first.select("subject_id", "is_train"), on="subject_id")
        .filter(pl.col("is_train"))
        .select("subject_id", "address")
    )
    holdout_members = (
        placed.join(subject_first.select("subject_id", "is_train"), on="subject_id")
        .filter(~pl.col("is_train"))
        .select("subject_id", "address")
    )

    early_tx = transactions.filter(pl.col("first_seen_us") < boundary_us)
    late_tx = transactions.filter(pl.col("first_seen_us") >= boundary_us)

    train_block = _aggregate(_sides(early_tx), train_members)
    holdout_block = _aggregate(_sides(late_tx), holdout_members)
    activity = pl.concat([train_block, holdout_block])

    # The sent-pair table per subject, over its own window, for the origin features.
    early_pairs = (
        _sides(early_tx)
        .filter(pl.col("side") == "in")
        .join(train_members, on="address", how="inner")
        .select("subject_id", "txid")
        .unique()
    )
    late_pairs = (
        _sides(late_tx)
        .filter(pl.col("side") == "in")
        .join(holdout_members, on="address", how="inner")
        .select("subject_id", "txid")
        .unique()
    )
    sent_pairs = pl.concat([early_pairs, late_pairs])

    ensemble_rows = origin_estimates.filter(pl.col("estimator") == ENSEMBLE)
    fusion = (
        origin_fusion(ensemble_rows, sent_pairs)
        if not ensemble_rows.is_empty()
        else pl.DataFrame(
            schema={
                "subject_id": pl.String(),
                "mean_p_origin": pl.Float64(),
                "mean_origin_margin": pl.Float64(),
                "mean_n_announcements": pl.Float64(),
                "frac_top1_tor": pl.Float64(),
                "frac_origin_abstained": pl.Float64(),
            }
        )
    )

    # Windowed cluster shape and script diversity, computed per half so `active` is honest.
    active_early = _sides(early_tx).select("address").unique()
    active_late = _sides(late_tx).select("address").unique()
    shape = pl.concat(
        [
            cluster_shape(clusters, edges, train_members, active_early),
            cluster_shape(clusters, edges, holdout_members, active_late),
        ]
    )
    scripts = pl.concat(
        [
            script_types(addresses, active_early, train_members),
            script_types(addresses, active_late, holdout_members),
        ]
    )

    out = (
        subject_first.select("subject_id", "is_train")
        .join(activity, on="subject_id", how="left")
        .join(shape, on="subject_id", how="left")
        .join(scripts, on="subject_id", how="left")
        .join(fusion, on="subject_id", how="left")
    )
    for name in MODEL_FEATURES:
        if name not in out.columns:
            out = out.with_columns(pl.lit(None).alias(name))
    return out.select("subject_id", "is_train", *MODEL_FEATURES)
