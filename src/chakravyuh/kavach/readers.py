"""Three encodings in, one list of string-valued rows out.

Nothing here coerces, validates or rejects. A reader's whole job is to undo the encoding and
hand back what the file said, with the column names canonicalised and every value as a string
or a list of strings. Coercion happens once, in `seal.py`, so CSV, JSONL and XML cannot drift
into three slightly different notions of what a null is.

That convergence is also the test: `tests/test_kavach.py` seals all three fixture encodings
and asserts the resulting `rows.parquet` files are byte-identical. If a reader invents a
difference, that assertion is where it surfaces.

One shared rule, and it is the only place the encodings genuinely disagree. XML cannot tell an
empty list from a null, because both are an empty element. Section 1 fixes which columns are
lists, so every reader keys on the column name: a missing value in a list column is an empty
list everywhere, and a missing value in a scalar column is null everywhere.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from chakravyuh.kavach.schema import (
    LIST_COLUMNS,
    CaptureFormatError,
    Container,
    Encoding,
    canonical_column,
    detect_container,
    detect_encoding,
)

# One cell as the readers hand it over: a scalar, a list, or absent.
Cell = str | list[str] | None
Row = dict[str, Cell]


@dataclass(frozen=True, slots=True)
class Source:
    """One input file, decoded but not yet interpreted."""

    path: Path
    container: Container
    encoding: Encoding
    headers: dict[str, str]
    """Canonical column name to the spelling this file actually used."""
    unknown_headers: tuple[str, ...]
    """Headers we could not map. Reported in the manifest, never silently dropped."""
    rows: list[Row]


def decompress(raw: bytes) -> tuple[bytes, Container]:
    """The capture's bytes, unwrapped, and what was wrapped around them.

    The hash in `sealed/INPUT.sha256` is taken over the bytes as delivered, before this runs.
    Custody is a claim about the file we were handed, not about what it held.
    """
    container = detect_container(raw[:4])
    if container is Container.PLAIN:
        return raw, container
    if container is Container.GZIP:
        return gzip.decompress(raw), container

    # zstd via pyarrow, which is already a pinned dependency and ships the codec. The local
    # ignore rather than a mypy override: pyarrow has no py.typed marker, and one narrow
    # ignore at the only call site is cheaper than loosening the strict config for everything.
    import pyarrow as pa  # type: ignore[import-untyped]

    stream = pa.CompressedInputStream(pa.BufferReader(raw), "zstd")
    return bytes(stream.read()), container


def decode(raw: bytes, path: Path) -> str:
    """UTF-8 text with any BOM removed, or a refusal naming the file."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CaptureFormatError(
            f"{path.name} is not UTF-8 text at byte {exc.start}. If this is a binary capture "
            "format rather than CSV, JSONL or XML, it needs converting before intake."
        ) from exc


def _map_headers(names: list[str]) -> tuple[dict[str, str], tuple[str, ...]]:
    """Canonical name to original spelling, plus whatever we could not place.

    First spelling wins when two headers map to one canonical name. The loser is reported as
    unknown rather than quietly overwriting, because a file with both `src_ip` and `peer_ip`
    is a file whose author meant something by the distinction.
    """
    mapped: dict[str, str] = {}
    unknown: list[str] = []
    for name in names:
        canonical = canonical_column(name)
        if canonical is None or canonical in mapped:
            unknown.append(name)
            continue
        mapped[canonical] = name
    return mapped, tuple(unknown)


def _split_list(value: str) -> list[str]:
    """A CSV list cell. Pipe separated with no spaces, per the contract's conventions."""
    text = value.strip()
    return [] if not text else text.split("|")


def _cell_from_text(column: str, value: str | None) -> Cell:
    """One textual cell, with the list-or-null question settled by the column name."""
    if value is None or not value.strip():
        return [] if column in LIST_COLUMNS else None
    return _split_list(value) if column in LIST_COLUMNS else value.strip()


def _stringify(value: object) -> str:
    """One JSON scalar as text, without letting a float near an amount.

    JSON numbers are parsed with `Decimal`, so `0.00123` stays `0.00123` rather than becoming
    the nearest binary double. `str()` on a Decimal is exact.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _cell_from_json(column: str, value: object) -> Cell:
    """One JSON value as a cell, keyed on the column name like every other reader."""
    if isinstance(value, list):
        return [_stringify(item) for item in value]
    if value is None:
        return [] if column in LIST_COLUMNS else None
    text = _stringify(value)
    if column in LIST_COLUMNS:
        # A list column carrying a scalar: pipe-joined text from a CSV-ish producer.
        return _split_list(text)
    return text.strip() if text.strip() else None


def read_csv(text: str, path: Path) -> Source:
    """Delimited text with a header row."""
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise CaptureFormatError(f"{path.name} has no header row, so no column can be named")
    headers, unknown = _map_headers([name for name in reader.fieldnames if name is not None])

    rows: list[Row] = []
    for record in reader:
        # csv.DictReader yields nothing for a truly blank line, but a line of bare commas
        # survives as all-empty. Either way it is not a row, and a hostile file has both.
        if all(value is None or not str(value).strip() for value in record.values()):
            continue
        rows.append(
            {
                column: _cell_from_text(column, record.get(original))
                for column, original in headers.items()
            }
        )
    return Source(path, Container.PLAIN, Encoding.CSV, headers, unknown, rows)


def read_jsonl(text: str, path: Path) -> Source:
    """One JSON object per line."""
    raw_rows: list[dict[str, object]] = []
    order: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            node = json.loads(line, parse_float=Decimal)
        except json.JSONDecodeError as exc:
            raise CaptureFormatError(
                f"{path.name} line {number} is not valid JSON: {exc.msg}. JSON Lines is one "
                "complete object per line; a pretty-printed file has to be compacted first."
            ) from exc
        if not isinstance(node, dict):
            raise CaptureFormatError(
                f"{path.name} line {number} holds a {type(node).__name__}, not an object. "
                "Every line must be one announcement."
            )
        raw_rows.append(node)
        order.extend(key for key in node if key not in order)

    headers, unknown = _map_headers(order)
    rows: list[Row] = [
        {
            column: _cell_from_json(column, node.get(original))
            for column, original in headers.items()
        }
        for node in raw_rows
    ]
    return Source(path, Container.PLAIN, Encoding.JSONL, headers, unknown, rows)


def _xml_cell(column: str, element: ET.Element) -> Cell:
    """One XML element as a cell. Repeated `<item>` children are the list form."""
    items = list(element)
    if items:
        return [(item.text or "").strip() for item in items]
    return _cell_from_text(column, element.text)


def read_xml(text: str, path: Path) -> Source:
    """Repeated row elements, with repeated `<item>` children for lists."""
    if "<!DOCTYPE" in text[:4096].upper():
        # Refused before parsing rather than configured away after. Python's expat expands
        # internal entities by default, so a DOCTYPE is both the XXE vector and the
        # billion-laughs vector, and this is a stage whose entire premise is reading a file
        # handed over by someone else.
        raise CaptureFormatError(
            f"{path.name} carries a DOCTYPE declaration, which KAVACH refuses to parse. "
            "Document type definitions can pull in external entities and can expand to "
            "exhaust memory, and a capture has no legitimate use for one."
        )
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise CaptureFormatError(f"{path.name} is not well-formed XML: {exc}") from exc

    order: list[str] = []
    elements = list(root)
    for element in elements:
        order.extend(child.tag for child in element if child.tag not in order)

    headers, unknown = _map_headers(order)
    rows: list[Row] = []
    for element in elements:
        by_tag = {child.tag: child for child in element}
        row: Row = {}
        for column, original in headers.items():
            child = by_tag.get(original)
            row[column] = (
                _xml_cell(column, child)
                if child is not None
                else ([] if column in LIST_COLUMNS else None)
            )
        rows.append(row)
    return Source(path, Container.PLAIN, Encoding.XML, headers, unknown, rows)


def read(raw: bytes, path: Path) -> Source:
    """Any of the three encodings, in any of the supported containers.

    The caller has already hashed `raw`. Everything after this point is derived from a file
    whose sha256 is on disk.
    """
    payload, container = decompress(raw)
    text = decode(payload, path)
    encoding = detect_encoding(text)
    source = {
        Encoding.CSV: read_csv,
        Encoding.JSONL: read_jsonl,
        Encoding.XML: read_xml,
    }[encoding](text, path)
    return Source(
        path=source.path,
        container=container,
        encoding=source.encoding,
        headers=source.headers,
        unknown_headers=source.unknown_headers,
        rows=source.rows,
    )
