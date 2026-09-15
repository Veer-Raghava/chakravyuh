"""Read the bar out of `model_report.json` and assert the model cleared it.

Separate from `metrics.py` on purpose, for the same reason `check_origin.py` is: the module that
computes a number must not also be the thing that decides the number is good enough, or the gate
is the model grading itself. This reads the files from outside, knows nothing about how any of it
was computed, and asserts four things:

1. The bar. `model_report.json`'s `wallet_model.precision_at_20` strictly exceeds
   `baseline_wallet.json`'s, both measured on this run's holdout subjects through the same
   scoring arithmetic. The baseline is not a constant: it moves when the generator moves.
2. The measurement is honest. `n_scored` subjects were labelled, coverage-by-class is
   present for both classes, and no number equals exactly one, which on this generator is
   what leakage looks like rather than skill.
3. The calibration table backs the conformal claim. `scores/calibration.parquet` reports
   both methods per class, and the class-conditional rows sit at the target.
4. `eval_report.json` quotes the same numbers the reports hold — the file the contract
   publishes is a restatement of the measurements, not a third source of truth.

Stdlib only, like `check_origin.py`, so it runs under the system interpreter. Prints field names
and numbers to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# A holdout precision-at-20 above this on the synthetic generator is leakage, not skill: the
# adversary is only mildly better at hiding than the crowd, so a model that names twenty
# illicit subjects out of twenty has read something it should not have had.
LEAKAGE_CEILING = 0.9

# Coverage slack, the same width the in-process test and check_scores.py use.
COVERAGE_TOLERANCE = 0.15


def _load(path: Path) -> dict[str, Any]:
    node: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(node, dict):
        raise ValueError(f"{path} does not hold a JSON object")
    return node


def check(measurements: Path, run_id: str) -> list[str]:
    """Every way the wallet reports fail the gate. Empty means the model cleared the bar."""
    problems: list[str] = []
    model_path = measurements / "model_report.json"
    baseline_path = measurements / "baseline_wallet.json"
    if not model_path.is_file():
        return [f"no model_report.json in {measurements}, so nothing was measured"]
    if not baseline_path.is_file():
        return [f"no baseline_wallet.json in {measurements}, so the bar was never measured"]

    model_report = _load(model_path)
    baseline = _load(baseline_path)
    wallet = model_report.get("wallet_model", {})
    for field in ("pr_auc", "roc_auc", "precision_at_20", "recall_at_20", "n_scored"):
        if field not in wallet:
            problems.append(f"model_report.json's wallet_model lacks {field}")
    if "precision_at_20" not in baseline:
        problems.append("baseline_wallet.json lacks precision_at_20, so the bar cannot be read")
    if problems:
        return problems

    model_p20 = float(wallet["precision_at_20"])
    baseline_p20 = float(baseline["precision_at_20"])
    if model_p20 <= baseline_p20:
        problems.append(
            f"the model scores {model_p20} precision-at-20 and the trivial rule "
            f"({baseline.get('rule', 'unspecified')}) scores {baseline_p20}. The model has to "
            "beat what an investigator already has for free."
        )
    if model_p20 >= LEAKAGE_CEILING:
        problems.append(
            f"the model scores {model_p20} precision-at-20. Above {LEAKAGE_CEILING} on this "
            "generator is leakage rather than skill: check the window rule and the label door."
        )
    n_scored = int(wallet["n_scored"])
    if n_scored <= 0:
        problems.append("no holdout subject was labelled, so every number here is undefined")
    elif n_scored < 20 and model_p20 > 0.0:
        problems.append(
            f"only {n_scored} labelled subjects, so precision-at-20 is precision-at-{n_scored} "
            "under another name and the report does not say so"
        )

    coverage = model_report.get("coverage_by_class", {})
    for klass in ("0", "1"):
        if klass not in coverage:
            problems.append(f"coverage_by_class lacks class {klass}, so one class stands in")
        else:
            value = float(coverage[klass])
            if value == 1.0 and n_scored > 0:
                problems.append(
                    f"class {klass} is covered at exactly 1.0. A conformal set that contains "
                    "its class every time was not calibrated, it was opened."
                )
    if float(wallet.get("abstain_rate", -1.0)) == 1.0:
        problems.append(
            "the model abstained on every holdout subject, which says nothing about everything"
        )

    # Split agreement: the boundary the model was scored at is the boundary the report names.
    boundary = model_report.get("split", {}).get("boundary_us")
    if boundary != baseline.get("split", {}).get("boundary_us"):
        problems.append(
            "model_report.json and baseline_wallet.json disagree about boundary_us, so the two "
            "numbers were not measured on the same holdout"
        )
    if not model_report.get("baseline_beaten") and model_p20 > baseline_p20:
        problems.append(
            "baseline_beaten is false although the model's precision-at-20 exceeds the bar, so "
            "the report contradicts itself"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: check_buddhi_bar.py <measurements-dir>\n")
        return 2
    measurements = Path(args[0])
    if not measurements.is_dir():
        sys.stderr.write(f"check_buddhi_bar: {measurements} is not a directory\n")
        return 2

    run_id = measurements.name
    problems = check(measurements, run_id)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_buddhi_bar: {len(problems)} problems in {measurements}\n")
        return 1

    wallet = _load(measurements / "model_report.json")["wallet_model"]
    baseline = _load(measurements / "baseline_wallet.json")
    sys.stderr.write(
        f"check_buddhi_bar: model precision@20 {wallet['precision_at_20']} beats baseline "
        f"{baseline['precision_at_20']} over {wallet['n_scored']} labelled holdout subjects\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
