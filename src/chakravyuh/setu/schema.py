"""The four `normalised/` schemas, in contract section 4's column order.

Column order is part of the contract, not a stylistic choice: a parallel frontend track reads
these files and `contract-auditor` compares the order on disk against the document. Declaring
each schema as an ordered mapping and building every frame through it is what keeps the two in
step without anyone remembering to.
"""

from __future__ import annotations

from typing import Final

import polars as pl

STAGE: Final[str] = "setu"

ANNOUNCEMENTS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "row_id": pl.Int64(),
    "txid": pl.String(),
    "peer_ip": pl.String(),
    "peer_port": pl.Int32(),
    "observer_ip": pl.String(),
    "observer_port": pl.Int32(),
    "seen_us": pl.Int64(),
    "rank_in_tx": pl.Int32(),
    "delta_first_us": pl.Int64(),
    "geo_country": pl.String(),
    "asn": pl.Int32(),
    "as_org": pl.String(),
    "net_class": pl.String(),
    "peer_seen_count": pl.Int32(),
    "msg_type": pl.String(),
}

TRANSACTIONS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "txid": pl.String(),
    "first_seen_us": pl.Int64(),
    "last_seen_us": pl.Int64(),
    "n_announcements": pl.Int32(),
    "n_distinct_peers": pl.Int32(),
    "announce_spread_us": pl.Int64(),
    "input_addresses": pl.List(pl.String()),
    "output_addresses": pl.List(pl.String()),
    "input_amounts": pl.List(pl.Int64()),
    "output_amounts": pl.List(pl.Int64()),
    "n_in": pl.Int32(),
    "n_out": pl.Int32(),
    "total_in_sats": pl.Int64(),
    "total_out_sats": pl.Int64(),
    "fee_sats": pl.Int64(),
    "fee_rate_sat_vb": pl.Float64(),
    "is_coinbase": pl.Boolean(),
    "has_equal_outputs": pl.Boolean(),
    "change_index": pl.Int32(),
    "block_height": pl.Int32(),
}

ADDRESSES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "address": pl.String(),
    "script_type": pl.String(),
    "first_seen_us": pl.Int64(),
    "last_seen_us": pl.Int64(),
    "n_tx_in": pl.Int32(),
    "n_tx_out": pl.Int32(),
    "total_received_sats": pl.Int64(),
    "total_sent_sats": pl.Int64(),
    "balance_sats": pl.Int64(),
    "dwell_time_us": pl.Int64(),
}

PEERS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "peer_ip": pl.String(),
    "n_announcements": pl.Int32(),
    "n_txids": pl.Int32(),
    "mean_rank": pl.Float64(),
    "frac_rank_one": pl.Float64(),
    "distinct_ports": pl.Int32(),
    "geo_country": pl.String(),
    "asn": pl.Int32(),
    "as_org": pl.String(),
    "net_class": pl.String(),
    "first_us": pl.Int64(),
    "last_us": pl.Int64(),
}

OUTPUTS: Final[dict[str, dict[str, pl.DataType]]] = {
    "announcements.parquet": ANNOUNCEMENTS_SCHEMA,
    "transactions.parquet": TRANSACTIONS_SCHEMA,
    "addresses.parquet": ADDRESSES_SCHEMA,
    "peers.parquet": PEERS_SCHEMA,
}

NET_CLASSES: Final[frozenset[str]] = frozenset(
    {"residential", "hosting", "mobile", "tor_exit", "vpn_suspect", "unknown"}
)
"""Contract section 4's closed vocabulary. Null is not a member: it means "never classified"."""

REQUIRED_SEALED_COLUMNS: Final[tuple[str, ...]] = (
    "row_id",
    "ts_us",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
    "input_addresses",
    "output_addresses",
    "input_amounts",
    "output_amounts",
)
"""Without these there is no announcement. The optional extensions are read if present."""

OPTIONAL_SEALED_COLUMNS: Final[tuple[str, ...]] = (
    "geo_country",
    "asn",
    "msg_type",
    "vsize",
    "block_height",
    "script_types",
)


class SealedInputError(ValueError):
    """A `sealed/` directory SETU cannot normalise, named rather than guessed at."""


def conform(frame: pl.DataFrame, schema: dict[str, pl.DataType]) -> pl.DataFrame:
    """Select the schema's columns in its order and cast each to its declared type.

    Raises rather than filling: a column missing here is a bug in this stage, not a tolerance
    to absorb. The tolerance for absent columns belongs at intake, where the file arrives.
    """
    missing = [name for name in schema if name not in frame.columns]
    if missing:
        raise SealedInputError(f"cannot build frame, columns not derived: {', '.join(missing)}")
    return frame.select([pl.col(name).cast(dtype, strict=False) for name, dtype in schema.items()])
