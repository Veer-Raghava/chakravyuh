"""Exploratory saved-score blend and review-budget analysis; no new training."""

import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/bitcoin/results/ranking-recovery-analysis"
SOURCES = {
    "rich_tree": ROOT
    / "research/bitcoin/results/relational-summary-controls/address"
    / "xgboost_distribution_features-scores.parquet",
    "temporal_gnn": ROOT
    / "research/bitcoin/results/drishti-r47-graph-training/typed_temporal_gru-scores.parquet",
}


def metrics(y, score, ids):
    order = np.lexsort((np.asarray(ids), -score))
    positives = int(y.sum())
    budgets = {}
    for k in (20, 50, 100, 500, 1000):
        n = min(k, len(y))
        hits = int(y[order[:n]].sum())
        budgets[str(k)] = {
            "reviewed": n,
            "hits": hits,
            "precision": hits / n,
            "recall": hits / positives if positives else None,
        }
    return {
        "n": len(y),
        "positives": positives,
        "ap": float(average_precision_score(y, score)) if positives else None,
        "budgets": budgets,
    }


def main():
    # Register the finite candidates/selection rule before examining test scores.
    weights = (0.0, 0.25, 0.5, 0.75, 1.0)
    OUT.mkdir(parents=True, exist_ok=True)
    design = {
        "tree_weights": weights,
        "selection": "validation AP, then validation P@20; candidate order breaks ties",
        "score": "weighted mean of saved calibrated scores; blend is not separately calibrated",
        "units": "address-window decisions, not distinct controllers",
        "status": "exploratory; underlying worlds/test results already consumed",
    }
    (OUT / "design.json").write_text(json.dumps(design, indent=2) + "\n")
    keys = ["subject_id", "window_id"]
    tree = pl.read_parquet(SOURCES["rich_tree"]).rename({"score": "tree_score"})
    gnn = pl.read_parquet(SOURCES["temporal_gnn"]).rename(
        {"score": "gnn_score", "y": "gnn_y", "phase": "gnn_phase"}
    )
    assert tree.unique(subset=keys).height == tree.height
    assert gnn.unique(subset=keys).height == gnn.height
    joined = tree.join(gnn, on=keys, how="inner", validate="1:1")
    assert joined.height == tree.height == gnn.height
    assert (
        joined.filter(
            (pl.col("y") != pl.col("gnn_y")) | (pl.col("phase") != pl.col("gnn_phase"))
        ).height
        == 0
    )
    val = joined.filter(pl.col("phase") == "val")

    def evaluate(frame, w) -> dict:
        return metrics(
            frame["y"].to_numpy(),
            w * frame["tree_score"].to_numpy() + (1 - w) * frame["gnn_score"].to_numpy(),
            frame["subject_id"].to_list(),
        )

    validations = [{"tree_weight": w, "validation": evaluate(val, w)} for w in weights]
    selected = max(
        validations,
        key=lambda x: (x["validation"]["ap"], x["validation"]["budgets"]["20"]["precision"]),
    )["tree_weight"]
    test = joined.filter(pl.col("phase") == "test")
    results = {}
    for name, w in [
        ("rich_tree", 1.0),
        ("temporal_gnn", 0.0),
        ("validation_selected_blend", selected),
    ]:
        results[name] = {
            "tree_weight": w,
            "test": evaluate(test, w),
            "test_by_window": {
                str(wid): evaluate(test.filter(pl.col("window_id") == wid), w)
                for wid in sorted(test["window_id"].unique())
            },
        }
    report = {
        "design": design,
        "validation_candidates": validations,
        "selected_tree_weight": selected,
        "results": results,
        "sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in SOURCES.items()
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "selected_tree_weight": selected,
                "results": {k: v["test"] for k, v in results.items()},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
