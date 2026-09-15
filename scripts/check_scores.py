"""Check `scores/` against contract section 7, from outside the code that wrote it.

`check_stage.py` checks the manifest's arithmetic. This checks the files themselves, and the
four rules a schema check cannot see:

  The label is the conformal set, never the score. A row's `label` is derivable from
  `conf_low`/`conf_high` alone — `LIKELY_ILICIT` when only the high bound is set, and so on —
  so a file whose labels disagree with its intervals has scored through a side door.
  Coverage lands at the target, per class. The calibration table's `class_conditional` rows
  must sit within tolerance of `target_coverage` — a minority class covered at half the
  target is the exact failure the Mondrian wrapper exists to prevent, and the one that
  hides inside a blended number.
  No identifier in full. Section 0's truncation law applies to `top_features` names (they
  are feature names, checked against the vocabulary in docs/FEATURES.md) and to every string
  column a regex can sweep: nothing may look like a complete IPv4, TXID or Bitcoin address.
  The report keys exist and are non-null. `eval_report.json` is the contract's example
  object, `by_observer_fraction` and `by_traffic_type` included, `baseline_beaten` a real
  boolean — the section says a test asserts each key is present and non-null, and this is
  that test, run at gate scale rather than only in-process.

Transcribed from the contract by hand, never imported from `chakravyuh.buddhi`. A checker that
imports the writer's constants asserts only that a module equals itself.

Writes file names, field names and counts to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import polars as pl

# Contract section 7, column order and dtype. `top_features` is a list of structs; the
# contract fixes two field names, so the interior is checked as exactly those.
WALLET_SCORES: tuple[tuple[str, pl.DataType], ...] = (
    ("subject_id", pl.String()),
    ("risk_score", pl.Float64()),
    ("label", pl.String()),
    ("conf_low", pl.Float64()),
    ("conf_high", pl.Float64()),
    ("coverage_target", pl.Float64()),
    ("model", pl.String()),
    ("top_features", pl.List(pl.Struct({"name": pl.String(), "value": pl.Float64()}))),
    ("abstain", pl.Boolean()),
)

CALIBRATION: tuple[tuple[str, pl.DataType], ...] = (
    ("class", pl.String()),
    ("method", pl.String()),
    ("target_coverage", pl.Float64()),
    ("empirical_coverage", pl.Float64()),
    ("n_calibration", pl.Int32()),
    ("n_test", pl.Int32()),
    ("imbalance_ratio", pl.String()),
)

LABELS = {"LIKELY_ILICIT", "UNCLEAR", "LIKELY_LICIT", "ABSTAIN"}
MODELS = {"lightgbm_v1", "gnn_v1"}
METHODS = {"plain_conformal", "class_conditional"}

# The contract's example eval_report object: every key a reader may index, at the depth it
# appears. `by_observer_fraction` and `by_traffic_type` are lists the contract shows filled,
# so each element's keys are required too.
EVAL_REPORT: dict[str, object] = {
    "split": {"mode": str, "train_end_us": int, "val_end_us": int, "test_start_us": int},
    "wallet_model": {
        "pr_auc": float,
        "roc_auc": float,
        "precision_at_20": float,
        "recall_at_20": float,
    },
    "origin_estimator": {
        "top1_accuracy": float,
        "top3_accuracy": float,
        "abstain_rate": float,
        "by_observer_fraction": [{"fraction": float, "top1": float, "abstain": float}],
        "by_traffic_type": [{"type": str, "top1": float}],
    },
    "clustering": {"precision": float, "recall": float, "threshold": float},
    "baseline_beaten": bool,
    "seed": int,
    "run_id": str,
    "code_version": str,
}

# A complete identifier looks like one: four IPv4 octets, a 64-hex TXID, or a base58 address
# of full length. Section 0's truncations (x.x.x.x, first6…last4, first8…last4) never match.
# Values in the `kind:value` node-id form are exempt: section 7's `subject_id` is a node id by
# contract, the same join-key precedent as graph nodes' `node_id`, and `peek.py` truncates on
# the way out — the rendered artifacts (alerts, console) carry the truncated copies.
FULL_IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
FULL_TXID = re.compile(r"\b[0-9a-fA-F]{64}\b")
FULL_ADDRESS = re.compile(r"\b(?:1|3|bc1)[0-9A-Za-z]{25,60}\b")
NODE_ID = re.compile(r"^(?:addr|cluster|tx|peer|asn):")


def _complete_identifiers(values: pl.Series) -> dict[str, int]:
    """How many values of the column hold each kind of complete identifier.

    Values already in the `kind:value` node-id form are join keys and are exempt; the check is
    for a bare identifier sitting where a rendered value would.
    """
    strings = values.cast(pl.String())
    bare = strings.filter(~strings.str.contains(NODE_ID.pattern))
    return {
        kind: int(bare.str.contains(pattern.pattern).sum())
        for kind, pattern in (
            ("IPv4 address", FULL_IPV4),
            ("TXID", FULL_TXID),
            ("Bitcoin address", FULL_ADDRESS),
        )
    }


# Coverage slack, the same width the in-process test uses: wide enough that quantile noise
# on tens of calibration rows does not flicker, tight enough to catch a minority class left
# at half the target.
COVERAGE_TOLERANCE = 0.15

FEATURE_NAMES_PATH = Path("docs") / "FEATURES.md"


def _schema(
    frame: pl.DataFrame,
    expected: tuple[tuple[str, pl.DataType], ...],
    name: str,
) -> list[str]:
    """Column names in contract order, and each dtype, for one table."""
    problems: list[str] = []
    want = [column for column, _ in expected]
    got = list(frame.columns)
    if got != want:
        problems.append(f"{name}: columns are {got}, contract section 7 says {want}")
        return problems
    for column, dtype in expected:
        found = frame.schema[column]
        if found != dtype:
            problems.append(f"{name}: {column} is {found}, contract section 7 says {dtype}")
    return problems


def _label_matches_interval(scores: pl.DataFrame) -> list[str]:
    """The label is derivable from the interval alone; check the derivation, per section 7."""
    problems: list[str] = []
    # The writer encodes the interval as conf_low 0.0 when class 0 is in the set and
    # conf_high 1.0 when class 1 is, so the four sets map to the four labels directly.
    both = scores.filter((pl.col("conf_low") == 0.0) & (pl.col("conf_high") == 1.0))
    wrong_both = both.filter(pl.col("label") != "UNCLEAR").height
    if wrong_both:
        problems.append(
            f"{wrong_both} rows with both classes in the interval are not UNCLEAR. The label "
            "is the conformal set, never the score."
        )
    only_low = scores.filter((pl.col("conf_low") == 0.0) & (pl.col("conf_high") != 1.0))
    wrong_low = only_low.filter(pl.col("label") != "LIKELY_LICIT").height
    if wrong_low:
        problems.append(f"{wrong_low} rows whose interval names only class 0 are not LIKELY_LICIT")
    only_high = scores.filter((pl.col("conf_low") != 0.0) & (pl.col("conf_high") == 1.0))
    wrong_high = only_high.filter(pl.col("label") != "LIKELY_ILICIT").height
    if wrong_high:
        problems.append(
            f"{wrong_high} rows whose interval names only class 1 are not LIKELY_ILICIT"
        )
    neither = scores.filter((pl.col("conf_low") != 0.0) & (pl.col("conf_high") != 1.0))
    wrong_neither = neither.filter(pl.col("label") != "ABSTAIN").height
    if wrong_neither:
        problems.append(f"{wrong_neither} rows with an empty interval are not ABSTAIN")
    stray = set(scores["label"].unique().to_list()) - LABELS
    if stray:
        problems.append(f"label values outside contract section 7: {sorted(stray)}")
    # abstain agrees with the empty set, and the four labels are exactly the four sets.
    disagree = scores.filter(pl.col("abstain") != (pl.col("label") == "ABSTAIN")).height
    if disagree:
        problems.append(f"{disagree} rows where abstain and the label disagree")
    return problems


def _top_features(scores: pl.DataFrame, known: set[str] | None) -> list[str]:
    """Top five by absolute value, struct fields as the contract fixes them."""
    problems: list[str] = []
    if scores.height and known:
        named = scores.filter(pl.col("top_features").list.len() > 0)
        if named.height:
            names = named["top_features"].explode().struct.field("name").unique().to_list()
            stray = {str(one) for one in names} - known
            if stray:
                problems.append(f"top_features names outside docs/FEATURES.md: {sorted(stray)[:8]}")
    return problems


def _identifiers(scores: pl.DataFrame) -> list[str]:
    """No complete identifier anywhere a string column could carry one, per section 0."""
    problems: list[str] = []
    for column in scores.columns:
        if scores.schema[column] != pl.String():
            continue
        values = scores[column].drop_nulls().unique()
        for kind, hits in _complete_identifiers(values).items():
            if hits:
                problems.append(f"{column} carries {hits} complete {kind} values")
    return problems


def _coverage(calibration: pl.DataFrame) -> list[str]:
    """Class-conditional coverage lands at the target, per class — not one blended number."""
    problems: list[str] = []
    stray = set(calibration["method"].unique().to_list()) - METHODS
    if stray:
        problems.append(f"method values outside contract section 7: {sorted(stray)}")
    stray_class = set(calibration["class"].unique().to_list()) - {"0", "1"}
    if stray_class:
        problems.append(f"class values outside contract section 7: {sorted(stray_class)}")
    conditional = calibration.filter(pl.col("method") == "class_conditional")
    for row in conditional.iter_rows(named=True):
        target = float(row["target_coverage"])
        got = float(row["empirical_coverage"])
        if abs(got - target) > COVERAGE_TOLERANCE:
            problems.append(
                f"class {row['class']} conditional coverage {got:.4f} misses target "
                f"{target:.2f} by more than {COVERAGE_TOLERANCE}"
            )
    for column in ("target_coverage", "empirical_coverage", "n_calibration", "n_test"):
        if calibration[column].null_count():
            problems.append(f"null values in calibration.{column}")
    return problems


def _walk_keys(node: object, spec: object, path: str, problems: list[str]) -> None:
    """Every spec key present and non-null, recursive, lists of objects checked per element."""
    if isinstance(spec, dict):
        if not isinstance(node, dict):
            problems.append(f"{path} is not an object")
            return
        for key, sub in spec.items():
            if key not in node:
                problems.append(f"{path}.{key} missing")
            elif node[key] is None:
                problems.append(f"{path}.{key} is null")
            else:
                _walk_keys(node[key], sub, f"{path}.{key}", problems)
    elif isinstance(spec, list):
        if not isinstance(node, list):
            problems.append(f"{path} is not a list")
            return
        if not node:
            problems.append(f"{path} is empty, but the contract shows it filled")
            return
        for index, element in enumerate(node):
            _walk_keys(element, spec[0], f"{path}[{index}]", problems)
    elif isinstance(spec, type) and isinstance(node, bool) is not (spec is bool):
        problems.append(f"{path} is {type(node).__name__}, contract says {spec.__name__}")


def _eval_report(scores_dir: Path, run_id: str) -> list[str]:
    """The contract's report object, key by key, present and non-null."""
    path = scores_dir / "eval_report.json"
    if not path.is_file():
        return [f"no eval_report.json in {scores_dir}, which section 7 requires"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"eval_report.json is not JSON: {exc}"]
    problems: list[str] = []
    _walk_keys(report, EVAL_REPORT, "eval_report", problems)
    if isinstance(report, dict) and report.get("run_id") not in (None, run_id):
        problems.append(f"eval_report.json names run {report['run_id']!r}, not {run_id!r}")
    beaten = report.get("baseline_beaten") if isinstance(report, dict) else None
    if isinstance(beaten, bool) and not beaten:
        problems.append("baseline_beaten is false; the model did not clear the measured bar")
    return problems


def _feature_vocabulary() -> set[str] | None:
    """The names docs/FEATURES.md glosses, read for the top_features check."""
    path = Path(__file__).resolve().parent.parent / FEATURE_NAMES_PATH
    if not path.is_file():
        return None
    import re as _re

    return {
        m.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (m := _re.match(r"\|\s*`([a-z0-9_]+)`\s*\|", line))
    }


def check(scores_dir: Path, run_id: str) -> list[str]:
    """Every way `scores/` fails contract section 7. Empty means it holds."""
    problems: list[str] = []
    for name in ("wallet_scores.parquet", "calibration.parquet", "eval_report.json"):
        if not (scores_dir / name).is_file():
            problems.append(f"no {name} in {scores_dir}, which section 7 requires")
    if problems:
        return problems

    scores = pl.read_parquet(scores_dir / "wallet_scores.parquet")
    problems += _schema(scores, WALLET_SCORES, "wallet_scores.parquet")
    if problems:
        return problems
    if scores.is_empty():
        problems.append("wallet_scores.parquet has no rows, so nothing was scored")
        return problems

    problems += _label_matches_interval(scores)
    problems += _identifiers(scores)
    known = _feature_vocabulary()
    if known:
        problems += _top_features(scores, known)
    else:
        problems.append("docs/FEATURES.md is absent, so top_features names cannot be checked")

    calibration = pl.read_parquet(scores_dir / "calibration.parquet")
    problems += _schema(calibration, CALIBRATION, "calibration.parquet")
    if calibration.height:
        problems += _coverage(calibration)

    problems += _eval_report(scores_dir, run_id)

    meta = scores_dir / "_meta.json"
    if not meta.is_file():
        problems.append("no _meta.json, so scores/ cannot be traced to its inputs")
    else:
        node = json.loads(meta.read_text(encoding="utf-8"))
        counts = node.get("counts", {})
        if counts.get("out") != scores.height:
            problems.append(
                f"_meta.json counts.out {counts.get('out')} != {scores.height} rows written"
            )
        for entry in node.get("outputs", []):
            if not (scores_dir.parent / entry.get("path", "")).is_file():
                problems.append(f"_meta.json lists missing output {entry.get('path')}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        sys.stderr.write("usage: check_scores.py <run-id> <scores-dir>\n")
        return 2
    run_id, scores_dir = args[0], Path(args[1])
    if not scores_dir.is_dir():
        sys.stderr.write(f"check_scores: {scores_dir} is not a directory\n")
        return 2

    problems = check(scores_dir, run_id)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_scores: {len(problems)} problems in {scores_dir}\n")
        return 1

    scores = pl.read_parquet(scores_dir / "wallet_scores.parquet", columns=["label", "abstain"])
    counts = scores.group_by("label").len().sort("label")
    summary = ", ".join(f"{row[0]} {row[1]}" for row in counts.iter_rows())
    sys.stderr.write(f"check_scores: {scores_dir} OK, {scores.height} subjects, {summary}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
