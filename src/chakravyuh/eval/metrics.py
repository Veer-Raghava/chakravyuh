"""Cluster scoring. The only module that opens the clustering answer key.

A stage passes its predicted clusters in and gets two numbers back. No frame crosses back, no
label crosses back, and no argument is a path: the run id is what locates both the answer key and
the measurements directory, exactly as `validate.py` does it, so there is deliberately no way to
point this at a different run's truth.

The number is pairwise, not full-cluster. Contract section 5 quotes 0.36 precision and 0.44
recall for the multi-input heuristic on *full* clusters, where a cluster counts only if it is
recovered exactly. That metric is discontinuous: one wrong edge destroys a 134-address cluster's
score entirely, so it moves in jumps as an analyst drags a threshold and tells them nothing about
whether the drag helped. Pairwise precision and recall move smoothly, which is what the console
needs. The JSON records `metric: "pairwise"` so nobody compares these two numbers to the
contract's two by accident.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

import polars as pl

from chakravyuh.mayajaal.writers import RUN_ID

GROUND_TRUTH_ROOT = Path("ground_truth")
MEASUREMENTS_ROOT = Path("measurements")
ENTITIES = "entities.parquet"


@dataclass(frozen=True)
class ClusterScore:
    """What a stage is allowed to learn about its own clustering. Numbers, never members."""

    pair_precision: float
    pair_recall: float
    pair_f1: float
    predicted_pairs: int
    true_pairs: int
    shared_pairs: int
    n_predicted_clusters: int
    n_universe_addresses: int


def _pairs(groups: Sequence[Sequence[str]], universe: set[str]) -> set[tuple[str, str]]:
    """Every unordered same-group pair, restricted to `universe`.

    The restriction is what makes recall a measurement of the heuristic rather than of capture
    coverage. An entity owning a thousand addresses of which this capture saw four has 499500 true
    pairs in the answer key and six that any clustering could possibly recover; scoring against
    the former would report a recall near zero no matter how good the heuristic was.
    """
    found: set[tuple[str, str]] = set()
    for group in groups:
        inside = sorted(set(group) & universe)
        found.update(combinations(inside, 2))
    return found


def score_clusters(
    run_id: str,
    predicted: Sequence[Sequence[str]],
    universe: Sequence[str],
    threshold: float,
    heuristics: Sequence[str],
) -> ClusterScore | None:
    """Score `predicted` against the run's answer key. Returns None when it is absent.

    `run_id` is a run id, never a path. `predicted` is a sequence of address groups, `universe`
    is every address the caller observed, and the remaining two are recorded in the report so a
    number can be traced to the cut that produced it.

    None rather than an exception when the answer key does not exist, because Law 2 rule 6 says
    inference must complete with it absent, and a caller that asked for a score it cannot have
    should warn and carry on rather than die.

    The two trees are resolved from the working directory rather than from the repository root,
    which is what `writers.run_roots` does and what makes a test's throwaway workspace behave
    exactly like the repository. The run name is validated with the same pattern, so `..` can
    never walk out of either tree.
    """
    if not RUN_ID.match(run_id):
        raise ValueError(f"run_id must match {RUN_ID.pattern}, got {run_id!r}")
    key = GROUND_TRUTH_ROOT / run_id / ENTITIES
    if not key.is_file():
        return None

    seen = set(universe)
    predicted_pairs = _pairs(predicted, seen)
    true_pairs = _pairs(
        pl.read_parquet(key, columns=["addresses"])["addresses"].to_list(),
        seen,
    )
    shared = predicted_pairs & true_pairs

    precision = len(shared) / len(predicted_pairs) if predicted_pairs else 0.0
    recall = len(shared) / len(true_pairs) if true_pairs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    score = ClusterScore(
        pair_precision=precision,
        pair_recall=recall,
        pair_f1=f1,
        predicted_pairs=len(predicted_pairs),
        true_pairs=len(true_pairs),
        shared_pairs=len(shared),
        n_predicted_clusters=len(predicted),
        n_universe_addresses=len(seen),
    )

    report = {
        "run_id": run_id,
        "metric": "pairwise",
        "metric_note": (
            "Same-cluster address pairs, restricted to the addresses the stage observed. Not "
            "comparable to the full-cluster 0.36/0.44 quoted in contract section 5."
        ),
        "threshold": threshold,
        "heuristics": sorted(heuristics),
        **asdict(score),
    }
    out = MEASUREMENTS_ROOT / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "cluster_metrics.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return score
