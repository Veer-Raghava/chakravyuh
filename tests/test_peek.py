"""peek.py is the only sanctioned way to look at pipeline data, so its redaction is a
security control and not a formatting convenience. These tests pin the truncation widths
CLAUDE.md specifies, pin the two cases where a value-shape rule would otherwise destroy or
leak data, and check the rendered report against the real fixture for verbatim identifiers.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import peek  # noqa: E402

CAPTURE_CSV = REPO / "data" / "fixtures" / "capture" / "capture.csv"
SYNTHETIC_TXID = "f1a70007" + "0" * 56


def test_truncation_widths() -> None:
    assert peek.truncate_ip("203.0.113.66") == "203.0.x.x"
    assert peek.truncate_ip("2001:db8:0:1::7") == "2001:db8:x"
    assert peek.truncate_address("bc1qfixtureaddress0001") == "bc1qfi…0001"
    assert peek.truncate_txid(SYNTHETIC_TXID) == "f1a70007…0000"


def test_short_values_pass_through_untruncated() -> None:
    # Nothing this short can be an address or a txid, and padding it into a fake one
    # would be a lie in a forensics report.
    assert peek.truncate_address("bc1q") == "bc1q"
    assert peek.truncate_txid("f1a7") == "f1a7"


def test_hash_columns_print_in_full_but_txid_columns_do_not() -> None:
    digest = "e" * 64
    assert peek.redact("sha256", digest) == digest
    assert peek.redact("merkle_root", digest) == digest
    assert peek.redact("signature", digest) == digest
    # Same sixty-four hex characters, different column, so the column name must decide.
    assert peek.redact("txid", digest) == "eeeeeeee…eeee"


def test_node_id_prefixes_route_by_kind() -> None:
    assert peek.redact("node_id", "peer:203.0.113.66") == "peer:203.0.x.x"
    assert peek.redact("node_id", "addr:bc1qfixtureaddress0001") == "addr:bc1qfi…0001"
    assert peek.redact("node_id", f"tx:{SYNTHETIC_TXID}") == "tx:f1a70007…0000"


def test_timestamps_survive_redaction() -> None:
    # An ISO 8601 timestamp contains two colons. A loose IPv6 shape rule truncates it to
    # "2026-03-01T09:00:x", silently destroying every timestamp in the file.
    stamp = "2026-03-01T09:00:00.001200+00:00"
    assert peek.redact("timestamp", stamp) == stamp


def test_large_amounts_are_not_mistaken_for_addresses() -> None:
    # "3125000000" starts with 3 and has ten characters, which matches the base58 shape.
    assert peek.redact("output_amounts", "3125000000") == "3125000000"
    assert peek.redact("total_sats", 3_125_000_000) == "3125000000"


def test_list_columns_show_at_most_three_elements() -> None:
    rendered = peek.redact("output_amounts", [1, 2, 3, 4, 5])
    assert rendered == "[1, 2, 3, (+2 more)]"
    assert peek.redact("output_amounts", []) == "[]"


def test_unknown_column_falls_back_to_value_shape() -> None:
    assert peek.redact("some_new_column", "203.0.113.66") == "203.0.x.x"
    assert peek.redact("some_new_column", SYNTHETIC_TXID) == "f1a70007…0000"


def test_csv_load_reports_the_whole_file() -> None:
    table = peek.load(CAPTURE_CSV)
    assert table.n_rows == 197
    assert [name for name, _ in table.columns][:6] == [
        "timestamp",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
        "txid",
    ]
    assert len(table.sample) == 3
    # One announcing peer has an unresolvable ASN; the coinbase has no inputs.
    assert table.nulls["asn"] == 1
    assert table.nulls["input_addresses"] == 9


def test_rendered_output_leaks_no_complete_identifier() -> None:
    """Render the real fixture and grep the result for every identifier it contains."""
    table = peek.load(CAPTURE_CSV)
    rendered = peek.render(CAPTURE_CSV, table)

    identifiers: set[str] = set()
    for row in table.sample:
        for column in ("src_ip", "dst_ip", "txid"):
            value = row[column]
            assert isinstance(value, str)
            identifiers.add(value)
        for column in ("input_addresses", "output_addresses"):
            cell = row[column]
            identifiers.update(cell if isinstance(cell, list) else [cell] if cell else [])

    assert identifiers, "sample carried no identifiers, so this test proved nothing"
    leaked = sorted(i for i in identifiers if i in rendered)
    assert not leaked, f"{len(leaked)} complete identifiers reached rendered output"

    # And the redacted forms are actually there, so the assertion above is not passing
    # because render() produced nothing.
    assert "203.0.x.x" in rendered
    assert "f1a70001…0000" in rendered


def test_no_flag_can_defeat_truncation() -> None:
    source = (REPO / "scripts" / "peek.py").read_text(encoding="utf-8")
    for banned in ("--full", "--raw", "--no-redact", "--untruncated"):
        assert banned not in source, f"peek.py grew a {banned} escape hatch"


# Mirrors tests/test_contracts.py. Nothing here needs pytest, so the file also runs under a
# bare interpreter, which is the only way to check redaction before `uv sync` has succeeded.
if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    print(f"failures: {failures}")
    raise SystemExit(1 if failures else 0)
