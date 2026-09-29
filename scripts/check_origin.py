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

# The granularities the reframe reports, coarsest last. A ceiling cannot fall as the granularity
# coarsens: an operator is recoverable on every transaction its exact host is, plus the ones a
# sibling peer in the same ASN carries. The gate asserts that ordering, so a rollup that lost mass
# somewhere shows up as an L1 ceiling below L0's rather than as a plausible-looking number.
GRAIN_ORDER = ("l0_host", "l1_asn", "l2_region")
HERO = "l1_asn"

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


def _check_granularity(report: dict[str, Any]) -> list[str]:
    """The reframe's bar: L1 is the hero, so it is gated the way L0 is, plus two honesty checks.

    The per-granularity block is what the console leads with, so a wrong number here misleads more
    than a wrong L0 number an officer never sees. Four things:

    1. The hero bar. `ensemble` beats both trivial rules at L1, the operator granularity, the same
       comparison the L0 bar makes but on the number the product actually sells.
    2. No estimator scores above its own granularity's ceiling, at every granularity.
    3. Ceilings do not fall as granularity coarsens (L0 <= L1 <= L2). A rollup that dropped mass
       shows up here as an operator less recoverable than its own host, which cannot be true.
    4. The shipped headline equals the re-derived L1. `l1_headline` is scored off origin_l1.parquet
       and `by_granularity.l1_asn` is rolled up independently in metrics.py; a gap means the file
       shipped a different operator than its own candidate mass implies.
    """
    grain = report.get("by_granularity")
    if not isinstance(grain, dict):
        return ["no by_granularity in the report, so the L1 hero the reframe sells is unmeasured"]

    problems: list[str] = []
    hero = grain.get(HERO, {})
    hero_scores = hero.get("scores")
    if not isinstance(hero_scores, dict) or ESTIMATOR not in hero_scores:
        problems.append(
            f"by_granularity.{HERO} scores no {ESTIMATOR}. It is the hero granularity, so it has "
            "to be measured or the run's ground truth predates true_origin_asn; regenerate it."
        )
        return problems
    bar = max(float(hero_scores[name]["top1"]) for name in BASELINES if name in hero_scores)
    best = max(
        (name for name in BASELINES if name in hero_scores),
        key=lambda name: float(hero_scores[name]["top1"]),
    )
    if float(hero_scores[ESTIMATOR]["top1"]) <= bar:
        problems.append(
            f"{ESTIMATOR} scores {hero_scores[ESTIMATOR]['top1']} top-1 at {HERO} and the best "
            f"trivial rule ({best}) scores {bar}. The operator attribution is the product; it has "
            "to beat what an investigator already has for free."
        )

    for gname in GRAIN_ORDER:
        node = grain.get(gname, {})
        ceiling = node.get("recoverable_ceiling")
        node_scores = node.get("scores")
        if ceiling is None or not isinstance(node_scores, dict):
            continue
        for name, score in sorted(node_scores.items()):
            if float(score.get("top1", 0.0)) > float(ceiling) + 1e-9:
                problems.append(
                    f"{name} scores {score['top1']} top-1 at {gname} against a ceiling of "
                    f"{ceiling}. No estimator can be right about a key no observer heard."
                )

    ceilings = [
        (gname, grain[gname]["recoverable_ceiling"])
        for gname in GRAIN_ORDER
        if gname in grain and "recoverable_ceiling" in grain[gname]
    ]
    for (coarser_name, coarser), (finer_name, finer) in zip(ceilings[1:], ceilings, strict=False):
        if float(coarser) < float(finer) - 1e-9:
            problems.append(
                f"{coarser_name} ceiling {coarser} is below {finer_name} ceiling {finer}. A "
                "coarser granularity cannot be less recoverable, so the rollup dropped mass."
            )

    headline = grain.get("l1_headline")
    if isinstance(headline, dict):
        shipped = float(headline.get("top1", 0.0))
        derived = float(hero_scores[ESTIMATOR]["top1"])
        if abs(shipped - derived) > PARITY_TOLERANCE:
            problems.append(
                f"l1_headline scores {shipped} but by_granularity.{HERO} re-derives {derived} for "
                f"{ESTIMATOR}. The shipped operator and its own candidate mass disagree."
            )
    return problems


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
    problems += _check_granularity(report)
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
