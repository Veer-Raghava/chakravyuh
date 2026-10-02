"""Frozen graph-summary trees and static typed graphs on predeclared paired P2P worlds."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import polars as pl
import torch
from common import digest, log, ranking
from observed_world import generate
from relational_summary_controls import feature_matrix
from sklearn.linear_model import LogisticRegression
from temporal_hetero_benchmark import Model, build_graphs, dataset, rollout
from typed_graph_transfer import calibrate
from xgboost import XGBClassifier

OUT = Path("research/bitcoin/results/rich-relation-transfer")
ROOTS = {
    "cioh": Path("research/bitcoin/results/temporal-hetero-extended"),
    "address": Path("research/bitcoin/results/address-atomic-benchmark"),
}
NAMES = ("typed_static", "xgboost_distribution_features", "lightgbm_distribution_features")
SEEDS = (70017, 80029)


def raw_scores(graphs, models):
    with torch.no_grad():
        neural, _ = rollout(models["typed_static"], graphs)
    matrix = feature_matrix(graphs)
    return {
        "typed_static": neural,
        "xgboost_distribution_features": models["xgboost_distribution_features"].predict_proba(
            matrix
        )[:, 1],
        "lightgbm_distribution_features": models["lightgbm_distribution_features"].predict(matrix),
    }


def scored_frame(graphs, p):
    return pl.concat(
        [
            g["subjects"].with_columns(
                pl.lit(g["window_id"]).alias("window_id"), pl.lit(g["phase"]).alias("phase")
            )
            for g in graphs
        ]
    ).with_columns(pl.Series("score", p))


def controller_frames(graphs, frame, labels, active):
    blocks = []
    for g in graphs[7:]:
        mapping = g["members"].join(labels, on="address").select("subject_id", "owner").unique()
        positive = active.filter(pl.col("first_seen_us").is_between(g["start_us"], g["end_us"]))[
            "owner"
        ].unique()
        current = frame.filter(pl.col("window_id") == g["window_id"]).select("subject_id", "score")
        blocks.append(
            mapping.join(current, on="subject_id")
            .group_by("owner")
            .agg(pl.col("score").max())
            .with_columns(
                pl.col("owner").is_in(positive).cast(pl.Int8).alias("y"),
                pl.lit(g["window_id"]).alias("window_id"),
            )
        )
    return pl.concat(blocks)


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    estimators, calibrators, scalers, errors = {}, {}, {}, {}
    for mode, parent in ROOTS.items():
        graphs, _ = dataset(partition_mode="address" if mode == "address" else "heuristic")
        scalers[mode] = joblib.load(parent / "scalers.joblib")
        saved = torch.load(parent / "typed_static.pt", weights_only=True)
        neural = Model({"subject": 23, "transaction": 6, "ip": 9}, True, False)
        neural.load_state_dict(saved["state_dict"])
        neural.eval()
        tree_root = Path("research/bitcoin/results/relational-summary-controls") / mode
        tree = XGBClassifier()
        tree.load_model(tree_root / "xgboost_distribution_features.json")
        estimators[mode] = {
            "typed_static": neural,
            "xgboost_distribution_features": tree,
            "lightgbm_distribution_features": lgb.Booster(
                model_file=str(tree_root / "lightgbm_distribution_features.txt"),
                params={"num_threads": 4},
            ),
        }
        raw = raw_scores(graphs, estimators[mode])
        y = np.concatenate([g["y"].numpy() for g in graphs])
        cal = np.concatenate([np.repeat(g["phase"] == "cal", len(g["y"])) for g in graphs])
        calibrators[mode], errors[mode] = {}, {}
        for name, p in raw.items():
            clipped = np.clip(p, 1e-6, 1 - 1e-6)
            mapping = LogisticRegression(max_iter=1000, random_state=42).fit(
                np.log(clipped[cal] / (1 - clipped[cal]))[:, None], y[cal]
            )
            calibrators[mode][name] = mapping
            reference = parent if name == "typed_static" else tree_root
            expected = pl.read_parquet(reference / f"{name}-scores.parquet")["score"].to_numpy()
            error = float(np.max(np.abs(calibrate(p, mapping) - expected)))
            assert error == 0, (mode, name, error)
            errors[mode][name] = error
    log(
        "rich_relation_transfer_preregistered",
        seeds=list(SEEDS),
        replay_errors=errors,
        primary="cioh-xgboost_distribution_features, selected by common-controller validation",
        no_transfer_fit=True,
    )
    joblib.dump({"scalers": scalers, "calibrators": calibrators}, OUT / "frozen-transforms.joblib")
    worlds = []
    for seed in SEEDS:
        started = time.perf_counter()
        tx, addresses, ann, peers, labels, active, metadata = generate(seed)
        frames, outputs = {}, {}
        for mode in ROOTS:
            graphs, _ = build_graphs(
                tx,
                addresses,
                ann,
                peers,
                labels,
                active,
                scalers[mode],
                partition_mode="address" if mode == "address" else "heuristic",
            )
            for name, raw in raw_scores(graphs, estimators[mode]).items():
                p = calibrate(raw, calibrators[mode][name])
                frame = scored_frame(graphs, p)
                test = frame.filter(pl.col("phase") == "test")
                outputs.setdefault(mode, {})[name] = {
                    "subject_window": ranking(test["y"].to_numpy(), test["score"].to_numpy())
                }
                test.write_parquet(OUT / f"seed{seed}-{mode}-{name}.parquet", compression="zstd")
                frames[mode, name] = controller_frames(graphs, frame, labels, active)
        common = (
            frames["cioh", "typed_static"]
            .select("owner", "window_id", "y")
            .join(
                frames["address", "typed_static"].select("owner", "window_id"),
                on=["owner", "window_id"],
            )
        )
        for (mode, name), frame in frames.items():
            aligned = frame.join(common.select("owner", "window_id"), on=["owner", "window_id"])
            assert aligned.height == common.height
            unique = aligned.group_by("owner").agg(pl.col("score").max(), pl.col("y").max())
            outputs[mode][name].update(
                controller_window=ranking(aligned["y"].to_numpy(), aligned["score"].to_numpy()),
                unique_controller=ranking(unique["y"].to_numpy(), unique["score"].to_numpy()),
            )
            aligned.write_parquet(
                OUT / f"seed{seed}-{mode}-{name}-controllers.parquet", compression="zstd"
            )
        world = {**metadata, "models": outputs, "seconds": time.perf_counter() - started}
        (OUT / f"seed{seed}.json").write_text(json.dumps(world, indent=2, sort_keys=True) + "\n")
        worlds.append(world)
        log("rich_relation_transfer_world_complete", seed=seed, no_transfer_fit=True)
    report = {
        "worlds": worlds,
        "canonical_replay_errors": errors,
        "seconds": time.perf_counter() - begin,
        "source_sha256": digest(__file__),
        "limitations": [
            "New seeds, same simulator family; no real Bitcoin generalization claim.",
            "Models/transforms frozen; labels used only for research evaluation projection.",
            "Controller universe is common intersection; identity keys unavailable in production.",
            "Max scores are not calibrated controller probabilities; no confident-answer policy.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
