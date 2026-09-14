"""`python -m chakravyuh.jaal --in data/generated/<run>/normalised --out data/generated/<run>`.

Scoring lives here and nowhere else in the stage. `chakravyuh.eval.metrics` is imported by this
file alone, so `stage.py` stays a pure read of `normalised/` and the one place the pipeline
touches the eval package is a file that is not itself part of the pipeline. The stage receives
two numbers back and never sees a label.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from chakravyuh.jaal.build import NormalisedInputError
from chakravyuh.jaal.cluster import DEFAULT_THRESHOLD
from chakravyuh.jaal.stage import InputPathError, build_run, resolve_in, resolve_out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chakravyuh.jaal",
        description="Fuse the chain and network layers into one graph, and cluster addresses.",
    )
    parser.add_argument(
        "--in",
        dest="normalised",
        type=Path,
        required=True,
        help=(
            "the normalised/ directory written by SETU, which must sit under data/. A stage that "
            "can be pointed anywhere is a stage that can be pointed at the answer key."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out",
        type=Path,
        required=True,
        help="run directory under data/generated/. graph/ is written inside it.",
    )
    parser.add_argument(
        "--threshold",
        dest="threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=(
            f"confidence cut for the derived cluster view, default {DEFAULT_THRESHOLD}. The edge "
            "table is unaffected: raising this drops clusters, never SAME_OWNER edges."
        ),
    )
    parser.add_argument(
        "--score",
        dest="score",
        action="store_true",
        help=(
            "score the clustering against this run's answer key via chakravyuh.eval.metrics, "
            "which locates and writes its own report and returns two numbers. Without the answer "
            "key present this warns and the graph is written anyway."
        ),
    )
    return parser


def _score(out: Path, threshold: float) -> None:
    """Hand the predicted clusters to eval and print what comes back. Two numbers, no members."""
    from chakravyuh.eval import metrics

    graph = out / "graph"
    clusters = pl.read_parquet(graph / "clusters.parquet")
    nodes = pl.read_parquet(graph / "nodes.parquet")
    universe = [
        node.removeprefix("addr:")
        for node in nodes.filter(pl.col("kind") == "address")["node_id"].to_list()
    ]
    heuristics = sorted({name for used in clusters["heuristics_used"].to_list() for name in used})
    score = metrics.score_clusters(
        out.name, clusters["addresses"].to_list(), universe, threshold, heuristics
    )
    if score is None:
        sys.stderr.write(
            "jaal: no answer key for this run, so the clustering was not scored. The graph is "
            "written and complete.\n"
        )
        return
    sys.stderr.write(
        f"jaal: pairwise precision {score.pair_precision:.4f}, recall {score.pair_recall:.4f} "
        f"over {score.n_predicted_clusters} clusters\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        out = resolve_out(args.out)
        meta = build_run(resolve_in(args.normalised), out, args.threshold)
    except (InputPathError, NormalisedInputError) as exc:
        # stderr, not stdout: T20 bans print and the contract reserves stdout for peek.py.
        sys.stderr.write(f"jaal: {exc}\n")
        return 2
    if args.score:
        _score(out, args.threshold)
    sys.stderr.write(f"jaal: graph built, meta at {meta}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
