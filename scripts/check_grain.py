"""Check that a SETU grain split preserved what it must, reading both sides from disk.

`check_stage.py` checks a stage against its own `_meta.json`. This checks `normalised/`
against the `sealed/` directory it came from, which is the one thing a stage cannot assert
about itself: a reshape that lost rows would record the loss consistently in both places.

Four things:

1. one sealed row is one announcement, and both agree with `counts.in` and `counts.out`
2. one distinct txid is one transaction row
3. one distinct `src_ip` is one peer row
4. when `_meta.json` says enrichment found nothing, `as_org` and `net_class` are wholly null
   and the warning is on the record, so the degraded path is exercised and not merely claimed

Writes counts and column names to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

NULL_WITHOUT_VENDOR = ("as_org", "net_class")
NO_VENDOR_WARNING = "enrichment_unavailable_geo_asn_net_class_are_null"


def _rows(path: Path) -> int:
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    return int(pq.ParquetFile(path).metadata.num_rows)


def _distinct(path: Path, column: str) -> int:
    """Distinct values in one column. One column is read, never the whole file."""
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=[column])
    return int(len(table.column(column).unique()))


def _nulls(path: Path, column: str) -> tuple[int, int]:
    """`(nulls, rows)` for one column."""
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=[column])
    return int(table.column(column).null_count), int(table.num_rows)


def check(sealed: Path, normalised: Path) -> list[str]:
    """Every way the split failed to preserve a count. Empty means it holds."""
    rows_file = sealed / "rows.parquet"
    if not rows_file.is_file():
        return [f"no rows.parquet in {sealed}"]
    meta_path = normalised / "_meta.json"
    if not meta_path.is_file():
        return [f"no _meta.json in {normalised}"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    problems: list[str] = []
    sealed_rows = _rows(rows_file)
    expected = {
        "announcements.parquet": (sealed_rows, "sealed rows"),
        "transactions.parquet": (_distinct(rows_file, "txid"), "distinct txids"),
        "peers.parquet": (_distinct(rows_file, "src_ip"), "distinct peers"),
    }
    for name, (want, what) in expected.items():
        target = normalised / name
        if not target.is_file():
            problems.append(f"{name} does not exist")
            continue
        got = _rows(target)
        if got != want:
            problems.append(f"{name} holds {got} rows, sealed/ holds {want} {what}")

    counts = meta.get("counts", {})
    if counts.get("in") != sealed_rows:
        problems.append(f"counts.in is {counts.get('in')}, sealed/rows.parquet holds {sealed_rows}")
    if counts.get("out") != sealed_rows:
        problems.append(f"counts.out is {counts.get('out')}, and no announcement may be dropped")

    enrichment = meta.get("params", {}).get("enrichment", {})
    if enrichment and not any(enrichment.values()):
        if NO_VENDOR_WARNING not in meta.get("warnings", []):
            problems.append(
                f"enrichment found nothing but {NO_VENDOR_WARNING} is not in warnings. A silent "
                "fallback is how a demo ships with every geo column empty and nobody noticing."
            )
        peers = normalised / "peers.parquet"
        if peers.is_file():
            for column in NULL_WITHOUT_VENDOR:
                nulls, total = _nulls(peers, column)
                if nulls != total:
                    problems.append(
                        f"no vendored list was read, but peers.{column} is filled on "
                        f"{total - nulls} of {total} rows"
                    )

    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        sys.stderr.write("usage: check_grain.py <sealed-dir> <normalised-dir>\n")
        return 2
    sealed, normalised = Path(args[0]), Path(args[1])
    for root in (sealed, normalised):
        if not root.is_dir():
            sys.stderr.write(f"check_grain: {root} is not a directory\n")
            return 2

    problems = check(sealed, normalised)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_grain: {len(problems)} problems in {normalised}\n")
        return 1
    sys.stderr.write(
        f"check_grain: {_rows(sealed / 'rows.parquet')} sealed rows became "
        f"{_rows(normalised / 'announcements.parquet')} announcements and "
        f"{_rows(normalised / 'transactions.parquet')} transactions\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
