"""Strong graph-feature trees: two-hop typed context distributions, never neighbor labels."""

from __future__ import annotations

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import temporal_hetero_benchmark as graph
import torch
from common import digest, log
from xgboost import XGBClassifier

OUT = Path("research/bitcoin/results/relational-summary-controls")


def summaries(context, edges, size):
    """Degree and per-dimension mean/std/min/max; empty neighborhoods have zero context."""
    source, target = edges.numpy()
    values = context.numpy()[source].astype(np.float64)
    count = np.bincount(target, minlength=size)
    total = np.zeros((size, context.shape[1]))
    squares = np.zeros_like(total)
    minimum = np.full_like(total, np.inf)
    maximum = np.full_like(total, -np.inf)
    np.add.at(total, target, values)
    np.add.at(squares, target, values**2)
    np.minimum.at(minimum, target, values)
    np.maximum.at(maximum, target, values)
    denominator = np.maximum(count[:, None], 1)
    mean = total / denominator
    std = np.sqrt(np.maximum(squares / denominator - mean**2, 0))
    minimum[count == 0] = 0
    maximum[count == 0] = 0
    return np.column_stack([np.log1p(count), mean, std, minimum, maximum]).astype(np.float32)


def feature_matrix(graphs):
    blocks = []
    for g in graphs:
        tx_context = torch.cat(
            [
                g["transaction"],
                graph.pool(g["ip"], g["edges"]["announces"], len(g["transaction"])),
                graph.pool(g["subject"], g["edges"]["funds"], len(g["transaction"])),
            ],
            1,
        )
        blocks.append(
            np.column_stack(
                [
                    g["subject"].numpy(),
                    summaries(tx_context, g["edges"]["receives"], len(g["y"])),
                    summaries(tx_context, g["edges"]["funds"].flip(0), len(g["y"])),
                ]
            )
        )
    return np.concatenate(blocks)


def main():
    begin = time.perf_counter()
    torch.set_num_threads(4)
    report = {}
    for mode in ("cioh", "address"):
        output = OUT / mode
        output.mkdir(parents=True, exist_ok=True)
        graph.OUT = output
        graphs, _ = graph.dataset(partition_mode="address" if mode == "address" else "heuristic")
        x = feature_matrix(graphs)
        assert x.shape[1] == 329 and np.isfinite(x).all()
        y = np.concatenate([g["y"].numpy() for g in graphs])
        fit = np.concatenate([np.repeat(g["phase"] == "fit", len(g["y"])) for g in graphs])
        results = {}
        tree = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            min_child_weight=10,
            subsample=0.9,
            colsample_bytree=0.9,
            n_jobs=4,
            tree_method="hist",
            random_state=42,
        )
        tree.fit(x[fit], y[fit])
        tree.save_model(output / "xgboost_distribution_features.json")
        results["xgboost_distribution_features"] = graph.assess(
            graphs, tree.predict_proba(x)[:, 1], "xgboost_distribution_features"
        )
        params = {
            "objective": "binary",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 40,
            "lambda_l2": 1.0,
            "num_threads": 4,
            "seed": 42,
            "deterministic": True,
            "force_col_wise": True,
            "verbosity": -1,
        }
        model = lgb.train(params, lgb.Dataset(x[fit], label=y[fit]), num_boost_round=300)
        model.save_model(str(output / "lightgbm_distribution_features.txt"))
        results["lightgbm_distribution_features"] = graph.assess(
            graphs, model.predict(x), "lightgbm_distribution_features"
        )
        report[mode] = results
    result = {
        "models": report,
        "features": 329,
        "seconds": time.perf_counter() - begin,
        "source_sha256": digest(__file__),
        "limitations": [
            "Consumed synthetic world; supplementary strong baseline, not new confirmation.",
            "Two-hop context includes self contributions and collaborator addresses.",
            "All statistics label-free; float64 accumulation, fit-only base type scaling.",
            "Moments/extrema summaries omit complete neighbor identities and ordering.",
            "Controller/workload projection required before production comparison.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    log("relational_summary_controls_complete", output=str(OUT / "report.json"))


if __name__ == "__main__":
    main()
