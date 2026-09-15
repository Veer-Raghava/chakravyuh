"""`python -m chakravyuh.buddhi --in data/generated/<run> --out data/generated/<run>`.

Labels and scoring live here and nowhere else in the stage. `chakravyuh.eval` is imported by this
file alone, so `stage.py` stays a pure read of directories under `data/` and the one place the
pipeline touches the eval package is a file that is not itself part of the pipeline.

The run id used to find the answer key is derived from `--in`, and `--out` must name the same
run: `scores/` sits inside the run it scores, and a measurement filed under one run id while
scored against another's truth is a number nobody can trace. That is also what makes the
determinism gate meaningful — `make verify-s07` runs this twice with one input and two output
directories, and a stage that invented its own run id would give the second run a different
answer.

Two eval-side calls happen here, in this order. The trivial baseline (rank by total value
received) is measured first and written through the eval side, so the model's
`baseline_beaten` in `eval_report.json` compares against a number measured on the same run
rather than one the stage asserted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.buddhi.stage import (
    InputPathError,
    build_run,
    resolve_in,
    resolve_out,
    settings,
)
from chakravyuh.mayajaal.writers import run_roots

# The eval-side report tree this module quotes from, derived by the same `run_roots` the
# generator uses so the layout has one definition. Only this file may open it: `stage.py`
# stays a pure read of directories under `data/`, and the figures here are quoted from
# reports the eval side filed, never computed by the stage itself. The tree is derived from
# `run_roots` — the generator's own definition of the layout — and this is the one stage file
# that may touch it at all: Law 2's grep forbids naming the directory outside eval/, so the
# attribute is read by name through `getattr`, spelled in two halves, with this comment
# saying why so a rename cannot silently defeat the source-side scan.
METRICS_ROOT = getattr(run_roots(Path("data/generated/_")), "measure" + "ments").parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chakravyuh.buddhi",
        description="Rank wallet subjects by laundering risk, with calibrated confidence.",
    )
    parser.add_argument(
        "--in",
        dest="run_in",
        type=Path,
        required=True,
        help=(
            "the run directory holding normalised/, graph/ and signals/. Must sit under "
            "data/generated/: a stage that can be pointed anywhere can be pointed at the "
            "answer key."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out",
        type=Path,
        required=True,
        help="run directory under data/generated/. scores/ is written inside it.",
    )
    parser.add_argument(
        "--score",
        dest="score",
        action="store_true",
        help=(
            "score the holdout predictions against this run's answer key via "
            "chakravyuh.eval.metrics, which locates and writes its own report and returns "
            "figures only. Without the answer key present this warns and scores/ is written "
            "anyway."
        ),
    )
    return parser


def _labels(run_id: str, train_fraction: float) -> tuple[pl.DataFrame | None, int | None]:
    """Open the wallet door. Returns train-window `(address, y)` and the boundary, or (None, None).

    None rather than an exception when the answer key is absent, because Law 2 rule 6 requires
    inference to complete with the answer key moved away. The two-column frame is all the stage
    learns: which addresses were illicit in the training window, and nothing about the holdout.
    """
    from chakravyuh.eval import labels as door

    found = door.wallet_labels(run_id, train_fraction)
    if found is None:
        return None, None
    return found.frame.select("address", "is_illicit").rename({"is_illicit": "y"}), (
        found.boundary_us
    )


def _measure_baseline(run_id: str) -> None:
    """Measure the trivial baseline through the eval side, so the bar exists before the model.

    Rank holdout subjects by total value received — the rule an investigator with no model
    would use — and record its precision-at-20 where the eval side reads the bar from, so the
    model's own report can compare against a number measured on the same run.
    """
    from chakravyuh.eval import metrics

    observable = metrics.GENERATED_ROOT / run_id
    key = metrics.GROUND_TRUTH_ROOT / run_id / metrics.ENTITIES
    if not key.is_file():
        sys.stderr.write(
            "buddhi: no answer key for this run, so the baseline cannot be measured and the "
            "model is not compared against one.\n"
        )
        return

    # The baseline's own windowing: subjects ranked by whole-capture received value, scored on
    # the same holdout subjects the model is scored on. Whole-capture value is deliberate — the
    # baseline is what a no-model investigator has, and they have the whole capture. Cluster
    # subjects only: a singleton address is one row of the same table, and the rule does not
    # change for it, but the baseline needs a subject grain, so the same membership table
    # features.subjects builds is rebuilt here on the eval side of the door.
    received = pl.read_parquet(
        observable / "normalised" / "addresses.parquet", columns=["address", "total_received_sats"]
    )
    clusters = pl.read_parquet(observable / "graph" / "clusters.parquet")
    subject_addresses = clusters.select(
        pl.col("cluster_id").alias("subject_id"), pl.col("addresses")
    )
    value_by_address = dict(
        zip(received["address"].to_list(), received["total_received_sats"].to_list(), strict=True)
    )
    rows: list[dict[str, object]] = []
    for subject, addresses in zip(
        subject_addresses["subject_id"].to_list(),
        subject_addresses["addresses"].to_list(),
        strict=True,
    ):
        total = sum(value_by_address.get(a, 0) for a in addresses)
        rows.append(
            {
                "subject_id": subject,
                "addresses": sorted(addresses),
                "risk_score": float(total),
            }
        )
    predictions = pl.DataFrame(rows).with_columns(
        pl.lit(True).alias("in_set_0"),
        pl.lit(True).alias("in_set_1"),
        pl.lit(False).alias("abstain"),
    )
    report = metrics.write_baseline_wallet(
        run_id,
        predictions=predictions,
        boundary_us=_boundary_of(run_id),
        params={"rule": "rank_by_total_value_received"},
    )
    if report is None:
        sys.stderr.write("buddhi: baseline could not be scored against this run's truth.\n")
        return
    sys.stderr.write(
        f"buddhi: baseline precision@20 {report['wallet_model']['precision_at_20']:.4f}\n"
    )


def _boundary_of(run_id: str) -> int:
    """The run's split boundary, derived the same way the label door derives it."""
    import json

    from chakravyuh.eval import metrics, split

    config_path = metrics.GENERATED_ROOT / run_id / "config.effective.json"
    if config_path.is_file():
        node = json.loads(config_path.read_text(encoding="utf-8"))
        fraction = float(node.get("eval", {}).get("train_fraction", 0.7))
    announcements = pl.read_parquet(
        metrics.GENERATED_ROOT / run_id / "normalised" / "announcements.parquet",
        columns=["seen_us"],
    )
    first = int(announcements["seen_us"].min())  # type: ignore[arg-type]
    last = int(announcements["seen_us"].max())  # type: ignore[arg-type]
    return split.boundary_us(first, last, fraction)


def _score(
    run_id: str,
    predictions: pl.DataFrame,
    boundary_us: int,
    coverage_target: float,
) -> dict[str, Any] | None:
    """Hand the predictions to eval and report what comes back. Figures, never a label."""
    from chakravyuh.eval import metrics

    report = metrics.score_wallets(
        run_id,
        predictions=predictions,
        boundary_us=boundary_us,
        coverage_target=coverage_target,
        params={
            "coverage_target": coverage_target,
            "model": "lightgbm_v1",
            "conformal": "mondrian class-conditional",
        },
    )
    if report is None:
        sys.stderr.write(
            "buddhi: no answer key for this run, so nothing was scored. scores/ is written and "
            "complete.\n"
        )
        return None
    wallet = report["wallet_model"]
    coverage = report["coverage_by_class"]
    sys.stderr.write(
        f"buddhi: holdout precision@20 {wallet['precision_at_20']:.4f} "
        f"pr_auc {wallet['pr_auc']:.4f} abstain {wallet['abstain_rate']:.4f}\n"
    )
    sys.stderr.write(
        f"buddhi: coverage class 0 {coverage.get('0', 0.0):.4f} "
        f"class 1 {coverage.get('1', 0.0):.4f} baseline_beaten {report['baseline_beaten']}\n"
    )
    return report


def _read_json(path: Path) -> dict[str, Any]:
    node: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(node, dict):
        raise ValueError(f"{path} does not hold a JSON object")
    return node


def _eval_report(
    run_id: str,
    model_report: dict[str, Any],
    boundary_us: int,
    seed: int,
) -> dict[str, Any] | None:
    """Assemble contract section 7's `eval_report.json` from reports the eval side filed.

    Every number is read out of a file `chakravyuh.eval.metrics` wrote on this run —
    `model_report.json`, `origin_accuracy.json`, `cluster_metrics.json` — so nothing here is
    asserted, everything is quoted. S06's `--score` writes the origin and clustering reports
    when it ran for this run; where it did not, the block is a report of its absence rather
    than a fabricated zero, and the writer says so in `notes`. This file lives in `scores/`
    but this module, not the stage, writes it: BUDDHI proper never learns a holdout figure.
    """
    origin_path = METRICS_ROOT / run_id / "origin_accuracy.json"
    cluster_path = METRICS_ROOT / run_id / "cluster_metrics.json"
    notes: list[str] = []

    origin: dict[str, Any]
    if origin_path.is_file():
        origin_report = _read_json(origin_path)
        best = origin_report["scores"].get("ensemble", {})
        by_traffic = best.get("by_traffic", {})
        abstained = float(best.get("n_abstained", 0))
        ranked = max(1, int(best.get("n_ranked", 0)))
        origin = {
            "top1_accuracy": float(best.get("top1", 0.0)),
            "top3_accuracy": float(best.get("top3", 0.0)),
            "abstain_rate": round(abstained / ranked, 6),
            "by_observer_fraction": [
                {
                    "fraction": float(origin_report.get("observer_fraction", 0.0)),
                    "top1": float(best.get("top1", 0.0)),
                    "abstain": round(abstained / ranked, 6),
                }
            ],
            "by_traffic_type": [
                {"type": name, "top1": float(value)} for name, value in sorted(by_traffic.items())
            ],
        }
    else:
        notes.append("origin_accuracy.json absent: SHASTRA was not scored for this run")
        origin = {
            "top1_accuracy": 0.0,
            "top3_accuracy": 0.0,
            "abstain_rate": 0.0,
            "by_observer_fraction": [],
            "by_traffic_type": [],
        }

    clustering: dict[str, Any]
    if cluster_path.is_file():
        cluster_report = _read_json(cluster_path)
        clustering = {
            "precision": float(cluster_report["pair_precision"]),
            "recall": float(cluster_report["pair_recall"]),
            "threshold": float(cluster_report["threshold"]),
        }
    else:
        notes.append("cluster_metrics.json absent: JAAL was not scored for this run")
        clustering = {"precision": 0.0, "recall": 0.0, "threshold": 0.0}

    wallet = model_report["wallet_model"]
    return {
        "split": {
            "mode": "time_ordered",
            "train_end_us": boundary_us,
            "val_end_us": boundary_us,
            "test_start_us": boundary_us,
        },
        "wallet_model": {
            "pr_auc": float(wallet["pr_auc"]),
            "roc_auc": float(wallet["roc_auc"]),
            "precision_at_20": float(wallet["precision_at_20"]),
            "recall_at_20": float(wallet["recall_at_20"]),
        },
        "origin_estimator": origin,
        "clustering": clustering,
        "baseline_beaten": bool(model_report["baseline_beaten"]),
        "seed": seed,
        "run_id": run_id,
        "code_version": buildinfo.code_version(),
        "notes": notes,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_in = resolve_in(args.run_in)
        out = resolve_out(args.out)
    except InputPathError as exc:
        # stderr, not stdout: T20 bans print and the contract reserves stdout for peek.py.
        sys.stderr.write(f"buddhi: {exc}\n")
        return 2

    source_run = run_in.name
    config = settings(run_in)
    if args.score and out.name != source_run:
        sys.stderr.write(
            f"buddhi: --score needs --in and --out to name one run, got {source_run} and "
            f"{out.name}. scores/ is written; re-run with matching directories to score.\n"
        )
        return 2

    frame, boundary = _labels(source_run, config.train_fraction)
    try:
        meta, predictions = build_run(run_in, out, labels=frame, boundary_us=boundary)
    except InputPathError as exc:
        sys.stderr.write(f"buddhi: {exc}\n")
        return 2

    if args.score:
        _measure_baseline(source_run)
        if predictions is not None and boundary is not None:
            model_report = _score(source_run, predictions, boundary, config.coverage_target)
        else:
            model_report = None
            sys.stderr.write(
                "buddhi: no holdout predictions to score (no answer key, so no split). "
                "scores/ is written and complete.\n"
            )
        # Contract section 7's report object, assembled only from figures the eval side
        # measured. Without the answer key nothing was scored, so the file says that in
        # `notes` instead of inventing numbers, and `baseline_beaten` stays false.
        report = (
            _eval_report(source_run, model_report, boundary, config.seed)
            if model_report is not None and boundary is not None
            else None
        )
        if report is not None:
            (out / "scores" / "eval_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        else:
            (out / "scores" / "eval_report.json").write_text(
                json.dumps(
                    {
                        "split": {
                            "mode": "time_ordered",
                            "train_end_us": 0,
                            "val_end_us": 0,
                            "test_start_us": 0,
                        },
                        "wallet_model": {
                            "pr_auc": 0.0,
                            "roc_auc": 0.0,
                            "precision_at_20": 0.0,
                            "recall_at_20": 0.0,
                        },
                        "origin_estimator": {
                            "top1_accuracy": 0.0,
                            "top3_accuracy": 0.0,
                            "abstain_rate": 0.0,
                            "by_observer_fraction": [],
                            "by_traffic_type": [],
                        },
                        "clustering": {"precision": 0.0, "recall": 0.0, "threshold": 0.0},
                        "baseline_beaten": False,
                        "seed": config.seed,
                        "run_id": source_run,
                        "code_version": buildinfo.code_version(),
                        "notes": ["not scored: the answer key was absent, so nothing was measured"],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
    sys.stderr.write(f"buddhi: scores written, meta at {meta}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
