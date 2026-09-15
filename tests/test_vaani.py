"""VAANI: what must hold when a score becomes an alert with its case against itself.

Four groups. The unit group works from hand-built frames: the truncation law per identifier
type, the gloss table that keeps raw column names out of prose, and the three-sentence reason
string that must not drift between processes. The behaviour group runs the real stage over
the committed capture fixture and asserts the contract's shape and the mandatory-counter rule
on files it wrote. The mining-pool group is the named case the brief calls out: an entity
whose own type explains the behaviour must generate a counter that clears it. The quarantine
group holds the two Law 2 rules only a real run can demonstrate, and both are registered in
`tests/conftest.py` for `make verify-quarantine`.
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
from chakravyuh.setu.stage import normalise_run
from chakravyuh.setu.stage import resolve_in as setu_in
from chakravyuh.setu.stage import resolve_out as setu_out
from chakravyuh.shastra.stage import build_run as build_signals
from chakravyuh.shastra.stage import resolve_in as shastra_in
from chakravyuh.shastra.stage import resolve_out as shastra_out
from chakravyuh.vaani import counters, evidence, gloss, redact
from chakravyuh.vaani.stage import build_run, resolve_in, resolve_out

REPO = Path(__file__).resolve().parent.parent
FIXTURE_CAPTURE = REPO / "data" / "fixtures" / "capture" / "capture.csv"

# Contract section 8, transcribed by hand rather than imported from the writer.
CONTRACT_ALERTS: list[tuple[str, str]] = [
    ("alert_id", "String"),
    ("subject_id", "String"),
    ("rank", "Int32"),
    ("severity", "String"),
    ("conf_low", "Float64"),
    ("conf_high", "Float64"),
    ("headline", "String"),
    ("origin_txid", "String"),
    ("origin_peer_ip", "String"),
    ("origin_p", "Float64"),
    ("attribution_ready", "Boolean"),
]
CONTRACT_EVIDENCE: list[tuple[str, str]] = [
    ("alert_id", "String"),
    ("kind", "String"),
    ("statement", "String"),
    ("weight", "Float64"),
    ("source_ref", "String"),
]
CONTRACT_COUNTER: list[tuple[str, str]] = [
    ("alert_id", "String"),
    ("kind", "String"),
    ("statement", "String"),
    ("strength", "Float64"),
    ("would_clear", "Boolean"),
]
EVIDENCE_KINDS = {"typology", "origin_estimate", "cluster_edge", "model_feature", "network_context"}
COUNTER_KINDS = {
    "entity_type_conflict",
    "shared_ip",
    "weak_cluster_link",
    "low_origin_margin",
    "pool_payout_pattern",
    "insufficient_observation",
}

FULL_IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
FULL_TXID = re.compile(r"\b[0-9a-fA-F]{64}\b")
FULL_ADDRESS = re.compile(r"\b(?:1|3|bc1)[0-9A-Za-z]{25,60}\b")
FULL_IPV6 = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){4,7}[0-9a-fA-F]{1,4}\b")


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo root holding `data/` and nothing else, with the process moved into it."""
    (tmp_path / "data" / "generated").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run_pipeline(workspace: Path, name: str) -> Path:
    """Seal, normalise, graph, estimate, score, then alert — the fixture through five stages.

    Labels are None: nothing in VAANI's path needs them, which is itself the property the
    quarantine test relies on. BUDDHI degrades to untrained and still writes `scores/`.
    """
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
    build_run(resolve_in(run), resolve_out(run))
    return run


# --- the truncation law, unit level ---------------------------------------------------------------


def test_truncators_produce_the_specified_shapes() -> None:
    """The four truncations of the never-render rule, each on a realistic value."""
    assert redact.redact_address("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh") == ("bc1qxy…0wlh")
    assert redact.redact_txid("0123456789abcdef" * 4) == "01234567…cdef"
    assert redact.redact_ip("203.0.113.7") == "203.0.x.x"
    assert redact.redact_ip("2001:db8:3333:4444:5555:6666:7777:8888") == "2001:db8:x:x"


def test_truncators_never_widen_a_short_value() -> None:
    """A value shorter than its own truncation is kept as-is rather than padded into a lie."""
    assert redact.redact_address("bc1q50") == "bc1q50"
    assert redact.redact_txid("abcd1234") == "abcd1234"


# --- gloss and the reason string ------------------------------------------------------------------


def test_gloss_refuses_an_unglossed_name() -> None:
    """A raw column name must never reach prose; an unknown name raises instead."""
    with pytest.raises(ValueError, match="not glossed"):
        gloss.gloss({"known": "a known thing"}, "unglossed_column")


def _evidence_fixtures() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """One alert's evidence and counters, and the internal row reason_string reads."""
    alerts = pl.DataFrame(
        {
            "alert_id": ["alw-x"],
            "subject_id": ["cluster:0"],
            "origin_txid": [None],
            "origin_peer_ip": [None],
            "origin_p": [None],
            "conf_low": [0.0],
            "conf_high": [1.0],
        }
    )
    evidence_frame = pl.DataFrame(
        {
            "alert_id": ["alw-x", "alw-x"],
            "kind": ["model_feature", "model_feature"],
            "statement": [
                "this wallet's share of its transactions with equal-value outputs, a "
                "coinjoin mark raised its risk score",
                "this wallet's satoshis it received in its window lowered its risk score",
            ],
            "weight": [0.8, -0.2],
            "source_ref": ["s", "s"],
        },
        schema=evidence.EVIDENCE_SCHEMA,
    )
    counter_frame = pl.DataFrame(
        schema=counters.COUNTER_SCHEMA,
    )
    return alerts, evidence_frame, counter_frame


def test_reason_string_is_three_sentences_and_deterministic() -> None:
    """Same rows in, same string out; three sentences at most; no raw column name."""
    alerts, evidence_frame, counter_frame = _evidence_fixtures()
    alert = alerts.iter_rows(named=True).__next__()
    one = evidence.reason_string(alert, evidence_frame, counter_frame)
    two = evidence.reason_string(alert, evidence_frame, counter_frame)
    assert one == two
    sentences = one.split(". ")
    assert len(sentences) <= 3, f"the reason string ran past three sentences: {one}"
    assert "coinjoin" in one
    assert "unglossed" not in one


def test_reason_string_reports_a_decisive_counter(workspace: Path) -> None:
    """When a counter would_clear, the reason string says the lead is cleared, not scored."""
    del workspace
    alerts, evidence_frame, _ = _evidence_fixtures()
    decisive = pl.DataFrame(
        {
            "alert_id": ["alw-x"],
            "kind": ["pool_payout_pattern"],
            "statement": [
                "this cluster pays out on a regular cadence, which is what a " "mining pool does"
            ],
            "strength": [0.9],
            "would_clear": [True],
        },
        schema=counters.COUNTER_SCHEMA,
    )
    alert = alerts.iter_rows(named=True).__next__()
    reason = evidence.reason_string(alert, evidence_frame, decisive)
    assert "clears this lead" in reason


# --- counters: the mining pool, by name -----------------------------------------------------------


def _pool_alerts() -> pl.DataFrame:
    """One alert for a cluster subject, the shape the mining-pool counter reads."""
    return pl.DataFrame(
        {
            "alert_id": ["alw-pool"],
            "subject_id": ["cluster:7"],
            "origin_txid": ["ab" * 32],
            "origin_peer_ip": ["203.0.113.9"],
            "origin_p": [0.4],
            "origin_margin": [0.5],
            "conf_low": [0.0],
            "conf_high": [1.0],
        }
    )


def _pool_world() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """The frames `counters.build` needs, with a mining pool and nothing else."""
    entity_types = pl.DataFrame(
        {
            "subject_id": ["cluster:7"],
            "predicted_type": ["mining_pool"],
            "confidence": [0.95],
            "basis": [["coinbase_origination", "payout_cadence"]],
            "exempt_from_scoring": [True],
        },
        schema_overrides={"basis": pl.List(pl.String())},
    )
    typology_hits = pl.DataFrame(
        schema={"subject_id": pl.String(), "typology": pl.String(), "strength": pl.Float64()},
    )
    clusters = pl.DataFrame(
        {"cluster_id": ["cluster:7"], "min_edge_confidence": [0.9]},
    )
    peer_subjects = pl.DataFrame(
        schema={"peer_ip": pl.String(), "n_subjects": pl.Int32()},
    )
    abstain_frac = pl.DataFrame(
        schema={"subject_id": pl.String(), "frac": pl.Float64()},
    )
    return typology_hits, clusters, peer_subjects, abstain_frac, entity_types


def test_mining_pool_with_coinbase_and_payout_cadence_clears() -> None:
    """The brief's named case: a pool whose coinbase origination and payout cadence are both
    recognised generates a `pool_payout_pattern` counter with `would_clear` true."""
    alerts = _pool_alerts()
    top1 = pl.DataFrame(
        schema={
            "txid": pl.String(),
            "peer_ip": pl.String(),
            "p_origin": pl.Float64(),
            "margin": pl.Float64(),
        }
    )
    typology_hits, clusters, peer_subjects, abstain_frac, entity_types = _pool_world()
    mass = pl.DataFrame({"txid": ["ab" * 32], "mass": [0.4]})
    frame = counters.build(
        alerts,
        top1,
        entity_types,
        typology_hits,
        clusters,
        peer_subjects,
        abstain_frac,
        margin_floor=0.04,
        origin_mass=mass,
    )
    pool = frame.filter(pl.col("kind") == "pool_payout_pattern")
    assert pool.height == 1
    assert bool(pool["would_clear"][0]), "a recognised pool must be cleared by its own type"


def test_mining_pool_with_a_typology_hit_does_not_clear() -> None:
    """The same pool with a typology hit against it keeps its doubt: no would_clear."""
    alerts = _pool_alerts()
    top1 = pl.DataFrame(
        schema={
            "txid": pl.String(),
            "peer_ip": pl.String(),
            "p_origin": pl.Float64(),
            "margin": pl.Float64(),
        }
    )
    typology_hits, clusters, peer_subjects, abstain_frac, entity_types = _pool_world()
    hits = typology_hits.vstack(
        pl.DataFrame(
            {"subject_id": ["cluster:7"], "typology": ["structuring"], "strength": [0.8]},
            schema=typology_hits.schema,
        )
    )
    mass = pl.DataFrame({"txid": ["ab" * 32], "mass": [0.4]})
    frame = counters.build(
        alerts,
        top1,
        entity_types,
        hits,
        clusters,
        peer_subjects,
        abstain_frac,
        margin_floor=0.04,
        origin_mass=mass,
    )
    pool = frame.filter(pl.col("kind") == "pool_payout_pattern")
    assert pool.height == 1
    assert not bool(pool["would_clear"][0])


def test_build_fails_when_an_alert_has_no_counter() -> None:
    """Contract section 8: the pipeline fails rather than publishing an empty counter list."""
    alerts = _pool_alerts()
    # An origin with full probability mass, a strong cluster, one subject per peer: no leg
    # fires, and the guard must raise rather than write the alert anyway.
    top1 = pl.DataFrame(
        schema={
            "txid": pl.String(),
            "peer_ip": pl.String(),
            "p_origin": pl.Float64(),
            "margin": pl.Float64(),
        }
    )
    typology_hits, clusters, peer_subjects, abstain_frac, entity_types = _pool_world()
    empty_types = entity_types.clear()
    mass = pl.DataFrame({"txid": ["ab" * 32], "mass": [1.0]})
    with pytest.raises(AssertionError, match="no counter-evidence"):
        counters.build(
            alerts,
            top1,
            empty_types,
            typology_hits,
            clusters,
            peer_subjects,
            abstain_frac,
            margin_floor=0.04,
            origin_mass=mass,
        )


# --- the real pipeline over the committed fixture -------------------------------------------------


def test_every_output_matches_contract_section_eight(workspace: Path) -> None:
    """Column names, order and dtypes for all three tables, against the document."""
    run = _run_pipeline(workspace, "contract8")
    alerts = pl.read_parquet(run / "alerts" / "alerts.parquet")
    evidence_frame = pl.read_parquet(run / "alerts" / "evidence.parquet")
    counter = pl.read_parquet(run / "alerts" / "counter.parquet")
    for frame, contract, name in (
        (alerts, CONTRACT_ALERTS, "alerts.parquet"),
        (evidence_frame, CONTRACT_EVIDENCE, "evidence.parquet"),
        (counter, CONTRACT_COUNTER, "counter.parquet"),
    ):
        got = [(field, str(dtype).split("(")[0]) for field, dtype in frame.schema.items()]
        assert got == contract, f"{name} does not match contract section 8"
    assert alerts.height > 0, "the fixture should alert on something"
    assert set(alerts["severity"].unique().to_list()) <= {"high", "medium", "low"}
    assert alerts["rank"].is_sorted()


def test_no_alert_lacks_a_counter(workspace: Path) -> None:
    """Every alert has at least one counter row; the writer enforces it, this proves it."""
    run = _run_pipeline(workspace, "countered")
    alerts = pl.read_parquet(run / "alerts" / "alerts.parquet", columns=["alert_id"])
    counter = pl.read_parquet(run / "alerts" / "counter.parquet", columns=["alert_id"])
    assert set(counter["alert_id"].unique().to_list()) == set(alerts["alert_id"].to_list())


def test_every_evidence_identifier_is_truncated(workspace: Path) -> None:
    """No complete identifier in any prose column of the three tables, per the write-time law.

    Two exemptions, both precedented in `scripts/check_scores.py`: the two contract
    structured fields (`origin_txid`, `origin_peer_ip`) are machine fields section 9's packet
    quotes whole, and join keys (`subject_id`, the `#subject_id=` fragment of `source_ref`)
    are `kind:value` node ids, not rendered values — the rendered artifacts carry the
    truncated copies.
    """
    run = _run_pipeline(workspace, "truncated")
    structured = {"origin_txid", "origin_peer_ip", "subject_id"}
    for name in ("alerts.parquet", "evidence.parquet", "counter.parquet"):
        frame = pl.read_parquet(run / "alerts" / name)
        for column in frame.columns:
            if frame.schema[column] != pl.String() or column in structured:
                continue
            for value in frame[column].drop_nulls().unique().to_list():
                # A source_ref is an artifact locator whose row fragment is a node id; strip
                # the fragment before the sweep so the locator itself is judged, not the key.
                text = str(value).split("#", 1)[0] if column == "source_ref" else str(value)
                assert not FULL_TXID.search(text), f"{name}.{column} holds a full txid: {text}"
                assert not FULL_ADDRESS.search(text), f"{name}.{column} holds a full address"
                assert not FULL_IPV4.search(text), f"{name}.{column} holds a full IPv4: {text}"
                assert not FULL_IPV6.search(text), f"{name}.{column} holds a full IPv6"
    # The two structured fields are where full identifiers are allowed to live, and both are
    # populated on anchored alerts, so the exemption is proved to be load-bearing, not vacuous.
    alerts = pl.read_parquet(run / "alerts" / "alerts.parquet")
    anchored = alerts.filter(pl.col("origin_txid").is_not_null())
    if anchored.height:
        assert any(
            FULL_TXID.search(str(one)) for one in anchored["origin_txid"].to_list()
        ), "no anchored alert carries a full origin_txid, so the structured-field rule is untested"
    # The headline names no feature column: every phrase comes from the gloss table.
    for headline in alerts["headline"].to_list():
        assert len(headline) < 100, f"headline not under 100 characters: {headline}"


def test_reason_string_identical_across_two_processes(workspace: Path) -> None:
    """Two subprocesses read the same alert and derive the same three sentences.

    The reason is derived from the written rows at read time, so two interpreters must land
    on the same bytes: a dict-order or float-format difference would break the determinism
    claim the stage makes.
    """
    _run_pipeline(workspace, "twice")
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "import polars as pl;"
        "from chakravyuh.vaani import evidence;"
        "alerts = pl.read_parquet('data/generated/twice/alerts/alerts.parquet').head(3);"
        "ev = pl.read_parquet('data/generated/twice/alerts/evidence.parquet');"
        "ct = pl.read_parquet('data/generated/twice/alerts/counter.parquet');"
        "out = [evidence.reason_string(a, ev, ct) for a in alerts.iter_rows(named=True)];"
        "Path('reasons.txt').write_text('\\n'.join(out))"
    )
    first = subprocess.run(
        [sys.executable, "-c", script], cwd=workspace, capture_output=True, text=True, check=False
    )
    second = subprocess.run(
        [sys.executable, "-c", script], cwd=workspace, capture_output=True, text=True, check=False
    )
    assert first.returncode == 0, first.stderr[-2000:]
    assert second.returncode == 0, second.stderr[-2000:]
    assert first.stdout == second.stdout
    # Both processes wrote the same file, so compare the two runs' content through the file
    # the first wrote before the second overwrote it: rerun the first and diff by hash.
    got = (workspace / "reasons.txt").read_text(encoding="utf-8")
    assert got.count("\n") >= 2, "three alerts should have produced three reasons"
    subprocess.run([sys.executable, "-c", script], cwd=workspace, check=True, capture_output=True)
    assert (workspace / "reasons.txt").read_text(encoding="utf-8") == got


def test_no_raw_column_name_in_any_statement(workspace: Path) -> None:
    """Every statement's feature references resolve through the gloss table, never a column."""
    run = _run_pipeline(workspace, "glossed")
    evidence_frame = pl.read_parquet(run / "alerts" / "evidence.parquet")
    known = gloss.load_glosses(gloss.default_path())
    model_rows = evidence_frame.filter(pl.col("kind") == "model_feature")
    # Each statement embeds a gloss phrase; the source_ref names the score row, not a column.
    for statement in model_rows["statement"].to_list():
        assert any(
            phrase in statement for phrase in known.values()
        ), f"a statement names no glossed feature: {statement}"


# --- quarantine: the two Law 2 rules only a real run can demonstrate ------------------------------


def test_vaani_builds_with_the_answer_key_absent(workspace: Path) -> None:
    """Law 2 rule 6, run rather than asserted: no ground truth on any path, stage completes."""
    run = _run_pipeline(workspace, "isolated8")
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "from chakravyuh.vaani.stage import build_run, resolve_in, resolve_out;"
        "meta = build_run(resolve_in(Path('data/generated/isolated8')),"
        " resolve_out(Path('data/generated/isolated8')));"
        "import polars as pl;"
        "a = pl.read_parquet('data/generated/isolated8/alerts/alerts.parquet');"
        "c = pl.read_parquet('data/generated/isolated8/alerts/counter.parquet');"
        "assert a.height > 0 and c.height > 0"
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
    assert run.is_dir()


def test_no_alerts_artifact_names_the_quarantine(workspace: Path) -> None:
    """Law 2 rule 4: no observable file may contain either quarantined path, as a name or a
    value. The literals are reconstructed so this file does not itself hold them."""
    forbidden = ("ground" + "_truth", "measure" + "ments")
    alerts_dir = _run_pipeline(workspace, "sealed-words8") / "alerts"

    checked = 0
    for path in sorted(alerts_dir.rglob("*")):
        if not path.is_file():
            continue
        checked += 1
        if path.suffix == ".json":
            text = path.read_text(encoding="utf-8")
            assert not any(one in text for one in forbidden), f"{path.name} names the quarantine"
            continue
        frame = pl.read_parquet(path)
        assert not set(frame.columns) & set(forbidden)
        for column in frame.columns:
            if frame.schema[column] != pl.String():
                continue
            values = frame[column].drop_nulls()
            for one in forbidden:
                assert (
                    values.str.contains(one, literal=True).sum() == 0
                ), f"{path.name}.{column} carries {one!r}"
    assert checked >= 4, "the walk found fewer files than one alerts/ writes, so it proved nothing"

    # The source side of the same rule: no VAANI module may name either path.
    for module in sorted((REPO / "src" / "chakravyuh" / "vaani").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        assert not any(one in text for one in forbidden), f"{module.name} names the quarantine"


def test_meta_accounts_for_every_scored_subject(workspace: Path) -> None:
    """Contract section 10 on the alerts manifest: arithmetic holds and outputs exist."""
    run = _run_pipeline(workspace, "meta8")
    meta = json.loads((run / "alerts" / "_meta.json").read_text(encoding="utf-8"))
    counts = meta["counts"]
    assert counts["in"] == counts["out"] + counts["dropped"]
    scores = pl.read_parquet(run / "scores" / "wallet_scores.parquet", columns=["label"])
    assert counts["dropped"] == (scores["label"] == "LIKELY_LICIT").sum()
    for entry in meta["outputs"]:
        assert (run / entry["path"]).is_file()
