"""Atomic versus CIOH model retrieval on common hidden controller-window keys, for audit only."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import polars as pl
from buddhi_world_transfer import activity, windows
from common import digest, log, ranking

from chakravyuh.buddhi import snapshot
from chakravyuh.jaal import provenance

OUT = Path("research/bitcoin/results/address-controller-comparison")
ROOTS = {
    "cioh": Path("research/bitcoin/results/temporal-hetero-extended"),
    "address": Path("research/bitcoin/results/address-atomic-benchmark"),
}
NAMES = (
    "mlp",
    "typed_static",
    "typed_temporal_gru",
    "typed_temporal_shuffled",
    "xgboost_local",
    "xgboost_typed_features",
    "temporal_embeddings_xgboost",
)
KEYS = ["owner", "window_id"]


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    root = Path("data/generated/agency-v2/normalised")
    tx = pl.read_parquet(root / "transactions.parquet")
    addresses = pl.read_parquet(root / "addresses.parquet")
    labels = (
        pl.read_parquet("ground_truth/agency-v2/entities.parquet")
        .select(pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address"))
        .explode("address")
    )
    active = activity(
        tx,
        labels,
        pl.read_parquet("ground_truth/agency-v2/campaigns.parquet").select("entity_ids", "txids"),
    )
    ledger = provenance.ownership_evidence(tx)
    frames, diagnostics = {}, []
    for mode, result_root in ROOTS.items():
        mappings = []
        for window_id, (phase, start, end) in enumerate(windows(tx)):
            if phase not in ("val", "test"):
                continue
            view = snapshot.build(
                tx,
                addresses,
                ledger,
                start_us=start,
                end_us=end,
                threshold=0.3,
                partition_mode="address" if mode == "address" else "heuristic",
            )
            if mode == "address":
                assert view.edges.height == 0
                assert view.members.group_by("subject_id").len()["len"].max() == 1
            mapping = view.members.join(labels, on="address").select("subject_id", "owner").unique()
            positive = active.filter(pl.col("first_seen_us").is_between(start, end))[
                "owner"
            ].unique()
            mappings.append((window_id, phase, mapping, positive))
            diagnostics.append(
                {
                    "mode": mode,
                    "window": window_id,
                    "subjects": view.table.height,
                    "ownership_edges": view.edges.height,
                    "controllers": mapping["owner"].n_unique(),
                }
            )
        for name in NAMES:
            path = result_root / f"{name}-scores.parquet"
            if "distribution_features" in name:
                path = (
                    Path("research/bitcoin/results/relational-summary-controls") / mode / path.name
                )
            saved = pl.read_parquet(path)
            blocks = []
            for window_id, phase, mapping, positive in mappings:
                block = saved.filter(pl.col("window_id") == window_id).select("subject_id", "score")
                joined = mapping.join(block, on="subject_id")
                assert joined["subject_id"].n_unique() == block.height
                blocks.append(
                    joined.group_by("owner")
                    .agg(pl.col("score").max())
                    .with_columns(
                        pl.col("owner").is_in(positive).cast(pl.Int8).alias("y"),
                        pl.lit(window_id).alias("window_id"),
                        pl.lit(phase).alias("phase"),
                    )
                )
            frames[mode, name] = pl.concat(blocks)
            frames[mode, name].write_parquet(OUT / f"{mode}-{name}.parquet", compression="zstd")
    common = (
        frames["cioh", "mlp"]
        .select(*KEYS, "y")
        .join(frames["address", "mlp"].select(*KEYS, pl.col("y").alias("other_y")), on=KEYS)
    )
    assert common.unique(KEYS).height == common.height
    assert common.select(pl.col("y") == pl.col("other_y")).to_series().all()
    metrics = {}
    for (mode, name), frame in frames.items():
        aligned = frame.join(common.select(KEYS), on=KEYS).sort(KEYS)
        assert aligned.height == common.height
        metrics.setdefault(mode, {})[name] = {
            phase: ranking(block["y"].to_numpy(), block["score"].to_numpy())
            for phase in ("val", "test")
            for block in [aligned.filter(pl.col("phase") == phase)]
        }
    selected = max(
        ((mode, name) for mode in ROOTS for name in NAMES),
        key=lambda pair: (
            metrics[pair[0]][pair[1]]["val"]["p_at_20"],
            metrics[pair[0]][pair[1]]["val"]["ap"],
        ),
    )
    report = {
        "models": metrics,
        "controller_validation_selected": list(selected),
        "common_controller_windows": common.height,
        "diagnostics": diagnostics,
        "seconds": time.perf_counter() - begin,
        "source_sha256": digest(__file__),
        "limitations": [
            "Hidden controller projection is diagnostic, not production identity recovery.",
            "Consumed canonical world; controller selection is exploratory protocol refinement.",
            "Common universe conditions on controllers represented by both approaches.",
            "Two trained representations, same split; no superiority claim from raw address P20.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log("address_controller_comparison_complete", selected=list(selected))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-rich", action="store_true")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output
    if args.include_rich:
        NAMES += ("xgboost_distribution_features", "lightgbm_distribution_features")
    main()
