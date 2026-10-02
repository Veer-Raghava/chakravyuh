"""Label-free candidate features with an explicit decision time and strict history cutoff.

Candidates use announcements received within a fixed horizon after first observation. Historical
peer/payer/ASN statistics use only events strictly before that first observation. The monitor
count is an explicit registry/config input, never inferred from the future capture. This module
is opt-in and is not yet the stage's default; saved historical models require their own recipe.
"""

from __future__ import annotations

import polars as pl

from chakravyuh.shastra.schema import HOSTING_CLASSES, NET_CLASS_CODES, TOR_CLASS


def _history_join(
    query: pl.DataFrame, history: pl.DataFrame, by: list[str], time_name: str
) -> pl.DataFrame:
    return query.sort("history_cutoff_us").join_asof(
        history.sort(time_name),
        left_on="history_cutoff_us",
        right_on=time_name,
        by=by,
        strategy="backward",
    )


def candidates(
    announcements: pl.DataFrame,
    peers: pl.DataFrame,
    transactions: pl.DataFrame,
    *,
    n_observers: int,
    horizon_us: int = 5_000_000,
    relay_delay_us: float = 2_000_000.0,
) -> pl.DataFrame:
    """One row per (transaction, observed peer), with evidence available by decision_us.

    Peer static metadata is assumed to be supplied by a fixed offline lookup snapshot. A mutable
    vendor database requires its own versioned, as-of snapshot; capture-derived histories are
    recomputed here, and no graph or full-window SETU statistics are consumed.
    """
    if n_observers < 1 or horizon_us < 0 or relay_delay_us <= 0:
        raise ValueError("positive observer count/delay and nonnegative horizon required")
    if announcements.is_empty():
        raise ValueError("candidate extraction requires at least one observation")
    first = announcements.group_by("txid").agg(pl.col("seen_us").min().alias("first_seen_us"))
    window = (
        announcements.join(first, on="txid")
        .filter(pl.col("seen_us") <= pl.col("first_seen_us") + horizon_us)
        .with_columns(
            (pl.col("seen_us") - pl.col("first_seen_us")).alias("delta_first_us"),
            pl.col("seen_us").rank(method="min").over("txid").cast(pl.Int32()).alias("rank_in_tx"),
        )
    )
    grouped = window.group_by("txid", "peer_ip").agg(
        pl.col("row_id").min(),
        pl.col("seen_us").min(),
        pl.col("seen_us").max().alias("last_evidence_us"),
        pl.col("first_seen_us").first(),
        pl.col("delta_first_us").min(),
        pl.col("rank_in_tx").min(),
        pl.len().cast(pl.Int32()).alias("n_announcements"),
        pl.col("observer_ip").n_unique().cast(pl.Int32()).alias("n_observers_seen"),
        (pl.col("seen_us").max() - pl.col("seen_us").min()).alias("announce_spread_us"),
        pl.col("seen_us").sum().alias("_seen_sum"),
    )
    payer = transactions.select("txid", pl.col("input_addresses").list.first().alias("payer"))
    per_tx = window.group_by("txid").agg(
        pl.col("observer_ip").n_unique().cast(pl.Int32()).alias("n_observers_in_tx")
    )
    query = (
        grouped.join(peers.select("peer_ip", "asn", "net_class"), on="peer_ip", how="left")
        .join(payer, on="txid", how="left")
        .join(per_tx, on="txid")
        .with_columns(
            (pl.col("first_seen_us") - 1).alias("history_cutoff_us"),
            (pl.col("first_seen_us") + horizon_us).alias("decision_us"),
            pl.len().over("txid").cast(pl.Int32()).alias("n_candidates"),
        )
    )
    events = window.sort("seen_us", "row_id").with_columns(
        (pl.col("rank_in_tx") == 1).cast(pl.Int64()).alias("_rank_one")
    )
    peer_history = events.with_columns(
        pl.col("peer_ip").cum_count().over("peer_ip").alias("_peer_observations"),
        pl.col("_rank_one").cum_sum().over("peer_ip").alias("_peer_firsts"),
    ).select(
        "peer_ip",
        pl.col("seen_us").alias("peer_history_us"),
        (pl.col("_peer_firsts") / pl.col("_peer_observations")).alias("peer_frac_rank_one"),
    )
    distinct_history = (
        grouped.sort("seen_us", "txid", "peer_ip")
        .with_columns(
            pl.col("txid").cum_count().over("peer_ip").cast(pl.Int32()).alias("peer_n_txids")
        )
        .select("peer_ip", pl.col("seen_us").alias("peer_distinct_us"), "peer_n_txids")
    )
    payer_history = (
        grouped.join(payer, on="txid")
        .drop_nulls("payer")
        .sort("seen_us", "txid", "peer_ip")
        .with_columns(
            pl.col("txid")
            .cum_count()
            .over("payer", "peer_ip")
            .cast(pl.Int32())
            .alias("payer_shared")
        )
        .select("payer", "peer_ip", pl.col("seen_us").alias("payer_history_us"), "payer_shared")
    )
    asn_events = (
        events.join(peers.select("peer_ip", "asn"), on="peer_ip")
        .drop_nulls("asn")
        .sort("seen_us", "row_id")
    )
    asn_history = asn_events.with_columns(
        pl.col("asn").cum_count().over("asn").alias("_asn_observations"),
        pl.col("_rank_one").cum_sum().over("asn").alias("_asn_firsts"),
    ).select(
        "asn",
        pl.col("seen_us").alias("asn_history_us"),
        (pl.col("_asn_firsts") / pl.col("_asn_observations")).alias("asn_frac_rank_one"),
    )
    query = _history_join(query, peer_history, ["peer_ip"], "peer_history_us")
    query = _history_join(query, distinct_history, ["peer_ip"], "peer_distinct_us")
    query = _history_join(query, payer_history, ["payer", "peer_ip"], "payer_history_us")
    query = _history_join(query, asn_history, ["asn"], "asn_history_us")
    result = (
        query.with_columns(
            pl.col("peer_frac_rank_one").fill_null(0.0),
            pl.col("peer_n_txids").fill_null(0),
            pl.col("payer_shared").fill_null(0),
            pl.col("asn_frac_rank_one").fill_null(0.0),
            (pl.lit(n_observers) - pl.col("n_observers_seen"))
            .clip(lower_bound=0)
            .cast(pl.Int32())
            .alias("n_observers_blind"),
            (pl.col("net_class") == TOR_CLASS).fill_null(False).alias("is_tor_exit"),
            pl.col("net_class").is_in(list(HOSTING_CLASSES)).fill_null(False).alias("is_hosting"),
            pl.col("net_class")
            .replace_strict(NET_CLASS_CODES, default=0, return_dtype=pl.Int32())
            .alias("net_class_code"),
            pl.max_horizontal(
                "peer_history_us", "peer_distinct_us", "payer_history_us", "asn_history_us"
            ).alias("max_history_us"),
        )
        .with_columns(
            (
                pl.col("peer_n_txids")
                + ((pl.col("peer_n_txids") > 0) & pl.col("asn").is_not_null()).cast(pl.Int32())
            ).alias("peer_degree"),
            (
                pl.col("n_observers_seen") * (pl.col("peer_frac_rank_one") + 1e-12).log()
                - pl.col("delta_first_us") / relay_delay_us
                - (pl.col("_seen_sum") / pl.col("n_announcements") - pl.col("seen_us"))
                / relay_delay_us
            ).alias("mle_logscore"),
        )
        .drop(
            "_seen_sum", "peer_history_us", "peer_distinct_us", "payer_history_us", "asn_history_us"
        )
    )
    if result.filter(pl.col("max_history_us") >= pl.col("first_seen_us")).height:
        raise AssertionError("history reached the transaction being predicted")
    if result.filter(pl.col("last_evidence_us") > pl.col("decision_us")).height:
        raise AssertionError("candidate evidence extends beyond the decision horizon")
    return result.sort("txid", "peer_ip")
