"""Contract tests for the S00 fixture set and the ground-truth quarantine.

These read the three fixture files from disk rather than importing the builder that wrote
them. That independence is the point: a bug in scripts/make_fixtures.py must fail a test
here instead of being trusted away, and every column set below is transcribed from
docs/DATA-CONTRACTS.md rather than imported from code.

Standard library only, so this file runs under a bare interpreter as well as under pytest:

    python3 tests/test_contracts.py
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
CAPTURE = REPO / "data" / "fixtures" / "capture"

# Section 1. Twelve required columns then six optional ones, in file order.
REQUIRED = (
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
    "input_addresses",
    "input_amounts",
    "output_addresses",
    "output_amounts",
    "geo_country",
    "asn",
)
OPTIONAL = ("fee_sats", "vsize", "script_types", "block_height", "msg_type", "observer_id")
COLUMNS = REQUIRED + OPTIONAL

LIST_STR = ("input_addresses", "output_addresses", "script_types")
LIST_INT = ("input_amounts", "output_amounts")
SCALAR_INT = ("src_port", "dst_port", "asn", "fee_sats", "vsize", "block_height")
NULLABLE = ("geo_country", "asn", "block_height")

# Columns that make a row identify the same transaction, so rows sharing a txid must carry
# byte-identical values for all of them. Invariant 5.
CHAIN = ("input_addresses", "input_amounts", "output_addresses", "output_amounts")

N_ROWS = 197
N_TXIDS = 26

RESERVED_V4_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.")
RESERVED_V6_PREFIX = "2001:db8:"
ASN_DOC_RANGE = range(64496, 64512)

# Every column name from section 2, the ground-truth section. None of these may appear in an
# observable artifact. Matching is exact and never by substring: the capture legitimately
# carries input_addresses and output_addresses, and a substring rule would reject the
# fixture for containing the forbidden name "addresses".
FORBIDDEN_GT_COLUMNS = frozenset(
    {
        "true_origin_ip",
        "true_origin_entity_id",
        "broadcast_us",
        "used_tor",
        "used_vpn",
        "observed_by_n",
        "behind_cgnat",
        "entity_id",
        "entity_type",
        "is_illicit",
        "typologies",
        "campaign_id",
        "entity_ids",
        "addresses",
        "ips",
        "typology",
        "txids",
        "start_us",
        "end_us",
        "total_sats",
    }
)


def txid_of(idx: int) -> str:
    return f"f1a7{idx:04d}" + "0" * 56


def _us(stamp: str) -> int:
    """Microseconds since the epoch, from an ISO 8601 timestamp with an explicit offset."""
    return int(datetime.fromisoformat(stamp).timestamp() * 1_000_000)


def _coerce(column: str, raw: str | None) -> object:
    """Turn one CSV or XML text field into the value the JSONL form holds natively."""
    if column in LIST_STR:
        return [] if not raw else raw.split("|")
    if column in LIST_INT:
        return [] if not raw else [int(v) for v in raw.split("|")]
    if raw is None or raw == "":
        return None
    return int(raw) if column in SCALAR_INT else raw


def load_csv() -> list[dict[str, Any]]:
    with (CAPTURE / "capture.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert list(reader.fieldnames or []) == list(COLUMNS), "CSV header is not section 1"
        return [{c: _coerce(c, row[c]) for c in COLUMNS} for row in reader]


def load_jsonl() -> list[dict[str, Any]]:
    text = (CAPTURE / "capture.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line]


def load_xml() -> list[dict[str, Any]]:
    """List columns arrive as repeated <item> children; a null arrives as an empty element.

    An empty list and a null are indistinguishable in the XML, which is why the column name
    decides: section 1 fixes which columns are lists, so nothing is actually ambiguous.
    """
    root = ET.parse(CAPTURE / "capture.xml").getroot()
    rows: list[dict[str, Any]] = []
    for el in root.findall("row"):
        row: dict[str, Any] = {}
        for column in COLUMNS:
            child = el.find(column)
            assert child is not None, f"XML row is missing {column}"
            items = child.findall("item")
            if column in LIST_STR or column in LIST_INT:
                joined = "|".join(i.text or "" for i in items)
                row[column] = _coerce(column, joined)
            else:
                row[column] = _coerce(column, child.text)
        rows.append(row)
    return rows


def _by_txid(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["txid"], []).append(row)
    return grouped


def test_all_three_fixture_files_load() -> None:
    for rows in (load_csv(), load_jsonl(), load_xml()):
        assert len(rows) == N_ROWS
        assert set(rows[0]) == set(COLUMNS)


def test_three_formats_describe_the_same_capture() -> None:
    """Byte-level encodings differ; the capture they describe must not."""
    from_csv, from_jsonl, from_xml = load_csv(), load_jsonl(), load_xml()
    for i, (a, b, c) in enumerate(zip(from_csv, from_jsonl, from_xml, strict=True)):
        assert a == b, f"row {i} differs between CSV and JSONL"
        assert a == c, f"row {i} differs between CSV and XML"


def test_column_order_and_types_match_section_one() -> None:
    for row in load_jsonl():
        assert list(row) == list(COLUMNS)
        for column in LIST_STR:
            assert all(isinstance(v, str) for v in row[column])
        for column in LIST_INT:
            assert all(isinstance(v, int) for v in row[column])
        for column in SCALAR_INT:
            assert row[column] is None or isinstance(row[column], int)
        for column in set(COLUMNS) - set(LIST_STR) - set(LIST_INT) - set(SCALAR_INT):
            assert isinstance(row[column], str)


def test_only_nullable_columns_carry_nulls() -> None:
    for i, row in enumerate(load_jsonl()):
        for column in COLUMNS:
            if column in NULLABLE or column in LIST_STR or column in LIST_INT:
                continue
            assert row[column] is not None, f"row {i}: {column} is null but not nullable"


def test_timestamps_are_iso_8601_with_microseconds_and_an_offset() -> None:
    for row in load_jsonl():
        stamp = row["timestamp"]
        assert stamp.endswith("+00:00"), stamp
        assert len(stamp.split(".")[1]) == len("000000+00:00"), stamp
        datetime.fromisoformat(stamp)


def test_no_ground_truth_column_name_appears_in_an_observable_fixture() -> None:
    """A leaked label makes every published number a lie, so this checks names, not values."""
    observable = set(COLUMNS)
    leaked = sorted(observable & FORBIDDEN_GT_COLUMNS)
    assert not leaked, f"section 2 column names in an observable artifact: {leaked}"

    # Anti-vacuity: exact matching is the whole point, so prove the set is non-empty and
    # that a near-miss the capture does carry is not treated as a hit.
    assert "true_origin_ip" in FORBIDDEN_GT_COLUMNS
    assert "input_addresses" in observable
    assert "addresses" in FORBIDDEN_GT_COLUMNS


def test_no_src_module_reaches_for_ground_truth() -> None:
    """Only src/chakravyuh/eval/ may read ground_truth/. Everything else is checked by grep."""
    quarantine = REPO / "src" / "chakravyuh" / "eval"
    offenders: list[str] = []
    checked = 0
    for module in sorted((REPO / "src").rglob("*.py")):
        if quarantine in module.parents:
            continue
        checked += 1
        if "ground_truth" in module.read_text(encoding="utf-8"):
            offenders.append(str(module.relative_to(REPO)))
    assert not offenders, f"modules outside eval/ reference ground_truth: {offenders}"
    assert checked >= 10, f"only {checked} modules scanned, so the grep proved little"

    # Anti-vacuity: the skip clause must be excluding something real.
    permitted = (quarantine / "__init__.py").read_text(encoding="utf-8")
    assert "ground_truth" in permitted, "eval/__init__.py no longer names its own quarantine"


def test_no_fixture_value_looks_like_a_ground_truth_label() -> None:
    """Section 2's is_illicit and typologies must not have leaked in as values either."""
    text = (CAPTURE / "capture.jsonl").read_text(encoding="utf-8")
    for banned in ("is_illicit", "true_origin", "typolog", "campaign_id", "entity_id"):
        assert banned not in text, f"fixture values mention {banned}"


def test_every_txid_is_sixty_four_lowercase_hex() -> None:
    for row in load_jsonl():
        txid = row["txid"]
        assert len(txid) == 64, txid
        assert txid == txid.lower()
        int(txid, 16)


def test_chain_columns_are_identical_across_rows_sharing_a_txid() -> None:
    """Invariant 5. Two peers announcing one transaction must not disagree about it."""
    for txid, rows in _by_txid(load_jsonl()).items():
        for column in CHAIN + ("fee_sats", "vsize", "script_types", "block_height"):
            values = {json.dumps(row[column]) for row in rows}
            assert len(values) == 1, f"{txid[:8]}… disagrees on {column} across {len(rows)} rows"


def test_exactly_one_row_violates_the_load_invariants() -> None:
    """Invariant 3: one address per amount. The fixture breaks it once, deliberately."""
    bad = [
        row
        for row in load_jsonl()
        if len(row["input_addresses"]) != len(row["input_amounts"])
        or len(row["output_addresses"]) != len(row["output_amounts"])
    ]
    assert len(bad) == 1, f"expected exactly one malformed row, found {len(bad)}"
    assert bad[0]["txid"] == txid_of(26)
    assert len(bad[0]["input_addresses"]) == 2
    assert len(bad[0]["input_amounts"]) == 3


def test_script_types_has_one_entry_per_output() -> None:
    for row in load_jsonl():
        assert len(row["script_types"]) == len(row["output_addresses"])
        assert set(row["script_types"]) <= {"p2pkh", "p2sh", "p2wpkh", "p2wsh", "p2tr"}


def test_inputs_cover_outputs_and_the_fee_is_the_difference() -> None:
    """Invariant 4, plus section 4's rule that a coinbase carries a zero fee."""
    for row in load_jsonl():
        total_in, total_out = sum(row["input_amounts"]), sum(row["output_amounts"])
        if not row["input_addresses"] and not row["input_amounts"]:
            assert row["fee_sats"] == 0, f"{row['txid'][:8]}… is a coinbase with a fee"
            continue
        assert total_in >= total_out, f"{row['txid'][:8]}… spends more than it holds"
        assert row["fee_sats"] == total_in - total_out


def test_amounts_are_positive_integer_satoshis() -> None:
    for row in load_jsonl():
        for amount in row["input_amounts"] + row["output_amounts"]:
            assert isinstance(amount, int) and amount > 0, amount


def test_all_twelve_awkward_cases_are_present() -> None:
    """Section 11's checklist, one assertion per case, in the order section 11 lists them.

    A generator that never produces these is a generator that flatters every downstream
    stage, so this is the test that keeps the fixture honest.
    """
    rows = load_jsonl()
    grouped = _by_txid(rows)
    assert len(grouped) == N_TXIDS
    first_seen = {t: min(_us(r["timestamp"]) for r in rs) for t, rs in grouped.items()}
    openers = {
        t: min(rs, key=lambda r: (_us(r["timestamp"]), r["src_ip"]))["src_ip"]
        for t, rs in grouped.items()
    }

    # 1. A coinbase, which has zero inputs.
    coinbase = [t for t, rs in grouped.items() if not rs[0]["input_addresses"]]
    assert coinbase == [txid_of(1)], "no coinbase transaction"
    assert grouped[txid_of(1)][0]["input_amounts"] == []

    # 2. A wallet with a regular payout cadence: three beats exactly 600 s apart.
    beats = [txid_of(2), txid_of(3), txid_of(4)]
    shared = {frozenset(grouped[t][0]["input_addresses"]) for t in beats}
    assert len(shared) == 1, "the cadence transactions do not share an input address"
    gaps = [first_seen[b] - first_seen[a] for a, b in zip(beats, beats[1:], strict=False)]
    assert gaps == [600_000_000, 600_000_000], f"cadence gaps are {gaps} microseconds"

    # 3. A transaction announced by exactly one peer, so origin must abstain.
    singles = [t for t, rs in grouped.items() if len({r["src_ip"] for r in rs}) == 1]
    assert txid_of(5) in singles and len(grouped[txid_of(5)]) == 1

    # 4. A transaction announced by more than fifteen peers.
    widest = max(grouped.values(), key=lambda rs: len({r["src_ip"] for r in rs}))
    assert len({r["src_ip"] for r in widest}) > 15

    # 5. Two peers announcing in the same microsecond.
    ties = [
        t
        for t, rs in grouped.items()
        if any(
            len({r["src_ip"] for r in rs if r["timestamp"] == stamp}) > 1
            for stamp in {r["timestamp"] for r in rs}
        )
    ]
    assert txid_of(7) in ties, "no two peers share a microsecond"

    # 6. A first announcer that is a Tor exit.
    assert openers[txid_of(8)] == "203.0.113.66"

    # 7. Two distinct wallets behind one IP, separable only by source port.
    ports: dict[str, set[int]] = {}
    for row in rows:
        ports.setdefault(row["src_ip"], set()).add(row["src_port"])
        assert row["dst_port"] == 8333
    cgnat = sorted(ip for ip, p in ports.items() if len(p) > 1)
    assert cgnat == ["203.0.113.90"], f"expected one CGNAT address, found {cgnat}"
    assert ports["203.0.113.90"] == {41000, 41001}
    assert openers[txid_of(9)] == openers[txid_of(10)] == "203.0.113.90"
    behind = {r["src_port"]: r["txid"] for r in rows if r["src_ip"] == "203.0.113.90"}
    assert behind[41000] != behind[41001], "the two CGNAT ports announce the same transaction"

    # 8. Equal value outputs, which defeat common-input-ownership clustering.
    equal = [
        t
        for t, rs in grouped.items()
        if len(rs[0]["output_amounts"]) >= 4 and len(set(rs[0]["output_amounts"])) == 1
    ]
    assert txid_of(11) in equal
    assert grouped[txid_of(11)][0]["output_amounts"] == [250_000] * 4

    # 9. A peel chain at least three hops long: each hop spends the previous hop's change.
    hops = [grouped[txid_of(i)][0] for i in (12, 13, 14)]
    for earlier, later in zip(hops, hops[1:], strict=False):
        link = set(later["input_addresses"]) & set(earlier["output_addresses"])
        assert len(link) == 1, "peel chain is broken"
    assert len({h["txid"] for h in hops}) == 3

    # 10. An IPv6 peer, which must not crash /24 aggregation.
    v6 = sorted({r["src_ip"] for r in rows if ":" in r["src_ip"]})
    assert v6 == ["2001:db8:0:1::7"]
    assert openers[txid_of(15)] == "2001:db8:0:1::7"

    # 11. A peer whose ASN does not resolve. Null, not zero.
    missing_asn = [r for r in rows if r["asn"] is None]
    assert len(missing_asn) == 1
    assert missing_asn[0]["src_ip"] == "203.0.113.140"
    assert 0 not in {r["asn"] for r in rows}, "a missing ASN was encoded as zero"

    # 12. A malformed row that must be rejected rather than loaded.
    assert len(grouped[txid_of(26)]) == 1
    assert len(grouped[txid_of(26)][0]["input_addresses"]) != len(
        grouped[txid_of(26)][0]["input_amounts"]
    )


def test_no_fixture_identifier_can_belong_to_a_real_person_or_a_real_coin() -> None:
    """Every address, IP and ASN is either reserved for documentation or structurally invalid.

    An invented identifier can turn out to belong to someone. A forensics tool whose test
    data names a real wallet has failed at its own premise, so this is checked rather than
    asserted in a comment.
    """
    rows = load_jsonl()

    for row in rows:
        ip = row["src_ip"]
        assert ip.startswith(RESERVED_V4_PREFIXES) or ip.startswith(RESERVED_V6_PREFIX), ip
        assert row["dst_ip"].startswith("198.51.100."), row["dst_ip"]
        assert row["asn"] is None or row["asn"] in ASN_DOC_RANGE, row["asn"]
        assert row["geo_country"] is None or len(row["geo_country"]) == 2

    addresses = {a for r in rows for a in r["input_addresses"] + r["output_addresses"]}
    assert addresses, "fixture carries no addresses, so this test proved nothing"
    for address in sorted(addresses):
        if address.startswith("bc1"):
            # "i" is not in the bech32 charset, so this string can never decode.
            assert "i" in address[4:], f"{address[:6]}… could be a valid bech32 address"
        else:
            assert address[0] in {"1", "3"}, address[:6]
            # "0" is not in the base58 alphabet, so this string can never checksum.
            assert "0" in address[1:], f"{address[:6]}… could be a valid base58 address"

    # txids are valid hex so KAVACH's parser is exercised, but the f1a7 prefix plus an index
    # plus fifty-six zeros is not a plausible hash of anything.
    for row in rows:
        assert row["txid"].startswith("f1a7")
        assert row["txid"].endswith("0" * 40)


def test_fixture_is_small_enough_to_read_by_eye() -> None:
    """Section 11 asks for a set a person can check by hand, not a benchmark."""
    for name in ("capture.csv", "capture.jsonl", "capture.xml"):
        path = CAPTURE / name
        assert path.exists(), f"missing fixture {name}"
        assert path.stat().st_size < 1_000_000, f"{name} is too big to read by eye"
    assert (CAPTURE.parent / "README.md").exists(), "fixtures/README.md is missing"


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
