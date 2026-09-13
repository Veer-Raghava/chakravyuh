"""The grain split, as pure frame-to-frame functions.

One sealed row is one announcement of one transaction by one peer. This module turns that
single table into the four of contract section 4: the announcement grain, the transaction
grain, and the two entity grains derived from them. Nothing here writes a file and nothing here
reads one, which is what lets the tests hand these functions a six-row frame.

Every aggregate is a group-by. A per-transaction loop over announcements is the trap the stage
brief names, and at a million rows it is also the difference between seconds and an afternoon.
Every output is sorted on its primary key before it is returned: group-by output order is not
guaranteed, and the gate compares two runs byte for byte.
"""

from __future__ import annotations

from typing import Final

import polars as pl

from chakravyuh.setu import schema
from chakravyuh.setu.enrich import Enricher

CHANGE_UNDETERMINED: Final[int] = -1
"""Contract section 4's sentinel. Distinct from output 0, which is a real index."""

ROUND_SATS: Final[int] = 1000
"""A payment tends to be chosen by a human and lands on a round figure; change is whatever is
left after the fee and does not. This is the only change signal available from one transaction
in isolation, and it is deliberately weak: S05 owns the real heuristic, which needs the graph."""

_SCRIPT_TYPE_FROM_ADDRESS: Final[pl.Expr] = (
    pl.when(pl.col("address").str.starts_with("bc1p"))
    .then(pl.lit("p2tr"))
    .when(pl.col("address").str.starts_with("bc1q") & (pl.col("address").str.len_chars() == 42))
    .then(pl.lit("p2wpkh"))
    .when(pl.col("address").str.starts_with("bc1q") & (pl.col("address").str.len_chars() == 62))
    .then(pl.lit("p2wsh"))
    .when(pl.col("address").str.starts_with("3"))
    .then(pl.lit("p2sh"))
    .when(pl.col("address").str.starts_with("1"))
    .then(pl.lit("p2pkh"))
    .otherwise(None)
)
"""Bech32 splits on length, not prefix: 42 characters is a 20-byte witness program and 62 is a
32-byte one, and `bc1q` alone cannot tell them apart. Used only where `script_types` was absent
from the capture."""


def _optional(frame: pl.DataFrame, name: str, dtype: pl.DataType) -> pl.Expr:
    """The named column, or a typed all-null stand-in when the capture never carried it."""
    if name in frame.columns:
        return pl.col(name).cast(dtype, strict=False)
    return pl.lit(None, dtype=dtype).alias(name)


def peer_facts(ips: list[str], enricher: Enricher) -> pl.DataFrame:
    """One row per distinct peer IP: what `vendor/` says about it.

    Built over distinct IPs rather than announcements, which is the whole reason the lookup can
    be a plain `bisect` instead of an interval join. Column names carry a `v_` prefix so the
    join site has to decide explicitly whether the capture's own value or the vendored one wins.
    """
    facts = [enricher.lookup(ip) for ip in ips]
    return pl.DataFrame(
        {
            "peer_ip": ips,
            "v_geo_country": [fact.geo_country for fact in facts],
            "v_asn": [fact.asn for fact in facts],
            "as_org": [fact.as_org for fact in facts],
            "net_class": [fact.net_class for fact in facts],
        },
        schema={
            "peer_ip": pl.String(),
            "v_geo_country": pl.String(),
            "v_asn": pl.Int32(),
            "as_org": pl.String(),
            "net_class": pl.String(),
        },
    )


def base_announcements(rows: pl.DataFrame) -> pl.DataFrame:
    """The announcement grain, before enrichment. One row in, one row out, always.

    `rank_in_tx` uses min-ranking, so two peers announcing in the same microsecond are both
    rank 1. An ordinal rank would break that tie on file order, which would put file order into
    `frac_rank_one` and from there into the origin estimator's features.
    """
    missing = [name for name in schema.REQUIRED_SEALED_COLUMNS if name not in rows.columns]
    if missing:
        raise schema.SealedInputError(
            f"sealed/rows.parquet is missing {', '.join(missing)}. SETU reads the output of "
            "KAVACH, which always emits contract section 3's columns."
        )
    return (
        rows.select(
            pl.col("row_id"),
            pl.col("txid"),
            pl.col("src_ip").alias("peer_ip"),
            pl.col("src_port").cast(pl.Int32, strict=False).alias("peer_port"),
            pl.col("dst_ip").alias("observer_ip"),
            pl.col("dst_port").cast(pl.Int32, strict=False).alias("observer_port"),
            pl.col("ts_us").alias("seen_us"),
            _optional(rows, "geo_country", pl.String()),
            _optional(rows, "asn", pl.Int32()),
            _optional(rows, "msg_type", pl.String()),
        )
        .with_columns(
            rank_in_tx=pl.col("seen_us").rank(method="min").over("txid").cast(pl.Int32),
            delta_first_us=pl.col("seen_us") - pl.col("seen_us").min().over("txid"),
        )
        .sort("row_id")
    )


def peers(base: pl.DataFrame, facts: pl.DataFrame) -> pl.DataFrame:
    """One row per distinct peer IP, per contract section 4.

    `frac_rank_one` is the feature this table exists for: a peer that is consistently the first
    announcement seen is either close to our observers or actually originating traffic, and
    telling those apart is what S06 is for.
    """
    aggregated = base.group_by("peer_ip").agg(
        n_announcements=pl.len().cast(pl.Int32),
        n_txids=pl.col("txid").n_unique().cast(pl.Int32),
        mean_rank=pl.col("rank_in_tx").mean(),
        frac_rank_one=(pl.col("rank_in_tx") == 1).mean(),
        distinct_ports=pl.col("peer_port").n_unique().cast(pl.Int32),
        in_geo_country=pl.col("geo_country").drop_nulls().first(),
        in_asn=pl.col("asn").drop_nulls().first(),
        first_us=pl.col("seen_us").min(),
        last_us=pl.col("seen_us").max(),
    )
    return schema.conform(
        aggregated.join(facts, on="peer_ip", how="left").with_columns(
            # The capture's own value wins where it has one: contract section 4 says geo and
            # ASN are "enriched if null on input", not overwritten. A real NTRO file may carry
            # an ASN resolved at capture time, which is closer to the truth than a later lookup.
            geo_country=pl.coalesce("in_geo_country", "v_geo_country"),
            asn=pl.coalesce("in_asn", "v_asn"),
        ),
        schema.PEERS_SCHEMA,
    ).sort("peer_ip")


def announcements(base: pl.DataFrame, peer_table: pl.DataFrame) -> pl.DataFrame:
    """The announcement grain with per-peer facts attached. Row count is preserved exactly."""
    attached = base.join(
        peer_table.select(
            "peer_ip",
            pl.col("geo_country").alias("p_geo_country"),
            pl.col("asn").alias("p_asn"),
            "as_org",
            "net_class",
            pl.col("n_txids").alias("peer_seen_count"),
        ),
        on="peer_ip",
        how="left",
    ).with_columns(
        geo_country=pl.coalesce("geo_country", "p_geo_country"),
        asn=pl.coalesce("asn", "p_asn"),
    )
    return schema.conform(attached, schema.ANNOUNCEMENTS_SCHEMA).sort("row_id")


def _change_index(txs: pl.DataFrame) -> pl.DataFrame:
    """`txid` to the suspected change output index, or -1.

    A candidate is an output paying an address that is not one of this transaction's own inputs
    and whose value is not a round number of satoshis. Exactly one candidate is a finding; none
    or several is `-1`, because this stage would rather say nothing than guess. The rule is
    deliberately conservative: a change index that is nearly always right for a structural
    reason would hand S05's clustering a free answer and make its measured precision a lie.
    """
    exploded = (
        txs.select("txid", "input_addresses", "output_addresses", "output_amounts")
        .with_columns(out_index=pl.int_ranges(0, pl.col("output_addresses").list.len()))
        .explode("output_addresses", "output_amounts", "out_index")
    )
    candidates = exploded.filter(
        (pl.col("output_amounts") % ROUND_SATS != 0)
        & ~pl.col("input_addresses").list.contains(pl.col("output_addresses"))
    )
    return candidates.group_by("txid").agg(
        n_candidates=pl.len(),
        candidate_index=pl.col("out_index").min().cast(pl.Int32),
    )


def transactions(rows: pl.DataFrame) -> pl.DataFrame:
    """The transaction grain, one row per distinct txid.

    The chain columns are taken from the first row of each group rather than reconciled across
    the group. KAVACH has already quarantined every txid whose rows disagreed about them, so by
    the time a row reaches here the group is internally consistent by construction.
    """
    # Materialised before the group-by rather than inside it: a literal has nothing to
    # aggregate, so `pl.lit(None).first()` is an error rather than a null.
    rows = rows.with_columns(
        _optional(rows, "vsize", pl.Int32()),
        _optional(rows, "block_height", pl.Int32()),
    )
    grouped = rows.group_by("txid").agg(
        first_seen_us=pl.col("ts_us").min(),
        last_seen_us=pl.col("ts_us").max(),
        n_announcements=pl.len().cast(pl.Int32),
        n_distinct_peers=pl.col("src_ip").n_unique().cast(pl.Int32),
        input_addresses=pl.col("input_addresses").first(),
        output_addresses=pl.col("output_addresses").first(),
        input_amounts=pl.col("input_amounts").first(),
        output_amounts=pl.col("output_amounts").first(),
        vsize=pl.col("vsize").first(),
        block_height=pl.col("block_height").first(),
    )
    derived = grouped.with_columns(
        announce_spread_us=pl.col("last_seen_us") - pl.col("first_seen_us"),
        n_in=pl.col("input_addresses").list.len().cast(pl.Int32),
        n_out=pl.col("output_addresses").list.len().cast(pl.Int32),
        total_in_sats=pl.col("input_amounts").list.sum(),
        total_out_sats=pl.col("output_amounts").list.sum(),
        has_equal_outputs=pl.col("output_amounts").list.n_unique()
        < pl.col("output_amounts").list.len(),
    ).with_columns(
        is_coinbase=pl.col("n_in") == 0,
        # Derived, never read from the capture's optional `fee_sats`. Inputs minus outputs is
        # the definition; a carried column that disagrees with it would be the one worth
        # doubting. Coinbase has no inputs, so its fee is zero rather than a negative number.
        fee_sats=pl.when(pl.col("n_in") == 0)
        .then(pl.lit(0, dtype=pl.Int64))
        .otherwise(pl.col("total_in_sats") - pl.col("total_out_sats")),
    )
    with_rate = derived.with_columns(
        fee_rate_sat_vb=pl.when(pl.col("vsize").is_null() | (pl.col("vsize") <= 0))
        .then(None)
        .otherwise(pl.col("fee_sats") / pl.col("vsize"))
    )
    with_change = with_rate.join(_change_index(with_rate), on="txid", how="left").with_columns(
        change_index=pl.when((pl.col("n_candidates") == 1) & (pl.col("n_out") >= 2))
        .then(pl.col("candidate_index"))
        .otherwise(pl.lit(CHANGE_UNDETERMINED, dtype=pl.Int32))
    )
    return schema.conform(with_change, schema.TRANSACTIONS_SCHEMA).sort("txid")


def _sides(txs: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Every (address, amount, time) an address was spent at, and every one it was paid at."""
    spent = (
        txs.select("txid", "first_seen_us", "input_addresses", "input_amounts")
        .explode("input_addresses", "input_amounts")
        .rename({"input_addresses": "address", "input_amounts": "sats"})
        .drop_nulls("address")
    )
    received = (
        txs.select("txid", "first_seen_us", "output_addresses", "output_amounts")
        .explode("output_addresses", "output_amounts")
        .rename({"output_addresses": "address", "output_amounts": "sats"})
        .drop_nulls("address")
    )
    return spent, received


def _dwell(spent: pl.DataFrame, received: pl.DataFrame) -> pl.DataFrame:
    """Median microseconds an address held value before spending it, within this capture.

    Each spend is matched to the most recent payment into that same address using an as-of
    join, and the median is taken over those gaps. Null where an address only ever received or
    only ever spent, which is the common case at the edges of a capture window: coins funded
    before it opened have no visible receipt here, and saying nothing is the correct answer.
    """
    if spent.height == 0 or received.height == 0:
        return pl.DataFrame(schema={"address": pl.String(), "dwell_time_us": pl.Int64()})
    matched = (
        spent.select("address", "first_seen_us")
        .sort("first_seen_us")
        .join_asof(
            received.select("address", pl.col("first_seen_us").alias("paid_us")).sort("paid_us"),
            left_on="first_seen_us",
            right_on="paid_us",
            by="address",
            strategy="backward",
        )
    )
    return (
        matched.drop_nulls("paid_us")
        .with_columns(gap=pl.col("first_seen_us") - pl.col("paid_us"))
        .group_by("address")
        .agg(dwell_time_us=pl.col("gap").median().cast(pl.Int64))
    )


def declared_script_types(rows: pl.DataFrame) -> pl.DataFrame:
    """Address to the script type the capture declared for it, from the optional column.

    Read from the sealed rows rather than from `transactions.parquet`, because `script_types`
    is one of our optional extensions and contract section 4 has no column for it. Rows whose
    `script_types` list does not line up with their outputs are skipped: a mismatched pair
    cannot be zipped, and inventing an alignment would mislabel an address.
    """
    empty = pl.DataFrame(schema={"address": pl.String(), "declared_script_type": pl.String()})
    if "script_types" not in rows.columns:
        return empty
    return (
        rows.filter(pl.col("script_types").list.len() == pl.col("output_addresses").list.len())
        .unique(subset="txid", keep="first")
        .select("output_addresses", "script_types")
        .explode("output_addresses", "script_types")
        .rename({"output_addresses": "address", "script_types": "declared_script_type"})
        .drop_nulls("address")
        .group_by("address")
        .agg(declared_script_type=pl.col("declared_script_type").drop_nulls().first())
    )


def addresses(txs: pl.DataFrame, declared: pl.DataFrame) -> pl.DataFrame:
    """One row per distinct address, per contract section 4.

    `balance_sats` is received minus sent **within this capture only**. An address funded
    before the capture opened will show a negative balance here, and that is the honest value:
    the alternative is to invent a starting balance nobody observed.
    """
    spent, received = _sides(txs)
    out_side = received.group_by("address").agg(
        n_tx_out=pl.col("txid").n_unique().cast(pl.Int32),
        total_received_sats=pl.col("sats").sum(),
        out_first=pl.col("first_seen_us").min(),
        out_last=pl.col("first_seen_us").max(),
    )
    in_side = spent.group_by("address").agg(
        n_tx_in=pl.col("txid").n_unique().cast(pl.Int32),
        total_sent_sats=pl.col("sats").sum(),
        in_first=pl.col("first_seen_us").min(),
        in_last=pl.col("first_seen_us").max(),
    )
    joined = (
        out_side.join(in_side, on="address", how="full", coalesce=True)
        .join(declared, on="address", how="left")
        .join(_dwell(spent, received), on="address", how="left")
        .with_columns(
            n_tx_in=pl.col("n_tx_in").fill_null(0),
            n_tx_out=pl.col("n_tx_out").fill_null(0),
            total_received_sats=pl.col("total_received_sats").fill_null(0),
            total_sent_sats=pl.col("total_sent_sats").fill_null(0),
        )
        .with_columns(
            first_seen_us=pl.min_horizontal("out_first", "in_first"),
            last_seen_us=pl.max_horizontal("out_last", "in_last"),
            balance_sats=pl.col("total_received_sats") - pl.col("total_sent_sats"),
            script_type=pl.coalesce("declared_script_type", _SCRIPT_TYPE_FROM_ADDRESS),
        )
    )
    return schema.conform(joined, schema.ADDRESSES_SCHEMA).sort("address")
