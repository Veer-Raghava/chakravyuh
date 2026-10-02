"""Event ledger and point-in-time ownership views, without labels or destructive merges.

Legacy graph artifacts omit ownership timestamps. This opt-in API retains every transaction's
claim before deduplication so later stronger evidence cannot acquire an earlier timestamp.
The event time is first_seen_us: callers must ensure the complete transaction body was available
then. If ingestion receives the body later, supply that later availability time instead.
Confidence values are existing heuristic weights, not measured pair-ownership probabilities.
"""

from __future__ import annotations

import polars as pl

from chakravyuh.jaal import cluster, mixer
from chakravyuh.jaal.build import EDGES_SCHEMA, conform

LEDGER_SCHEMA: dict[str, pl.DataType] = {
    "src": pl.String(),
    "dst": pl.String(),
    "txid": pl.String(),
    "available_us": pl.Int64(),
    "confidence": pl.Float64(),
    "evidence": pl.String(),
}


def _claims(frame: pl.DataFrame, members: str, evidence: str, confidence: float) -> pl.DataFrame:
    pairs = cluster._member_pairs(frame, members, ("txid", "first_seen_us"))
    return conform(
        pairs.select(
            (pl.lit("addr:") + pl.col("anchor")).alias("src"),
            (pl.lit("addr:") + pl.col("member")).alias("dst"),
            pl.col("txid"),
            pl.col("first_seen_us").alias("available_us"),
            pl.lit(confidence).alias("confidence"),
            pl.lit(evidence).alias("evidence"),
        ),
        LEDGER_SCHEMA,
    )


def ownership_evidence(transactions: pl.DataFrame) -> pl.DataFrame:
    """Retain transaction/time provenance for both existing ownership heuristics."""
    if transactions["first_seen_us"].null_count() or transactions["txid"].null_count():
        raise ValueError("ownership evidence requires non-null availability and transaction IDs")
    eligible = transactions.filter(~pl.col("is_coinbase") & ~mixer.is_mixer())
    common = _claims(
        eligible.filter(pl.col("n_in") >= 2),
        "input_addresses",
        "multi_input",
        cluster.MULTI_INPUT_CONFIDENCE,
    )
    change = _claims(
        cluster._change_members(eligible),
        "members",
        "change_addr",
        cluster.CHANGE_ADDR_CONFIDENCE,
    )
    return (
        pl.concat([common, change]).unique().sort("available_us", "txid", "evidence", "src", "dst")
    )


def snapshot_edges(ledger: pl.DataFrame, cutoff_us: int) -> pl.DataFrame:
    """Select strongest evidence known at or before cutoff; retain its actual timestamp.

    Apply the ownership threshold afterwards with cluster.components/clusters. Multiple claims
    of the same pair are retained in the ledger, not treated as independent probability draws.
    Ties prefer the earliest evidence, then stable transaction/evidence identifiers.
    """
    past = ledger.filter(pl.col("available_us") <= cutoff_us)
    kept = past.sort(
        ["src", "dst", "confidence", "available_us", "txid", "evidence"],
        descending=[False, False, True, False, False, False],
    ).unique(subset=["src", "dst"], keep="first", maintain_order=True)
    return conform(
        kept.select(
            "src",
            "dst",
            pl.lit("SAME_OWNER").alias("kind"),
            pl.col("available_us").alias("ts_us"),
            pl.lit(None).cast(pl.Int64).alias("sats"),
            "confidence",
            "evidence",
        ),
        EDGES_SCHEMA,
    )
