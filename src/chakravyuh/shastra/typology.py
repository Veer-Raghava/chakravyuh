"""SHASTRA typology detectors: heuristic laundering-morphology hits over observable transactions.

Each detector is a pure threshold rule on the normalised transaction graph. Nothing here reads a
label or the answer key: a hit is a shape an analyst can point at, computed from the capture alone.
The vocabulary matches MAYAJAAL's own typology names and docs/DATA-CONTRACTS section 2, so a hit
names the same laundering pattern the world can plant — but it is asserted from morphology, never
from truth, which is exactly why a hit can be wrong and the model that consumes it must earn its
weight rather than read the answer.

A hit is one (subject, typology) pair with every transaction that fed it, so the console can show
an analyst the transactions behind an accusation and BUDDHI can window the hit by those txids. The
thresholds are module constants, following the estimator's own precedent (`estimate.TREE_PARAMS`):
a detector is a fixed rule, and a rule that moved with the config could not be replayed.
"""

from __future__ import annotations

import hashlib
from typing import Final

import polars as pl

from chakravyuh.shastra import schema

# Fan-out: one send paying many fresh addresses at once, the split move's signature. Six is well
# above an ordinary payment's one-or-two outputs and below a mining pool's dozens of payouts.
FAN_OUT_MIN_OUTPUTS: Final[int] = 6
# CoinJoin-like: equal-value outputs are the mark SETU already flags; three or more of them in one
# transaction is a mixing round rather than a coincidental pair.
COINJOIN_MIN_OUTPUTS: Final[int] = 3
# Peel: a two-output send where one output is a thin slice and the rest is change carried onward.
# A single peel is ordinary; a chain of them is the typology, so a minimum count gates the hit.
PEEL_MAX_SHARE: Final[float] = 0.35
PEEL_MIN_TXNS: Final[int] = 2
# Structuring: repeated near-identical single-output sends, the smurfing signature. The band is
# relative, so the detector never needs to know the reporting threshold it is structured under.
STRUCT_MIN_TXNS: Final[int] = 3
STRUCT_MAX_CV: Final[float] = 0.15

TRANSACTION_COLUMNS: Final[tuple[str, ...]] = (
    "txid",
    "input_addresses",
    "output_amounts",
    "total_out_sats",
    "n_out",
    "is_coinbase",
    "has_equal_outputs",
)


def address_subject(clusters: pl.DataFrame, addresses: pl.DataFrame) -> pl.DataFrame:
    """One row per (address, subject_id): a JAAL cluster, or the address as its own singleton.

    The same subject grain BUDDHI scores on, restated here rather than imported so SHASTRA keeps
    reading only its own inputs. A clustered address takes its cluster id; every other address is
    its own subject under the `addr:` prefix, so every address maps to exactly one subject.
    """
    clustered = (
        clusters.select(
            pl.col("cluster_id").alias("subject_id"), pl.col("addresses").alias("address")
        )
        .explode("address")
        .drop_nulls("address")
    )
    singles = (
        addresses.select("address")
        .filter(~pl.col("address").is_in(clustered["address"]))
        .with_columns(("addr:" + pl.col("address")).alias("subject_id"))
    )
    return pl.concat([clustered, singles.select("subject_id", "address")])


def _sender_txns(transactions: pl.DataFrame, addr_subject: pl.DataFrame) -> pl.DataFrame:
    """One row per (subject_id, txid) the subject sent, carrying that transaction's morphology.

    A transaction is attributed to every distinct subject owning one of its input addresses. Most
    have one owner; a collaborative multi-input transaction has more, and attributing the shape to
    each is the honest reading, since each of them signed it.
    """
    spends = (
        transactions.filter(~pl.col("is_coinbase"))
        .select(
            "txid",
            "n_out",
            "total_out_sats",
            "has_equal_outputs",
            pl.col("output_amounts").list.min().alias("min_out_sats"),
            pl.col("input_addresses").alias("address"),
        )
        .explode("address")
    )
    return (
        spends.join(addr_subject, on="address", how="inner")
        .drop("address")
        .unique(subset=["subject_id", "txid"])
    )


def _hits(per_subject: pl.DataFrame, typology: str, threshold: float) -> pl.DataFrame:
    """Attach the contract columns to a frame that already has subject_id, txids and strength."""
    return per_subject.with_columns(
        pl.col("subject_id")
        .map_elements(
            lambda s: hashlib.sha256(f"{typology}:{s}".encode()).hexdigest()[:16],
            return_dtype=pl.String(),
        )
        .alias("hit_id"),
        pl.lit(typology).alias("typology"),
        pl.struct(
            threshold=pl.lit(float(threshold)),
            window_us=pl.lit(0, dtype=pl.Int64()),
        ).alias("params"),
    ).select("hit_id", "typology", "subject_id", "txids", "strength", "params")


def detect(
    transactions: pl.DataFrame, clusters: pl.DataFrame, addresses: pl.DataFrame
) -> pl.DataFrame:
    """Every typology hit in the capture, one row per (subject, typology).

    Deterministic, no labels.
    """
    addr_subject = address_subject(clusters, addresses)
    sent = _sender_txns(transactions, addr_subject)
    if sent.is_empty():
        return schema.empty(schema.TYPOLOGY_HITS_SCHEMA)

    fan = (
        sent.filter(pl.col("n_out") >= FAN_OUT_MIN_OUTPUTS)
        .group_by("subject_id")
        .agg(
            pl.col("txid").sort().alias("txids"),
            pl.col("n_out").max().cast(pl.Float64).alias("strength"),
        )
    )
    coinjoin = (
        sent.filter(pl.col("has_equal_outputs") & (pl.col("n_out") >= COINJOIN_MIN_OUTPUTS))
        .group_by("subject_id")
        .agg(pl.col("txid").sort().alias("txids"), pl.len().cast(pl.Float64).alias("strength"))
    )
    peel = (
        sent.filter(
            (pl.col("n_out") == 2)
            & (pl.col("min_out_sats") <= PEEL_MAX_SHARE * pl.col("total_out_sats"))
        )
        .group_by("subject_id")
        .agg(pl.col("txid").sort().alias("txids"), pl.len().cast(pl.Float64).alias("strength"))
        .filter(pl.col("strength") >= PEEL_MIN_TXNS)
    )
    struct = (
        sent.filter(pl.col("n_out") == 1)
        .group_by("subject_id")
        .agg(
            pl.col("txid").sort().alias("txids"),
            pl.len().alias("_n"),
            pl.col("total_out_sats").mean().alias("_mean"),
            pl.col("total_out_sats").cast(pl.Float64).std().alias("_std"),
        )
        .filter(
            (pl.col("_n") >= STRUCT_MIN_TXNS)
            & (pl.col("_mean") > 0)
            & (pl.col("_std").fill_null(0.0) <= STRUCT_MAX_CV * pl.col("_mean"))
        )
        .with_columns(pl.col("_n").cast(pl.Float64).alias("strength"))
        .select("subject_id", "txids", "strength")
    )

    hits = pl.concat(
        [
            _hits(fan, "fan_out", FAN_OUT_MIN_OUTPUTS),
            _hits(coinjoin, "coinjoin_like", COINJOIN_MIN_OUTPUTS),
            _hits(peel, "peel_chain", PEEL_MAX_SHARE),
            _hits(struct, "structuring", STRUCT_MAX_CV),
        ]
    )
    return schema.conform(hits.sort("typology", "subject_id"), schema.TYPOLOGY_HITS_SCHEMA)
