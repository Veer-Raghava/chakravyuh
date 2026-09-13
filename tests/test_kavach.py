"""KAVACH: what must hold about an intake stage reading someone else's file.

Two tests here are marked `quarantine` and registered in `tests/conftest.py`: the one that
runs the whole stage with the answer key absent from the filesystem, and the one that greps
the sealed output for the quarantined names. They are the Law 2 rules that only a real run can
demonstrate, so they are collected by `make verify-quarantine` as well as by the stage gate.

Every test that writes does so under `tmp_path`, and changes directory into it first. That is
not only hygiene: KAVACH's path guard is relative to the working directory, so running from
`tmp_path` exercises the guard rather than bypassing it.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from chakravyuh.kavach import readers
from chakravyuh.kavach.schema import (
    AmountUnit,
    CaptureFormatError,
    Container,
    Encoding,
    Shape,
    TimestampFormat,
    amount_shape,
    canonical_column,
    detect_amount_unit,
    detect_container,
    detect_encoding,
    detect_timestamp_format,
    to_sats,
)
from chakravyuh.kavach.seal import InputPathError, resolve_out, seal

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "data" / "fixtures" / "capture"
ENCODINGS = ("csv", "jsonl", "xml")


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo root with a `data/` tree, and the process moved into it."""
    (tmp_path / "data" / "generated").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _place(workspace: Path, name: str, payload: bytes | str) -> Path:
    """Write a capture under `data/` so the guard will accept it."""
    target = workspace / "data" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        target.write_text(payload, encoding="utf-8")
    else:
        target.write_bytes(payload)
    return target


def _seal_fixture(workspace: Path, encoding: str, run: str | None = None) -> Path:
    """Copy one committed fixture into the workspace and seal it. Returns `sealed/`."""
    source = FIXTURES / f"capture.{encoding}"
    placed = _place(workspace, f"capture.{encoding}", source.read_bytes())
    out = workspace / "data" / "generated" / (run or f"run-{encoding}")
    seal(placed, resolve_out(out))
    return out / "sealed"


def _manifest(sealed: Path) -> dict[str, object]:
    """The sealed manifest. Values are read back with `_int` and `_list` below."""
    payload: dict[str, object] = json.loads((sealed / "manifest.json").read_text(encoding="utf-8"))
    return payload


def _int(manifest: dict[str, object], key: str) -> int:
    value = manifest[key]
    assert isinstance(value, int), f"{key} is {type(value).__name__}, expected int"
    return value


# --------------------------------------------------------------------------------------------
# detection, from content and never from a name
# --------------------------------------------------------------------------------------------


def test_format_is_detected_from_content_not_from_the_extension() -> None:
    """The file that matters in a demo is the one an evaluator renamed."""
    assert detect_encoding('{"txid": "ab"}\n') is Encoding.JSONL
    assert detect_encoding("<rows><row/></rows>") is Encoding.XML
    assert detect_encoding("timestamp,src_ip\n1,2\n") is Encoding.CSV
    # A BOM and leading blank lines must not change the answer.
    assert detect_encoding('﻿\n\n  {"txid": "ab"}\n') is Encoding.JSONL

    assert detect_container(b"\x28\xb5\x2f\xfd\x00") is Container.ZSTD
    assert detect_container(b"\x1f\x8b\x08\x00") is Container.GZIP
    assert detect_container(b"timestamp,src_ip") is Container.PLAIN

    with pytest.raises(CaptureFormatError, match="JSON array"):
        detect_encoding('[{"txid": "ab"}]')
    with pytest.raises(CaptureFormatError, match="empty"):
        detect_encoding("   \n\n")


def test_amount_unit_needs_the_whole_column_to_agree() -> None:
    """One corrupt decimal must not reinterpret a satoshi file as BTC.

    The failure this guards is silent: multiplying every amount by 1e8 scales inputs and
    outputs alike, so `inputs >= outputs` still holds and no later invariant fires.
    """
    assert detect_amount_unit({"input_amounts": ["1", "200", "30000"]}) is AmountUnit.SATS
    assert detect_amount_unit({"input_amounts": ["0.5", "1.25"]}) is AmountUnit.BTC

    with pytest.raises(CaptureFormatError, match="input_amounts"):
        detect_amount_unit({"input_amounts": ["100000", "0.5", "200000"]})
    with pytest.raises(CaptureFormatError, match="disagree"):
        detect_amount_unit({"input_amounts": ["100000"], "output_amounts": ["0.5"]})

    # Junk is excluded from detection and costs its own row later, not the whole file.
    assert detect_amount_unit({"input_amounts": ["100", "", "oops"]}) is AmountUnit.SATS
    assert amount_shape("1e8") is Shape.BAD

    assert to_sats("0.00000001", AmountUnit.BTC) == 1
    assert to_sats("1.5", AmountUnit.BTC) == 150_000_000
    assert to_sats("12345", AmountUnit.SATS) == 12345
    with pytest.raises(ValueError, match="finer than one satoshi"):
        to_sats("0.000000001", AmountUnit.BTC)


def test_timestamp_format_is_read_from_magnitude() -> None:
    assert detect_timestamp_format(["1757520000"]) is TimestampFormat.EPOCH_S
    assert detect_timestamp_format(["1757520000000"]) is TimestampFormat.EPOCH_MS
    assert detect_timestamp_format(["1757520000000000"]) is TimestampFormat.EPOCH_US
    assert detect_timestamp_format(["2026-09-11T00:00:00Z"]) is TimestampFormat.ISO8601


def test_headers_match_case_insensitively_and_through_aliases() -> None:
    assert canonical_column("TimeStamp") == "timestamp"
    assert canonical_column("  SRC_IP ") == "src_ip"
    assert canonical_column("tx_hash") == "txid"
    assert canonical_column("in_amounts") == "input_amounts"
    assert canonical_column("nothing_like_a_column") is None


# --------------------------------------------------------------------------------------------
# the three encodings converge
# --------------------------------------------------------------------------------------------


def test_all_three_encodings_seal_to_byte_identical_rows(workspace: Path) -> None:
    """The reader contract, stated as bytes.

    Three files describing the same 197 announcements must produce one `rows.parquet`. Anything
    a reader invents, a null spelled differently or a list split differently, surfaces here.
    """
    digests = {}
    for encoding in ENCODINGS:
        sealed = _seal_fixture(workspace, encoding)
        digests[encoding] = hashlib.sha256((sealed / "rows.parquet").read_bytes()).hexdigest()

    assert (
        len(set(digests.values())) == 1
    ), f"the three encodings disagree: { {k: v[:12] for k, v in digests.items()} }"


def test_the_documented_bad_row_lands_in_rejected_with_its_reason(workspace: Path) -> None:
    """`data/fixtures/README.md` documents exactly one intentional rejection.

    Two input addresses against three input amounts, at `row_id` 189. The count and the reason
    are both fixed by that file, so a change in either is a change in behaviour.
    """
    sealed = _seal_fixture(workspace, "csv")
    rejected = pl.read_parquet(sealed / "rejected.parquet")

    assert rejected.height == 1
    assert rejected["reject_reason"].to_list() == ["input_length_mismatch"]
    assert rejected["row_id"].to_list() == [189]
    # The rejected row keeps its original text, because an investigator has to see what arrived.
    assert rejected["txid"][0] is not None

    # The array columns are real `list` types here too, per the section 1 Parquet convention.
    # Pipe-joined text is the CSV spelling of an array, not the Parquet one, and storing it that
    # way would make the frontend parse strings out of a column the contract says is a list.
    # `list[string]` rather than `list[int64]`: this row exists precisely because its amounts did
    # not typecheck, so the tokens have to survive untyped and separable.
    for column in ("input_addresses", "output_addresses", "input_amounts", "output_amounts"):
        assert rejected.schema[column] == pl.List(pl.String), column
    # The documented defect is two input addresses against three input amounts. If these were
    # stored pipe-joined, both lengths would read as 1 and the mismatch would be invisible.
    assert len(rejected["input_addresses"][0]) == 2
    assert len(rejected["input_amounts"][0]) == 3


def test_manifest_arithmetic_holds_and_matches_the_parquet(workspace: Path) -> None:
    for encoding in ENCODINGS:
        sealed = _seal_fixture(workspace, encoding)
        manifest = _manifest(sealed)

        read = _int(manifest, "rows_read")
        kept = _int(manifest, "rows_sealed")
        dropped = _int(manifest, "rows_rejected")

        assert (read, kept, dropped) == (197, 196, 1), f"{encoding} broke the fixture arithmetic"
        assert read == kept + dropped
        assert pl.read_parquet(sealed / "rows.parquet").height == kept
        assert pl.read_parquet(sealed / "rejected.parquet").height == dropped
        reasons = manifest["reject_reasons"]
        assert isinstance(reasons, dict)
        assert sum(reasons.values()) == dropped

        meta = json.loads((sealed / "_meta.json").read_text(encoding="utf-8"))
        assert meta["counts"] == {
            "in": read,
            "out": kept,
            "dropped": dropped,
            "drop_reasons": manifest["reject_reasons"],
        }


def test_types_are_coerced_to_the_contract(workspace: Path) -> None:
    sealed = _seal_fixture(workspace, "csv")
    rows = pl.read_parquet(sealed / "rows.parquet")

    assert rows.schema["ts_us"] == pl.Int64
    assert rows.schema["ts_raw"] == pl.String
    assert rows.schema["src_ip_version"] == pl.Int8
    assert rows.schema["input_amounts"] == pl.List(pl.Int64)
    assert rows.schema["row_id"] == pl.Int64

    # row_id is zero-based file order, and the rejected row's id is absent from the kept set.
    kept_ids = rows["row_id"].to_list()
    assert kept_ids == sorted(kept_ids)
    assert 189 not in kept_ids
    assert set(rows["src_ip_version"].unique().to_list()) <= {4, 6}


# --------------------------------------------------------------------------------------------
# tolerance: a missing optional column is a warning, never a crash
# --------------------------------------------------------------------------------------------


def test_a_missing_optional_column_completes_with_a_warning(workspace: Path) -> None:
    """A real NTRO file has none of our six extensions. It must still seal."""
    source = (FIXTURES / "capture.csv").read_text(encoding="utf-8").splitlines()
    header = source[0].split(",")
    drop = {header.index(name) for name in ("vsize", "msg_type", "observer_id")}
    trimmed = "\n".join(
        ",".join(cell for index, cell in enumerate(_split_csv(line)) if index not in drop)
        for line in source
    )

    placed = _place(workspace, "thin.csv", trimmed)
    out = workspace / "data" / "generated" / "thin"
    seal(placed, resolve_out(out))
    sealed = out / "sealed"

    manifest = _manifest(sealed)
    assert _int(manifest, "rows_read") == 197
    missing = manifest["columns_missing_optional"]
    assert isinstance(missing, list)
    assert set(missing) == {"vsize", "msg_type", "observer_id"}
    status = manifest["column_status"]
    assert isinstance(status, dict)
    assert status["vsize"] == "MISSING"
    assert status["timestamp"] == "MAPPED"
    warnings = manifest["warnings"]
    assert isinstance(warnings, list)
    assert any("vsize" in warning for warning in warnings)

    # A missing column is a null column, present in the schema and readable.
    rows = pl.read_parquet(sealed / "rows.parquet")
    assert rows["vsize"].null_count() == rows.height


def _split_csv(line: str) -> list[str]:
    import csv
    import io

    return next(iter(csv.reader(io.StringIO(line))))


def test_a_column_the_contract_requires_is_a_whole_file_failure(workspace: Path) -> None:
    """Missing `txid` is not 197 rejected rows, it is a file we cannot read at all."""
    placed = _place(workspace, "no_txid.csv", "timestamp,src_ip\n2026-01-01T00:00:00Z,10.0.0.1\n")
    out = workspace / "data" / "generated" / "no-txid"
    with pytest.raises(CaptureFormatError, match="txid"):
        seal(placed, resolve_out(out))


# --------------------------------------------------------------------------------------------
# custody: the hash precedes the parse
# --------------------------------------------------------------------------------------------


def test_the_input_hash_is_written_before_anything_is_parsed(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Break the reader, and `INPUT.sha256` must exist anyway.

    This is the ordering claim the evidence packet rests on. If hashing moved after parsing,
    the recorded digest would describe whatever survived the reader rather than the file that
    was handed over, and this test is the only thing that can tell the difference.
    """
    placed = _place(workspace, "capture.csv", (FIXTURES / "capture.csv").read_bytes())
    expected = hashlib.sha256(placed.read_bytes()).hexdigest()

    def explode(raw: bytes, path: Path) -> readers.Source:
        raise RuntimeError("reader deliberately broken")

    monkeypatch.setattr(readers, "read", explode)

    out = workspace / "data" / "generated" / "broken"
    with pytest.raises(RuntimeError, match="deliberately broken"):
        seal(placed, resolve_out(out))

    recorded = (out / "sealed" / "INPUT.sha256").read_text(encoding="utf-8")
    assert recorded.split()[0] == expected
    assert not (out / "sealed" / "rows.parquet").exists()


def test_the_staleness_link_records_the_upstream_hash(workspace: Path) -> None:
    """From S03 on, every `_meta.json` says which upstream manifest it consumed."""
    upstream = {"stage": "mayajaal", "run_id": "x"}
    directory = workspace / "data" / "capture"
    directory.mkdir(parents=True)
    (directory / "_meta.json").write_text(json.dumps(upstream), encoding="utf-8")
    (directory / "part-0000.csv").write_text(
        (FIXTURES / "capture.csv").read_text(encoding="utf-8"), encoding="utf-8"
    )

    out = workspace / "data" / "generated" / "linked"
    seal(directory, resolve_out(out))
    meta = json.loads((out / "sealed" / "_meta.json").read_text(encoding="utf-8"))

    link = meta["params"]["upstream_meta"]
    assert link["sha256"] == hashlib.sha256((directory / "_meta.json").read_bytes()).hexdigest()
    # `_meta.json` is not itself a capture, so it must not have been sealed as one.
    assert _int(_manifest(out / "sealed"), "rows_read") == 197


def test_the_code_version_names_a_revision_not_the_package(workspace: Path) -> None:
    """The contract asks `code_version` for a git sha and `tool_version` for `0.1.0`.

    Writing the package version into both makes the field unable to answer the only question it
    exists for: which code produced this seal. `code_version` is deliberately not masked out of
    the comparison gates, so it has to be stable within a commit and different between commits.
    """
    sealed = _seal_fixture(workspace, "csv")
    manifest = _manifest(sealed)
    meta = json.loads((sealed / "_meta.json").read_text(encoding="utf-8"))

    code = manifest["code_version"]
    assert isinstance(code, str)
    # A short sha, optionally marked dirty. Not the package version, and not `v0.1.0`.
    assert code[:12] == code[:12].lower()
    assert re.fullmatch(r"[0-9a-f]{7,40}(-dirty)?", code), code
    assert str(manifest["tool_version"]).count(".") == 2
    assert code != manifest["tool_version"]
    assert meta["code_version"] == code


def test_inputs_enumerate_the_capture_files_and_their_row_counts(workspace: Path) -> None:
    """`inputs` mirrors `INPUT.sha256`, and its row counts are the checkable half.

    The upstream `_meta.json` is an input in the custody sense, but it carries no rows. It is
    recorded under `params.upstream_meta` and deliberately absent here, so every `rows` value is
    an integer and the list sums to `counts.in` — which is the only way a shard read short shows
    up as a discrepancy rather than inside a correct-looking total.
    """
    upstream = {"stage": "mayajaal", "run_id": "x"}
    directory = workspace / "data" / "capture"
    directory.mkdir(parents=True)
    (directory / "_meta.json").write_text(json.dumps(upstream), encoding="utf-8")
    text = (FIXTURES / "capture.csv").read_text(encoding="utf-8")
    header, *body = text.splitlines()
    half = len(body) // 2
    (directory / "part-0000.csv").write_text(
        "\n".join([header, *body[:half]]) + "\n", encoding="utf-8"
    )
    (directory / "part-0001.csv").write_text(
        "\n".join([header, *body[half:]]) + "\n", encoding="utf-8"
    )

    out = workspace / "data" / "generated" / "sharded"
    seal(directory, resolve_out(out))
    meta = json.loads((out / "sealed" / "_meta.json").read_text(encoding="utf-8"))
    manifest = _manifest(out / "sealed")

    inputs = meta["inputs"]
    assert [Path(entry["path"]).name for entry in inputs] == ["part-0000.csv", "part-0001.csv"]
    # Same files, same order, as the manifest and INPUT.sha256.
    input_files = manifest["input_files"]
    assert isinstance(input_files, list)
    assert [entry["path"] for entry in inputs] == [e["path"] for e in input_files]
    assert [
        Path(line.split("  ", 1)[1]).name
        for line in (out / "sealed" / "INPUT.sha256").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] == ["part-0000.csv", "part-0001.csv"]
    # The upstream manifest is not among them.
    assert all("_meta.json" not in entry["path"] for entry in inputs)
    assert all(isinstance(entry["rows"], int) for entry in inputs)
    assert sum(entry["rows"] for entry in inputs) == meta["counts"]["in"] == 197


def test_the_manifest_wall_clock_is_excluded_from_its_recorded_hash(workspace: Path) -> None:
    """`sealed_at_us` cannot reproduce, so it is masked everywhere, not only in the diff."""
    sealed = _seal_fixture(workspace, "csv")
    manifest = _manifest(sealed)
    meta = json.loads((sealed / "_meta.json").read_text(encoding="utf-8"))

    assert "sealed_at_us" in manifest
    masked = {k: v for k, v in manifest.items() if k != "sealed_at_us"}
    expected = hashlib.sha256(
        json.dumps(masked, indent=2, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert meta["params"]["manifest"]["sha256_masked"] == expected

    # And the raw hash is nowhere in `outputs`, where a later stage would trust it to reproduce.
    assert all(Path(o["path"]).name != "manifest.json" for o in meta["outputs"])


# --------------------------------------------------------------------------------------------
# invariants that only a real file violates
# --------------------------------------------------------------------------------------------


def test_rows_disagreeing_about_one_txid_are_all_quarantined(workspace: Path) -> None:
    """Invariant 5, by hand.

    Three announcements of one txid, one of which claims a different output amount. The file is
    corrupt at that point and KAVACH does not pick a winner: a majority vote is a guess with
    extra steps, and the whole group goes to `rejected.parquet`.
    """
    txid = "a" * 64
    other = "b" * 64
    header = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,"
        "input_addresses,output_addresses,input_amounts,output_amounts\n"
    )
    row = "2026-01-01T00:00:0{n}Z,10.0.0.{n},10.9.9.9,8333,8333,{txid},A1,B1,1000,{out}\n"
    payload = header + "".join(
        (
            row.format(n=0, txid=txid, out=900),
            row.format(n=1, txid=txid, out=900),
            row.format(n=2, txid=txid, out=800),  # the disagreement
            row.format(n=3, txid=other, out=900),
        )
    )

    placed = _place(workspace, "disagree.csv", payload)
    out = workspace / "data" / "generated" / "disagree"
    seal(placed, resolve_out(out))
    sealed = out / "sealed"

    rejected = pl.read_parquet(sealed / "rejected.parquet")
    assert rejected.height == 3
    assert set(rejected["reject_reason"].to_list()) == {"chain_columns_disagree"}
    assert rejected["row_id"].to_list() == [0, 1, 2]

    rows = pl.read_parquet(sealed / "rows.parquet")
    assert rows.height == 1
    assert rows["row_id"].to_list() == [3]

    manifest = _manifest(sealed)
    assert _int(manifest, "rows_read") == 4
    assert _int(manifest, "rows_sealed") + _int(manifest, "rows_rejected") == 4


def test_each_reject_reason_is_reachable(workspace: Path) -> None:
    """One row per reason, so the vocabulary cannot rot into an unreachable branch."""
    header = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,"
        "input_addresses,output_addresses,input_amounts,output_amounts\n"
    )
    good = "2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,8333,8333,{txid},A1,B1,1000,900\n"
    cases = {
        "txid_malformed": good.format(txid="not-a-txid"),
        "timestamp_unparseable": good.format(txid="c" * 64).replace(
            "2026-01-01T00:00:00Z", "half past four"
        ),
        "input_length_mismatch": (
            f"2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,8333,8333,{'d' * 64},A1|A2,B1,1000,900\n"
        ),
        "output_length_mismatch": (
            f"2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,8333,8333,{'e' * 64},A1,B1,1000,900|50\n"
        ),
        "no_outputs": (f"2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,8333,8333,{'f' * 64},A1,,1000,\n"),
        "value_not_conserved": (
            f"2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,8333,8333,{'1' * 64},A1,B1,900,1000\n"
        ),
        "amount_unparseable": (
            f"2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,8333,8333,{'2' * 64},A1,B1,ten,900\n"
        ),
        "integer_unparseable": (
            f"2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,eighty,8333,{'3' * 64},A1,B1,1000,900\n"
        ),
        "missing_required_value": (
            f"2026-01-01T00:00:00Z,,10.9.9.9,8333,8333,{'4' * 64},A1,B1,1000,900\n"
        ),
    }

    placed = _place(workspace, "reasons.csv", header + "".join(cases.values()))
    out = workspace / "data" / "generated" / "reasons"
    seal(placed, resolve_out(out))
    sealed = out / "sealed"

    manifest = _manifest(sealed)
    assert _int(manifest, "rows_sealed") == 0
    reasons = manifest["reject_reasons"]
    assert isinstance(reasons, dict)
    assert set(reasons) == set(cases)


def test_a_coinbase_row_conserves_nothing_and_is_kept(workspace: Path) -> None:
    """No inputs means minted value, so `inputs >= outputs` does not apply."""
    header = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,"
        "input_addresses,output_addresses,input_amounts,output_amounts\n"
    )
    payload = header + (
        f"2026-01-01T00:00:00Z,10.0.0.1,10.9.9.9,8333,8333,{'5' * 64},,B1,,625000000\n"
    )
    placed = _place(workspace, "coinbase.csv", payload)
    out = workspace / "data" / "generated" / "coinbase"
    seal(placed, resolve_out(out))

    rows = pl.read_parquet(out / "sealed" / "rows.parquet")
    assert rows.height == 1
    assert rows["input_addresses"].to_list() == [[]]
    assert rows["output_amounts"].to_list() == [[625_000_000]]


# --------------------------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------------------------


def test_a_capture_path_outside_the_data_tree_is_refused(workspace: Path) -> None:
    """An allowlist, so no sibling tree is reachable however the path is spelled.

    A denylist would have to name the directories it excludes, and Law 2 rule 1 is a grep for
    those names over `src/`. Allowing only `data/` says the same thing without naming anything.
    """
    outside = workspace / "elsewhere" / "capture.csv"
    outside.parent.mkdir(parents=True)
    outside.write_text("timestamp,txid\n1,2\n", encoding="utf-8")

    with pytest.raises(InputPathError):
        seal(outside, resolve_out(workspace / "data" / "generated" / "nope"))

    # Including via traversal, which is the spelling that gets forgotten.
    with pytest.raises(InputPathError):
        seal(
            workspace / "data" / ".." / "elsewhere" / "capture.csv",
            resolve_out(workspace / "data" / "generated" / "nope"),
        )

    with pytest.raises(InputPathError):
        resolve_out(workspace / "elsewhere" / "run")


def test_a_doctype_is_refused_before_the_parser_sees_it() -> None:
    """XXE and billion-laughs, at a stage whose whole premise is a stranger's file."""
    bomb = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE rows [<!ENTITY a "aaaaaaaaaa">]>\n'
        "<rows><row><txid>&a;</txid></row></rows>"
    )
    with pytest.raises(CaptureFormatError, match="DOCTYPE"):
        readers.read(bomb.encode("utf-8"), Path("bomb.xml"))


def test_a_compressed_capture_is_transparent(workspace: Path) -> None:
    """gzip and zstd both decompress before the format is sniffed."""
    import gzip

    text = (FIXTURES / "capture.csv").read_text(encoding="utf-8")

    gz = _place(workspace, "capture.csv.gz", gzip.compress(text.encode("utf-8")))
    out_gz = workspace / "data" / "generated" / "gz"
    seal(gz, resolve_out(out_gz))
    assert _int(_manifest(out_gz / "sealed"), "rows_read") == 197

    import pyarrow as pa  # type: ignore[import-untyped]

    sink = pa.BufferOutputStream()
    with pa.CompressedOutputStream(sink, "zstd") as stream:
        stream.write(text.encode("utf-8"))
    zst = _place(workspace, "capture.csv.zst", sink.getvalue().to_pybytes())
    out_zst = workspace / "data" / "generated" / "zst"
    seal(zst, resolve_out(out_zst))
    assert _int(_manifest(out_zst / "sealed"), "rows_read") == 197

    # Same rows either way, and the container is recorded rather than inferred from the name.
    assert (
        hashlib.sha256((out_gz / "sealed" / "rows.parquet").read_bytes()).digest()
        == hashlib.sha256((out_zst / "sealed" / "rows.parquet").read_bytes()).digest()
    )


# --------------------------------------------------------------------------------------------
# the quarantine, registered in tests/conftest.py
# --------------------------------------------------------------------------------------------


def test_kavach_seals_with_the_answer_key_absent(workspace: Path) -> None:
    """Law 2 rule 6, run rather than asserted.

    A subprocess whose working directory holds only `data/`. The answer key is not merely
    unread here, it does not exist on any path the process could construct, so a stage that had
    quietly grown a dependency on it cannot complete.
    """
    _place(workspace, "capture.csv", (FIXTURES / "capture.csv").read_bytes())
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "from chakravyuh.kavach.seal import seal, resolve_out;"
        "seal(Path('data/capture.csv'), resolve_out(Path('data/generated/isolated')))"
    )
    finished = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-2000:]

    manifest = json.loads(
        (workspace / "data" / "generated" / "isolated" / "sealed" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["rows_sealed"] == 196


def test_no_sealed_artifact_names_the_quarantine(workspace: Path) -> None:
    """Law 2 rule 4: an observable file may not contain either quarantined name.

    Reconstructed from parts so this test file does not itself hold the literal strings the
    guard in `tests/test_contracts.py` greps for.
    """
    forbidden = ("ground" + "_truth", "measure" + "ments")
    sealed = _seal_fixture(workspace, "csv")

    for path in sorted(sealed.rglob("*")):
        if not path.is_file():
            continue
        blob = path.read_bytes().lower()
        for name in forbidden:
            assert name.encode("ascii") not in blob, f"{path.name} names {name}"
