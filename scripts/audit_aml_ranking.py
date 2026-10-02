"""Read-only audit of a saved BUDDHI run; never refit or overwrite its evaluation.

Run with the project interpreter, --run agency-v2 and --out <new-json-path>.
Outputs aggregate diagnostics only; refuses to replace an existing file.
This reproduces the repository's holdout subject/majority-label policy, including
its full-capture cluster membership limitation. It does not repair that policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import polars as pl
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
)

from chakravyuh.buddhi.features import MODEL_FEATURES, subjects
from chakravyuh.eval.metrics import _auc
from chakravyuh.mayajaal.writers import RUN_ID


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="agency-v2")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output already exists; choose a new audit path")
    if not RUN_ID.fullmatch(args.run):
        parser.error("invalid run id")
    root = Path("data/generated") / args.run
    report_path = Path("measurements") / args.run / "model_report.json"
    report = json.loads(report_path.read_text())
    boundary = report["split"]["boundary_us"]
    scores = pl.read_parquet(root / "scores/wallet_scores.parquet")
    addresses = pl.read_parquet(root / "normalised/addresses.parquet")
    clusters = pl.read_parquet(root / "graph/clusters.parquet")
    truth_path = Path("ground_truth") / args.run / "entities.parquet"
    truth = (
        pl.read_parquet(truth_path)
        .select("is_illicit", "addresses")
        .explode("addresses")
        .rename({"addresses": "address"})
        .drop_nulls("address")
        .unique("address")
    )
    members = subjects(clusters, addresses).join(
        addresses.select("address", "first_seen_us"), on="address"
    )
    first = members.group_by("subject_id").agg(pl.col("first_seen_us").min().alias("first"))
    labels = (
        members.filter(pl.col("first_seen_us") >= boundary)
        .join(truth, on="address")
        .group_by("subject_id")
        .agg((pl.col("is_illicit").sum() * 2 > pl.len()).cast(pl.Int64).alias("y"))
    )
    frame = (
        scores.join(first.filter(pl.col("first") >= boundary), on="subject_id")
        .join(labels, on="subject_id")
        .sort(["risk_score", "subject_id"], descending=[True, False])
    )
    y, p = frame["y"].to_numpy(), frame["risk_score"].to_numpy()
    if len(y) < 50 or not 0 < y.sum() < len(y):
        parser.error("audit needs at least 50 holdout rows and both label classes")
    predicted = (p >= 0.5).astype(int)
    metrics = {
        "n_scored": len(y),
        "n_illicit": int(y.sum()),
        "illicit_prevalence": float(y.mean()),
        "repository_ap": _auc(y.tolist(), p.tolist(), True),
        "threshold_grouped_ap": float(average_precision_score(y, p)),
        "precision_at_20": float(y[:20].mean()),
        "precision_at_50": float(y[:50].mean()),
        "recall_at_50": float(y[:50].sum() / y.sum()),
        "precision_at_threshold_0_5": float(precision_score(y, predicted, zero_division=0)),
        "recall_at_threshold_0_5": float(recall_score(y, predicted, zero_division=0)),
        "f1_at_threshold_0_5": float(f1_score(y, predicted, zero_division=0)),
        "brier_score": float(brier_score_loss(y, p)),
        "constant_prevalence_brier": float(y.mean() * (1 - y.mean())),
    }
    sources = [
        report_path,
        truth_path,
        root / "scores/wallet_scores.parquet",
        root / "normalised/addresses.parquet",
        root / "graph/clusters.parquet",
    ]
    payload = json.dumps(
        {
            "run_id": args.run,
            "policy": "saved holdout subjects; majority illicit over holdout members; ties licit",
            "caveat": (
                "Diagnostic replay, not a repaired prospective evaluation or UI queue metric."
            ),
            "boundary_us": boundary,
            "feature_names": list(MODEL_FEATURES),
            "source_sha256": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
            },
            "metrics": metrics,
            "ap_tie_counterexample": {
                "y": [1, 1, 0],
                "scores": [0.5, 0.5, 0.5],
                "repository_ap": _auc([1, 1, 0], [0.5, 0.5, 0.5], True),
                "threshold_grouped_ap": float(average_precision_score([1, 1, 0], [0.5] * 3)),
            },
        },
        indent=2,
        sort_keys=True,
    )
    with args.out.open("x") as output:
        output.write(payload + "\n")


if __name__ == "__main__":
    main()
