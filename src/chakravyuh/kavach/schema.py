"""What a capture column is called, what shape its values have, and what units they carry.

Everything in this module is a decision about someone else's file. KAVACH is the only stage
that reads data it did not write, so the tolerance lives here and nowhere downstream: by the
time `sealed/rows.parquet` exists, the column names are the contract's names, the amounts are
satoshis and the timestamps are UTC microseconds, and no later stage has to wonder.

Three detections, all from content and never from a filename:

- the container, from the first magic bytes, so a zstd-compressed capture is transparent
- the encoding, from the first non-whitespace byte of the decompressed text
- the amount unit and the timestamp format, from the values themselves

The amount rule is the one worth reading twice. "Any decimal anywhere means BTC" is wrong in a
way that hides: one malformed decimal in a satoshi file would flip every value by 1e8, and
because the factor applies to inputs and outputs alike, value conservation still holds and the
invariant that should catch it never fires. So a column is satoshis only when every parseable
token is integer-shaped, BTC only when every parseable token is fractional, and anything mixed
is an error naming the column rather than a guess.
"""

from __future__ import annotations

import re
from decimal import Decimal
from enum import Enum
from typing import Final

# Section 1's twelve, in the contract's order. The first ten are required; a capture without
# one of them cannot be sealed at all. `geo_country` and `asn` are explicitly nullable.
REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "timestamp",
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
NULLABLE_REQUIRED_COLUMNS: Final[tuple[str, ...]] = ("geo_country", "asn")

# Our extensions. A real NTRO file will not have them, so every one of these may be absent and
# absence is a warning, never a failure.
OPTIONAL_COLUMNS: Final[tuple[str, ...]] = (
    "fee_sats",
    "vsize",
    "script_types",
    "block_height",
    "msg_type",
    "observer_id",
)

PS_COLUMNS: Final[tuple[str, ...]] = (
    *REQUIRED_COLUMNS,
    *NULLABLE_REQUIRED_COLUMNS,
    *OPTIONAL_COLUMNS,
)

# Keyed on the column name rather than on the value, because the encodings disagree about how
# to spell an empty list and only the name can settle it. XML in particular cannot distinguish
# an empty list from a null: both are an empty element.
LIST_COLUMNS: Final[frozenset[str]] = frozenset(
    {"input_addresses", "output_addresses", "input_amounts", "output_amounts", "script_types"}
)
AMOUNT_COLUMNS: Final[tuple[str, ...]] = ("input_amounts", "output_amounts")
INT_COLUMNS: Final[frozenset[str]] = frozenset(
    {"src_port", "dst_port", "asn", "fee_sats", "vsize", "block_height"}
)

# The chain columns of section 1: the ones that describe the transaction rather than the
# announcement, and therefore repeat identically across every row announcing one txid.
CHAIN_COLUMNS: Final[tuple[str, ...]] = (
    "input_addresses",
    "output_addresses",
    "input_amounts",
    "output_amounts",
    "fee_sats",
    "vsize",
    "script_types",
    "block_height",
)

# Aliases are a judgement about what a stranger's file might call things, not something the
# frozen contract specifies. Matching is case-insensitive and whitespace-stripped on top of
# this table. Deliberately conservative: a wrong alias silently mislabels a column, which is
# worse than a MISSING tag that shows up in the manifest and can be fixed by renaming a header.
COLUMN_ALIASES: Final[dict[str, str]] = {
    "ts": "timestamp",
    "time": "timestamp",
    "time_utc": "timestamp",
    "timestamp_utc": "timestamp",
    "source_ip": "src_ip",
    "src_addr": "src_ip",
    "peer_ip": "src_ip",
    "destination_ip": "dst_ip",
    "dst_addr": "dst_ip",
    "observer_ip": "dst_ip",
    "source_port": "src_port",
    "sport": "src_port",
    "destination_port": "dst_port",
    "dport": "dst_port",
    "tx_id": "txid",
    "tx_hash": "txid",
    "hash": "txid",
    "inputs": "input_addresses",
    "in_addresses": "input_addresses",
    "outputs": "output_addresses",
    "out_addresses": "output_addresses",
    "in_amounts": "input_amounts",
    "input_values": "input_amounts",
    "out_amounts": "output_amounts",
    "output_values": "output_amounts",
    "country": "geo_country",
    "cc": "geo_country",
    "as_number": "asn",
    "autonomous_system": "asn",
    "height": "block_height",
    "virtual_size": "vsize",
    "message_type": "msg_type",
    "command": "msg_type",
    "node_id": "observer_id",
    "sensor_id": "observer_id",
}

SATS_PER_BTC: Final[Decimal] = Decimal(100_000_000)

TXID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_INTEGER_RE: Final[re.Pattern[str]] = re.compile(r"^[+-]?\d+$")
_DECIMAL_RE: Final[re.Pattern[str]] = re.compile(r"^[+-]?\d*\.\d+$|^[+-]?\d+\.\d*$")


class Encoding(Enum):
    """How the decompressed bytes are laid out."""

    CSV = "csv"
    JSONL = "jsonl"
    XML = "xml"


class Container(Enum):
    """What, if anything, is wrapped around those bytes."""

    PLAIN = "plain"
    ZSTD = "zstd"
    GZIP = "gzip"


class AmountUnit(Enum):
    SATS = "sats"
    BTC = "btc"


class TimestampFormat(Enum):
    ISO8601 = "iso8601"
    EPOCH_S = "epoch_s"
    EPOCH_MS = "epoch_ms"
    EPOCH_US = "epoch_us"


class Shape(Enum):
    """What one amount token looks like before anything is assumed about its unit."""

    INTEGER = "integer"
    DECIMAL = "decimal"
    BAD = "bad"


class CaptureFormatError(ValueError):
    """The file cannot be read at all: wrong shape, ambiguous units, missing required column.

    Distinct from a rejected row. A rejected row is one row we can point at in
    `sealed/rejected.parquet`; this is the whole file, and there is nothing to point at.
    """


_MAGIC: Final[tuple[tuple[bytes, Container], ...]] = (
    (b"\x28\xb5\x2f\xfd", Container.ZSTD),
    (b"\x1f\x8b", Container.GZIP),
)


def detect_container(head: bytes) -> Container:
    """Which compression wraps these bytes, from the magic number alone."""
    for magic, container in _MAGIC:
        if head.startswith(magic):
            return container
    return Container.PLAIN


def detect_encoding(text: str) -> Encoding:
    """CSV, JSONL or XML, from the first character that is not whitespace or a BOM.

    Never from the extension. The one file that matters in a demo is the one an evaluator
    renamed, and a loader that trusts `.csv` fails on exactly that file.
    """
    stripped = text.lstrip("﻿ \t\r\n")
    if not stripped:
        raise CaptureFormatError("the capture is empty, so there is no format to detect")
    first = stripped[0]
    if first == "<":
        return Encoding.XML
    if first == "{":
        return Encoding.JSONL
    if first == "[":
        raise CaptureFormatError(
            "this looks like a JSON array, and KAVACH reads JSON Lines: one object per line, "
            "no enclosing brackets and no commas between records. Convert it, or hand us CSV "
            "or XML. Guessing between the two would silently mis-split nested records."
        )
    return Encoding.CSV


def canonical_column(name: str) -> str | None:
    """The contract's name for a header, or None if we do not recognise it."""
    key = name.strip().lower()
    if key in PS_COLUMNS:
        return key
    return COLUMN_ALIASES.get(key)


def amount_shape(token: str) -> Shape:
    """Whether one amount token is integer-shaped, fractional, or neither.

    Scientific notation is BAD rather than DECIMAL on purpose. `1e8` is either a hundred
    million satoshis or a hundred million BTC and nothing in the token says which, so it
    becomes a row we can point at instead of a file-wide assumption.
    """
    text = token.strip()
    if not text:
        return Shape.BAD
    if _INTEGER_RE.match(text):
        return Shape.INTEGER
    if _DECIMAL_RE.match(text):
        return Shape.DECIMAL
    return Shape.BAD


def detect_amount_unit(columns: dict[str, list[str]]) -> AmountUnit:
    """Satoshis or BTC for the whole file, or an error naming the column that cannot decide.

    `columns` maps each amount column to every token seen in it. Tokens that are neither
    integer- nor decimal-shaped are excluded here and rejected per row later: one piece of
    junk should cost one row, not reinterpret the file.

    All-integer is satoshis. All-fractional is BTC. Mixed is refused, because that is the
    shape a satoshi file with one corrupt decimal has, and silently reading it as BTC
    multiplies every amount by 1e8 while leaving `inputs >= outputs` true.
    """
    shapes: dict[str, set[Shape]] = {}
    for column, tokens in columns.items():
        seen = {amount_shape(token) for token in tokens} - {Shape.BAD}
        if seen:
            shapes[column] = seen

    if not shapes:
        # Nothing parseable anywhere. Every row will be rejected on its own merits; the unit
        # recorded in the manifest is then a statement about a file with no amounts in it.
        return AmountUnit.SATS

    mixed = sorted(column for column, seen in shapes.items() if len(seen) > 1)
    if mixed:
        raise CaptureFormatError(
            f"cannot tell satoshis from BTC: {', '.join(mixed)} holds both whole numbers and "
            "fractions. Refusing to guess, because reading a satoshi column as BTC multiplies "
            "every amount by 1e8 and still conserves value, so no later check would catch it."
        )

    units = {
        AmountUnit.SATS if seen == {Shape.INTEGER} else AmountUnit.BTC for seen in shapes.values()
    }
    if len(units) > 1:
        per_column = ", ".join(
            f"{column}={'sats' if seen == {Shape.INTEGER} else 'btc'}"
            for column, seen in sorted(shapes.items())
        )
        raise CaptureFormatError(
            f"amount columns disagree about their unit: {per_column}. One capture carries one "
            "unit; a file mixing them has to be split or corrected before it can be sealed."
        )
    return units.pop()


def to_sats(token: str, unit: AmountUnit) -> int:
    """One amount token as int64 satoshis, or ValueError.

    Decimal throughout. A float BTC value loses precision at the eighth decimal, which is
    exactly the digit that matters, and this number is printed into an evidence packet.
    """
    shape = amount_shape(token)
    if shape is Shape.BAD:
        raise ValueError(f"not a number: {token.strip()!r}")
    value = Decimal(token.strip())
    if unit is AmountUnit.BTC:
        value = value * SATS_PER_BTC
    if value != value.to_integral_value():
        raise ValueError("amount is finer than one satoshi")
    return int(value)


def detect_timestamp_format(tokens: list[str]) -> TimestampFormat:
    """Which of the contract's four timestamp spellings this file uses.

    Epoch magnitude picks the unit: seconds through the 2030s are ten digits, milliseconds
    thirteen, microseconds sixteen. A file whose timestamps are not all numeric is ISO 8601,
    and the per-row parser still handles either spelling, so a stray integer among ISO strings
    costs nothing. This detection exists for the manifest, which must record one answer.
    """
    numeric = [token for token in tokens if _INTEGER_RE.match(token.strip())]
    if not numeric or len(numeric) < len(tokens):
        return TimestampFormat.ISO8601
    widest = max(len(token.strip().lstrip("+-")) for token in numeric)
    if widest >= 15:
        return TimestampFormat.EPOCH_US
    if widest >= 12:
        return TimestampFormat.EPOCH_MS
    return TimestampFormat.EPOCH_S
