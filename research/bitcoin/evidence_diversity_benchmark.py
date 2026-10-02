"""Preregistered evidence-overlap policies, canonical validation then held-out windows."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

import polars as pl
from common import digest, log
from evidence_diversity import select
from temporal_hetero_benchmark import dataset

OUT = Path("research/bitcoin/results/evidence-diversity")


def main():
    started = time.perf_counter()
    policies = [
        ("score_only", None),
        ("jaccard_050", 0.5),
        ("jaccard_025", 0.25),
        ("disjoint", 0.0),
    ]
    log(
        "evidence_diversity_preregistered",
        policies=policies,
        k=20,
        pool=2000,
        selection="maximum unique positive controllers in validation; tie score-only first",
        primary="typed_static",
        no_truth_in_selection=True,
    )
    graphs, _ = dataset(threshold=1.0, partition_mode="address")
    owners = (
        pl.read_parquet("ground_truth/agency-v2/entities.parquet")
        .select(pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address"))
        .explode("address")
    )
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, parent in [
        ("typed_static", "address-atomic-benchmark"),
        ("xgboost_distribution_features", "relational-summary-controls/address"),
    ]:
        scores = pl.read_parquet(f"research/bitcoin/results/{parent}/{name}-scores.parquet")
        rows = []
        for g in graphs:
            if g["phase"] not in ("val", "test"):
                continue
            ids = g["subjects"]["subject_id"].to_list()
            supports = defaultdict(set)
            for si, ti in g["edges"]["funds"].T.tolist():
                supports[ids[si]].add(ti)
            for ti, si in g["edges"]["receives"].T.tolist():
                supports[ids[si]].add(ti)
            block = (
                scores.filter(pl.col("window_id") == g["window_id"])
                .sort(["score", "subject_id"], descending=[True, False])
                .head(2000)
            )
            candidates = list(block.select("subject_id", "score").iter_rows())
            for policy, overlap in policies:
                selected = select(candidates, supports, overlap=overlap)
                # All answer keys attached after selection, never passed into selector.
                evaluated = (
                    block.filter(pl.col("subject_id").is_in(selected))
                    .with_columns(pl.col("subject_id").str.strip_prefix("addr:").alias("address"))
                    .join(owners, on="address")
                )
                assert evaluated.height == len(selected)
                rows.append(
                    dict(
                        model=name,
                        window=g["window_id"],
                        phase=g["phase"],
                        policy=policy,
                        returned=len(selected),
                        positive_addresses=int(evaluated["y"].sum()),
                        distinct_controllers=evaluated["owner"].n_unique(),
                        distinct_positive_controllers=evaluated.filter(pl.col("y") == 1)[
                            "owner"
                        ].n_unique(),
                    )
                )
        assert len(rows) == 16, "expected one validation and three test windows per policy"
        selected_policy = max(
            policies,
            key=lambda p: sum(
                r["distinct_positive_controllers"]
                for r in rows
                if r["phase"] == "val" and r["policy"] == p[0]
            ),
        )[0]
        results[name] = dict(validation_selected_policy=selected_policy, windows=rows)
    report = dict(
        results=results,
        seconds=time.perf_counter() - started,
        source_sha256=digest(__file__),
        selector_sha256=digest("research/bitcoin/evidence_diversity.py"),
        limitations=[
            "Canonical consumed world; new-world confirmation still required.",
            "Truth measures retrieval after selection; deployment cannot count true controllers.",
            "TX overlap indicates repetitive evidence, not verified common ownership.",
            "Twenty leads per window; sums can repeat a controller across windows.",
            "Candidate pool and nonempty-evidence eligibility fixed across policies.",
            "No claims about precision guarantees or optimal diversification.",
        ],
    )
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log("evidence_diversity_complete", report=str(OUT / "report.json"))


if __name__ == "__main__":
    main()
