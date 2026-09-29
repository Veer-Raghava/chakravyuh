"""BUDDHI: what must hold when a risk score is written for every wallet subject.

Four groups. The behaviour group works from hand-built frames small enough to check by eye:
the window rule that keeps future data out of any feature, the majority-vote label the model
trains on, the conformal set that decides the contract's `label` vocabulary, and the
calibration table that reports per-class coverage rather than one blended number. The
calibration group fits the real LightGBM-plus-MAPIE chain on a synthetic frame sized for
seconds, not gate scale, and asserts the one property the brief is about: class-conditional
coverage lands within tolerance of the target, per class. The stage group runs the real
pipeline over the committed capture fixture with hand-made labels, sealed and normalised and
graphed fresh inside a throwaway repo root. The quarantine group holds the two Law 2 rules
only a real run can demonstrate, and both are registered in `tests/conftest.py` for
`make verify-quarantine`.

Nothing here runs the gate's two-interpreter byte compare: `make verify-s07` does that at
scale, and a test that re-ran it would be a slower copy of the same assertion.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from chakravyuh.buddhi import embed, features, model, recipe, stage
from chakravyuh.buddhi.features import ALL_FEATURES, FEATURE_GLOSSES, MODEL_FEATURES
from chakravyuh.buddhi.stage import (
    LABEL_ABSTAIN,
    LABEL_LIKELY_ILICIT,
    LABEL_LIKELY_LICIT,
    LABEL_UNCLEAR,
    _row_label,
    build_run,
    resolve_in,
    resolve_out,
)
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

REPO = Path(__file__).resolve().parent.parent
FIXTURE_CAPTURE = REPO / "data" / "fixtures" / "capture" / "capture.csv"

# Contract section 7, transcribed by hand rather than imported from the writer. A schema test
# that reads the same constant the code writes from asserts only that a module equals itself.
CONTRACT_WALLET_SCORES: list[tuple[str, str]] = [
    ("subject_id", "String"),
    ("risk_score", "Float64"),
    ("label", "String"),
    ("conf_low", "Float64"),
    ("conf_high", "Float64"),
    ("coverage_target", "Float64"),
    ("model", "String"),
    ("top_features", "List"),
    ("abstain", "Boolean"),
]
CONTRACT_CALIBRATION: list[tuple[str, str]] = [
    ("class", "String"),
    ("method", "String"),
    ("target_coverage", "Float64"),
    ("empirical_coverage", "Float64"),
    ("n_calibration", "Int32"),
    ("n_test", "Int32"),
    ("imbalance_ratio", "String"),
]
CONTRACT_LABELS = {"LIKELY_ILICIT", "UNCLEAR", "LIKELY_LICIT", "ABSTAIN"}
CONTRACT_METHODS = {"plain_conformal", "class_conditional"}

# Coverage is a quantile guarantee measured on tens of rows, not thousands; a tolerance this
# wide still catches "the minority class under-covered by a wide margin", which is the
# failure the Mondrian partition exists to prevent.
COVERAGE_TOLERANCE = 0.15


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo root holding `data/` and nothing else, with the process moved into it."""
    (tmp_path / "data" / "generated").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run_pipeline(
    workspace: Path, name: str, labels: pl.DataFrame | None, *, gnn: bool = False
) -> Path:
    """Seal, normalise, graph, estimate, then score with the labels handed in.

    The fixture rather than a generated capture: 197 rows, every value chosen by hand. `labels`
    is a train-window `(address, y)` frame — the exact shape `__main__.py` extracts from the
    label door — and nothing else about the run knows it exists. `gnn` is the `--gnn` flag: it
    turns on the embedding columns and the second booster, nothing else.
    """
    target = workspace / "data" / "capture.csv"
    target.write_bytes(FIXTURE_CAPTURE.read_bytes())
    seal(target, kavach_out(Path("data/generated") / name))
    run = workspace / "data" / "generated" / name
    normalise_run(setu_in(run / "sealed"), setu_out(run))
    build_graph(jaal_in(run / "normalised"), jaal_out(run))
    build_signals(shastra_in(run / "normalised"), shastra_out(run))
    # Derived from the run's own span, the same formula `__main__.py` uses — a constant below
    # the fixture's microsecond timestamps would leave nothing before it and nothing to train.
    announcements = pl.read_parquet(
        run / "normalised" / "announcements.parquet", columns=["seen_us"]
    )
    boundary = boundary_us(
        int(announcements["seen_us"].min()),  # type: ignore[arg-type]
        int(announcements["seen_us"].max()),  # type: ignore[arg-type]
        0.7,
    )
    build_run(
        resolve_in(run),
        resolve_out(run),
        labels=labels,
        boundary_us=boundary,
        use_embeddings=gnn,
    )
    return run


# --- behaviour, from hand-built frames ----------------------------------------------------------


NEW_FEATURES = (
    "fan_in_ratio",
    "peel_chain_depth",
    "peel_leak_frac",
    "structuring_frac",
    "burstiness",
    "fee_anomaly",
)


def test_new_features_declared_and_glossed() -> None:
    for name in NEW_FEATURES:
        assert name in MODEL_FEATURES, f"{name} missing from MODEL_FEATURES"
    # `ALL_FEATURES`, not `MODEL_FEATURES`: the embedding columns are glossed too, because the
    # GNN booster's SHAP rows name them and `scripts/check_scores.py` validates those names
    # against the same vocabulary. The baseline set stays a strict prefix of the full one, which
    # is what makes the plain invocation's features exactly the first thirty-three.
    assert ALL_FEATURES[: len(MODEL_FEATURES)] == MODEL_FEATURES
    glossed = {n for n, _ in FEATURE_GLOSSES}
    assert set(ALL_FEATURES) == glossed, "every model feature needs exactly one gloss"
    assert len(FEATURE_GLOSSES) == len(set(n for n, _ in FEATURE_GLOSSES)), "no duplicate glosses"


def test_features_md_is_the_same_vocabulary() -> None:
    """`docs/FEATURES.md` is what `scripts/check_scores.py` validates `top_features` against.

    So a feature added to the model and not to that table is not a documentation gap — it turns
    the gate red the next time the feature reaches a SHAP row, which is how the six morphological
    features and the three operator ones were caught. Checked here at test scale, where the name
    of the missing feature is the failure message, rather than only at gate scale.
    """
    import re

    text = (REPO / "docs" / "FEATURES.md").read_text(encoding="utf-8")
    table = {
        match.group(1): match.group(2).strip()
        for match in re.finditer(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(.+?)\s*\|$", text, re.MULTILINE)
    }
    assert sorted(table) == sorted(ALL_FEATURES), "FEATURES.md and ALL_FEATURES disagree"
    # Not just the names: the table is quoted verbatim by the report, so the wording has to match
    # the glosses the code carries rather than merely covering the same set of features.
    for name, gloss in FEATURE_GLOSSES:
        assert table[name] == gloss, f"FEATURES.md gloss for {name} is stale"


def _subject_frame(rows: list[dict[str, object]], boundary: int) -> pl.DataFrame:
    """A minimal subject table with the columns `features.build` writes."""

    def _first_us(row: dict[str, object]) -> int:
        if "subject_first_us" in row:
            value = row["subject_first_us"]
            return value if isinstance(value, int) else boundary
        return boundary - 1 if row["is_train"] else boundary + 1

    frame = pl.DataFrame(
        {
            "subject_id": [str(r["subject_id"]) for r in rows],
            "is_train": [bool(r["is_train"]) for r in rows],
            "subject_first_us": [_first_us(r) for r in rows],
            **{name: [r.get(name) for r in rows] for name in MODEL_FEATURES},
        }
    )
    return frame


def test_no_feature_sees_a_subjects_future() -> None:
    """The trap the brief names: the row split is easy, the window is where leakage lives.

    One subject with activity on both sides of the boundary. `features.build` must place it
    by its earliest activity and then compute every feature from its window's transactions
    only — a send at t=5_000 must never appear in a train subject's `n_tx_sent` even though
    the frame handed in holds it.
    """
    transactions = pl.DataFrame(
        {
            "txid": ["t1", "t2"],
            "first_seen_us": [1_000, 5_000],
            "n_out": [1, 1],
            "input_addresses": [["A"], ["A"]],
            "output_addresses": [["B"], ["C"]],
            "output_amounts": [[500], [500]],
            "total_out_sats": [500, 500],
            "fee_rate_sat_vb": [1.0, 1.0],
            "is_coinbase": [False, False],
            "has_equal_outputs": [False, False],
        },
        schema_overrides={
            "input_addresses": pl.List(pl.String()),
            "output_addresses": pl.List(pl.String()),
            "output_amounts": pl.List(pl.Int64()),
        },
    )
    clusters = pl.DataFrame(
        {"cluster_id": ["cluster:0"], "addresses": [["A", "B"]]},
        schema_overrides={"addresses": pl.List(pl.String())},
    )
    addresses = pl.DataFrame(
        {
            "address": ["A", "B", "C"],
            "script_type": ["p2pkh", "p2pkh", "p2pkh"],
            "first_seen_us": [1_000, 1_000, 5_000],
        }
    )
    edges = pl.DataFrame(
        schema={
            "src": pl.String(),
            "dst": pl.String(),
            "kind": pl.String(),
            "confidence": pl.Float64(),
            "evidence": pl.String(),
        },
    )
    origin_estimates = pl.DataFrame(
        schema={
            "txid": pl.String(),
            "p_origin": pl.Float64(),
            "rank": pl.Int32(),
            "margin": pl.Float64(),
            "abstain": pl.Boolean(),
            "features": pl.Struct,
            "estimator": pl.String(),
        },
    )
    table = features.build(transactions, clusters, addresses, edges, origin_estimates, 3_000)
    row = table.filter(pl.col("subject_id") == "cluster:0")
    assert row["is_train"][0], "earliest activity at 1_000 is before the boundary at 3_000"
    # Two sends inside the window's transactions; only the pre-boundary one may be counted.
    assert row["n_tx_sent"][0] == 1
    assert row["total_sent_sats"][0] == 500
    # The address that appears only post-boundary is not yet a member the model can see.
    assert row["n_addresses"][0] == 2


def test_the_majority_label_ties_to_licit() -> None:
    """The eval side scores holdout subjects by majority `is_illicit`, ties licit; the model
    must learn from the same definition or the two disagree about what `y` means."""
    members = pl.DataFrame(
        {
            "subject_id": ["s1", "s1", "s1", "s2"],
            "address": ["a", "b", "c", "d"],
            "y": [1, 1, 0, 0],
        }
    )
    grouped = members.group_by("subject_id").agg(
        (2 * pl.col("y").sum() > pl.len()).cast(pl.Int64).alias("y")
    )
    by_id = dict(zip(grouped["subject_id"].to_list(), grouped["y"].to_list(), strict=True))
    assert by_id["s1"] == 1  # two of three illicit: majority
    assert by_id["s2"] == 0  # one member, licit


def test_the_row_label_vocabulary_is_the_conformal_set() -> None:
    """Contract section 7's four labels, decided by the set alone and never by the score."""
    assert _row_label(True, True) == LABEL_UNCLEAR
    assert _row_label(False, False) == LABEL_ABSTAIN
    assert _row_label(False, True) == LABEL_LIKELY_ILICIT
    assert _row_label(True, False) == LABEL_LIKELY_LICIT


def test_predict_sets_behave_like_sets() -> None:
    """A set contains its class at target coverage; a model that abstains has an empty set.

    Fitted on a separable synthetic frame arranged so the time-ordered calibration tail
    holds both classes — negatives and positives interleaved in blocks, both present in the
    last quarter — the sets must behave like sets: no row is both UNCLEAR and ABSTAIN.
    """
    rng = np.random.default_rng(7)
    n = 400
    # Blocks of each class, interleaved, so any time cut past the first block sees both.
    halves = [rng.normal(2.0, 0.3, n // 8), rng.normal(0.0, 0.3, n // 8)]
    x0 = np.concatenate(halves * (n // (n // 4)))
    frame = pl.DataFrame(
        {
            "n_addresses": x0,
            "n_tx_sent": rng.normal(size=n),
            **{name: rng.normal(size=n) for name in MODEL_FEATURES[2:]},
        },
    )
    y = (x0 > 1.0).astype(np.int64)
    order = pl.Series("_order", np.arange(n, dtype=np.int64))
    bundle, calibrated = model.fit(
        frame.with_columns(order, pl.Series("y", y)),
        seed=0,
        coverage_target=0.9,
    )
    assert calibrated.trained and calibrated.mondrian
    sets = model.predict_sets(bundle, frame)
    both = sets["in_set_0"] & sets["in_set_1"]
    neither = ~sets["in_set_0"] & ~sets["in_set_1"]
    assert not (both & neither).any()


def test_coverage_is_per_class_and_near_the_target() -> None:
    """The brief's central demand: empirical coverage per class at the target level.

    One blended number can hide a minority class covered at half the target, which is the
    exact failure a Mondrian wrapper exists to prevent. Both classes here must land within
    tolerance, and the calibration table must show both methods so the difference between
    plain and class-conditional is on the record.
    """
    rng = np.random.default_rng(11)
    n = 800
    illicit = rng.normal(2.0, 0.4, n // 5)
    licit = rng.normal(0.0, 0.4, n - n // 5)
    x0 = np.concatenate([illicit, licit])
    y = np.concatenate([np.ones(illicit.size), np.zeros(licit.size)]).astype(np.int64)
    perm = rng.permutation(n)
    frame = pl.DataFrame(
        {"n_addresses": x0[perm], **{name: rng.normal(size=n) for name in MODEL_FEATURES[1:]}}
    )
    y_shuffled = y[perm]
    order = pl.Series("_order", np.arange(n))
    bundle, calibrated = model.fit(
        frame.with_columns(order, pl.Series("y", y_shuffled)), seed=0, coverage_target=0.9
    )
    assert calibrated.trained and calibrated.mondrian
    sets = model.predict_sets(bundle, frame)
    # Coverage is measured on the calibration rows, class by class — the same rows the
    # quantiles were read from, which is what the guarantee is a statement about.
    cal: pl.DataFrame = bundle["calibration_rows"]
    cal_sets = model.predict_sets(bundle, cal)
    for k, column in ((0, "in_set_0"), (1, "in_set_1")):
        mask = cal["y"] == k
        member_rows = cal_sets.filter(mask)
        empirical = (
            float(member_rows[column].mean())  # type: ignore[arg-type]
            if member_rows.height
            else 0.0
        )
        assert (
            abs(empirical - 0.9) <= COVERAGE_TOLERANCE
        ), f"class {k} covered at {empirical:.3f}, target 0.9"
    del sets
    assert set(cal["y"].unique().to_list()) == {0, 1}


def test_fit_refuses_one_class_and_says_so() -> None:
    """A training window with a single class trains nothing and records why, rather than
    producing a model whose conformal quantiles are meaningless."""
    frame = _subject_frame(
        [
            {"subject_id": "s1", "is_train": True, "y": 0},
        ],
        1_000,
    ).with_columns(pl.lit(0).alias("y"), pl.lit(0).alias("_order"))
    bundle, calibrated = model.fit(
        frame.select("_order", "y", *MODEL_FEATURES), seed=0, coverage_target=0.9
    )
    assert not calibrated.trained
    assert calibrated.reason == "one_class_in_training_window"
    assert bundle == {}


def test_recipe_is_time_ordered_and_deterministic() -> None:
    rng = np.random.default_rng(0)
    n = 400
    X = rng.normal(size=(n, 4))
    time_index = np.arange(n, dtype="int64")  # strictly increasing
    y = (X[:, 0] + rng.normal(scale=0.3, size=n) > 0).astype("int64")

    r1 = recipe.train_and_score(X, y, time_index, train_fraction=0.7, seed=0, coverage_target=0.9)
    r2 = recipe.train_and_score(X, y, time_index, train_fraction=0.7, seed=0, coverage_target=0.9)
    # Time-ordered: the test slice is exactly the rows at/after the boundary.
    assert r1.n_train + r1.n_test == n
    assert r1.n_test == int((time_index >= r1.boundary).sum())
    # Deterministic: two calls, identical scores.
    assert np.array_equal(r1.scores, r2.scores)
    assert r1.scores.shape == r1.y_test.shape == r1.in_set_1.shape


def test_the_calibration_table_shows_why_mondrian_exists(workspace: Path) -> None:
    """`_calibration_frame` on a synthetic bundle: plain under-covers the minority class,
    class-conditional does not — the contrast the file exists to put on the record.

    The committed fixture is too small to calibrate (fewer labelled subjects than the
    calibrator's floor), so this is the one place the table's content is asserted. The
    imbalance is deliberate: a blended 90% quantile spends its slack on the majority class.
    """
    del workspace
    rng = np.random.default_rng(23)
    n = 800
    # One shared axis, classes overlapping but shifted; blocks interleaved so the time-ordered
    # calibration tail holds both classes, positives the scarcer.
    blocks = [rng.normal(1.6, 0.6, 16), rng.normal(0.0, 0.6, 64)]
    x0 = np.concatenate(blocks * (n // 80))
    y = np.concatenate([np.ones(16), np.zeros(64)] * (n // 80)).astype(np.int64)
    perm = rng.permutation(n)
    frame = pl.DataFrame(
        {"n_addresses": x0[perm], **{name: rng.normal(size=n) for name in MODEL_FEATURES[1:]}}
    )
    order = pl.Series("_order", np.arange(n))
    bundle, calibrated = model.fit(
        frame.with_columns(order, pl.Series("y", y[perm])), seed=0, coverage_target=0.9
    )
    assert calibrated.trained and calibrated.mondrian
    cal: pl.DataFrame = bundle["calibration_rows"]
    table = stage._calibration_frame(bundle, frame.head(0), 0.9)
    assert table.height == 4
    assert set(table["method"].unique().to_list()) == CONTRACT_METHODS
    assert set(table["class"].unique().to_list()) == {"0", "1"}
    for row in table.iter_rows(named=True):
        assert 0.0 <= row["empirical_coverage"] <= 1.0
        assert row["target_coverage"] == 0.9
        assert row["imbalance_ratio"].startswith("1:")
        assert row["n_calibration"] == int((cal["y"] == int(row["class"])).sum())
        assert row["n_test"] == 0
    plain_pos = table.filter((pl.col("class") == "1") & (pl.col("method") == "plain_conformal"))[
        "empirical_coverage"
    ][0]
    cond_pos = table.filter((pl.col("class") == "1") & (pl.col("method") == "class_conditional"))[
        "empirical_coverage"
    ][0]
    assert plain_pos < cond_pos, "plain set under-covers the minority; Mondrian must do better"
    assert cond_pos >= 0.9 - COVERAGE_TOLERANCE

    """`baseline_beaten` compares against a number measured on the same run and filed where
    `score_wallets` reads it — not a constant the stage asserted."""
    run_dir = REPO / "data" / "generated" / "_sweep-0.10"
    if not run_dir.is_dir():
        pytest.skip("reference run _sweep-0.10 not present in this checkout")
    report_path = REPO / "measurements" / "_sweep-0.10" / "baseline_wallet.json"
    if not report_path.is_file():
        pytest.skip("baseline_wallet.json not measured in this checkout")
    filed = json.loads(report_path.read_text(encoding="utf-8"))
    assert "precision_at_20" in filed
    model_report = json.loads(
        (REPO / "measurements" / "_sweep-0.10" / "model_report.json").read_text(encoding="utf-8")
    )
    assert model_report["baseline_beaten"] == (
        model_report["wallet_model"]["precision_at_20"] > filed["precision_at_20"]
    )


# --- the real pipeline over the committed fixture -------------------------------------------------


def _fixture_labels(run: Path, addresses: list[str]) -> pl.DataFrame:
    """Hand-made train-window labels, deterministic by address order and clustered.

    The fixture's clusters are tiny, so an alternating per-address label makes every
    multi-member cluster tie to licit and the training window holds one class. Labelling by
    index blocks — the first half of the chosen addresses illicit, the rest licit — gives
    both classes subjects to train on whatever the capture's clustering did. The values are
    chosen, not derived: this is the exact two-column shape `__main__.py` extracts from the
    label door, and no code under `src/chakravyuh/buddhi/` sees where it came from.
    """
    chosen = sorted(addresses)[: max(8, len(addresses) // 2)]
    half = len(chosen) // 2
    return pl.DataFrame(
        {
            "address": chosen,
            "y": [1] * half + [0] * (len(chosen) - half),
        },
        schema={"address": pl.String(), "y": pl.Int64()},
    )


def test_every_output_matches_contract_section_seven(workspace: Path) -> None:
    """Column names, order and dtypes, against the document rather than against the writer."""
    run = _run_pipeline(workspace, "contract", None)
    scores = pl.read_parquet(run / "scores" / "wallet_scores.parquet")
    got = [(name, str(dtype).split("(")[0]) for name, dtype in scores.schema.items()]
    assert got == CONTRACT_WALLET_SCORES
    calibration = pl.read_parquet(run / "scores" / "calibration.parquet")
    got_cal = [(name, str(dtype).split("(")[0]) for name, dtype in calibration.schema.items()]
    assert got_cal == CONTRACT_CALIBRATION

    meta = json.loads((run / "scores" / "_meta.json").read_text(encoding="utf-8"))
    counts = meta["counts"]
    assert counts["in"] == counts["out"] + counts["dropped"]
    assert counts["out"] == scores.height
    for entry in meta["outputs"]:
        assert (run / entry["path"]).is_file()


def test_labels_vocabularies_and_set_consistency_over_a_real_run(workspace: Path) -> None:
    """`label` and `abstain` agree with the interval columns; `coverage_target` is the run's."""
    run = _run_pipeline(workspace, "vocab", None)
    scores = pl.read_parquet(run / "scores" / "wallet_scores.parquet")
    assert set(scores["label"].unique().to_list()) <= CONTRACT_LABELS
    abstains = scores.filter(pl.col("abstain"))
    assert abstains.height == 0 or (abstains["label"] == LABEL_ABSTAIN).all()
    unclear = scores.filter((pl.col("conf_low") == 0.0) & (pl.col("conf_high") == 1.0))
    # Both classes in the set is UNCLEAR, whatever the raw score says.
    assert (unclear["label"] == LABEL_UNCLEAR).all() or unclear.height == 0
    # Every other interval is anchored on the score and genuinely has a width — the property the
    # old set-membership mapping broke, collapsing every alert to the point (1.0, 1.0).
    assert scores.select(
        (
            (pl.col("conf_low") <= pl.col("risk_score"))
            & (pl.col("risk_score") <= pl.col("conf_high"))
        ).all()
    ).item()
    assert (scores["conf_low"] != scores["conf_high"]).any()
    assert scores["coverage_target"].unique().to_list() == [0.9]


def test_calibration_table_reports_both_methods_per_class(workspace: Path) -> None:
    """Four rows: both classes, plain and class-conditional, so the contrast is on the file."""
    run = _run_pipeline(workspace, "calib", None)
    calibration = pl.read_parquet(run / "scores" / "calibration.parquet")
    if calibration.height == 0:
        pytest.skip("the fixture is too small to calibrate; the empty table is the honest shape")
    assert set(calibration["method"].unique().to_list()) == CONTRACT_METHODS
    assert set(calibration["class"].unique().to_list()) == {"0", "1"}
    assert calibration.filter(pl.col("method") == "class_conditional").height == 2
    for row in calibration.iter_rows(named=True):
        assert 0.0 <= row["empirical_coverage"] <= 1.0
        assert row["target_coverage"] == 0.9
        assert row["imbalance_ratio"].startswith("1:")


def test_the_input_path_guard_refuses_a_sibling_tree(workspace: Path) -> None:
    """`--in` may name a run under data/generated/ and nothing else — the guard that keeps a
    stage invocation from being pointed at the answer key's tree."""
    outside = workspace / "outside"
    outside.mkdir()
    with pytest.raises(Exception, match="resolves outside"):
        resolve_in(outside)
    with pytest.raises(Exception, match="resolves outside"):
        resolve_out(outside)


def test_the_split_boundary_is_one_formula_in_one_place() -> None:
    """BUDDHI and the label door must derive the same boundary from the same capture.

    The stage takes `boundary_us` from `__main__.py`, which takes it from the same
    `eval.split.boundary_us` the labels door calls; this asserts the property that function
    is, so the two stages cannot disagree about where the training window ended.
    """
    from chakravyuh.eval.split import boundary_us

    assert boundary_us(1_000, 1_000, 0.7) == 1_001  # zero span: nothing to hold out
    assert boundary_us(0, 1_000_000, 0.7) == 700_000
    assert boundary_us(0, 3, 0.7) == 2  # floored, not rounded
    with pytest.raises(ValueError, match="strictly between"):
        boundary_us(0, 1_000, 1.0)


def test_the_window_rule_agrees_between_the_two_stage_calls(workspace: Path) -> None:
    """The boundary the labels door derives is the boundary the stage windows by.

    A disagreement between S06 and S07 about `train_fraction` would silently give the model
    a different training window than the labels — the exact cross-stage fault the brief asks
    a test to fail on. Both doors derive from `eval.split.boundary_us`, so the same span and
    fraction give the same microsecond for both.
    """
    from chakravyuh.eval.labels import wallet_labels
    from chakravyuh.eval.split import boundary_us

    # The label door and the stage both read `config.effective.json`'s train_fraction and
    # both land on `eval.split.boundary_us`; one derived boundary is checked against the
    # door's on the fixture run.
    run = _run_pipeline(workspace, "agree", None)
    boundary, _ = _fixture_boundary(run)
    found = wallet_labels("agree", 0.7)
    if found is None:
        pytest.skip("no answer key in a throwaway workspace; the door correctly returns None")
    assert found.boundary_us == boundary
    del boundary_us


def _fixture_boundary(run: Path) -> tuple[int, int]:
    """The boundary this workspace's run would derive: same formula, same span."""
    from chakravyuh.eval.split import boundary_us

    announcements = pl.read_parquet(
        run / "normalised" / "announcements.parquet", columns=["seen_us"]
    )
    first = int(announcements["seen_us"].min())  # type: ignore[arg-type]
    last = int(announcements["seen_us"].max())  # type: ignore[arg-type]
    return boundary_us(first, last, 0.7), last


# --- the graph embedding, hand-built and by eye ---------------------------------------------------


def _tagged() -> pl.DataFrame:
    """A tagged edge table in `_window`'s input shape: both endpoint times, nullable."""
    return pl.DataFrame(
        {
            "src": ["addr:A", "tx:tx1", "addr:C", "asn:1"],
            "dst": ["tx:tx1", "addr:B", "tx:tx2", "peer:p1"],
            "kind": ["spends", "pays", "spends", "hosted_in"],
            "sats": [100, 100, 40, 0],
            "confidence": [1.0, 0.9, 1.0, 1.0],
            "ts_src": [1_000, 1_000, 5_000, None],
            "ts_dst": [1_000, 5_000, 5_000, None],
        }
    )


def test_the_embedding_window_rule_matches_the_cluster_rule() -> None:
    """An edge is in a window when no endpoint falls outside it; an untimestamped edge is in both.

    Same rule `features.cluster_shape` applies, and it is what keeps the embedding from being the
    one feature that reads across the boundary. The `asn:1 -> peer:p1` edge has no time on either
    end: it is infrastructure metadata, not a fact about the capture's timeline, so excluding it
    from a window would be subtracting topology the window's subjects actually had.
    """
    tagged = _tagged()
    train = embed._window(tagged, "train", 3_000)
    holdout = embed._window(tagged, "holdout", 3_000)

    # `addr:A -> tx:tx1` is wholly pre-boundary and so is in the train window only; `addr:C ->
    # tx:tx2` is wholly post-boundary and so is in the holdout one only; and the untimestamped
    # `asn:1 -> peer:p1` is in both.
    assert set(train["dst"].to_list()) == {"tx:tx1", "peer:p1"}
    assert set(holdout["dst"].to_list()) == {"tx:tx2", "peer:p1"}
    # `tx:tx1 -> addr:B` crosses the boundary: pre-boundary source, post-boundary destination, so
    # it is in neither window. An edge that spans the boundary is the one that would leak.
    assert "addr:B" not in train["dst"].to_list()
    assert "addr:B" not in holdout["dst"].to_list()
    # No boundary derived means no window exists, so the whole graph is the only honest answer.
    assert embed._window(tagged, "train", 0).height == tagged.height


def _dual_graph() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """`(edges, transactions, addresses, members)`: one pre-boundary subject, one post, one none.

    S1's address A is pre-boundary, S2's address Z appears in no edge at all, and S3's address C
    exists only after the boundary. All three are subjects the model must score; only the first
    has a graph position in the train window.
    """
    edges = pl.DataFrame(
        {
            "src": ["addr:A", "tx:tx1", "addr:C", "asn:1"],
            "dst": ["tx:tx1", "addr:B", "tx:tx2", "peer:p1"],
            "kind": ["spends", "pays", "spends", "hosted_in"],
            "sats": [100, 100, 50, 0],
            "confidence": [1.0, 0.9, 1.0, 1.0],
        }
    )
    transactions = pl.DataFrame({"txid": ["tx1", "tx2"], "first_seen_us": [1_000, 5_000]})
    addresses = pl.DataFrame(
        {
            "address": ["A", "B", "Z", "C"],
            "first_seen_us": [1_000, 5_000, 1_000, 5_000],
        }
    )
    members = pl.DataFrame({"subject_id": ["S1", "S2", "S3"], "address": ["A", "Z", "C"]})
    return edges, transactions, addresses, members


def test_a_subject_with_no_graph_node_gets_no_row_not_a_zero() -> None:
    """Absent, not zero — `stage.py` reads that null to decide which booster answered.

    S2's address Z is in `members` and in `addresses` but in no edge, and S3's address C is only
    reachable through a post-boundary edge. Imputing zeros for either would put a fabricated graph
    position into the GNN booster's features and let it answer for a subject it has never seen.
    """
    edges, transactions, addresses, members = _dual_graph()
    train = embed.subject_embeddings(
        edges, transactions, addresses, members, half="train", boundary_us=3_000
    )
    assert train["subject_id"].to_list() == ["S1"]
    # Never wider than `DIM`, and every direction it does have is the caller's to null-fill when a
    # window offers fewer: a four-node graph has four singular directions, not eight padded ones.
    assert train.width == 1 + min(embed.DIM, 4)
    assert all(name.startswith("embed_") for name in train.columns[1:])

    # The other half of the window rule, seen from a subject: A's only edge is pre-boundary, so S1
    # belongs to the train window's graph and C's only edge is post-boundary, so S3 belongs to the
    # holdout one. Neither subject is in both, which is the point of the boundary.
    holdout = embed.subject_embeddings(
        edges, transactions, addresses, members, half="holdout", boundary_us=3_000
    )
    assert holdout["subject_id"].to_list() == ["S3"]

    # With no boundary derived there is no window to be inside of, so the whole graph is one.
    whole = embed.subject_embeddings(
        edges, transactions, addresses, members, half="train", boundary_us=0
    )
    assert set(whole["subject_id"].to_list()) == {"S1", "S3"}


def test_the_embedding_is_deterministic_and_signed_by_rule() -> None:
    """Same input, same bytes — and the SVD's sign ambiguity resolved by the output, not by luck.

    `make verify-s07` byte-compares two interpreters, so an embedding that flipped a singular
    vector's sign between processes would turn that gate red without anything being wrong. `_reduce`
    states the rule: the largest-magnitude entry of each column is positive. The property is
    asserted on the node matrix where it is defined — a subject's embedding is the mean of its
    member addresses' rows, so no single row of it carries the pin.
    """
    hidden = np.array(
        [
            [1.0, -2.0, 3.0, 0.5],
            [4.0, 5.0, -6.0, 7.0],
            [-7.0, 8.0, 9.0, -1.5],
            [10.0, -11.0, 12.0, 2.5],
            [0.25, 3.0, -4.0, -8.0],
        ]
    )
    reduced = embed._reduce(hidden, 3)
    assert reduced.shape == (5, 3)
    assert np.array_equal(reduced, embed._reduce(hidden, 3))
    for column in range(reduced.shape[1]):
        vector = reduced[:, column]
        assert vector[int(np.argmax(np.abs(vector)))] >= 0.0, f"column {column} sign is not pinned"

    edges, transactions, addresses, members = _dual_graph()
    first = embed.subject_embeddings(
        edges, transactions, addresses, members, half="train", boundary_us=3_000
    )
    second = embed.subject_embeddings(
        edges, transactions, addresses, members, half="train", boundary_us=3_000
    )
    assert first.equals(second)


def test_the_gnn_run_flags_each_row_with_the_booster_that_scored_it(workspace: Path) -> None:
    """`model` is the audit trail: a mixed run has to say which rows came from which booster.

    The fixture is small, so the embedding may cover no training subject at all — which is the
    other outcome worth asserting. Either the run says every row is `gbm_gnn_v2` *and* records a
    fitted GNN leg, or it says no row is, and records why. What it may not do is claim rows it
    did not score, which is the same invariant `scripts/check_scores.py` enforces at gate scale.
    """
    run = _run_pipeline(workspace, "gnn", None, gnn=True)
    scores = pl.read_parquet(run / "scores" / "wallet_scores.parquet")
    meta = json.loads((run / "scores" / "_meta.json").read_text(encoding="utf-8"))

    # Adding the embedding leg does not change section 7's schema, and the counterfactual column
    # the eval side needs stays out of the shipped file.
    got = [(name, str(dtype).split("(")[0]) for name, dtype in scores.schema.items()]
    assert got == CONTRACT_WALLET_SCORES

    names = set(scores["model"].unique().to_list())
    assert names <= {"gbm_v2", "gbm_gnn_v2"}, names
    gnn_rows = scores.filter(pl.col("model") == "gbm_gnn_v2").height
    params = meta["params"]
    if gnn_rows:
        assert params["model_gnn"] is not None
        assert params["model_gnn"]["n_rows_scored"] == gnn_rows
    else:
        assert any(
            "fall_back_to_the_baseline_model" in warning for warning in meta["warnings"]
        ), meta["warnings"]


def test_the_plain_run_never_names_the_embedding_model(workspace: Path) -> None:
    """The GNN leg is droppable: without `--gnn` nothing about it reaches the artifacts.

    Default is off, and off has to mean off — a canonical run's rows must all name `gbm_v2` and its
    meta must carry no GNN block, or the flag would be a decoration rather than a switch.
    """
    run = _run_pipeline(workspace, "plain", None)
    scores = pl.read_parquet(run / "scores" / "wallet_scores.parquet")
    assert set(scores["model"].unique().to_list()) == {"gbm_v2"}
    meta = json.loads((run / "scores" / "_meta.json").read_text(encoding="utf-8"))
    assert meta["params"]["model_gnn"] is None
    assert not any("gnn" in w for w in meta["warnings"]), meta["warnings"]


# --- quarantine: the two Law 2 rules only a real run can demonstrate ------------------------------


def test_buddhi_builds_with_the_answer_key_absent(workspace: Path) -> None:
    """Law 2 rule 6, run rather than asserted.

    A subprocess whose working directory holds only `data/`. The answer key does not exist on
    any path the process could construct, so a stage that had quietly grown a dependency on
    it cannot complete. The hand-off of labels is the constructor's argument, and here it is
    None on both sides of the boundary.
    """
    _run_pipeline(workspace, "isolated", None)
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "from chakravyuh.buddhi.stage import build_run, resolve_in, resolve_out;"
        "meta, preds = build_run(resolve_in(Path('data/generated/isolated')),"
        " resolve_out(Path('data/generated/isolated')), labels=None, boundary_us=None);"
        "import polars as pl;"
        "s = pl.read_parquet('data/generated/isolated/scores/wallet_scores.parquet');"
        "labels = {'ABSTAIN','UNCLEAR','LIKELY_LICIT','LIKELY_ILICIT'};"
        "assert s.height > 0 and set(s['label'].unique()) <= labels"
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


def test_no_scores_artifact_names_the_quarantine(workspace: Path) -> None:
    """Law 2 rule 4: no observable file may contain either quarantined path, as a name or a
    value. `scores/` is the stage most tempted — it is the one that was handed labels — and
    this is the file the source-tree grep in `tests/test_contracts.py` cannot see into.

    The literals are reconstructed rather than written, so this file does not itself hold
    the two strings the source-tree grep looks for.
    """
    forbidden = ("ground" + "_truth", "measure" + "ments")
    scores = _run_pipeline(workspace, "sealed-words", None) / "scores"

    checked = 0
    for path in sorted(scores.rglob("*")):
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
    assert checked >= 3, "the walk found fewer files than one scores/ writes, so it proved nothing"

    # The source side of the same rule: no BUDDHI module may name either path.
    for module in sorted((REPO / "src" / "chakravyuh" / "buddhi").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        assert not any(one in text for one in forbidden), f"{module.name} names the quarantine"


def test_campaign_recall_counts_entity_once() -> None:
    from chakravyuh.eval import metrics

    # Two illicit entities with holdout activity; A has one flagged member, B none.
    preds = pl.DataFrame(
        {
            "subject_id": ["s1", "s2", "s3"],
            "addresses": [["a1"], ["a2"], ["b1"]],
            "risk_score": [0.9, 0.2, 0.1],
            "in_set_0": [False, True, True],
            "in_set_1": [True, False, False],  # only s1 flagged illicit
            "abstain": [False, False, False],
        }
    )
    truth = pl.DataFrame(
        {
            "entity_id": ["A", "A", "B"],
            "is_illicit": [True, True, True],
            "address": ["a1", "a2", "b1"],
        }
    )
    caught, total, recall = metrics._campaign_recall(preds, truth)
    assert total == 2
    assert caught == 1
    assert recall == 0.5


def test_asn_fusion_reads_abstained_rows_and_flags_them() -> None:
    """The operator belief travels with the share of sends the stage refused it.

    An L1 row abstains when the shortlist mass split across operators, but it still carries the
    operator ranked first and its probability. Averaging that belief is only honest if the refusal
    rate rides beside it — otherwise a subject whose sends could not be separated at all averages
    to the same feature value as one the estimator separated cleanly.
    """
    sent = pl.DataFrame({"subject_id": ["s1", "s1", "s2"], "txid": ["t1", "t2", "t3"]})
    l1 = pl.DataFrame(
        {
            "txid": ["t1", "t2", "t3"],
            "p_asn": [0.5, 0.1, 0.2],
            "margin": [0.4, 0.0, 0.1],
            "abstain": [True, False, True],
        }
    )
    out = features.asn_fusion(l1, sent).sort("subject_id")
    # s1 sent t1 (abstained) and t2 (acted): both values count, one of the two refuses.
    assert out["mean_p_asn"].to_list() == pytest.approx([0.3, 0.2])
    assert out["mean_asn_margin"].to_list() == pytest.approx([0.2, 0.1])
    assert out["frac_l1_abstained"].to_list() == pytest.approx([0.5, 1.0])

    # A run that shipped no operator headline yields the typed empty frame, not a crash.
    empty = features.asn_fusion(pl.DataFrame(schema={"txid": pl.String()}), sent)
    assert empty.height == 0
    assert set(empty.columns) == set(features.ASN_FUSION_SCHEMA)


def _load_checker() -> object:
    """`scripts/check_scores.py` as a module, so its report check can be called in-process.

    Loaded by path rather than imported: `scripts/` is not a package, and the point of this
    checker is that it is *not* imported from the code that writes the report.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_scores", REPO / "scripts" / "check_scores.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report_with_grains() -> dict[str, object]:
    """An `eval_report.json` body complete enough that only the grains can be the failure."""
    return {
        "split": {"mode": "time_ordered", "train_end_us": 1, "val_end_us": 2, "test_start_us": 3},
        "wallet_model": {
            "pr_auc": 0.1,
            "roc_auc": 0.5,
            "precision_at_20": 0.2,
            "recall_at_20": 0.1,
            "tx_pr_auc": 0.3,
            "campaign_recall": 0.25,
        },
        "origin_estimator": {
            "top1_accuracy": 0.4,
            "top3_accuracy": 0.6,
            "abstain_rate": 0.2,
            "by_observer_fraction": [{"fraction": 0.6, "top1": 0.4, "abstain": 0.2}],
            "by_traffic_type": [{"type": "clear", "top1": 0.4}],
        },
        "clustering": {"precision": 0.9, "recall": 0.8, "threshold": 0.36},
        "baseline_beaten": True,
        "seed": 0,
        "run_id": "r",
        "code_version": "test",
        "protocol": "inductive_time_ordered",
        "elliptic_external": {"available": False, "reason": "not_run_for_this_run"},
        "embedding_leg": {"available": False, "reason": "embeddings_not_requested"},
    }


@pytest.mark.parametrize(
    "drop",
    ["campaign_recall", "tx_pr_auc"],
)
def test_check_scores_requires_the_new_grains(tmp_path: Path, drop: str) -> None:
    """A grain the checker does not name is a grain nobody re-measures.

    Both new wallet_model figures are nullable by accident and by omission: a writer that
    stopped emitting one would leave the old four keys intact and every existing check green.
    """
    checker = _load_checker()
    report = _report_with_grains()
    wallet = report["wallet_model"]
    assert isinstance(wallet, dict)
    del wallet[drop]
    (tmp_path / "eval_report.json").write_text(json.dumps(report), encoding="utf-8")

    problems = checker._eval_report(tmp_path, "r")  # type: ignore[attr-defined]
    assert any(drop in problem for problem in problems), problems


def test_check_scores_refuses_rows_its_own_gate_rejected(tmp_path: Path) -> None:
    """A row may name the embedding model only where the report says the leg cleared its gate.

    `model` exists so a mixed run stays auditable; the audit is only real if the per-row claim and
    the run's own measurement are compared. The two files are written by the same process, so a
    mismatch is a bug or a hand-edit, and either way the shipment is not the run the gate approved.
    """
    checker = _load_checker()
    scores = pl.DataFrame(
        {
            "subject_id": ["cluster:1", "cluster:2"],
            "model": ["gbm_gnn_v2", "gbm_v2"],
        }
    )

    rejected = _report_with_grains()
    rejected["embedding_leg"] = {"available": False, "reason": "gnn_does_not_beat_baseline"}
    (tmp_path / "eval_report.json").write_text(json.dumps(rejected), encoding="utf-8")
    problems = checker._embedding_gate(scores, tmp_path)  # type: ignore[attr-defined]
    assert len(problems) == 1 and "gnn_does_not_beat_baseline" in problems[0], problems

    # A model name outside the vocabulary is caught too: the vocabulary check is what keeps a
    # renamed booster from shipping under a name nothing validates.
    assert checker._model_names(scores) == []  # type: ignore[attr-defined]
    stray = scores.with_columns(pl.lit("gnn_v1").alias("model"))
    assert checker._model_names(stray), (  # type: ignore[attr-defined]
        "a model name outside the vocabulary must be reported"
    )

    # The gate is green only when the report says so — and then the row is allowed to say it.
    approved = _report_with_grains()
    approved["embedding_leg"] = {"available": True, "reason": None}
    (tmp_path / "eval_report.json").write_text(json.dumps(approved), encoding="utf-8")
    assert checker._embedding_gate(scores, tmp_path) == []  # type: ignore[attr-defined]


def test_check_scores_requires_the_inductive_protocol(tmp_path: Path) -> None:
    """The protocol is a string, so presence alone proves nothing: a transductive run could
    carry the right key with the wrong name on it. The checker compares the value."""
    checker = _load_checker()

    report = _report_with_grains()
    (tmp_path / "eval_report.json").write_text(json.dumps(report), encoding="utf-8")
    assert checker._eval_report(tmp_path, "r") == []  # type: ignore[attr-defined]

    for bad in ("random_split", ""):
        report["protocol"] = bad
        (tmp_path / "eval_report.json").write_text(json.dumps(report), encoding="utf-8")
        problems = checker._eval_report(tmp_path, "r")  # type: ignore[attr-defined]
        assert any("protocol" in problem for problem in problems), problems

    del report["protocol"]
    (tmp_path / "eval_report.json").write_text(json.dumps(report), encoding="utf-8")
    problems = checker._eval_report(tmp_path, "r")  # type: ignore[attr-defined]
    assert any("protocol" in problem for problem in problems), problems


def test_check_scores_requires_the_external_block(tmp_path: Path) -> None:
    """Both shapes of the block pass the gate; not having a block at all does not.

    The honest-absence shape is not a failure — a run whose external leg never ran is a legitimate
    run — so the checker must accept it. What it must not accept is silence, because silence is
    indistinguishable from a writer that dropped the field.
    """
    checker = _load_checker()
    report = _report_with_grains()

    # The shape a run carries when the leg did not run for it.
    (tmp_path / "eval_report.json").write_text(json.dumps(report), encoding="utf-8")
    assert checker._eval_report(tmp_path, "r") == []  # type: ignore[attr-defined]

    # The shape it carries once the leg has run.
    report["elliptic_external"] = {"available": True, "pr_auc": 0.8, "n_test": 10}
    (tmp_path / "eval_report.json").write_text(json.dumps(report), encoding="utf-8")
    assert checker._eval_report(tmp_path, "r") == []  # type: ignore[attr-defined]

    del report["elliptic_external"]
    (tmp_path / "eval_report.json").write_text(json.dumps(report), encoding="utf-8")
    problems = checker._eval_report(tmp_path, "r")  # type: ignore[attr-defined]
    assert any("elliptic_external" in problem for problem in problems), problems
