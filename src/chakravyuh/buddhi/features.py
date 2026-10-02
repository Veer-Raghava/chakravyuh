"""One row per wallet subject, with every feature the risk model is allowed to see.

The subject grain, not the address grain. An entity's addresses share an owner and therefore a
risk, and the label door (`chakravyuh.eval.labels.wallet_labels`) is answered per address but
meaningful per owner. A subject is one predicted cluster from `graph/clusters.parquet`, or one
address that no `SAME_OWNER` edge linked to anything: those are still wallets an investigator can
be asked about, and leaving them unscored would silently drop most of the capture.

**The window rule, which is the whole point of this file.** A subject is train if its earliest
activity in the capture is before the split boundary, holdout otherwise. A train subject's
features are computed over pre-boundary transactions only; a holdout subject's, over
post-boundary transactions only. Transaction activity is sliced by that boundary, because
`normalised/addresses.parquet` already carries whole-capture aggregates and a subject that trains
on its own future is the leak the brief names. Cluster shape is windowed with the same rule: a
cluster's late-arriving members are future information about its early self, so only members
active inside the window count, and `min_edge_confidence` is the weakest link among edges whose
both ends were active in the window. This does not make full-capture cluster membership causal:
a later ownership edge can still determine the supplied subject partition. Global upstream
origin scores and typology detections can also include later information. The opt-in snapshot
API supplies a point-in-time partition and excludes those upstream artifacts.

Every column here is observable. Nothing is read from a sibling tree and nothing is derived from
a label, which is what lets `stage.py` stay a pure read of directories under `data/`.
"""

from __future__ import annotations

from typing import Final

import polars as pl

from chakravyuh.buddhi import embed

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
# `sats` is read for the embedding leg alone: `cluster_shape` never needed it, but `embed._design`
# weighs an edge by the value it moved, so the column has to be here whether or not `--gnn` is on.
# Reading it in a plain run costs nothing and keeps one edge table rather than two.
EDGE_COLUMNS = ("src", "dst", "kind", "confidence", "evidence", "sats")
ADDRESS_COLUMNS = ("address", "script_type")
ORIGIN_ESTIMATE_COLUMNS = ("txid", "p_origin", "rank", "margin", "abstain", "features")
# The four columns the operator-grain fusion reads. `abstain` is not optional: the whole point of
# `frac_l1_abstained` is that a reader of `mean_p_asn` can see how often the stage refused.
ORIGIN_L1_COLUMNS = ("txid", "p_asn", "margin", "abstain")
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
    "mean_p_asn",
    "mean_asn_margin",
    "frac_l1_abstained",
    "mean_n_announcements",
    "n_typologies",
    "n_typology_txns",
    "fan_in_ratio",
    "peel_chain_depth",
    "peel_leak_frac",
    "structuring_frac",
    "burstiness",
    "fee_anomaly",
)

# The columns the GNN booster adds on top of `MODEL_FEATURES`. A separate tuple, so the baseline
# model's feature set is exactly what it was and `stage.py` can build either booster from one
# table. Named by position because an SVD's directions carry no meaning a gloss could name
# individually — the honest gloss is the same sentence for all of them, see `embed.py`.
EMBEDDING_FEATURES: tuple[str, ...] = tuple(f"embed_{i:02d}" for i in range(embed.DIM))
ALL_FEATURES: tuple[str, ...] = MODEL_FEATURES + EMBEDDING_FEATURES

# One sentence, shared by every embedding column, because the SVD's directions are unnamed: saying
# these are "a structural summary" is the most a reader can be told about a basis vector that has
# no units. The wording is duplicated into `docs/FEATURES.md`, which carries the same table.
EMBEDDING_GLOSS: Final[str] = (
    "one direction of the graph embedding: a two-hop structural summary of the dual graph, "
    "computed with no labels"
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
    ("mean_p_asn", "average confidence in the network operator behind the transactions it sent"),
    ("mean_asn_margin", "how far ahead the top operator usually was of the runner-up"),
    ("frac_l1_abstained", "share of its sends where no single operator could be named"),
    ("mean_n_announcements", "average propagation breadth of its sends"),
    ("n_typologies", "distinct laundering morphologies SHASTRA flagged on its sends in its window"),
    ("n_typology_txns", "transactions it sent in its window that fed a SHASTRA typology hit"),
    ("fan_in_ratio", "most addresses it consolidated into a single transaction"),
    ("peel_chain_depth", "longest run of peel-style sends (one payment plus change) it made"),
    (
        "peel_leak_frac",
        "average share of value leaving as the payment, not the change, in those peels",
    ),
    ("structuring_frac", "share of its sends whose amounts sit just under round-number thresholds"),
    ("burstiness", "how clustered in time its sends are (coefficient of variation of the gaps)"),
    ("fee_anomaly", "how far its fee rate sat from the going rate in its window, on average"),
) + tuple((name, EMBEDDING_GLOSS) for name in EMBEDDING_FEATURES)

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

# The six morphological shape features, computed over a subject's in-window sends only. Their
# output schema, used to type the empty-window branch so the two halves concat for any boundary.
MORPHOLOGY_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "fan_in_ratio": pl.Int32(),
    "peel_chain_depth": pl.Int32(),
    "peel_leak_frac": pl.Float64(),
    "structuring_frac": pl.Float64(),
    "burstiness": pl.Float64(),
    "fee_anomaly": pl.Float64(),
}

# Round-number sat thresholds for structuring: an output landing in [0.9*T, T) is a payment nudged
# just under a reporting line. The band edges are integers for every T, so the test is int64-clean.
_STRUCTURING_LADDER: Final[tuple[int, ...]] = (100_000, 1_000_000, 10_000_000, 100_000_000)

# The operator-grain fusion columns, typed for the branch where the run shipped no L1 headline at
# all (a world with no ASN substrate), so the join is a null column rather than a missing one.
ASN_FUSION_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "mean_p_asn": pl.Float64(),
    "mean_asn_margin": pl.Float64(),
    "frac_l1_abstained": pl.Float64(),
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
    # Join actual evidence endpoints rather than materializing every possible member pair.
    # Large exchange subjects otherwise require O(n_addresses ** 2) intermediate rows.
    held_pairs = pairs.join(
        active_members.select("subject_id", pl.col("address").alias("left")), on="left"
    ).join(
        active_members.select("subject_id", pl.col("address").alias("right")),
        on=["subject_id", "right"],
    )
    weakest = held_pairs.group_by("subject_id", maintain_order=True).agg(
        pl.col("confidence").min().alias("min_edge_confidence"),
        pl.col("evidence").n_unique().alias("n_heuristics"),
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


def asn_fusion(origin_l1: pl.DataFrame, sent: pl.DataFrame) -> pl.DataFrame:
    """The operator estimate, as three per-subject features over the same windowed sends.

    `origin_l1` is the shipped `signals/origin_l1.parquet`: one row per transaction carrying the
    operator the estimator ranked first, its `p_asn`, the gap to the runner-up, and whether the
    stage stood behind that operator at all.

    `p_asn` and `margin` are read on **every** row, abstained ones included, and that is the
    point. An abstention here is a statement about the shortlist — the mass split across
    operators, or the candidate estimate refused the transaction upstream — not a claim that the
    row is empty. The operator and its probability remain the estimator's belief, and a belief is
    something a feature may carry. What the row does *not* carry is a promise that the belief is
    right, so the share of sends the stage refused travels beside it as `frac_l1_abstained`, the
    same pairing `mean_p_origin` / `frac_origin_abstained` already uses at the host grain.

    Reading the value without the refusal beside it would let a subject whose sends the estimator
    could not separate at all look exactly like one it separated cleanly — which is the mistake
    this pairing exists to make impossible.
    """
    sent_txids = sent.select("subject_id", "txid").unique()
    if origin_l1.is_empty():
        return pl.DataFrame(schema=ASN_FUSION_SCHEMA)
    rows = origin_l1.select("txid", "p_asn", "margin", "abstain")
    joined = sent_txids.join(rows, on="txid", how="inner")
    if joined.is_empty():
        return pl.DataFrame(schema=ASN_FUSION_SCHEMA)
    return joined.group_by("subject_id", maintain_order=True).agg(
        pl.col("p_asn").mean().alias("mean_p_asn"),
        pl.col("margin").mean().alias("mean_asn_margin"),
        pl.col("abstain").cast(pl.Float64).mean().alias("frac_l1_abstained"),
    )


def typology_load(hits: pl.DataFrame, sent_pairs: pl.DataFrame) -> pl.DataFrame:
    """Per subject: distinct typologies and hit-bearing transactions, counted inside its window.

    SHASTRA writes one hit per (subject, typology) over the whole capture; joining its txids back
    to `sent_pairs` — which is already restricted to each subject's train-or-holdout window — keeps
    only the flagged transactions that fall in the window this subject is measured over. A hit
    whose transactions all sit on the wrong side of the boundary contributes nothing, so the
    join restricts hit overlap, but cannot undo future observations used by the upstream detector.
    A prospective evaluation must recompute those detections at the decision cutoff.
    """
    if hits.is_empty():
        return pl.DataFrame(
            schema={
                "subject_id": pl.String(),
                "n_typologies": pl.Int32(),
                "n_typology_txns": pl.Int32(),
            }
        )
    exploded = (
        hits.select("subject_id", "typology", "txids")
        .explode("txids")
        .rename({"txids": "txid"})
        .join(sent_pairs, on=["subject_id", "txid"], how="inner")
    )
    return exploded.group_by("subject_id").agg(
        pl.col("typology").n_unique().cast(pl.Int32()).alias("n_typologies"),
        pl.col("txid").n_unique().cast(pl.Int32()).alias("n_typology_txns"),
    )


def morphology(transactions: pl.DataFrame, sent_pairs: pl.DataFrame) -> pl.DataFrame:
    """Six transaction-shape features over the subject's in-window sends, joined on subject_id.

    `transactions` is the window's transactions (already sliced by the boundary in `build`), and
    `sent_pairs` is `(subject_id, txid)` restricted to each subject's window; joining them gives the
    transactions each subject sent and nothing else — the same windowing every other feature obeys.
    A subject that sent nothing has no row here and reads as zero after the caller's `fill_null(0)`,
    the same "the detector ran and found nothing" convention the typology block uses.
    """
    if sent_pairs.is_empty():
        return pl.DataFrame(schema=MORPHOLOGY_SCHEMA)

    # The window's going fee rate; every send's deviation is measured against this one scalar.
    window_fee_median = pl.lit(
        transactions.select(pl.col("fee_rate_sat_vb").median()).item(), dtype=pl.Float64
    )
    tx = transactions.select(
        "txid",
        "first_seen_us",
        "n_out",
        "total_out_sats",
        "fee_rate_sat_vb",
        pl.col("input_addresses").list.len().alias("n_in"),
        pl.col("output_amounts").list.min().alias("min_out"),
        pl.col("output_amounts").list.max().alias("max_out"),
        pl.col("output_amounts"),
    )
    sent = sent_pairs.select("subject_id", "txid").unique().join(tx, on="txid", how="inner")

    # fan_in_ratio mirrors `max_fan_out`'s max-over-sent-txs shape, on the input count instead.
    fan_in = sent.group_by("subject_id", maintain_order=True).agg(
        pl.col("n_in").max().cast(pl.Int32()).alias("fan_in_ratio")
    )

    # ponytail: subject-grain peel count, not the full graph tracer (P2)
    # A peel: one input, two outputs, the smaller under a quarter of the larger (payment + change,
    # not a coinjoin-style split). `min_out * 4 < max_out` keeps the test int64-clean.
    peels = sent.filter(
        (pl.col("n_in") == 1) & (pl.col("n_out") == 2) & (pl.col("min_out") * 4 < pl.col("max_out"))
    )
    peel = (
        peels.with_columns((pl.col("min_out") / pl.col("total_out_sats")).alias("_leak"))
        .group_by("subject_id", maintain_order=True)
        .agg(
            pl.len().cast(pl.Int32()).alias("peel_chain_depth"),
            pl.col("_leak").mean().alias("peel_leak_frac"),
        )
    )

    # ponytail: fixed round-threshold ladder, not learned (P2)
    band = pl.lit(False)
    for t in _STRUCTURING_LADDER:
        band = band | ((pl.element() >= int(t * 0.9)) & (pl.element() < t))
    structuring = (
        sent.with_columns(pl.col("output_amounts").list.eval(band).list.any().alias("_structured"))
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("_structured").mean().cast(pl.Float64).alias("structuring_frac"))
    )

    # burstiness: coefficient of variation of successive send gaps; 0.0 under three sends (fewer
    # than two gaps) or when every send shares a timestamp (mean gap zero, no spread to speak of).
    gaps = (
        sent.sort("first_seen_us")
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("first_seen_us").sort().diff().drop_nulls().alias("_gaps"))
    )
    burst = gaps.with_columns(
        pl.when((pl.col("_gaps").list.len() < 2) | (pl.col("_gaps").list.mean() == 0))
        .then(pl.lit(0.0))
        .otherwise(pl.col("_gaps").list.std() / pl.col("_gaps").list.mean())
        .cast(pl.Float64())
        .alias("burstiness")
    ).select("subject_id", "burstiness")

    fee = (
        sent.with_columns((pl.col("fee_rate_sat_vb") - window_fee_median).alias("_dev"))
        .group_by("subject_id", maintain_order=True)
        .agg(pl.col("_dev").mean().cast(pl.Float64).alias("fee_anomaly"))
    )

    result = fan_in
    for other in (peel, structuring, burst, fee):
        result = result.join(other, on="subject_id", how="full", coalesce=True)
    return result.select(list(MORPHOLOGY_SCHEMA))


def build(
    transactions: pl.DataFrame,
    clusters: pl.DataFrame,
    addresses: pl.DataFrame,
    edges: pl.DataFrame,
    origin_estimates: pl.DataFrame,
    boundary_us: int,
    typology_hits: pl.DataFrame | None = None,
    origin_l1: pl.DataFrame | None = None,
    *,
    use_embeddings: bool = False,
) -> pl.DataFrame:
    """The subject table: windowed activity given the caller's partition and upstream evidence.

    The window rule is applied exactly once, here. A subject whose earliest activity is before
    `boundary_us` is a train subject and is aggregated over pre-boundary transactions; every
    other subject is aggregated over post-boundary transactions. Both halves run through the same
    `_aggregate`, so neither can quietly grow a different definition.

    `use_embeddings` appends the GNN leg's columns — the label-free dual-graph embedding of
    `buddhi.embed`, computed per half so it obeys the same window rule as everything else here.
    It defaults off: the baseline feature set is a call with no argument, which is what makes the
    add-on droppable rather than merely optional.
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

    # The operator-grain fusion, over the same windowed sends. A run that shipped no L1 headline
    # at all contributes a typed empty frame, so the join yields nulls rather than dropping rows.
    asn = (
        asn_fusion(origin_l1, sent_pairs)
        if origin_l1 is not None and not origin_l1.is_empty()
        else pl.DataFrame(schema=ASN_FUSION_SCHEMA)
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

    typ = typology_load(typology_hits if typology_hits is not None else pl.DataFrame(), sent_pairs)

    # Transaction-shape features, computed per half so each subject's sends stay inside its window.
    morph = pl.concat(
        [
            morphology(early_tx, early_pairs),
            morphology(late_tx, late_pairs),
        ]
    )

    # The graph embedding, per half like cluster shape and for the same reason: a subject's
    # embedding must come from the graph its own window could see. The two halves are concatenated
    # diagonally so a window that produced fewer columns (a design with fewer than DIM raw
    # features) still lines up, leaving the absent directions null rather than zero.
    embedded = (
        pl.concat(
            [
                embed.subject_embeddings(
                    edges,
                    transactions,
                    addresses,
                    train_members,
                    half="train",
                    boundary_us=boundary_us,
                ),
                embed.subject_embeddings(
                    edges,
                    transactions,
                    addresses,
                    holdout_members,
                    half="holdout",
                    boundary_us=boundary_us,
                ),
            ],
            how="diagonal",
        )
        if use_embeddings
        else pl.DataFrame(schema={"subject_id": pl.String()})
    )

    feature_columns = MODEL_FEATURES + (EMBEDDING_FEATURES if use_embeddings else ())
    out = (
        subject_first.select("subject_id", "is_train")
        .join(activity, on="subject_id", how="left")
        .join(shape, on="subject_id", how="left")
        .join(scripts, on="subject_id", how="left")
        .join(fusion, on="subject_id", how="left")
        .join(asn, on="subject_id", how="left")
        .join(typ, on="subject_id", how="left")
        .join(morph, on="subject_id", how="left")
        .join(embedded, on="subject_id", how="left")
    )
    # A subject with no typology hit in its window has zero, not null: the detector ran and found
    # nothing, which is a real observation the tree can split on, unlike a genuinely absent feature.
    out = out.with_columns(
        pl.col("n_typologies").fill_null(0), pl.col("n_typology_txns").fill_null(0)
    )
    # Same convention for the shape features: a subject that sent nothing in its window has no shape
    # to measure, which reads as zero — a real observation, not a missing one.
    out = out.with_columns(
        pl.col(name).fill_null(0) for name in MORPHOLOGY_SCHEMA if name != "subject_id"
    )
    # The embedding columns are deliberately NOT filled: a null there says the subject had no node
    # in its window's graph, which is a different fact from a structural summary of nothing, and it
    # is the fact `stage.py` reads to decide which booster scores the row.
    for name in feature_columns:
        if name not in out.columns:
            out = out.with_columns(pl.lit(None).alias(name))
    return out.select("subject_id", "is_train", *feature_columns)
