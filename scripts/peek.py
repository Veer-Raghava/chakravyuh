#!/usr/bin/env python3
"""Inspect a Parquet or CSV file without ever emitting a complete identifier.

This is the only sanctioned way to look at pipeline data. Prints the row count, every
column with its dtype and null count, and three sample rows with identifiers truncated
per CLAUDE.md: IPv4 keeps two octets, IPv6 keeps two hextets, addresses keep first six
and last four, txids keep first eight and last four. SHA-256 values, Merkle roots and
signatures print in full, because a truncated hash cannot be verified and that is the
whole reason those columns exist.

There is deliberately no flag that defeats truncation. If a stage needs untruncated
values, it reads the Parquet file directly in code; nothing needs them on a screen.

Redaction routes by column name before it looks at the value, because a txid and a
SHA-256 are both sixty-four lowercase hex characters and no rule that inspects only the
value can tell them apart.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IPV4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
# Hex digits and colons only. An ISO 8601 timestamp also contains two colons, and without
# this constraint the value-shape fallback truncates every timestamp in the file.
_IPV6ISH = re.compile(r"^[0-9a-fA-F:]+$")
_ADDRISH = re.compile(r"^(bc1|[13])[A-Za-z0-9]{9,}$")

# The deliberate exception to the truncation rule.
_HASH_COLUMNS = frozenset(
    {
        "sha256",
        "hash",
        "merkle_root",
        "prev_root",
        "leaf_hash",
        "expected_packet_sha256",
        "input_sha256",
        "signature",
        "pubkey",
    }
)
_TXID_COLUMNS = frozenset({"txid", "txids", "origin_txid"})
_IP_COLUMNS = frozenset(
    {
        "src_ip",
        "dst_ip",
        "peer_ip",
        "observer_ip",
        "ips",
        "origin_peer_ip",
        "runner_up_peer_ip",
        "true_origin_ip",
    }
)
_ADDR_COLUMNS = frozenset(
    {
        "address",
        "addresses",
        "input_addresses",
        "output_addresses",
        "addresses_redacted",
    }
)
_MAX_LIST_ITEMS = 3
_MAX_TEXT = 80


def truncate_ip(value: str) -> str:
    """IPv4 keeps two octets, IPv6 keeps two hextets.

    CLAUDE.md specifies the IPv4 rule only. The IPv6 rule here is the same idea applied to
    the same fraction of the address; docs/DECISIONS.md records that it was chosen and not
    inherited from a contract.
    """
    if _IPV4.match(value):
        first, second = value.split(".")[:2]
        return f"{first}.{second}.x.x"
    if ":" in value:
        return ":".join(value.split(":")[:2]) + ":x"
    return value


def truncate_address(value: str) -> str:
    """First six and last four. Strings too short to be an address pass through."""
    return value if len(value) < 11 else f"{value[:6]}…{value[-4:]}"


def truncate_txid(value: str) -> str:
    """First eight and last four. Strings too short to be a txid pass through."""
    return value if len(value) < 13 else f"{value[:8]}…{value[-4:]}"


_NODE_KIND = {"peer": truncate_ip, "addr": truncate_address, "tx": truncate_txid}


def redact(column: str, value: object) -> str:
    """Render one cell as a string that contains no complete identifier.

    Precedence: hash allowlist, then the `kind:value` node id form the graph stage uses,
    then the column-name tables, then the shape of the value itself. Column name wins over
    value shape on purpose, so a new hash column can be allowlisted by name rather than by
    hoping its bytes look different from a txid.
    """
    if value is None:
        return ""
    if isinstance(value, (list | tuple)):
        items = [redact(column, v) for v in value[:_MAX_LIST_ITEMS]]
        extra = len(value) - _MAX_LIST_ITEMS
        return "[" + ", ".join(items) + (f", (+{extra} more)" if extra > 0 else "") + "]"
    if column in _HASH_COLUMNS:
        return str(value)

    text = str(value)
    kind, sep, rest = text.partition(":")
    if sep and kind in _NODE_KIND:
        return f"{kind}:{_NODE_KIND[kind](rest)}"
    if column in _TXID_COLUMNS:
        return truncate_txid(text)
    if column in _IP_COLUMNS:
        return truncate_ip(text)
    if column in _ADDR_COLUMNS:
        return truncate_address(text)

    # Value-shape fallback, for columns no contract has named yet. Numeric strings are
    # excluded first: a large satoshi amount matches the base58 address pattern.
    if not text.isdigit():
        if _HEX64.match(text):
            return truncate_txid(text)
        if _IPV4.match(text) or (text.count(":") >= 2 and _IPV6ISH.match(text)):
            return truncate_ip(text)
        if _ADDRISH.match(text):
            return truncate_address(text)
    return text if len(text) <= _MAX_TEXT else text[: _MAX_TEXT - 3] + "..."


class Table(NamedTuple):
    n_rows: int
    columns: list[tuple[str, str]]
    nulls: dict[str, int]
    sample: list[dict[str, Any]]


def _load_csv(path: Path) -> Table:
    """Read a CSV with the standard library, so peek works before uv sync ever runs.

    CSV carries no types, so dtypes here are inferred from the values and labelled as such.
    """
    # ponytail: full scan to count rows and nulls. Fine at fixture scale; switch to
    # pl.scan_csv at S10 if a million-row CSV ever needs peeking.
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        names = list(reader.fieldnames or [])
        nulls = dict.fromkeys(names, 0)
        all_int = dict.fromkeys(names, True)
        any_list = dict.fromkeys(names, False)
        sample: list[dict[str, Any]] = []
        n_rows = 0
        for row in reader:
            n_rows += 1
            for name in names:
                cell = row.get(name) or ""
                if cell == "":
                    nulls[name] += 1
                    continue
                if "|" in cell:
                    any_list[name] = True
                if all_int[name] and not cell.lstrip("-").isdigit():
                    all_int[name] = False
            if len(sample) < 3:
                sample.append({n: (row.get(n) or None) for n in names})

    columns = [
        (n, "list (inferred)" if any_list[n] else ("i64 (inferred)" if all_int[n] else "str"))
        for n in names
    ]
    # Undo the pipe encoding for the sample only, so redact() recurses per element instead
    # of truncating one long joined string. A column whose every cell held a single element
    # is not detected as a list; that renders as a plain string and redacts correctly anyway.
    for row in sample:
        for name in names:
            cell = row[name]
            if any_list[name] and isinstance(cell, str):
                row[name] = cell.split("|")
    return Table(n_rows=n_rows, columns=columns, nulls=nulls, sample=sample)


def _load_parquet(path: Path) -> Table:
    """Read a Parquet file lazily, so peeking a large file does not materialise it."""
    import polars as pl  # imported here so the CSV path has no third-party dependency

    frame = pl.scan_parquet(path)
    schema = frame.collect_schema()
    n_rows = int(frame.select(pl.len()).collect().item())
    null_row = frame.select(pl.all().null_count()).collect().row(0)
    names = list(schema.names())
    return Table(
        n_rows=n_rows,
        columns=[(n, str(schema[n])) for n in names],
        nulls=dict(zip(names, (int(v) for v in null_row), strict=True)),
        sample=frame.head(3).collect().to_dicts(),
    )


def load(path: Path) -> Table:
    if path.suffix == ".parquet":
        return _load_parquet(path)
    if path.suffix in {".csv", ".tsv"}:
        return _load_csv(path)
    raise ValueError(f"peek understands .parquet and .csv, not {path.suffix!r}")


def render(path: Path, table: Table) -> str:
    """Build the whole report as one string, so tests can assert on it without capturing
    stdout and so nothing can be emitted that has not passed through redact()."""
    width = max((len(name) for name, _ in table.columns), default=1)
    lines = [str(path), f"rows: {table.n_rows}", "", f"columns: {len(table.columns)}"]
    for name, dtype in table.columns:
        lines.append(f"  {name:<{width}}  {dtype:<16}  nulls {table.nulls.get(name, 0)}")
    lines += ["", f"sample: {len(table.sample)} rows, identifiers truncated"]
    for i, row in enumerate(table.sample):
        lines.append(f"  [{i}]")
        for name, _ in table.columns:
            lines.append(f"    {name:<{width}}  {redact(name, row.get(name))}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Parquet or CSV file, redacted.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    path: Path = args.path
    if not path.exists():
        print(f"peek: no such file: {path}")
        return 1
    print(render(path, load(path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
