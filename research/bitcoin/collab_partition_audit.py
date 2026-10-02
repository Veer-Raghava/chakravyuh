"""Forward-time partition test for learned collaborative-spend screening.

Uses mixer-audit's early-time LightGBM scores, a validation-selected threshold, and
test-period common-input edges only. Ground truth is opened solely to score this experiment.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import polars as pl

from chakravyuh.jaal import mixer
from common import digest, log, partition_metrics, save


class ConstrainedPartition:
    def __init__(self, nodes, cannot):
        self.parent = {n: n for n in nodes}
        self.members = {n: {n} for n in nodes}
        self.cannot = cannot
        self.rejected = 0

    def find(self, node):
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def merge(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if len(self.members[ra]) < len(self.members[rb]):
            ra, rb = rb, ra
        large, small = self.members[ra], self.members[rb]
        if any(self.cannot.get(node, set()) & large for node in small):
            self.rejected += 1
            return
        self.parent[rb] = ra
        large.update(small)
        del self.members[rb]

    def groups(self):
        return list(self.members.values())


def run(run_id, score_dir, out):
    start = time.perf_counter()
    root = Path("data/generated") / run_id
    tx_path = root / "normalised/transactions.parquet"
    truth_path = Path("ground_truth") / run_id / "entities.parquet"
    labels_path = Path("ground_truth") / run_id / "chain_txs.parquet"
    score_path = score_dir / "mixer-scores.parquet"
    audit = json.loads((score_dir / "mixer-audit.json").read_text())
    cut = audit["models"]["lightgbm_balanced"]["validation_precision_target_cut"]
    if cut is None:
        raise RuntimeError("no validation-selected model threshold")
    test_start = audit["split_us"][1]

    txs = pl.read_parquet(tx_path).filter(pl.col("first_seen_us") >= test_start)
    scores = pl.read_parquet(score_path).filter(pl.col("time_us") >= test_start)
    score_by_tx = dict(scores.select("txid", "lgbm_score").iter_rows())
    gt_tx = {
        txid: input_owners
        for txid, input_owners in pl.read_parquet(labels_path)
        .select("txid", "input_entity_ids").iter_rows()
    }
    owner_by_address = {
        address: row["entity_id"]
        for row in pl.read_parquet(truth_path).iter_rows(named=True)
        for address in row["addresses"]
    }

    raw_edges, shaped_edges = [], []
    cannot = defaultdict(set)
    test_addresses = set()
    true_mixed_count = 0
    scored_tx = 0
    for tx in txs.sort("first_seen_us", "txid").iter_rows(named=True):
        if tx["is_coinbase"]:
            continue
        inputs = sorted(set(tx["input_addresses"]))
        if len(inputs) < 2:
            continue
        test_addresses.update(inputs)
        score = float(score_by_tx.get(tx["txid"], 0.0))
        flagged = score >= cut
        mixer_shape = bool(tx["has_equal_outputs"] and tx["n_out"] >= 3
                           and tx["n_in"] >= 2)
        scored_tx += 1
        input_owners = gt_tx.get(tx["txid"], [])
        true_mixed = len(set(input_owners)) > 1
        true_mixed_count += int(true_mixed)
        for b in inputs[1:]:
            a = inputs[0]
            raw_edges.append((tx["first_seen_us"], a, b))
            if not mixer_shape:
                shaped_edges.append((tx["first_seen_us"], a, b))
        if flagged:
            # A predicted collaborative spend is a cannot-link among its distinct inputs.
            for i, a in enumerate(inputs):
                for b in inputs[i + 1:]:
                    cannot[a].add(b)
                    cannot[b].add(a)

    ml_edges = []
    for tx in txs.sort("first_seen_us", "txid").iter_rows(named=True):
        if tx["is_coinbase"] or tx["n_in"] < 2:
            continue
        if float(score_by_tx.get(tx["txid"], 0.0)) >= cut:
            continue
        inputs = sorted(set(tx["input_addresses"]))
        ml_edges.extend((tx["first_seen_us"], inputs[0], b) for b in inputs[1:])

    owners = owner_by_address
    eligible = test_addresses & owners.keys()
    baseline = {}
    for name, edges in (("all_common_input", raw_edges),
                        ("equal_output_rule_filter", shaped_edges),
                        ("learned_filter", ml_edges)):
        p = ConstrainedPartition(eligible, {})
        for _, a, b in edges:
            if a in p.parent and b in p.parent:
                p.merge(a, b)
        baseline[name] = {"metrics": partition_metrics(p.groups(), owners, eligible),
                          "rejected_merges": p.rejected, "edge_events": len(edges)}

    constrained = ConstrainedPartition(eligible, cannot)
    for _, a, b in ml_edges:
        if a in constrained.parent and b in constrained.parent:
            constrained.merge(a, b)
    baseline["learned_filter_plus_cannot_link"] = {
        "metrics": partition_metrics(constrained.groups(), owners, eligible),
        "rejected_merges": constrained.rejected, "edge_events": len(ml_edges),
        "cannot_link_pairs": sum(map(len, cannot.values())) // 2,
    }

    result = {
        "run": run_id,
        "protocol": "training first 60% and threshold chosen on 60-80%; only >=80% transaction-time input edges clustered",
        "target": "synthetic input-owner heterogeneity; not a CoinJoin ground-truth label",
        "validation_threshold": cut, "test_start_us": test_start,
        "test_transactions_with_multi_input": scored_tx,
        "test_true_mixed_transactions": true_mixed_count,
        "test_addresses": len(eligible), "policies": baseline,
        "hashes": {str(p): digest(p) for p in [tx_path, truth_path, labels_path, score_path]},
        "elapsed_seconds": time.perf_counter() - start,
        "limitations": [
            "Generator-specific labels and behavior; no real-chain external validation.",
            "Input-pair cannot-links are an approximation; collaborative use does not identify a protocol.",
            "Only test-window edges are used, not a cumulative historical address graph.",
            "Greedy constrained union is order-dependent and needs comparison to signed correlation clustering.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    save(out / "collab-partition-audit.json", result)
    log("jaal_collab_partition_audit_complete", run=run_id, out=str(out),
        seconds=result["elapsed_seconds"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="agency-v2")
    parser.add_argument("--scores", type=Path,
                        default=Path("research/bitcoin/results/mixer-audit-v3"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.run, args.scores, args.out)
