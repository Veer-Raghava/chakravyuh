"""The three `graph/` schemas in contract section 5's column order, and the facts.

Column order is part of the contract, not a stylistic choice: a parallel frontend track reads
these files and `contract-auditor` compares the order on disk against the document. `conform()`
is restated here rather than imported from SETU because no stage imports another stage's
internals, and the duplication is the price of that rule.

Facts only. Everything this module emits carries `confidence` 1.0, because it was read off the
chain or off the capture. The inferred edges live in `cluster.py` and never reach 1.0.
"""

from __future__ import annotations

from typing import Final

import polars as pl

STAGE: Final[str] = "jaal"

# A vendored GeoIP table's claim about an address is not a fact the capture observed: the
# delegation may have changed since the table was cut. Section 5 reserves 1.0 for facts, so a
# HOSTED_IN edge built from a lookup sits just below it, which is enough for a console filtering
# on confidence to separate the two. Where the ASN arrived in the capture itself there was no
# lookup and the edge is an observation at 1.0. Unmeasured, and only ever an ordering.
HOSTING_CONFIDENCE: Final[float] = 0.95

NODES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "node_id": pl.String(),
    "kind": pl.String(),
    "label": pl.String(),
    "first_us": pl.Int64(),
    "last_us": pl.Int64(),
}

EDGES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "src": pl.String(),
    "dst": pl.String(),
    "kind": pl.String(),
    "ts_us": pl.Int64(),
    "sats": pl.Int64(),
    "confidence": pl.Float64(),
    "evidence": pl.String(),
}

CLUSTERS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "cluster_id": pl.String(),
    "addresses": pl.List(pl.String()),
    "n_addresses": pl.Int32(),
    "min_edge_confidence": pl.Float64(),
    "heuristics_used": pl.List(pl.String()),
    "threshold": pl.Float64(),
}

# Contract section 5's closed vocabularies. Anything outside these is a contract violation, so
# they are named once and asserted against rather than spelled out at each call site.
NODE_KINDS: Final[frozenset[str]] = frozenset({"address", "transaction", "peer", "cluster", "asn"})
EDGE_KINDS: Final[frozenset[str]] = frozenset(
    {"SPENDS", "RECEIVES", "ANNOUNCED_BY", "SAME_OWNER", "HOSTED_IN", "MEMBER_OF"}
)
EVIDENCE_KINDS: Final[frozenset[str]] = frozenset(
    {"multi_input", "change_addr", "observed", "geoip"}
)


class NormalisedInputError(ValueError):
    """A `normalised/` directory JAAL cannot build a graph from."""


def conform(frame: pl.DataFrame, schema: dict[str, pl.DataType]) -> pl.DataFrame:
    """`frame` selected in `schema`'s column order, each column cast to its declared type."""
    missing = [name for name in schema if name not in frame.columns]
    if missing:
        raise NormalisedInputError(f"cannot build frame, columns not derived: {', '.join(missing)}")
    return frame.select([pl.col(name).cast(dtype, strict=False) for name, dtype in schema.items()])


# Truncation, at write time rather than at render time. `label` is the one column contract
# section 5 calls a display label, and an investigator's console renders it directly, so a full
# identifier that reached this column would be a full identifier on a screen. The rules are
# CLAUDE.md's: IPv4 octets three and four become x, addresses keep first six and last four, txids
# keep first eight and last four. `node_id` keeps the full value because it is a join key, and
# `scripts/peek.py` truncates it on the way out.
def _label_expr(prefix: str, column: str) -> pl.Expr:
    """The `label` column for one node kind, already truncated."""
    value = pl.col(column).cast(pl.String())
    if prefix == "peer":
        # Two octets kept, the rest replaced. An IPv6 address is dotless, so the same replace
        # leaves it alone and the hextet rule below handles it.
        truncated = (
            pl.when(value.str.count_matches(r"\.") == 3)
            .then(value.str.replace(r"^(\d+\.\d+)\.\d+\.\d+$", "${1}.x.x"))
            .otherwise(value.str.replace(r"^([0-9a-fA-F]+:[0-9a-fA-F]*):.*$", "${1}:x:x"))
        )
    elif prefix == "tx":
        truncated = (
            pl.when(value.str.len_chars() >= 13)
            .then(value.str.slice(0, 8) + pl.lit("…") + value.str.slice(-4, 4))
            .otherwise(value)
        )
    elif prefix == "addr":
        truncated = (
            pl.when(value.str.len_chars() >= 11)
            .then(value.str.slice(0, 6) + pl.lit("…") + value.str.slice(-4, 4))
            .otherwise(value)
        )
    else:
        # asn and cluster are counters, not identifiers. Nothing to truncate.
        truncated = value
    return (pl.lit(f"{prefix}:") + truncated).alias("label")


def _nodes(
    frame: pl.DataFrame, prefix: str, kind: str, key: str, first: str, last: str
) -> pl.DataFrame:
    """One node per row of `frame`, which is already one row per distinct `key`."""
    return conform(
        frame.select(
            (pl.lit(f"{prefix}:") + pl.col(key).cast(pl.String())).alias("node_id"),
            pl.lit(kind).alias("kind"),
            _label_expr(prefix, key),
            pl.col(first).cast(pl.Int64()).alias("first_us"),
            pl.col(last).cast(pl.Int64()).alias("last_us"),
        ),
        NODES_SCHEMA,
    )


def address_nodes(addresses: pl.DataFrame) -> pl.DataFrame:
    """One node per row of `normalised/addresses.parquet`. Never fewer.

    The count is the assertion `scripts/check_graph.py` makes: a clustering implemented as a
    union-find merge would produce fewer address nodes than there are addresses, and that is
    precisely the failure contract section 5 forbids.
    """
    return _nodes(addresses, "addr", "address", "address", "first_seen_us", "last_seen_us")


def transaction_nodes(transactions: pl.DataFrame) -> pl.DataFrame:
    return _nodes(transactions, "tx", "transaction", "txid", "first_seen_us", "last_seen_us")


def peer_nodes(peers: pl.DataFrame) -> pl.DataFrame:
    return _nodes(peers, "peer", "peer", "peer_ip", "first_us", "last_us")


def asn_nodes(peers: pl.DataFrame) -> pl.DataFrame:
    """One node per distinct non-null ASN, spanning the window of every peer inside it.

    Null ASNs are the no-vendor path, which is every run in this repo today: `vendor/` is empty
    so `peers.asn` is entirely null and this returns zero rows. That is a graph with no ASN layer,
    not a broken graph, and the HOSTED_IN edges vanish with it.
    """
    span = (
        peers.filter(pl.col("asn").is_not_null())
        .group_by("asn")
        .agg(pl.col("first_us").min().alias("first_us"), pl.col("last_us").max().alias("last_us"))
        .sort("asn")
    )
    return _nodes(span, "asn", "asn", "asn", "first_us", "last_us")


def _value_edges(transactions: pl.DataFrame, side: str) -> pl.DataFrame:
    """`SPENDS` for inputs, `RECEIVES` for outputs. Direction follows the money.

    Contract section 5 splits what a caller might think of as one SPENDS_TO relation into two
    directed kinds, which is what makes the graph traversable in both directions without an edge
    carrying a sign.
    """
    spends = side == "input"
    exploded = (
        transactions.select(
            "txid",
            "first_seen_us",
            pl.col(f"{side}_addresses").alias("address"),
            pl.col(f"{side}_amounts").alias("sats"),
        )
        # Both lists are the same length by construction in SETU, so one explode over the pair
        # keeps each address beside its own amount.
        .explode("address", "sats")
        .filter(pl.col("address").is_not_null())
    )
    node = pl.lit("addr:") + pl.col("address")
    tx = pl.lit("tx:") + pl.col("txid")
    return conform(
        exploded.select(
            (node if spends else tx).alias("src"),
            (tx if spends else node).alias("dst"),
            pl.lit("SPENDS" if spends else "RECEIVES").alias("kind"),
            pl.col("first_seen_us").cast(pl.Int64()).alias("ts_us"),
            pl.col("sats").cast(pl.Int64()).alias("sats"),
            pl.lit(1.0).alias("confidence"),
            pl.lit("observed").alias("evidence"),
        ),
        EDGES_SCHEMA,
    )


def chain_edges(transactions: pl.DataFrame) -> pl.DataFrame:
    """Every input and output of every transaction, as directed value edges."""
    return pl.concat(
        [_value_edges(transactions, "input"), _value_edges(transactions, "output")]
    ).sort("src", "dst", "kind", "sats")


def announcement_edges(announcements: pl.DataFrame) -> pl.DataFrame:
    """One edge per distinct `(txid, peer_ip)`, carrying the earliest time that pair was seen.

    Deduplicated deliberately. A peer that re-announces the same transaction produces several
    capture rows, and an edge per row would make peer degree a count of packets rather than of
    transactions, which is the quantity the origin estimator cares about at S06.
    """
    pairs = (
        announcements.group_by("txid", "peer_ip")
        .agg(pl.col("seen_us").min().alias("ts_us"))
        .sort("txid", "peer_ip")
    )
    return conform(
        pairs.select(
            (pl.lit("tx:") + pl.col("txid")).alias("src"),
            (pl.lit("peer:") + pl.col("peer_ip")).alias("dst"),
            pl.lit("ANNOUNCED_BY").alias("kind"),
            pl.col("ts_us"),
            pl.lit(None).cast(pl.Int64()).alias("sats"),
            pl.lit(1.0).alias("confidence"),
            pl.lit("observed").alias("evidence"),
        ),
        EDGES_SCHEMA,
    )


def hosting_edges(peers: pl.DataFrame, from_lookup: bool) -> pl.DataFrame:
    """`peer:` to `asn:`, one per peer with a resolved ASN.

    `ts_us` is null because hosting is a state, not an event: the capture never observes the
    moment an address entered an AS.

    `from_lookup` is upstream's `optional_deps.geolite2`, and it decides both columns together.
    A vendored table's answer is `geoip` below 1.0, because a delegation can change between the
    table being cut and the capture being taken. An ASN the capture itself carried is `observed`
    at 1.0, because it was read off the wire at the moment in question. Writing `geoip` on a
    capture-carried value would have claimed a provenance this run does not have, which is what
    `contract-auditor` caught: `geolite2` false beside 171 `geoip` edges.
    """
    return conform(
        peers.filter(pl.col("asn").is_not_null())
        .sort("peer_ip")
        .select(
            (pl.lit("peer:") + pl.col("peer_ip")).alias("src"),
            (pl.lit("asn:") + pl.col("asn").cast(pl.String())).alias("dst"),
            pl.lit("HOSTED_IN").alias("kind"),
            pl.lit(None).cast(pl.Int64()).alias("ts_us"),
            pl.lit(None).cast(pl.Int64()).alias("sats"),
            pl.lit(HOSTING_CONFIDENCE if from_lookup else 1.0).alias("confidence"),
            pl.lit("geoip" if from_lookup else "observed").alias("evidence"),
        ),
        EDGES_SCHEMA,
    )
