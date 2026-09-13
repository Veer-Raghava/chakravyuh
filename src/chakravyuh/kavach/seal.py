"""Hash, read, coerce, route and account for every row of someone else's capture.

The order of the first two verbs is the whole custody claim. `sealed/INPUT.sha256` is written
from the bytes as delivered, before a reader is constructed, so the hash in the S09 evidence
packet is a statement about the file that arrived rather than about whatever survived parsing.
`tests/test_kavach.py` asserts that order by breaking the reader and checking the hash file
exists anyway.

The second commitment is arithmetic. `rows_read == rows_sealed + rows_rejected`, with no third
outcome anywhere in this module. A row that cannot be coerced is written to
`sealed/rejected.parquet` with a reason you can point at; nothing is dropped, because a count
that does not reconcile is worse than a rejection.

This stage reads `data/` and writes `data/generated/<run>/sealed/` and nothing else.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import polars as pl

from chakravyuh import __version__, buildinfo
from chakravyuh.kavach import readers
from chakravyuh.kavach.schema import (
    AMOUNT_COLUMNS,
    CHAIN_COLUMNS,
    INT_COLUMNS,
    LIST_COLUMNS,
    NULLABLE_REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
    PS_COLUMNS,
    REQUIRED_COLUMNS,
    TXID_RE,
    AmountUnit,
    CaptureFormatError,
    TimestampFormat,
    detect_amount_unit,
    detect_timestamp_format,
    to_sats,
)

STAGE: Final[str] = "kavach"

# The only directory KAVACH will read a capture from, resolved against the working directory.
# An allowlist rather than a denylist on purpose: spelling out what is excluded would put the
# quarantined directory names into this file, and Law 2 rule 1 is a grep over `src/`. The
# operational consequence is that an evaluator's file is copied under `data/` before sealing.
INPUT_ROOT: Final[str] = "data"
OUTPUT_ROOT: Final[str] = "data/generated"

CAPTURE_SUFFIXES: Final[frozenset[str]] = frozenset({".csv", ".jsonl", ".json", ".xml", ".txt"})
COMPRESSION_SUFFIXES: Final[frozenset[str]] = frozenset({".zst", ".zstd", ".gz"})

# Scalars that must carry a value on every row. The list columns are deliberately absent: an
# empty `input_addresses` is a coinbase transaction, not a defect.
MUST_BE_PRESENT: Final[tuple[str, ...]] = (
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
)

SEALED_SCHEMA: Final[dict[str, pl.DataType]] = {
    "row_id": pl.Int64(),
    "ts_us": pl.Int64(),
    "ts_raw": pl.String(),
    "src_ip": pl.String(),
    "src_ip_version": pl.Int8(),
    "dst_ip": pl.String(),
    "src_port": pl.Int32(),
    "dst_port": pl.Int32(),
    "txid": pl.String(),
    "input_addresses": pl.List(pl.String()),
    "output_addresses": pl.List(pl.String()),
    "input_amounts": pl.List(pl.Int64()),
    "output_amounts": pl.List(pl.Int64()),
    "geo_country": pl.String(),
    "asn": pl.Int32(),
    "fee_sats": pl.Int64(),
    "vsize": pl.Int32(),
    "script_types": pl.List(pl.String()),
    "block_height": pl.Int32(),
    "msg_type": pl.String(),
    "observer_id": pl.String(),
}

# The rejected rows keep the section 1 column names and hold the original text, because a row
# that failed coercion may have no valid typed form at all. But the array columns are still real
# `list` types, per the document's Parquet convention: `list[int64]` is impossible for a row
# rejected because its amounts would not parse, while `list[string]` is always possible and
# keeps the tokens separable. Pipe-joined text is the CSV spelling, not the Parquet one.
REJECTED_SCHEMA: Final[dict[str, pl.DataType]] = {
    "row_id": pl.Int64(),
    "reject_reason": pl.String(),
    **{
        column: pl.List(pl.String()) if column in LIST_COLUMNS else pl.String()
        for column in PS_COLUMNS
    },
}


class InputPathError(ValueError):
    """A path KAVACH will not read from, or will not write to."""


@dataclass(frozen=True, slots=True)
class InputFile:
    path: Path
    size: int
    sha256: str


@dataclass(slots=True)
class Accounting:
    """Everything the manifest has to be able to say afterwards."""

    rows_read: int = 0
    rows_sealed: int = 0
    rows_rejected: int = 0
    reject_reasons: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    duplicate_rows: int = 0


def _relative_to_cwd(path: Path, root: str) -> Path:
    """`path` resolved, refused unless it sits inside `<cwd>/<root>`."""
    base = (Path.cwd() / root).resolve()
    resolved = path.resolve()
    if resolved != base and base not in resolved.parents:
        raise InputPathError(
            f"{path} resolves outside {base}. KAVACH only reads and writes inside that "
            f"directory, which is how a capture path can never reach a sibling tree it has "
            f"no business in. Copy the file under {root}/ first, then seal it."
        )
    return resolved


def _is_capture(path: Path) -> bool:
    """Whether a file in an input directory looks like a capture rather than a manifest."""
    if path.name.startswith(".") or path.name == "_meta.json":
        return False
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if suffixes and suffixes[-1] in COMPRESSION_SUFFIXES:
        suffixes = suffixes[:-1]
    return bool(suffixes) and suffixes[-1] in CAPTURE_SUFFIXES


def resolve_inputs(target: Path) -> tuple[list[Path], Path]:
    """The capture files to seal, sorted, plus the directory they came from.

    A directory yields every capture file inside it, which is what a sharded export looks
    like. Sort order is by name, and it is what `row_id` counts along, so the same input set
    numbers its rows the same way every time.
    """
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    if resolved.is_file():
        return [resolved], resolved.parent
    if not resolved.is_dir():
        raise InputPathError(f"{target} is neither a file nor a directory")
    found = sorted(path for path in resolved.iterdir() if path.is_file() and _is_capture(path))
    if not found:
        raise InputPathError(
            f"{target} holds no capture file. Looked for {', '.join(sorted(CAPTURE_SUFFIXES))}, "
            f"optionally compressed with {', '.join(sorted(COMPRESSION_SUFFIXES))}."
        )
    return found, resolved


def resolve_out(target: Path) -> Path:
    """The run directory to write `sealed/` into, refused unless it is under `data/generated/`."""
    resolved = _relative_to_cwd(target, OUTPUT_ROOT)
    if resolved == (Path.cwd() / OUTPUT_ROOT).resolve():
        raise InputPathError(
            f"--out must name a run directory inside {OUTPUT_ROOT}/, not {OUTPUT_ROOT}/ itself"
        )
    return resolved


def hash_inputs(paths: list[Path], sealed: Path) -> list[InputFile]:
    """Hash every input byte for byte and write `INPUT.sha256`, before anything is parsed.

    Returns the raw bytes' digests in input order. Nothing in this function decodes, sniffs or
    decompresses: the claim being made is about the file that arrived.
    """
    sealed.mkdir(parents=True, exist_ok=True)
    files: list[InputFile] = []
    lines: list[str] = []
    for path in paths:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        files.append(InputFile(path=path, size=len(raw), sha256=digest))
        lines.append(f"{digest}  {path.name}")
    (sealed / "INPUT.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return files


def _parse_timestamp(token: str, fmt: TimestampFormat) -> tuple[int, bool]:
    """UTC microseconds, and whether the source string carried no timezone.

    Either spelling parses on any row, whatever the file-level detection said. The detection
    exists because the manifest must record one answer, not because a stray integer among ISO
    strings should cost a row.
    """
    text = token.strip()
    if text.lstrip("+-").isdigit():
        value = int(text)
        scale = {
            TimestampFormat.EPOCH_S: 1_000_000,
            TimestampFormat.EPOCH_MS: 1_000,
            TimestampFormat.EPOCH_US: 1,
            TimestampFormat.ISO8601: 1_000_000,
        }[fmt]
        return value * scale, False
    moment = datetime.fromisoformat(text)
    naive = moment.tzinfo is None
    if naive:
        # Recorded in the manifest as a warning rather than guessed at silently. Every other
        # time in this project is UTC microseconds, so reading a naive stamp as local time
        # would put one column on a different clock from all the rest.
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp() * 1_000_000), naive


def _ip_version(value: str) -> int | None:
    from ipaddress import ip_address

    try:
        return ip_address(value).version
    except ValueError:
        return None


def _as_list(cell: readers.Cell) -> list[str]:
    if isinstance(cell, list):
        return cell
    return [] if cell is None else [cell]


def _as_text(cell: readers.Cell) -> str | None:
    if cell is None:
        return None
    if isinstance(cell, list):
        return "|".join(cell)
    return cell


def _raw_view(row: readers.Row) -> dict[str, object]:
    """The row as it arrived, for `rejected.parquet`. A rejected value may not coerce at all.

    Scalars stay text and arrays stay arrays. The point of this file is that an investigator can
    see what was in the input, so a value is never reshaped on the way in here — that is the
    thing being preserved.
    """
    return {
        column: (_as_list(row.get(column)) if column in LIST_COLUMNS else _as_text(row.get(column)))
        for column in PS_COLUMNS
    }


def _coerce(
    row: readers.Row,
    row_id: int,
    unit: AmountUnit,
    fmt: TimestampFormat,
    present: frozenset[str],
) -> tuple[dict[str, object] | None, str | None, bool]:
    """One row, coerced, or the reason it cannot be. First failure wins.

    The third element is whether the timestamp was naive, which the caller counts into a
    single manifest warning rather than one per row.
    """
    for column in MUST_BE_PRESENT:
        if row.get(column) is None:
            return None, "missing_required_value", False

    txid = _as_text(row["txid"]) or ""
    if not TXID_RE.match(txid):
        return None, "txid_malformed", False

    try:
        ts_us, naive = _parse_timestamp(str(_as_text(row["timestamp"])), fmt)
    except ValueError:
        return None, "timestamp_unparseable", False

    ints: dict[str, int | None] = {}
    for column in INT_COLUMNS:
        text = _as_text(row.get(column))
        if text is None or not text.strip():
            ints[column] = None
            continue
        try:
            ints[column] = int(text.strip())
        except ValueError:
            return None, "integer_unparseable", naive

    amounts: dict[str, list[int]] = {}
    for column in AMOUNT_COLUMNS:
        try:
            amounts[column] = [to_sats(token, unit) for token in _as_list(row.get(column))]
        except ValueError:
            return None, "amount_unparseable", naive

    input_addresses = _as_list(row.get("input_addresses"))
    output_addresses = _as_list(row.get("output_addresses"))
    if len(input_addresses) != len(amounts["input_amounts"]):
        return None, "input_length_mismatch", naive
    if len(output_addresses) != len(amounts["output_amounts"]):
        return None, "output_length_mismatch", naive
    if not output_addresses:
        return None, "no_outputs", naive

    total_in = sum(amounts["input_amounts"])
    total_out = sum(amounts["output_amounts"])
    # Invariant 6, and it applies only off-coinbase: a coinbase row has no inputs and mints
    # its outputs, so the comparison is meaningless there rather than merely generous.
    if input_addresses and total_in < total_out:
        return None, "value_not_conserved", naive

    src_ip = str(_as_text(row["src_ip"]))
    fee = ints.get("fee_sats")
    if fee is None and "fee_sats" not in present and input_addresses:
        # The one synthesised column. Derivable exactly from what is already on the row, which
        # is what separates it from inventing a default port or a country.
        fee = total_in - total_out

    sealed: dict[str, object] = {
        "row_id": row_id,
        "ts_us": ts_us,
        "ts_raw": _as_text(row["timestamp"]),
        "src_ip": src_ip,
        "src_ip_version": _ip_version(src_ip),
        "dst_ip": _as_text(row["dst_ip"]),
        "src_port": ints.get("src_port"),
        "dst_port": ints.get("dst_port"),
        "txid": txid,
        "input_addresses": input_addresses,
        "output_addresses": output_addresses,
        "input_amounts": amounts["input_amounts"],
        "output_amounts": amounts["output_amounts"],
        "geo_country": _as_text(row.get("geo_country")),
        "asn": ints.get("asn"),
        "fee_sats": fee,
        "vsize": ints.get("vsize"),
        "script_types": _as_list(row.get("script_types")),
        "block_height": ints.get("block_height"),
        "msg_type": _as_text(row.get("msg_type")),
        "observer_id": _as_text(row.get("observer_id")),
    }
    return sealed, None, naive


def _chain_key(sealed: dict[str, object]) -> tuple[object, ...]:
    """The chain columns of one row, hashable, for the agreement check."""
    out: list[object] = []
    for column in CHAIN_COLUMNS:
        value = sealed.get(column)
        out.append(tuple(value) if isinstance(value, list) else value)
    return tuple(out)


def _quarantine_disagreeing(
    sealed_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], set[int]]:
    """Invariant 5: rows sharing a txid must agree on the chain columns.

    Every row of a disagreeing group is quarantined, not the minority. Section 1 says the file
    is corrupt at that point and KAVACH does not guess, and a majority vote is a guess with
    extra steps.
    """
    groups: dict[str, set[tuple[object, ...]]] = {}
    for row in sealed_rows:
        txid = str(row["txid"])
        groups.setdefault(txid, set()).add(_chain_key(row))
    corrupt = {txid for txid, keys in groups.items() if len(keys) > 1}
    if not corrupt:
        return sealed_rows, set()
    kept = [row for row in sealed_rows if str(row["txid"]) not in corrupt]
    dropped = {int(str(row["row_id"])) for row in sealed_rows if str(row["txid"]) in corrupt}
    return kept, dropped


def _frame(rows: list[dict[str, object]], schema: dict[str, pl.DataType]) -> pl.DataFrame:
    """A DataFrame with the declared schema, correct even when there are no rows."""
    if not rows:
        return pl.DataFrame(schema=schema)
    return pl.DataFrame(rows, schema=schema)


def _write_parquet(frame: pl.DataFrame, path: Path) -> str:
    """Write, then hash what was written. Compression is pinned so two seals agree byte for byte."""
    frame.write_parquet(path, compression="zstd", compression_level=3, statistics=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _masked_manifest_sha256(manifest: dict[str, object]) -> str:
    """The manifest's hash with its wall clock removed.

    `sealed_at_us` cannot be reproducible, so hashing the manifest raw would hand every
    downstream custody check a value that changes on every seal of identical bytes. Excluding
    it here means the same exclusion holds in the hash, in `compare_runs.py` and at S09,
    rather than only in the diff.
    """
    masked = {key: value for key, value in manifest.items() if key != "sealed_at_us"}
    payload = json.dumps(masked, indent=2, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _upstream_meta(directory: Path) -> tuple[str | None, str | None]:
    """The `_meta.json` beside the capture, as a repo-relative path and a hash.

    This is the staleness link every later stage carries. Absent for a hand-written fixture,
    which is a warning rather than a failure: a capture nobody generated has no upstream to
    be stale against.
    """
    candidate = directory / "_meta.json"
    if not candidate.is_file():
        return None, None
    raw = candidate.read_bytes()
    try:
        relative = candidate.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        relative = candidate.name
    return relative, hashlib.sha256(raw).hexdigest()


def seal(target: Path, out: Path) -> Path:
    """Seal a capture into `<out>/sealed/`. Returns the path to `manifest.json`.

    `target` and `out` are already resolved and guarded by the caller.
    """
    started_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    paths, source_dir = resolve_inputs(target)
    sealed_dir = out / "sealed"

    files = hash_inputs(paths, sealed_dir)

    sources = [readers.read(path.read_bytes(), path) for path in paths]

    present: set[str] = set()
    unknown: list[str] = []
    for source in sources:
        present.update(source.headers)
        unknown.extend(source.unknown_headers)

    missing_required = [column for column in REQUIRED_COLUMNS if column not in present]
    if missing_required:
        raise CaptureFormatError(
            f"the capture has no column for {', '.join(missing_required)}, and every row would "
            "be rejected for the same reason. Rename the header, or hand us a file that carries "
            f"it. Recognised spellings are in {__package__}.schema.COLUMN_ALIASES."
        )

    every_row: list[readers.Row] = [row for source in sources for row in source.rows]

    amount_tokens = {
        column: [token for row in every_row for token in _as_list(row.get(column))]
        for column in AMOUNT_COLUMNS
    }
    unit = detect_amount_unit(amount_tokens)
    fmt = detect_timestamp_format(
        [text for row in every_row if (text := _as_text(row.get("timestamp"))) is not None]
    )

    books = Accounting(rows_read=len(every_row))
    sealed_rows: list[dict[str, object]] = []
    rejected_rows: list[dict[str, object]] = []
    naive_stamps = 0

    for row_id, row in enumerate(every_row):
        coerced, reason, naive = _coerce(row, row_id, unit, fmt, frozenset(present))
        naive_stamps += int(naive)
        if coerced is None:
            rejected_rows.append({"row_id": row_id, "reject_reason": str(reason), **_raw_view(row)})
            continue
        sealed_rows.append(coerced)

    kept, disagreeing = _quarantine_disagreeing(sealed_rows)
    for row_id in sorted(disagreeing):
        rejected_rows.append(
            {
                "row_id": row_id,
                "reject_reason": "chain_columns_disagree",
                **_raw_view(every_row[row_id]),
            }
        )
    sealed_rows = kept

    rejected_rows.sort(key=lambda row: int(str(row["row_id"])))

    books.rows_sealed = len(sealed_rows)
    books.rows_rejected = len(rejected_rows)
    for bad in rejected_rows:
        reason = str(bad["reject_reason"])
        books.reject_reasons[reason] = books.reject_reasons.get(reason, 0) + 1
    seen: set[tuple[object, ...]] = set()
    for kept_row in sealed_rows:
        key = tuple(
            tuple(value) if isinstance(value, list) else value
            for column, value in sorted(kept_row.items())
            if column != "row_id"
        )
        if key in seen:
            books.duplicate_rows += 1
        seen.add(key)

    if naive_stamps:
        books.warnings.append(f"{naive_stamps} timestamps carried no timezone and were read as UTC")
    if books.duplicate_rows:
        books.warnings.append(
            f"{books.duplicate_rows} rows are exact duplicates of an earlier row, and were "
            "kept: nothing in the contract forbids a repeated announcement, and dropping them "
            "would break the row arithmetic that makes this stage accountable"
        )
    if unknown:
        books.warnings.append(
            f"{len(unknown)} columns were not recognised and are not sealed: "
            f"{', '.join(sorted(set(unknown)))}"
        )

    columns_missing_optional = [column for column in OPTIONAL_COLUMNS if column not in present]
    for column in columns_missing_optional:
        books.warnings.append(f"optional column {column} is absent and is sealed as all-null")
    for column in NULLABLE_REQUIRED_COLUMNS:
        if column not in present:
            books.warnings.append(f"nullable column {column} is absent and is sealed as all-null")

    rows_hash = _write_parquet(_frame(sealed_rows, SEALED_SCHEMA), sealed_dir / "rows.parquet")
    rejected_hash = _write_parquet(
        _frame(rejected_rows, REJECTED_SCHEMA), sealed_dir / "rejected.parquet"
    )
    input_hash = hashlib.sha256((sealed_dir / "INPUT.sha256").read_bytes()).hexdigest()

    upstream_path, upstream_hash = _upstream_meta(source_dir)
    if upstream_hash is None:
        books.warnings.append(
            "the capture has no _meta.json beside it, so this seal records no upstream hash "
            "and the staleness check has nothing to compare against"
        )

    status: dict[str, str] = {}
    for column in PS_COLUMNS:
        if column in present:
            status[column] = "MAPPED"
        elif column == "fee_sats":
            status[column] = "SYNTHESISED"
        else:
            status[column] = "MISSING"

    finished_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    manifest: dict[str, object] = {
        "input_files": [
            {
                "path": file.path.resolve().relative_to(Path.cwd().resolve()).as_posix(),
                "bytes": file.size,
                "sha256": file.sha256,
            }
            for file in files
        ],
        "rows_read": books.rows_read,
        "rows_sealed": books.rows_sealed,
        "rows_rejected": books.rows_rejected,
        "reject_reasons": dict(sorted(books.reject_reasons.items())),
        "amount_unit_detected": unit.value,
        "timestamp_format_detected": fmt.value,
        "columns_present": sorted(present),
        "columns_missing_optional": columns_missing_optional,
        "column_status": {column: status[column] for column in PS_COLUMNS},
        "column_spellings": {
            source.path.name: dict(sorted(source.headers.items())) for source in sources
        },
        "encodings_detected": {
            source.path.name: f"{source.encoding.value}/{source.container.value}"
            for source in sources
        },
        # A copy, not the list itself. The manifest is hashed the moment it is written, and an
        # alias that something appends to afterwards makes that hash a statement about a dict
        # nobody ever wrote to disk.
        "warnings": list(books.warnings),
        "sealed_at_us": finished_at_us,
        "code_version": buildinfo.code_version(),
        "tool_version": __version__,
    }
    manifest_path = sealed_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    meta = {
        "stage": STAGE,
        "run_id": out.name,
        "started_at_us": started_at_us,
        "finished_at_us": finished_at_us,
        "code_version": buildinfo.code_version(),
        "seed": 0,
        "params": {
            "input": target.resolve().relative_to(Path.cwd().resolve()).as_posix(),
            "amount_unit_detected": unit.value,
            "timestamp_format_detected": fmt.value,
            # The staleness link. Null when the capture was hand-written rather than generated.
            "upstream_meta": {"path": upstream_path, "sha256": upstream_hash},
            # manifest.json is deliberately absent from `outputs` below. It carries
            # `sealed_at_us`, so its raw hash cannot be reproducible, and a raw hash recorded
            # beside reproducible ones is a trap for whoever checks custody at S09. What is
            # recorded is the hash of the manifest with that one field removed.
            "manifest": {
                "path": "sealed/manifest.json",
                "sha256_masked": _masked_manifest_sha256(manifest),
                "masked_fields": ["sealed_at_us"],
            },
        },
        # Exactly the capture files, in the same order as INPUT.sha256 above, so the two lists
        # answer the same question and a reader can pair them by index. Every entry has an
        # integer row count, which is why the upstream manifest is not listed here: it carries
        # no rows, and `params.upstream_meta` already records its path and hash in full. Listing
        # it here as a third input with `rows: null` would make `rows` a mixed type and make
        # these entries sum to something other than `counts.in`.
        "inputs": [
            {
                "path": file.path.resolve().relative_to(Path.cwd().resolve()).as_posix(),
                "sha256": file.sha256,
                # Rows as this shard delivered them, before coercion. `sources` is built from
                # `paths` in order and `files` from the same list, so index i is one file.
                # Summing this column gives `counts.in`, which is what makes a shard that
                # silently read short visible in the manifest rather than only in the total.
                "rows": len(source.rows),
            }
            for file, source in zip(files, sources, strict=True)
        ],
        "outputs": [
            {"path": "sealed/rows.parquet", "sha256": rows_hash, "rows": books.rows_sealed},
            {
                "path": "sealed/rejected.parquet",
                "sha256": rejected_hash,
                "rows": books.rows_rejected,
            },
            {"path": "sealed/INPUT.sha256", "sha256": input_hash, "rows": len(files)},
        ],
        "counts": {
            "in": books.rows_read,
            "out": books.rows_sealed,
            "dropped": books.rows_rejected,
            "drop_reasons": dict(sorted(books.reject_reasons.items())),
        },
        "warnings": list(books.warnings),
        "optional_deps": {"geolite2": False, "kuzu": False, "gpu": False},
    }
    (sealed_dir / "_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if books.rows_read != books.rows_sealed + books.rows_rejected:
        raise AssertionError(
            f"rows_read {books.rows_read} != sealed {books.rows_sealed} + rejected "
            f"{books.rows_rejected}. A row went missing inside KAVACH, which is the one thing "
            "this stage exists to make impossible."
        )
    return manifest_path
