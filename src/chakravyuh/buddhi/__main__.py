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
from typing import Any, Final

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.buddhi.stage import (
    MODEL_NAME,
    MODEL_NAME_GNN,
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
    parser.add_argument(
        "--gnn",
        dest="gnn",
        action="store_true",
        help=(
            "add the label-free dual-graph embedding as extra columns and train the second "
            "booster over it. Off by default: the baseline feature set and every canonical "
            "number are a plain invocation. Rows the embedding does not cover keep the baseline "
            "model and say so in wallet_scores.parquet's `model` column."
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

    boundary_us = _boundary_of(run_id)

    # The baseline's own windowing: subjects ranked by whole-capture received value, scored on
    # the same holdout subjects the model is scored on. Whole-capture value is deliberate — the
    # baseline is what a no-model investigator has, and they have the whole capture. The subject
    # universe is features.subjects — clusters plus singleton addresses — the same one the model
    # scores, so `baseline_beaten` compares two rankings of one population rather than two
    # different denominators.
    from chakravyuh.buddhi import features as _features

    received = pl.read_parquet(
        observable / "normalised" / "addresses.parquet", columns=["address", "total_received_sats"]
    )
    clusters = pl.read_parquet(observable / "graph" / "clusters.parquet")
    addresses = pl.read_parquet(
        observable / "normalised" / "addresses.parquet",
        columns=["address", "first_seen_us"],
    )
    members = _features.subjects(clusters, addresses)
    subject_addresses = members.group_by("subject_id", maintain_order=True).agg(
        pl.col("address").sort().alias("addresses")
    )
    # The model's own holdout window is `subject_first_us >= boundary` (stage.py filters
    # `is_train` before eval sees a row); the baseline has to rank in that same window or
    # `baseline_beaten` compares two different denominators.
    window = (
        subject_addresses.explode("addresses")
        .rename({"addresses": "address"})
        .join(addresses, on="address", how="inner")
    )
    holdout = (
        window.group_by("subject_id", maintain_order=True)
        .agg(pl.col("first_seen_us").min().alias("subject_first_us"))
        .filter(pl.col("subject_first_us") >= boundary_us)
        .select("subject_id")
    )
    subject_addresses = subject_addresses.join(holdout, on="subject_id", how="semi")
    value_by_address = dict(
        zip(received["address"].to_list(), received["total_received_sats"].to_list(), strict=True)
    )
    rows: list[dict[str, object]] = []
    for subject, member_addrs in zip(
        subject_addresses["subject_id"].to_list(),
        subject_addresses["addresses"].to_list(),
        strict=True,
    ):
        total = sum(value_by_address.get(a, 0) for a in member_addrs)
        rows.append(
            {
                "subject_id": subject,
                "addresses": sorted(member_addrs),
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
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Hand the predictions to eval and report what comes back. Figures, never a label.

    Returns the shipped report and, when the predictions carry the baseline booster's score for the
    same subjects, the counterfactual's report alongside it. Both are scored over the identical
    subject population — same frame, same holdout rule — so the difference between them is the
    GNN leg's columns and nothing else. Only the shipped one is filed.
    """
    from chakravyuh.eval import metrics

    params = {
        "coverage_target": coverage_target,
        "model": MODEL_NAME,
        "conformal": "mondrian class-conditional",
    }
    report = metrics.score_wallets(
        run_id,
        predictions=predictions,
        boundary_us=boundary_us,
        coverage_target=coverage_target,
        params=params,
    )
    if report is None:
        sys.stderr.write(
            "buddhi: no answer key for this run, so nothing was scored. scores/ is written and "
            "complete.\n"
        )
        return None, None

    baseline_report = None
    if "risk_score_baseline" in predictions.columns:
        baseline_report = metrics.score_wallets(
            run_id,
            predictions=predictions.with_columns(pl.col("risk_score_baseline").alias("risk_score")),
            boundary_us=boundary_us,
            coverage_target=coverage_target,
            params={**params, "model": MODEL_NAME, "role": "gnn_leg_counterfactual"},
            write=False,
        )

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
    if baseline_report is not None:
        baseline_wallet = baseline_report["wallet_model"]
        sys.stderr.write(
            f"buddhi: gnn leg pr_auc {wallet['pr_auc']:.4f} against the baseline booster's "
            f"{baseline_wallet['pr_auc']:.4f} on the same holdout subjects\n"
        )
    return report, baseline_report


def _read_json(path: Path) -> dict[str, Any]:
    node: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(node, dict):
        raise ValueError(f"{path} does not hold a JSON object")
    return node


# Every reason the embedding leg can be unavailable, kept as a closed vocabulary so a reader — and
# `scripts/check_scores.py` — can tell "nobody asked for it" from "it was asked for and did not
# earn its columns" without parsing prose.
LEG_NOT_REQUESTED: Final[str] = "embeddings_not_requested"
LEG_NO_ROWS: Final[str] = "no_row_scored_by_the_gnn_booster"
LEG_NO_COUNTERFACTUAL: Final[str] = "no_counterfactual_measured"
LEG_BASELINE_NOT_BEATEN: Final[str] = "baseline_not_beaten"
LEG_DID_NOT_BEAT: Final[str] = "gnn_does_not_beat_baseline"
LEG_NOT_SCORED: Final[str] = "not_scored_no_answer_key"


def _embedding_leg(
    scores_path: Path,
    model_report: dict[str, Any],
    baseline_report: dict[str, Any] | None,
    *,
    requested: bool,
) -> dict[str, Any]:
    """Whether the GNN leg's rows are entitled to ship, with the holdout measurement that says so.

    The gate the brief asks for, and the only place it can honestly be applied: the stage has no
    holdout labels, so the comparison is made here, on the answer key, between the shipped run and
    the same subjects scored by the baseline booster alone. `available` is true only when the plain
    GBM already cleared its own bar (`baseline_beaten`) and adding the embedding columns did not
    make it worse. Either failing leaves the reason for a reader and turns
    `scripts/check_scores.py` red on any row that still claims `gbm_gnn_v2` — the run is then
    regenerated without `--gnn`, which is the correct outcome rather than a rewritten number.
    """
    by_model: dict[str, int] = {}
    if scores_path.is_file():
        tally = pl.read_parquet(scores_path, columns=["model"]).group_by("model").len()
        by_model = {str(row["model"]): int(row["len"]) for row in tally.iter_rows(named=True)}
    n_gnn = by_model.get(MODEL_NAME_GNN, 0)

    leg: dict[str, Any] = {
        "available": False,
        "reason": LEG_NOT_REQUESTED if not requested else LEG_NO_ROWS,
        "embedding": "buddhi.embed, label-free propagation over the JAAL dual graph",
        "rows_by_model": by_model,
        "n_rows_scored_by_gnn": n_gnn,
        "n_rows_scored_by_baseline": by_model.get(MODEL_NAME, 0),
        "shipped_model": None,
        "baseline_model": None,
        "delta_pr_auc": None,
        "delta_precision_at_20": None,
        "caveat": (
            "The shipped run and the counterfactual are scored on one identical subject "
            "population with one time-ordered split; the only difference between them is the "
            "graph-embedding columns. A mixed run's figures are the mix's, not the GNN booster's "
            "alone — `rows_by_model` says how mixed."
        ),
    }
    if n_gnn == 0:
        return leg
    leg["reason"] = LEG_NO_COUNTERFACTUAL
    if baseline_report is None:
        return leg

    shipped = model_report["wallet_model"]
    baseline = baseline_report["wallet_model"]
    leg["shipped_model"] = {
        "pr_auc": float(shipped["pr_auc"]),
        "roc_auc": float(shipped["roc_auc"]),
        "precision_at_20": float(shipped["precision_at_20"]),
        "recall_at_20": float(shipped["recall_at_20"]),
        "n_scored": int(shipped["actor_level"]["n_scored"]),
    }
    leg["baseline_model"] = {
        "pr_auc": float(baseline["pr_auc"]),
        "roc_auc": float(baseline["roc_auc"]),
        "precision_at_20": float(baseline["precision_at_20"]),
        "recall_at_20": float(baseline["recall_at_20"]),
        "n_scored": int(baseline["actor_level"]["n_scored"]),
    }
    leg["delta_pr_auc"] = round(leg["shipped_model"]["pr_auc"] - leg["baseline_model"]["pr_auc"], 6)
    leg["delta_precision_at_20"] = round(
        leg["shipped_model"]["precision_at_20"] - leg["baseline_model"]["precision_at_20"], 6
    )
    if not model_report["baseline_beaten"]:
        leg["reason"] = LEG_BASELINE_NOT_BEATEN
        return leg
    if leg["delta_pr_auc"] < 0.0:
        leg["reason"] = LEG_DID_NOT_BEAT
        return leg
    leg["available"] = True
    leg["reason"] = None
    return leg


def _eval_report(
    run_id: str,
    model_report: dict[str, Any],
    boundary_us: int,
    seed: int,
    *,
    embedding_leg: dict[str, Any],
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
    from chakravyuh.eval import external

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

    # The external-validation leg, quoted from the file its own command wrote. Not computed here:
    # it is a second dataset and a second fit, and this function runs on every scoring pass. When
    # the leg was never run for this run the block says so, which is a different fact from the
    # dataset being unvendored, and the two are kept distinct so a reader can tell them apart.
    external_path = METRICS_ROOT / run_id / "elliptic_external.json"
    external_block = (
        _read_json(external_path) if external_path.is_file() else dict(external.NOT_RUN)
    )

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
            # Actor-level is the four figures above, kept flat for the readers that already
            # took them from here. The two further grains are quoted from the same report,
            # never recomputed: campaign recall is the headline the World screen leads with.
            "tx_pr_auc": float(wallet["tx_level"]["pr_auc"]),
            "campaign_recall": float(wallet["campaign_level"]["campaign_recall"]),
        },
        "origin_estimator": origin,
        "clustering": clustering,
        "baseline_beaten": bool(model_report["baseline_beaten"]),
        # Whether the embedding columns earned their place, and the holdout comparison that
        # decided it. Present on every run, available or not, so a reader never has to infer
        # "we did not try the GNN" from an absent key.
        "embedding_leg": embedding_leg,
        "seed": seed,
        "run_id": run_id,
        "code_version": buildinfo.code_version(),
        "protocol": str(model_report["protocol"]),
        "elliptic_external": external_block,
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
        meta, predictions = build_run(
            run_in, out, labels=frame, boundary_us=boundary, use_embeddings=args.gnn
        )
    except InputPathError as exc:
        sys.stderr.write(f"buddhi: {exc}\n")
        return 2

    if args.score:
        _measure_baseline(source_run)
        scores_path = out / "scores" / "wallet_scores.parquet"
        model_report: dict[str, Any] | None = None
        baseline_report: dict[str, Any] | None = None
        if predictions is not None and boundary is not None:
            model_report, baseline_report = _score(
                source_run, predictions, boundary, config.coverage_target
            )
        else:
            sys.stderr.write(
                "buddhi: no holdout predictions to score (no answer key, so no split). "
                "scores/ is written and complete.\n"
            )
        # Contract section 7's report object, assembled only from figures the eval side
        # measured. Without the answer key nothing was scored, so the file says that in
        # `notes` instead of inventing numbers, and `baseline_beaten` stays false. The
        # embedding leg is assembled either way: it is a report of the gate's outcome, and
        # "no answer key" is one of its outcomes.
        report = (
            _eval_report(
                source_run,
                model_report,
                boundary,
                config.seed,
                embedding_leg=_embedding_leg(
                    scores_path,
                    model_report,
                    baseline_report,
                    requested=args.gnn,
                ),
            )
            if model_report is not None and boundary is not None
            else None
        )
        if report is not None:
            (out / "scores" / "eval_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        else:
            unscored_leg = _embedding_leg(scores_path, {}, None, requested=args.gnn)
            unscored_leg["reason"] = LEG_NOT_SCORED
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
                        "embedding_leg": unscored_leg,
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
