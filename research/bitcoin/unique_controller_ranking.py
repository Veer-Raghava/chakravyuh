"""Distinct-controller audit, with explicit address-alias inflation counts (truth diagnostic)."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from common import digest, log, ranking

ROOT = Path("research/bitcoin/results/relational-controller-comparison")


def main():
    frames = {path.stem: pl.read_parquet(path) for path in ROOT.glob("*.parquet")}
    first = frames["cioh-mlp"].select("owner", "window_id", "y")
    second = frames["address-mlp"].select("owner", "window_id")
    common = first.join(second, on=["owner", "window_id"])
    metrics = {}
    for name, frame in frames.items():
        aligned = frame.join(common.select("owner", "window_id"), on=["owner", "window_id"])
        block = (
            aligned.filter(pl.col("phase") == "test")
            .group_by("owner")
            .agg(pl.col("score").max(), pl.col("y").max())
            .sort("owner")
        )
        assert block.height == block["owner"].n_unique()
        metrics[name] = ranking(block["y"].to_numpy(), block["score"].to_numpy())
    labels = (
        pl.read_parquet("ground_truth/agency-v2/entities.parquet")
        .select(pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address"))
        .explode("address")
    )
    aliases = {}
    for name in (
        "typed_static",
        "typed_temporal_gru",
        "temporal_embeddings_xgboost",
        "xgboost_distribution_features",
    ):
        parent = Path("research/bitcoin/results/address-atomic-benchmark")
        if "distribution_features" in name:
            parent = Path("research/bitcoin/results/relational-summary-controls/address")
        raw = pl.read_parquet(parent / f"{name}-scores.parquet").filter(pl.col("phase") == "test")
        top = raw.sort(["score", "subject_id"], descending=[True, False]).head(20)
        owners = top.with_columns(pl.col("subject_id").str.strip_prefix("addr:").alias("address"))
        owners = owners.join(labels, on="address")
        assert owners.height == 20
        aliases[name] = {
            "raw_positive_address_windows": int(top["y"].sum()),
            "distinct_controllers_among_twenty": owners["owner"].n_unique(),
            "distinct_positive_controllers_among_twenty": owners.filter(pl.col("y") == 1)[
                "owner"
            ].n_unique(),
        }
    selection = json.loads((ROOT / "report.json").read_text())["controller_validation_selected"]
    report = {
        "distinct_controller_test": metrics,
        "address_alias_diagnostics": aliases,
        "prior_validation_selected": "-".join(selection),
        "source_sha256": digest(__file__),
        "limitations": [
            "Hidden owner deduplication is evaluation-only, unavailable to the investigator.",
            "Max across subject/window scores is not a calibrated controller probability.",
            "Positive means any observed campaign involvement in the held-out period.",
            "Same consumed world; no selection using the newly computed test metrics.",
        ],
    }
    path = Path("research/bitcoin/results/unique-controller-ranking.json")
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log("unique_controller_ranking_complete", selected=report["prior_validation_selected"])


if __name__ == "__main__":
    main()
