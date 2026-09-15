"""`python -m chakravyuh.shastra --in data/generated/<run>/normalised --out data/generated/<run>`.

Labels and scoring live here and nowhere else in the stage. `chakravyuh.eval` is imported by this
file alone, so `stage.py` stays a pure read of two directories under `data/` and the one place the
pipeline touches the eval package is a file that is not itself part of the pipeline.

The run id used to find the answer key is derived from `--in`, not from `--out`. The answer key
belongs to the capture, so an estimator reading `_run/normalised` must train on `_run`'s labels no
matter where its predictions are written. That is also what makes the determinism gate meaningful:
`make verify-s06` runs this twice with one input and two output directories, and a run id taken
from `--out` would silently give the second run no labels and a different answer.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from chakravyuh.shastra.stage import (
    InputPathError,
    build_run,
    resolve_in,
    resolve_out,
    settings,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chakravyuh.shastra",
        description="Estimate which announcing peer originated each transaction.",
    )
    parser.add_argument(
        "--in",
        dest="normalised",
        type=Path,
        required=True,
        help=(
            "the normalised/ directory written by SETU, whose sibling graph/ must exist. Must sit "
            "under data/: a stage that can be pointed anywhere can be pointed at the answer key."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out",
        type=Path,
        required=True,
        help="run directory under data/generated/. signals/ is written inside it.",
    )
    parser.add_argument(
        "--score",
        dest="score",
        action="store_true",
        help=(
            "score every estimator in signals/ against this run's answer key via "
            "chakravyuh.eval.metrics, which locates and writes its own report and returns numbers "
            "only. Without the answer key present this warns and signals/ is written anyway."
        ),
    )
    return parser


def _labels(run_id: str, train_fraction: float) -> tuple[pl.DataFrame | None, int | None]:
    """Open the origin door. Returns the training-window labels and the boundary, or (None, None).

    None rather than an exception when the answer key is absent, because Law 2 rule 6 requires
    inference to complete with the answer key moved away. The stage then falls back to the
    strongest label-free rule and records a warning.
    """
    from chakravyuh.eval import labels as door

    found = door.origin_labels(run_id, train_fraction)
    if found is None:
        return None, None
    return found.frame, found.boundary_us


def _score(run_id: str, train_fraction: float, observer_fraction: float) -> None:
    """Hand the run id to eval and report what comes back. Numbers, never a label."""
    from chakravyuh.eval import metrics

    scores = metrics.score_origin(
        run_id,
        train_fraction=train_fraction,
        observer_fraction=observer_fraction,
        params={"train_fraction": train_fraction},
    )
    if scores is None:
        sys.stderr.write(
            "shastra: no answer key for this run, so nothing was scored. signals/ is written and "
            "complete.\n"
        )
        return
    for name in sorted(scores):
        score = scores[name]
        sys.stderr.write(
            f"shastra: {name} top1 {score.top1:.4f} top3 {score.top3:.4f} "
            f"abstained {score.n_abstained}\n"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        normalised = resolve_in(args.normalised)
        out = resolve_out(args.out)
    except InputPathError as exc:
        # stderr, not stdout: T20 bans print and the contract reserves stdout for peek.py.
        sys.stderr.write(f"shastra: {exc}\n")
        return 2

    source_run = normalised.parent.name
    config = settings(normalised.parent)
    frame, boundary = _labels(source_run, config.train_fraction)
    try:
        meta = build_run(normalised, out, labels=frame, boundary_us=boundary)
    except InputPathError as exc:
        sys.stderr.write(f"shastra: {exc}\n")
        return 2

    if args.score:
        if out.name != source_run:
            # A measurement filed under one run id, scored against another run's truth, is a
            # number nobody can trace. Refuse rather than write it.
            sys.stderr.write(
                f"shastra: --score needs --in and --out to name one run, got {source_run} and "
                f"{out.name}. signals/ is written; re-run with matching directories to score.\n"
            )
            return 2
        _score(source_run, config.train_fraction, config.observer_fraction)
    sys.stderr.write(f"shastra: signals written, meta at {meta}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
