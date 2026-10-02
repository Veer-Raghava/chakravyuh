"""Frozen detector sensitivity to weak ownership merges; truth only evaluates controllers."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import polars as pl
import torch
from buddhi_world_transfer import activity
from common import digest, log, ranking
from temporal_hetero_benchmark import Model, build_graphs
from typed_graph_transfer import NAMES, calibrate, score
from xgboost import XGBClassifier

from chakravyuh.buddhi import snapshot
from chakravyuh.jaal import provenance

ROOT = Path("research/bitcoin/results/temporal-hetero-extended")
OUT = Path("research/bitcoin/results/partition-error-propagation")


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    normalised = Path("data/generated/agency-v2/normalised")
    tx, addresses, ann, peers = [
        pl.read_parquet(normalised / f"{name}.parquet")
        for name in ("transactions", "addresses", "announcements", "peers")
    ]
    labels = (
        pl.read_parquet("ground_truth/agency-v2/entities.parquet")
        .select(pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address"))
        .explode("address")
    )
    act = activity(
        tx,
        labels,
        pl.read_parquet("ground_truth/agency-v2/campaigns.parquet").select("entity_ids", "txids"),
    )
    scalers = joblib.load(ROOT / "scalers.joblib")
    calibrators = joblib.load(ROOT / "transfer/frozen-policies.joblib")["calibrators"]
    models, trees = {}, {}
    for name in NAMES:
        if "xgboost" in name:
            trees[name] = XGBClassifier()
            trees[name].load_model(ROOT / f"{name}.json")
        else:
            saved = torch.load(ROOT / f"{name}.pt", weights_only=True)
            models[name] = Model(
                {"subject": 23, "transaction": 6, "ip": 9}, saved["graph"], saved["temporal"]
            )
            models[name].load_state_dict(saved["state_dict"])
            models[name].eval()
    ledger = provenance.ownership_evidence(tx)
    output = {}
    for threshold in (0.3, 0.2):
        graphs, _ = build_graphs(
            tx, addresses, ann, peers, labels, act, scalers=scalers, threshold=threshold
        )
        predictions = score(graphs, models, trees)
        partition = []
        for graph in graphs[7:]:
            s = snapshot.build(
                tx,
                addresses,
                ledger,
                start_us=graph["start_us"],
                end_us=graph["end_us"],
                threshold=threshold,
            )
            mapping = s.members.join(labels, on="address").select("subject_id", "owner").unique()
            positive = act.filter(
                pl.col("first_seen_us").is_between(graph["start_us"], graph["end_us"])
            )["owner"].unique()
            partition.append((graph, mapping, positive))
        metrics = {}
        for name, raw in predictions.items():
            p = calibrate(raw, calibrators[name])
            cursor = sum(len(g["y"]) for g in graphs[:7])
            frames = []
            for graph, mapping, positive in partition:
                n = len(graph["y"])
                scores = (
                    graph["subjects"]
                    .select("subject_id")
                    .with_columns(pl.Series("score", p[cursor : cursor + n]))
                )
                # The same inference score is assigned to every represented controller.
                # Hidden owners never change inference; false merges contaminate negatives.
                frames.append(
                    mapping.join(scores, on="subject_id")
                    .group_by("owner")
                    .agg(pl.col("score").max())
                    .with_columns(
                        pl.col("owner").is_in(positive).cast(pl.Int8).alias("y"),
                        pl.lit(graph["window_id"]).alias("window_id"),
                    )
                )
                cursor += n
            frame = pl.concat(frames)
            path = OUT / f"threshold-{threshold}-{name}.parquet"
            frame.write_parquet(path, compression="zstd")
            metrics[name] = {
                "controller_window": ranking(frame["y"].to_numpy(), frame["score"].to_numpy()),
                "score_sha256": digest(path),
            }
        output[str(threshold)] = metrics
    report = {
        "models": output,
        "seconds": time.perf_counter() - begin,
        "source_sha256": digest(__file__),
        "limitations": [
            "Consumed canonical world; diagnostic, not independent confirmation.",
            "All weights/scalers/calibrators frozen from CIOH training.",
            "True owners used only for diagnostic projection and labels.",
            "Threshold change is an input-distribution shift, not retraining comparison.",
            "Controller-window decisions still repeat owners across windows.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log("partition_error_propagation_complete", output=str(OUT / "report.json"))


if __name__ == "__main__":
    main()
