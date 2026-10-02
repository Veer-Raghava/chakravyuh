"""Opt-in end-of-window AML features over ownership evidence available at decision time.

This API scores recurring as well as newly observed subjects. Unlike the legacy subject split,
each window gets its own graph partition. Global origin estimates and typology artifacts are
excluded until their own point-in-time recipes are available. No labels are consumed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import polars as pl

from chakravyuh.buddhi import features
from chakravyuh.jaal import cluster, provenance
from chakravyuh.jaal.build import CLUSTERS_SCHEMA, EDGES_SCHEMA
from chakravyuh.shastra.schema import ORIGIN_ESTIMATES_SCHEMA

SNAPSHOT_FEATURES = tuple(
    name
    for name in features.MODEL_FEATURES
    if name
    not in {
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
    }
)


@dataclass(frozen=True)
class Snapshot:
    table: pl.DataFrame
    members: pl.DataFrame
    edges: pl.DataFrame
    start_us: int
    end_us: int
    partition_mode: Literal["heuristic", "address"] = "heuristic"


def _flow_features(transactions: pl.DataFrame, members: pl.DataFrame) -> pl.DataFrame:
    """Exact gross input/output values per subject/transaction; counterparties are subjects.

    The legacy aggregate repeats a transaction's total output for every participating address.
    Here lists are exploded together, then aggregated once per subject/transaction. Gross input
    value includes subsequently returned change; it is not an inferred external payment amount.
    """
    inputs = (
        transactions.select(
            "txid",
            pl.col("input_addresses").alias("address"),
            pl.col("input_amounts").alias("value_sats"),
        )
        .explode("address", "value_sats")
        .drop_nulls("address")
    )
    outputs = (
        transactions.select(
            "txid",
            pl.col("output_addresses").alias("address"),
            pl.col("output_amounts").alias("value_sats"),
        )
        .explode("address", "value_sats")
        .drop_nulls("address")
    )
    sent = (
        inputs.join(members, on="address")
        .group_by("subject_id", "txid")
        .agg(pl.col("value_sats").sum().alias("value_sats"))
    )
    received = (
        outputs.join(members, on="address")
        .group_by("subject_id", "txid")
        .agg(pl.col("value_sats").sum().alias("value_sats"))
    )
    sent_summary = sent.group_by("subject_id").agg(
        pl.col("value_sats").sum().alias("total_sent_sats"),
        pl.col("value_sats").mean().alias("mean_sent_sats"),
    )
    sent_summary = sent_summary.join(
        sent.join(transactions.select("txid", "fee_rate_sat_vb", "has_equal_outputs"), on="txid")
        .group_by("subject_id")
        .agg(
            pl.col("fee_rate_sat_vb").mean().alias("mean_fee_rate"),
            pl.col("has_equal_outputs").mean().alias("frac_equal_outputs"),
        ),
        on="subject_id",
    )
    received_summary = received.group_by("subject_id").agg(
        pl.col("value_sats").sum().alias("total_received_sats"),
        pl.col("value_sats").mean().alias("mean_received_sats"),
    )
    relations = (
        pl.concat(
            [
                sent.select("subject_id", "txid").join(
                    outputs.select("txid", "address"), on="txid"
                ),
                received.select("subject_id", "txid").join(
                    inputs.select("txid", "address"), on="txid"
                ),
            ]
        )
        .join(members.select(pl.col("subject_id").alias("other_subject"), "address"), on="address")
        .filter(pl.col("subject_id") != pl.col("other_subject"))
    )
    counterparties = relations.group_by("subject_id").agg(
        pl.col("other_subject").n_unique().alias("n_counterparties")
    )
    return sent_summary.join(received_summary, on="subject_id", how="full", coalesce=True).join(
        counterparties, on="subject_id", how="full", coalesce=True
    )


def build(
    transactions: pl.DataFrame,
    addresses: pl.DataFrame,
    ledger: pl.DataFrame,
    *,
    start_us: int,
    end_us: int,
    threshold: float = 0.3,
    partition_mode: Literal["heuristic", "address"] = "heuristic",
) -> Snapshot:
    """Compute retrospective features available at the end of [start_us, end_us].

    It is legitimate to use an ownership claim discovered inside this window for the window's
    final decision; those claims never enter a preceding window. Availability of transaction
    bodies is assumed at first_seen_us, as in the ownership ledger. Local cluster IDs can change
    between snapshots; callers must use address evidence to track subjects across versions.
    """
    if start_us > end_us:
        raise ValueError("snapshot start must not exceed end")
    window = transactions.filter(
        (pl.col("first_seen_us") >= start_us) & (pl.col("first_seen_us") <= end_us)
    )
    observed = addresses.filter(pl.col("first_seen_us") <= end_us)
    if partition_mode not in ("heuristic", "address"):
        raise ValueError("unknown snapshot partition mode")
    edges = (
        pl.DataFrame(schema=EDGES_SCHEMA)
        if partition_mode == "address"
        else provenance.snapshot_edges(ledger, end_us).filter(pl.col("confidence") >= threshold)
    )
    if partition_mode == "address":
        groups = pl.DataFrame(schema=CLUSTERS_SCHEMA)
    else:
        groups, _ = cluster.clusters(edges, threshold)
    table = features.build(
        window,
        groups,
        observed,
        edges,
        pl.DataFrame(schema=ORIGIN_ESTIMATES_SCHEMA),
        end_us + 1,
    ).select("subject_id", *SNAPSHOT_FEATURES)
    members = (
        features.subjects(groups, observed)
        .join(table.select("subject_id"), on="subject_id")
        .sort("subject_id", "address")
    )
    flow = _flow_features(window, members.select("subject_id", "address"))
    replaced = [
        "total_sent_sats",
        "mean_sent_sats",
        "total_received_sats",
        "mean_received_sats",
        "balance_sats",
        "n_counterparties",
        "mean_fee_rate",
        "frac_equal_outputs",
    ]
    table = (
        table.drop(replaced)
        .join(flow, on="subject_id", how="left")
        .with_columns(
            pl.col("total_sent_sats").fill_null(0),
            pl.col("total_received_sats").fill_null(0),
            pl.col("n_counterparties").fill_null(0),
        )
        .with_columns(
            (pl.col("total_received_sats") - pl.col("total_sent_sats")).alias("balance_sats")
        )
        .select("subject_id", *SNAPSHOT_FEATURES)
        .sort("subject_id")
    )
    return Snapshot(table, members, edges, start_us, end_us, partition_mode)
