"""Frozen learned-link partition transfer to independent full-size in-memory chains."""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
from common import Partition, digest, log, partition_metrics
from jaal_lab import candidates
from jaal_seed_transfer import frame_from_run

from chakravyuh.jaal import cluster
from chakravyuh.mayajaal import adversary, chain, config
from chakravyuh.setu import normalise


def observable_shape(frame):
    change = normalise._change_index(frame)
    return frame.join(change, on="txid", how="left").with_columns(
        pl.col("output_amounts")
        .map_elements(lambda xs: len(set(xs)) < len(xs), return_dtype=pl.Boolean)
        .alias("has_equal_outputs"),
        pl.when((pl.col("n_candidates") == 1) & (pl.col("n_out") >= 2))
        .then(pl.col("candidate_index"))
        .otherwise(-1)
        .cast(pl.Int32)
        .alias("change_index"),
    )


def main():
    model_path = Path("research/bitcoin/results/canonical/change-lightgbm.txt")
    reference_path = Path("research/bitcoin/results/canonical/jaal-results.json")
    baseline = json.loads(reference_path.read_text())
    cutoff = baseline["models"]["lightgbm"]["threshold"]
    model = lgb.Booster(model_file=str(model_path))
    worlds = []
    for seed in (1337, 2026, 9001):
        started = time.perf_counter()
        cfg = config.load(
            Path("data/generated/agency-v2/config.effective.json"),
            seed=seed,
            n_txs=24000,
            anchor=Path("."),
        )
        adv = adversary.Adversary(cfg=cfg, rng=random.Random(seed + 1))
        generated = chain.generate(cfg, random.Random(seed), adv.plan)
        tx, addresses, owners = frame_from_run(generated)
        tx = observable_shape(tx)
        records, _ = candidates(tx, addresses, owners)
        x = np.asarray([r["x"] for r in records], dtype=np.float32)
        scores = model.predict(x, num_threads=4)
        selected = {}
        for score, row in zip(scores, records, strict=True):
            if not row["eligible"] or score < cutoff:
                continue
            if row["txid"] not in selected or score > selected[row["txid"]][0]:
                selected[row["txid"]] = (score, row)
        mi = [
            (a.removeprefix("addr:"), b.removeprefix("addr:"))
            for a, b in cluster.common_input_edges(tx).select("src", "dst").rows()
        ]
        change = [
            (a.removeprefix("addr:"), b.removeprefix("addr:"))
            for a, b in cluster.change_edges(tx).select("src", "dst").rows()
        ]
        learned = [(r["src"], r["dst"]) for _, r in selected.values()]
        observed = set(tx["input_addresses"].explode().drop_nulls().to_list()) | set(
            tx["output_addresses"].explode().drop_nulls().to_list()
        )
        output = {}
        for name, links, cap in [
            ("singleton", [], None),
            ("cioh", mi, None),
            ("cioh_weak_change", mi + change, None),
            ("cioh_learned_change", mi + learned, None),
            ("cioh_learned_cap128", mi + learned, 128),
            ("learned_only", learned, None),
        ]:
            p = Partition(observed)
            for a, b in links:
                p.merge(a, b, cap)
            output[name] = {
                **partition_metrics(p.groups(), owners, observed),
                "rejected_merges": p.rejected,
                "proposal_count": len(links),
                "proposal_precision": sum(owners.get(a) == owners.get(b) for a, b in links)
                / len(links)
                if links
                else None,
            }
        worlds.append(
            {
                "seed": seed,
                "observed_addresses": len(observed),
                "tx_rows": tx.height,
                "seconds": time.perf_counter() - started,
                "partitions": output,
            }
        )
        log("jaal_partition_transfer_world_complete", seed=seed, production_changes=False)
    out = Path("research/bitcoin/results/jaal-partition-transfer.json")
    report = {
        "frozen_threshold": cutoff,
        "worlds": worlds,
        "hashes": {str(p): digest(p) for p in [model_path, reference_path, Path(__file__)]},
        "limitations": [
            "same generator family; seed robustness only",
            "complete chain observed, no network-capture censoring in these partition trials",
            "offline final-capture partitions; do not interpret as pre-event training partitions",
            "model and threshold frozen from agency-v2 early fit/validation",
            "same payment request/configuration, block-clock realizations vary by seed",
        ],
    }
    out.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    log("jaal_partition_transfer_complete", output=str(out), production_changes=False)


if __name__ == "__main__":
    main()
