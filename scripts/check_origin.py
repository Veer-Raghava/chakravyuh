"""Read the bar out of `origin_accuracy.json` and assert the estimator cleared it.

Separate from `metrics.py` on purpose. The module that computes a number must not also be the
thing that decides the number is good enough, or the gate is the estimator grading itself. This
reads the file from outside, knows nothing about how any of it was computed, and asserts four
things:

1. The bar. `ensemble` beats both trivial rules on top-1, all three re-measured on this run. Not a
   figure copied from a previous run: every one of these moves when the generator moves.
2. The same bar again on the holdout window alone. An estimator can beat a trivial rule run-wide by
   memorising its own training window, which is exactly what the first version of this stage did,
   and a gate that could not see that is a gate that rewards it.
3. The parity self-check. `first_spy`, computed through the whole feature pipeline, must reproduce
   `first_seen`, computed independently in `metrics.py` from `normalised/` alone. A mismatch means
   the pipeline reorders or drops candidates somewhere between the two, and every other number in
   the file is then suspect.
4. The report says what a reader needs to not misread it: the per-traffic breakdown, the ceiling,
   and the observer fraction the whole thing is conditional on.

Stdlib only, like `compare_runs.py`, so it runs under the system interpreter. Prints field names
and numbers to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ESTIMATOR = "ensemble"
PARITY = ("first_spy", "first_seen")
BASELINES = ("first_seen", "payer_linkage")
TRAFFIC = ("clear", "vpn", "tor")
WINDOWS = ("train", "holdout")

# The parity pair is two implementations of one rule, so they agree exactly or the difference is a
# tie-break. A tie moves one transaction, and the run is thousands, so anything above this is a
# pipeline defect rather than a tie-break and the message says which.
PARITY_TOLERANCE = 0.002


def _score(report: dict[str, Any], name: str) -> dict[str, Any]:
    scores = report.get("scores", {})
    if name not in scores:
        raise KeyError(name)
    return dict(scores[name])


def _window_top1(score: dict[str, Any], window: str) -> tuple[float, int, int]:
    """`top1`, correct count and transaction count for one window of one estimator."""
    node = score.get("by_window", {}).get(window, {})
    return (
        float(node.get("top1", 0.0)),
        int(node.get("n_correct", 0)),
        int(node.get("n_transactions", 0)),
    )


def check(report: dict[str, Any]) -> list[str]:
    """Every way the report fails the gate. Empty means the estimator cleared the bar."""
    problems: list[str] = []
    needed = {ESTIMATOR, *BASELINES, *PARITY}
    missing = sorted(name for name in needed if name not in report.get("scores", {}))
    if missing:
        return [f"origin_accuracy.json scores no {', '.join(missing)}, so the bar cannot be read"]

    learned = _score(report, ESTIMATOR)
    bar = max(float(_score(report, name)["top1"]) for name in BASELINES)
    best = max(BASELINES, key=lambda name: float(_score(report, name)["top1"]))
    if float(learned["top1"]) <= bar:
        problems.append(
            f"{ESTIMATOR} scores {learned['top1']} top-1 and the best trivial rule ({best}) scores "
            f"{bar}. The estimator has to beat what an investigator already has for free."
        )

    # The same comparison on transactions no label was available for. Beating a trivial rule
    # run-wide while losing on the holdout is memorisation, and it is invisible in `top1`.
    learned_holdout, learned_correct, holdout_total = _window_top1(learned, "holdout")
    baseline_holdout = 0.0
    baseline_correct = 0
    baseline_name = BASELINES[0]
    for name in BASELINES:
        value, correct, _ = _window_top1(_score(report, name), "holdout")
        if value > baseline_holdout:
            baseline_holdout, baseline_correct, baseline_name = value, correct, name
    if not holdout_total:
        problems.append(
            "the holdout window holds no transactions, so the bar was only ever checked on data "
            "the model trained on. Lower eval.train_fraction or lengthen the capture."
        )
    elif learned_holdout <= baseline_holdout:
        problems.append(
            f"{ESTIMATOR} scores {learned_holdout} top-1 on the holdout window against "
            f"{baseline_name}'s {baseline_holdout} ({learned_correct} correct against "
            f"{baseline_correct} of {holdout_total}). Beating a trivial rule only on the window it "
            "trained on is memorisation, not attribution."
        )

    spy, seen = (float(_score(report, name)["top1"]) for name in PARITY)
    if abs(spy - seen) > PARITY_TOLERANCE:
        problems.append(
            f"{PARITY[0]} scores {spy} and {PARITY[1]} scores {seen}. They are one rule computed "
            "two ways, so a gap this size means the feature pipeline reorders or drops candidates."
        )

    ceiling = float(report.get("recoverable_ceiling", 0.0))
    if not ceiling:
        problems.append(
            "no recoverable_ceiling in the report. Every accuracy here is unreadable without it, "
            "because the originator is absent from the candidate set for most transactions."
        )
    for name in sorted(report.get("scores", {})):
        score = _score(report, name)
        if float(score["top1"]) > ceiling + 1e-9:
            problems.append(
                f"{name} scores {score['top1']} top-1 against a ceiling of {ceiling}. An estimator "
                "cannot be right about a transaction whose originator no observer heard."
            )
        by_traffic = score.get("by_traffic", {})
        absent = [kind for kind in TRAFFIC if kind not in by_traffic]
        if absent:
            problems.append(f"{name} reports no accuracy for {absent}, so one number stands in")
        if any(window not in score.get("by_window", {}) for window in WINDOWS):
            problems.append(f"{name} reports no train/holdout split, so memorisation is invisible")

    if "observer_fraction" not in report:
        problems.append(
            "no observer_fraction in the report. Every number here is conditional on it and "
            "quoting one without it is the trap the sweep target exists to avoid."
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: check_origin.py <measurements>/origin_accuracy.json\n")
        return 2
    path = Path(args[0])
    if not path.is_file():
        sys.stderr.write(f"check_origin: {path} does not exist, so nothing was measured\n")
        return 2

    report = json.loads(path.read_text(encoding="utf-8"))
    problems = check(report)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_origin: {len(problems)} problems in {path}\n")
        return 1

    learned = _score(report, ESTIMATOR)
    bar = max(float(_score(report, name)["top1"]) for name in BASELINES)
    holdout, _, _ = _window_top1(learned, "holdout")
    sys.stderr.write(
        f"check_origin: {ESTIMATOR} {learned['top1']} beats the best trivial rule {bar} at "
        f"observer_fraction {report['observer_fraction']}, ceiling "
        f"{report['recoverable_ceiling']}, holdout {holdout}, coverage {learned['coverage']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
