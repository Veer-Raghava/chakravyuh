"""Collate the observer-fraction sweep into one curve, because a single accuracy number is a lie.

Five runs, five worlds. At `observer_fraction` 0.50 the originator is in the candidate set for most
transactions and at 0.02 it almost never is, so an accuracy quoted without its fraction says
nothing at all: the same estimator scores an order of magnitude apart across this range while being
exactly as good. This writes `origin_curve.json` for the console and `origin_curve.md` for a human,
both carrying the ceiling beside every accuracy so neither can be read without it.

Stdlib only, like `compare_runs.py`. Takes fractions, never paths: the run id is derived from the
fraction exactly as the Makefile's sweep loop derives it, so a report can only ever be collated
from the runs that produced it. Prints numbers and field names to stderr. Never an identifier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MEASUREMENTS = Path("measurements")
SWEEP_PREFIX = "_sweep-"
OUT_RUN = "_sweep"
REPORT = "origin_accuracy.json"
TRAFFIC = ("clear", "vpn", "tor")

# What the curve reports per fraction, and the order the table columns appear in. `ceiling` first
# because every accuracy beside it is a share of it, and `coverage` last because it belongs to the
# estimator's refusal policy rather than to its accuracy.
COLUMNS = ("ceiling", "first_seen", "payer_linkage", "first_spy", "ensemble", "coverage")


def _read(fraction: str) -> dict[str, Any]:
    """One sweep run's report, or a raised error naming what to run."""
    path = MEASUREMENTS / f"{SWEEP_PREFIX}{fraction}" / REPORT
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} does not exist. Run `make sweep-observer-fraction`, which builds each world "
            f"and scores it, before collating."
        )
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _row(fraction: str, report: dict[str, Any]) -> dict[str, Any]:
    """One point on the curve: every estimator's top-1, the ceiling, and the traffic breakdown."""
    scores = report.get("scores", {})
    point: dict[str, Any] = {
        "observer_fraction": float(report.get("observer_fraction", float(fraction))),
        "ceiling": report.get("recoverable_ceiling"),
        "transactions_broadcast": report.get("transactions_broadcast"),
        "transactions_with_a_candidate": report.get("transactions_with_a_candidate"),
    }
    for name in sorted(scores):
        point[name] = {
            "top1": scores[name].get("top1"),
            "top3": scores[name].get("top3"),
            "coverage": scores[name].get("coverage"),
            "by_traffic": scores[name].get("by_traffic", {}),
            "by_window": scores[name].get("by_window", {}),
        }
    return point


def _cell(point: dict[str, Any], column: str) -> str:
    if column == "ceiling":
        return f"{point['ceiling']:.4f}"
    if column == "coverage":
        node = point.get("ensemble", {})
        return f"{node.get('coverage', 0.0):.3f}"
    node = point.get(column)
    if node is None:
        return "—"
    return f"{node['top1']:.4f}"


def _markdown(points: list[dict[str, Any]]) -> str:
    """The curve as a human reads it: one row per world, one table per traffic class."""
    lines = [
        "# Origin accuracy over observer fraction",
        "",
        "Top-1 accuracy as a share of **all broadcast transactions**, not of the transactions",
        "an observer recorded. `ceiling` is the share whose true originator is in the candidate",
        "set at all: no estimator here can exceed it, and an accuracy read without it looks like",
        "far more headroom than the capture has. `coverage` is the share of transactions",
        "`ensemble` was willing to answer; the rest it abstained on.",
        "",
        "| observer_fraction | " + " | ".join(COLUMNS) + " |",
        "|---" * (len(COLUMNS) + 1) + "|",
    ]
    for point in points:
        cells = " | ".join(_cell(point, column) for column in COLUMNS)
        lines.append(f"| {point['observer_fraction']:.2f} | {cells} |")

    lines += [
        "",
        "## By traffic class, `ensemble`",
        "",
        "Tor beats VPN where a transaction used both, so the harder class is never reported as the",
        "easier one.",
        "",
        "| observer_fraction | " + " | ".join(TRAFFIC) + " |",
        "|---" * (len(TRAFFIC) + 1) + "|",
    ]
    for point in points:
        by_traffic = point.get("ensemble", {}).get("by_traffic", {})
        cells = " | ".join(f"{by_traffic.get(kind, 0.0):.4f}" for kind in TRAFFIC)
        lines.append(f"| {point['observer_fraction']:.2f} | {cells} |")

    lines += [
        "",
        "## Holdout only, `ensemble` against the best trivial rule",
        "",
        "Transactions no label was available for. The denominator is transactions an observer",
        "heard, so these do not compare to the table above. Reported because an estimator can beat",
        "a trivial rule run-wide by memorising its own training window.",
        "",
        "| observer_fraction | ensemble | best trivial rule |",
        "|---|---|---|",
    ]
    for point in points:
        learned = point.get("ensemble", {}).get("by_window", {}).get("holdout", {})
        trivial = max(
            (
                point.get(name, {}).get("by_window", {}).get("holdout", {}).get("top1", 0.0)
                for name in ("first_seen", "payer_linkage")
            ),
            default=0.0,
        )
        lines.append(
            f"| {point['observer_fraction']:.2f} | {learned.get('top1', 0.0):.4f} | {trivial:.4f} |"
        )
    return "\n".join(lines) + "\n"


def collate(fractions: list[str]) -> tuple[dict[str, Any], str]:
    """The curve as JSON and as markdown, sorted by fraction so the table reads left to right."""
    points = [_row(fraction, _read(fraction)) for fraction in fractions]
    points.sort(key=lambda point: point["observer_fraction"])
    curve = {
        "metric": "top-1 over all broadcast transactions, per observer_fraction",
        "metric_note": (
            "One accuracy per world. The same estimator scores an order of magnitude apart across "
            "this range while being exactly as good, so a number quoted without its fraction and "
            "its ceiling is not a measurement."
        ),
        "observer_fractions": [point["observer_fraction"] for point in points],
        "points": points,
    }
    return curve, _markdown(points)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        sys.stderr.write("usage: collate_sweep.py <fraction> [<fraction> ...]\n")
        return 2
    try:
        curve, markdown = collate(args)
    except FileNotFoundError as exc:
        sys.stderr.write(f"collate_sweep: {exc}\n")
        return 1

    out = MEASUREMENTS / OUT_RUN
    out.mkdir(parents=True, exist_ok=True)
    (out / "origin_curve.json").write_text(
        json.dumps(curve, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "origin_curve.md").write_text(markdown, encoding="utf-8")
    sys.stderr.write(
        f"collate_sweep: {len(curve['points'])} worlds collated into {out}/origin_curve.md, "
        f"fractions {curve['observer_fractions']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
