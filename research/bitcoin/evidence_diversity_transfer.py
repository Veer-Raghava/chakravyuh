"""Frozen canonical diversity policies on saved independent-world address scores."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

import joblib
import polars as pl
from common import digest, log
from evidence_diversity import select
from observed_world import generate
from temporal_hetero_benchmark import build_graphs


def main():
    out = Path("research/bitcoin/results/evidence-diversity-transfer")
    out.mkdir(parents=True, exist_ok=False)
    parent = Path("research/bitcoin/results/rich-relation-transfer")
    policies = json.loads(
        Path("research/bitcoin/results/evidence-diversity/report.json").read_text()
    )
    # Reload the original fit-only base scalers. No fitting on either world.
    scalers = joblib.load(Path("research/bitcoin/results/address-atomic-benchmark/scalers.joblib"))
    worlds = []
    log(
        "evidence_diversity_transfer_preregistered",
        seeds=[70017, 80029],
        policy="canonical validation selection, no transfer selection",
        consumed_score_worlds=True,
    )
    for seed in (70017, 80029):
        start = time.perf_counter()
        tx, addresses, ann, peers, labels, active, metadata = generate(seed)
        expected = json.loads((parent / f"seed{seed}.json").read_text())
        assert metadata["observed_txid_sha256"] == expected["observed_txid_sha256"]
        graphs, _ = build_graphs(
            tx, addresses, ann, peers, labels, active, scalers, partition_mode="address"
        )
        rows = []
        for name in ("typed_static", "xgboost_distribution_features"):
            policy = policies["results"][name]["validation_selected_policy"]
            overlap = {
                "score_only": None,
                "jaccard_050": 0.5,
                "jaccard_025": 0.25,
                "disjoint": 0.0,
            }[policy]
            frame = pl.read_parquet(parent / f"seed{seed}-address-{name}.parquet")
            for g in graphs:
                if g["phase"] != "test":
                    continue
                ids = g["subjects"]["subject_id"].to_list()
                supports = defaultdict(set)
                for si, ti in g["edges"]["funds"].T.tolist():
                    supports[ids[si]].add(ti)
                for ti, si in g["edges"]["receives"].T.tolist():
                    supports[ids[si]].add(ti)
                block = (
                    frame.filter(pl.col("window_id") == g["window_id"])
                    .sort(["score", "subject_id"], descending=[True, False])
                    .head(2000)
                )
                candidates = list(block.select("subject_id", "score").iter_rows())
                for method, cutoff in [("score_only", None), (policy, overlap)]:
                    selected = select(candidates, supports, overlap=cutoff)
                    evaluated = (
                        block.filter(pl.col("subject_id").is_in(selected))
                        .with_columns(
                            pl.col("subject_id").str.strip_prefix("addr:").alias("address")
                        )
                        .join(labels, on="address")
                    )
                    assert evaluated.height == len(selected)
                    rows.append(
                        dict(
                            model=name,
                            window=g["window_id"],
                            policy=method,
                            returned=len(selected),
                            positive_addresses=int(evaluated["y"].sum()),
                            distinct_controllers=evaluated["owner"].n_unique(),
                            distinct_positive_controllers=evaluated.filter(pl.col("y") == 1)[
                                "owner"
                            ].n_unique(),
                        )
                    )
        worlds.append(dict(**metadata, windows=rows, seconds=time.perf_counter() - start))
        (out / f"seed{seed}.json").write_text(
            json.dumps(worlds[-1], indent=2, sort_keys=True) + "\n"
        )
        log("evidence_diversity_transfer_world_complete", seed=seed)
    report = dict(
        worlds=worlds,
        source_sha256=digest(__file__),
        limitations=[
            "Previously evaluated R39 worlds; policy transfer, not untouched model selection.",
            "Truth attaches after selection; diversity does not verify ownership.",
            "Same simulator family; per-window counts may repeat controllers across windows.",
            "Policies share nonempty evidence eligibility and candidate pool.",
        ],
    )
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
