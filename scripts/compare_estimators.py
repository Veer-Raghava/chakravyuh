"""Print every estimator's accuracy side by side, so the ensemble earns its place rather than
being asserted into it.

The stack is four rules — first_seen and payer_linkage are the trivial baselines an investigator
already has for free, timing_mle and first_spy are the real estimators, ensemble is the blend. The
report holds all of them scored on the same run; this reads them out and lays them next to each
other at both grains the product uses: L0 (the exact host, officer-only) and L1 (the network
operator, the hero). A blend that does not beat its own inputs is not a blend worth shipping, and
this is where that shows.

Stdlib only, like the other report readers. Takes the run's origin_accuracy.json, never a path it
builds itself. Prints to stdout because it is output, not a check.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# Baselines first, then estimators, so the table reads free-rules then learned-rules left to right.
ORDER = ("first_seen", "payer_linkage", "first_spy", "timing_mle", "ensemble")
HERO = "l1_asn"


def _l0_rows(report: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    scores = report.get("scores", {})
    rows = []
    for name in ORDER:
        node = scores.get(name)
        if not node:
            continue
        rows.append(
            (
                name,
                f"{node.get('top1', 0.0):.4f}",
                f"{node.get('top3', 0.0):.4f}",
                f"{node.get('coverage', 0.0):.3f}",
            )
        )
    return rows


def _l1_rows(report: dict[str, Any]) -> list[tuple[str, str, str]]:
    hero = report.get("by_granularity", {}).get(HERO, {})
    scores = hero.get("scores", {})
    rows = []
    for name in ORDER:
        node = scores.get(name)
        if not node:
            continue
        rows.append((name, f"{node.get('top1', 0.0):.4f}", f"{node.get('topk', 0.0):.4f}"))
    return rows


def _table(header: tuple[str, ...], rows: Sequence[Sequence[str]]) -> str:
    widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(header))
    out = [line]
    for row in rows:
        out.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(out)


def render(report: dict[str, Any]) -> str:
    ceiling = report.get("recoverable_ceiling")
    fraction = report.get("observer_fraction")
    out = [
        f"origin accuracy, every estimator side by side  "
        f"(observer_fraction {fraction}, L0 ceiling {ceiling})",
        "",
        "L0 host (officer-only): top-1 over all broadcast transactions",
        _table(("estimator", "top1", "top3", "coverage"), _l0_rows(report)),
    ]
    l1_rows = _l1_rows(report)
    if l1_rows:
        hero = report.get("by_granularity", {}).get(HERO, {})
        out += [
            "",
            f"L1 operator/ASN (the hero): ceiling {hero.get('recoverable_ceiling')}",
            _table(("estimator", "top1", "topk"), l1_rows),
        ]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: compare_estimators.py <measurements>/origin_accuracy.json\n")
        return 2
    path = Path(args[0])
    if not path.is_file():
        sys.stderr.write(f"compare_estimators: {path} does not exist, so nothing was measured\n")
        return 1
    report = json.loads(path.read_text(encoding="utf-8"))
    sys.stdout.write(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
