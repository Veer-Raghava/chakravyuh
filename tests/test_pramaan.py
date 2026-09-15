"""PRAMAAN: what must hold when an alert becomes signed, replayable evidence.

Five groups. The cryptography group proves the Ed25519 module against the RFC 8032 test
vectors and proves the tamper property rather than asserting it. The packet group runs
the real stage over the fixture pipeline and checks the contract section 9 shape, the
replay claim, and the identifier law on both PDFs by grepping the rendered bytes. The
merkle group proves the log is append-only: a rewrite is detected, not tolerated. The
stage group proves the signature path and the replay command behave as the gate drives
them. The quarantine group holds the two Law 2 rules only a real run can demonstrate,
and both are registered in `tests/conftest.py` for `make verify-quarantine`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from chakravyuh.buddhi.stage import build_run as buddhi_run
from chakravyuh.buddhi.stage import resolve_in as buddhi_in
from chakravyuh.buddhi.stage import resolve_out as buddhi_out
from chakravyuh.eval.split import boundary_us
from chakravyuh.jaal.stage import build_run as build_graph
from chakravyuh.jaal.stage import resolve_in as jaal_in
from chakravyuh.jaal.stage import resolve_out as jaal_out
from chakravyuh.kavach.seal import resolve_out as kavach_out
from chakravyuh.kavach.seal import seal
from chakravyuh.pramaan import documents, merkle, pdflib
from chakravyuh.pramaan import packet as packet_mod
from chakravyuh.pramaan import stage as pramaan
from chakravyuh.pramaan.ed25519 import public_key, sign, verify
from chakravyuh.setu.stage import normalise_run
from chakravyuh.setu.stage import resolve_in as setu_in
from chakravyuh.setu.stage import resolve_out as setu_out
from chakravyuh.shastra.stage import build_run as build_signals
from chakravyuh.shastra.stage import resolve_in as shastra_in
from chakravyuh.shastra.stage import resolve_out as shastra_out
from chakravyuh.vaani.stage import build_run as build_alerts
from chakravyuh.vaani.stage import resolve_in as vaani_in
from chakravyuh.vaani.stage import resolve_out as vaani_out

REPO = Path(__file__).resolve().parent.parent
FIXTURE_CAPTURE = REPO / "data" / "fixtures" / "capture" / "capture.csv"

# RFC 8032 section 7.1, TEST 1 and TEST 2, transcribed by hand rather than generated.
RFC_SEED_1 = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
RFC_PUB_1 = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
RFC_SIG_1 = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
    "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
)
RFC_SEED_2 = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
RFC_PUB_2 = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
RFC_SIG_2 = bytes.fromhex(
    "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
    "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
)

# The rendered-output law: complete identifiers never reach a page. Hashes are the
# deliberate exception and are swept separately, by their prefix.
FULL_IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
FULL_IPV6 = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){4,7}[0-9a-fA-F]{1,4}\b")
FULL_TXID = re.compile(r"\b[0-9a-f]{64}\b")
FULL_ADDRESS = re.compile(r"\b(?:1|3|bc1)[0-9A-Za-z]{25,60}\b")
# Labelled hashes are the deliberate exception: strip them before the txid sweep, so a
# bare 64-hex run still fails and a disclosed sha256 does not.
LABELLED_HASH = re.compile(r"(?<=sha256 )[0-9a-f]{64}|(?<=digest )[0-9a-f]{64}")

# Contract section 9, transcribed by hand. The packet is one JSON object; its top-level
# keys and the nested keys a test would silently miss.
CONTRACT_TOP = {
    "case_id",
    "generated_at_us",
    "tool_version",
    "code_version",
    "input",
    "subject",
    "attribution",
    "findings",
    "counter_findings",
    "confidence",
    "chain_of_custody",
    "replay",
    "legal",
}
CONTRACT_NESTED = {
    "input": {"files", "rows_sealed"},
    "subject": {"subject_id", "addresses_redacted", "cluster_id"},
    "attribution": {
        "peer_ip",
        "peer_port",
        "observed_at_utc",
        "p_origin",
        "margin",
        "runner_up_peer_ip",
        "asn",
        "as_org",
        "geo_country",
        "net_class",
    },
    "confidence": {"low", "high", "coverage_target", "method"},
    "replay": {"seed", "command", "expected_packet_sha256"},
    "legal": {"basis", "hash_disclosure"},
}


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo root holding `data/` and `keys/`, with the process moved into it."""
    (tmp_path / "data" / "generated").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run_pipeline(workspace: Path, name: str) -> Path:
    """Seal, normalise, graph, estimate, score, alert — the fixture through six stages."""
    target = workspace / "data" / "capture.csv"
    target.write_bytes(FIXTURE_CAPTURE.read_bytes())
    seal(target, kavach_out(Path("data/generated") / name))
    run = workspace / "data" / "generated" / name
    normalise_run(setu_in(run / "sealed"), setu_out(run))
    build_graph(jaal_in(run / "normalised"), jaal_out(run))
    build_signals(shastra_in(run / "normalised"), shastra_out(run))
    announcements = pl.read_parquet(
        run / "normalised" / "announcements.parquet", columns=["seen_us"]
    )
    boundary = boundary_us(
        int(announcements["seen_us"].min()),  # type: ignore[arg-type]
        int(announcements["seen_us"].max()),  # type: ignore[arg-type]
        0.7,
    )
    buddhi_run(buddhi_in(run), buddhi_out(run), labels=None, boundary_us=boundary)
    build_alerts(vaani_in(run), vaani_out(run))
    return run


def _first_alert(run: Path) -> str:
    alerts = pl.read_parquet(run / "alerts" / "alerts.parquet", columns=["alert_id"])
    return str(alerts["alert_id"][0])


def _signer(workspace: Path) -> pramaan.KeyMaterial:
    """A key pair in the workspace's own `keys/`, so tests never touch the real one."""
    keys_dir = workspace / "keys"
    keys_dir.mkdir(exist_ok=True)
    seed = bytes(range(32))
    (keys_dir / "ed25519.seed").write_bytes(seed)
    (keys_dir / "ed25519.pub").write_bytes(public_key(seed))
    return pramaan.KeyMaterial(seed)


# --- cryptography: the RFC vectors and the tamper property ----------------------------------------


def test_ed25519_matches_rfc8032_test_vectors() -> None:
    """The two smallest RFC vectors, byte for byte. A signature that fails these is noise."""
    assert public_key(RFC_SEED_1) == RFC_PUB_1
    assert sign(RFC_SEED_1, b"") == RFC_SIG_1
    assert verify(RFC_PUB_1, b"", RFC_SIG_1)
    assert public_key(RFC_SEED_2) == RFC_PUB_2
    assert sign(RFC_SEED_2, b"\x72") == RFC_SIG_2
    assert verify(RFC_PUB_2, b"\x72", RFC_SIG_2)


def test_verification_fails_on_any_tamper() -> None:
    """Flip one bit of the signature, of the message, of the key: verification must fail.
    A signature that has never been tested against a tampered input is untested."""
    sig = bytearray(sign(RFC_SEED_1, b""))
    for index in (0, 31, 32, 63):  # one in R, the R/S boundary, one in S
        broken = bytearray(sig)
        broken[index] ^= 1
        assert not verify(RFC_PUB_1, b"", bytes(broken)), f"bit flip at {index} accepted"
    assert not verify(RFC_PUB_1, b"x", bytes(sig)), "a different message was accepted"
    assert not verify(RFC_PUB_2, b"", bytes(sig)), "a different key was accepted"
    assert not verify(RFC_PUB_1, b"", sig + b"\x00"), "a padded signature was accepted"


def test_signing_is_deterministic() -> None:
    """RFC 8032 signing is nonce-free: the same key and message, the same signature."""
    assert sign(RFC_SEED_1, b"") == sign(RFC_SEED_1, b"")


# --- the packet over the real pipeline ------------------------------------------------------------


def test_packet_matches_contract_section_nine(workspace: Path) -> None:
    """Every contract key present, custody covering all six stages, replay field honest."""
    run = _run_pipeline(workspace, "contract9")
    alert_id = _first_alert(run)
    packet = packet_mod.build(run, alert_id, seed=42, replay_command="replay-cmd")
    assert set(packet.keys()) == CONTRACT_TOP
    for section, keys in CONTRACT_NESTED.items():
        assert set(packet[section].keys()) == keys, f"{section} does not match the contract"
    custody = [link["stage"] for link in packet["chain_of_custody"]]
    assert custody == ["kavach", "setu", "jaal", "shastra", "buddhi", "vaani"]
    for link in packet["chain_of_custody"]:
        assert re.fullmatch(r"[0-9a-f]{64}", link["sha256"])
    assert packet["replay"]["seed"] == 42
    assert packet["legal"]["basis"] == "BNSS 2023 s.94"
    assert "s.63(4)" in packet["legal"]["hash_disclosure"]
    assert packet["counter_findings"], "a packet without counter-evidence is not a packet"
    # An anchored alert carries the whole machine fields section 9 quotes; a fixture run
    # is small, so assert whichever branch holds rather than assume.
    if packet["attribution"]["peer_ip"]:
        assert packet["attribution"]["peer_port"] > 0
        assert packet["attribution"]["observed_at_utc"].endswith("+00:00")
    else:
        assert packet["attribution"]["peer_ip"] == ""


def test_replay_field_actually_verifies(workspace: Path) -> None:
    """The digest recomputes over the canonical bytes with the field blanked. A claim that
    cannot be recomputed by a second analyst is decoration, and this is the recomputation."""
    run = _run_pipeline(workspace, "replay9")
    alert_id = _first_alert(run)
    packet = packet_mod.build(run, alert_id, seed=42, replay_command="replay-cmd")
    assert packet_mod.verify_replay_field(packet)
    forged = json.loads(json.dumps(packet))
    forged["replay"]["expected_packet_sha256"] = "0" * 64
    assert not packet_mod.verify_replay_field(forged), "a forged digest verified"
    # Any other tamper also breaks the digest: the field covers the whole packet.
    tampered = json.loads(json.dumps(packet))
    tampered["subject"]["subject_id"] += "x"
    assert not packet_mod.verify_replay_field(tampered)


def test_packet_generation_end_to_end(workspace: Path) -> None:
    """The stage writes all five files per case, the signature verifies, and the head lands
    on stdout, which is where the contract says the second analyst reads it."""
    run = _run_pipeline(workspace, "packeted")
    alert_id = _first_alert(run)
    signer = _signer(workspace)
    written = pramaan.build_run(run, run, alert_id, signer, workspace)
    case_dir = written[0]
    for name in ("packet.json", "packet.pdf", "notice.pdf", "packet.sig", "merkle.log"):
        assert (case_dir / name).is_file(), f"{name} missing from the case directory"
    assert pramaan.verify_signature(case_dir, workspace / "keys")
    manifest = json.loads((run / "packets" / "_meta.json").read_text(encoding="utf-8"))
    assert manifest["stage"] == "pramaan"
    assert manifest["counts"]["in"] == manifest["counts"]["out"] + manifest["counts"]["dropped"]


def test_regeneration_of_the_same_case_is_byte_identical(workspace: Path) -> None:
    """Same run, same case, two generations: the packet bytes match. The Merkle log grows
    by one leaf rather than rewriting, because the log is history, not state."""
    run = _run_pipeline(workspace, "twice9")
    alert_id = _first_alert(run)
    signer = _signer(workspace)
    case_dir = pramaan.build_run(run, run, alert_id, signer, workspace)[0]
    first = (case_dir / "packet.json").read_bytes()
    sig_first = (case_dir / "packet.sig").read_bytes()
    pramaan.build_run(run, run, alert_id, signer, workspace)
    assert (case_dir / "packet.json").read_bytes() == first
    assert (case_dir / "packet.sig").read_bytes() == sig_first
    log = (run / "packets" / "merkle.log").read_text(encoding="utf-8").splitlines()
    assert len(log) == 2, "the second generation should have appended, not rewritten"


def test_no_full_identifier_in_either_pdf(workspace: Path) -> None:
    """Grep the rendered PDF bytes for complete identifiers. Uncompressed streams are the
    point: the text sits in the bytes as literal characters, so a grep is a real check.
    SHA-256 values are the deliberate exception and are labelled where they appear."""
    run = _run_pipeline(workspace, "pdf-redact")
    alert_id = _first_alert(run)
    signer = _signer(workspace)
    case_dir = pramaan.build_run(run, run, alert_id, signer, workspace)[0]
    for name in ("packet.pdf", "notice.pdf"):
        text = (case_dir / name).read_bytes().decode("cp1252", "replace")
        assert not FULL_IPV4.search(text), f"{name} renders a complete IPv4"
        assert not FULL_IPV6.search(text), f"{name} renders a complete IPv6"
        assert not FULL_ADDRESS.search(text), f"{name} renders a complete address"
        stripped = LABELLED_HASH.sub("", text)
        assert not FULL_TXID.search(stripped), f"{name} renders a complete txid outside a hash"
    # The exception is load-bearing: hashes do appear, labelled.
    packet_text = (case_dir / "packet.pdf").read_bytes().decode("cp1252", "replace")
    assert "sha256" in packet_text


def test_documents_render_deterministically() -> None:
    """The same packet renders to the same bytes, twice, in one process."""
    sample = {
        "case_id": "alw-x",
        "generated_at_us": 0,
        "tool_version": "0.1.0",
        "code_version": "test",
        "input": {"files": [{"path": "capture.csv", "sha256": "ab" * 32}], "rows_sealed": 3},
        "subject": {
            "subject_id": "addr:bc1qxy…0wlh",
            "addresses_redacted": ["bc1qxy…0wlh"],
            "cluster_id": "",
        },
        "attribution": {
            "peer_ip": "203.0.113.7",
            "peer_port": 8333,
            "observed_at_utc": "2026-01-01T00:00:00+00:00",
            "p_origin": 0.5,
            "margin": 0.2,
            "runner_up_peer_ip": "203.0.114.9",
            "asn": 64503,
            "as_org": "Example AS",
            "geo_country": "IN",
            "net_class": "hosting",
        },
        "findings": [{"statement": "one", "kind": "model_feature", "source_ref": "s"}],
        "counter_findings": [
            {"statement": "doubt", "kind": "insufficient_observation", "would_clear": False}
        ],
        "confidence": {
            "low": 0.1,
            "high": 0.9,
            "coverage_target": 0.9,
            "method": "class_conditional",
        },
        "chain_of_custody": [
            {"stage": "kavach", "at_us": 0, "inputs": [], "outputs": [], "sha256": "cd" * 32}
        ],
        "replay": {"seed": 42, "command": "cmd", "expected_packet_sha256": "ef" * 32},
        "legal": {
            "basis": "BNSS 2023 s.94",
            "hash_disclosure": "BSA 2023 s.63(4), Schedule Part A",
        },
    }
    assert documents.packet_pdf(sample) == documents.packet_pdf(sample)
    assert documents.notice_pdf(sample) == documents.notice_pdf(sample)


def test_no_evaluation_figure_reaches_the_packet(workspace: Path) -> None:
    """An accuracy presented as a property of the evidence is the one misleading claim a
    judge could call out. The packet carries case-local numbers and hashes; the benchmark
    vocabulary stays out of packet.json and both PDFs entirely."""
    run = _run_pipeline(workspace, "no-eval-figures")
    alert_id = _first_alert(run)
    signer = _signer(workspace)
    case_dir = pramaan.build_run(run, run, alert_id, signer, workspace)[0]
    forbidden = (
        "accuracy",
        "pr_auc",
        "roc_auc",
        "precision_at",
        "recall_at",
        "top1",
        "top3",
        "eval_report",
    )
    text = (case_dir / "packet.json").read_text(encoding="utf-8")
    assert not any(word in text for word in forbidden), "packet.json quotes a benchmark figure"
    for name in ("packet.pdf", "notice.pdf"):
        rendered = (case_dir / name).read_bytes().decode("cp1252", "replace")
        assert not any(word in rendered for word in forbidden), f"{name} quotes a benchmark"


# --- the merkle log is append-only ----------------------------------------------------------------


def test_merkle_log_detects_a_rewrite(tmp_path: Path) -> None:
    """Rewrite, remove or reorder a leaf and the recomputed chain breaks. Append-only is
    a property someone can check, not a file naming convention."""
    log = tmp_path / "merkle.log"
    a, b, c = b"one", b"two", b"three"
    merkle.append(log, a)
    merkle.append(log, b)
    assert merkle.verify(log) == (True, merkle.root_of([merkle.leaf(a), merkle.leaf(b)]))
    head_two = merkle.verify(log)[1]

    merkle.append(log, c)
    leaves, _ = merkle.read(log)
    assert leaves == [merkle.leaf(a), merkle.leaf(b), merkle.leaf(c)]
    head_three = merkle.verify(log)[1]
    assert head_three != head_two, "appending did not move the head"

    lines = log.read_text(encoding="utf-8").splitlines()
    log.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
    ok, _ = merkle.verify(log)
    assert not ok, "removing the first leaf went undetected"

    log.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
    ok, _ = merkle.verify(log)
    assert not ok, "reordering went undetected"

    tampered = lines[0].replace(merkle.leaf(a), "0" * 64)
    log.write_text("\n".join([tampered, *lines[1:]]) + "\n", encoding="utf-8")
    ok, _ = merkle.verify(log)
    assert not ok, "a replaced leaf went undetected"


# --- the stage driver and its guards --------------------------------------------------------------


def test_case_guard_rejects_unknown_and_cross_cases(workspace: Path) -> None:
    """A case id that is not an alert id in this run raises: `--case` is a join key, never
    a path, and letting one through would be a path traversal by another name."""
    run = _run_pipeline(workspace, "guarded")
    with pytest.raises(packet_mod.CaseError):
        packet_mod.resolve_case("../sealed/rows", run / "alerts")
    with pytest.raises(packet_mod.CaseError):
        packet_mod.resolve_case("alw-nonexistent", run / "alerts")


def test_verify_replay_command_returns_zero_and_detects_a_byte(workspace: Path) -> None:
    """The command the gate calls: true on a faithful run; after one byte of the packet
    changes, false. This is `make verify-replay` in miniature, in process."""
    run = _run_pipeline(workspace, "replay-cmd")
    alert_id = _first_alert(run)
    signer = _signer(workspace)
    case_dir = pramaan.build_run(run, run, alert_id, signer, workspace)[0]
    assert pramaan.verify_replay(run, run, alert_id, workspace)
    raw = (case_dir / "packet.json").read_bytes()
    broken = raw.replace(b'"rows_sealed":', b'"rows_sealed" :', 1)
    assert broken != raw
    (case_dir / "packet.json").write_bytes(broken)
    assert not pramaan.verify_replay(run, run, alert_id, workspace)


def test_stage_path_guards(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The restated path guard: nothing outside `data/generated/` can be named."""
    (workspace / "outside").mkdir()
    with pytest.raises(pramaan.InputPathError):
        pramaan.resolve_in(Path("outside/run"))
    with pytest.raises(pramaan.InputPathError):
        pramaan.resolve_out(Path("data/generated"))


# --- quarantine: the two Law 2 rules only a real run can demonstrate ------------------------------


def test_pramaan_builds_with_the_answer_key_absent(workspace: Path) -> None:
    """Law 2 rule 6, run rather than asserted: no answer key on any path, stage completes."""
    _run_pipeline(workspace, "isolated9")
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "from chakravyuh.pramaan import stage as pramaan;"
        "from chakravyuh.pramaan.stage import resolve_in, resolve_out;"
        "run = resolve_in(Path('data/generated/isolated9'));"
        "out = resolve_out(Path('data/generated/isolated9'));"
        "keys = pramaan.load_or_create_keys(Path.cwd());"
        "written = pramaan.build_run(run, out, None, keys, Path.cwd());"
        "assert written, 'no packets written'"
    )
    finished = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-2000:]


def test_no_packets_artifact_names_the_quarantine(workspace: Path) -> None:
    """Law 2 rule 4: no observable file may contain either quarantined path. The literals
    are reconstructed so this file does not itself hold them."""
    forbidden = ("ground" + "_truth", "measure" + "ments")
    packets_dir = _run_pipeline(workspace, "sealed-words9") / "packets"
    alert_id = _first_alert(packets_dir.parent)
    signer = _signer(workspace)
    pramaan.build_run(packets_dir.parent, packets_dir.parent, alert_id, signer, workspace)

    checked = 0
    for path in sorted(packets_dir.rglob("*")):
        if not path.is_file():
            continue
        checked += 1
        if path.suffix in {".json", ".log", ".pdf", ".sig"}:
            text = path.read_bytes().decode("cp1252", "replace")
            assert not any(one in text for one in forbidden), f"{path.name} names the quarantine"
        else:
            raise AssertionError(f"unexpected file shape in packets/: {path.name}")
    assert checked >= 6, "the walk found fewer files than one case writes, so it proved nothing"

    for module in sorted((REPO / "src" / "chakravyuh" / "pramaan").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        assert not any(one in text for one in forbidden), f"{module.name} names the quarantine"


def test_pdf_writer_renders_wrap_and_rules(tmp_path: Path) -> None:
    """The dependency-free writer's one page holds text, a rule, and the ellipsis that the
    truncation law produces, as literal characters in the stream."""
    doc = pdflib.Document("probe")
    page = doc.page()
    page.text(72, 72, "serif", 11, "bc1q4f…9f4d")
    page.rule(72, 90, 100.0)
    for line in pdflib.wrap("word " * 30, "serif", 11, 200.0):
        page.text(72, 120 + 14 * (len(doc.render()) % 7), "mono", 9, line)
    raw = doc.render()
    assert raw.startswith(b"%PDF-1.4")
    assert "bc1q4f…9f4d".encode("cp1252") in raw
    assert pdflib.wrap("a b c", "serif", 11, 20.0) == ["a b", "c"]
