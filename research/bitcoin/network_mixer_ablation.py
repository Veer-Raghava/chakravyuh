"""Point-in-time test of P2P announcement features for mixed-input screening."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl

from common import digest, log, ranking, save
from mixer_audit import FEATURES as CHAIN_FEATURES
from mixer_audit import build_rows, decision_metrics, select_cut


NETWORK_FEATURES = [
    "announcements_first_5s", "peers_first_5s", "observers_first_5s",
    "asns_first_5s", "countries_first_5s", "peer_seen_max_first_5s",
    "propagation_spread_first_5s",
]


def run(run_id: str, out: Path):
    start = time.perf_counter()
    root = Path("data/generated") / run_id
    tx_path = root / "normalised/transactions.parquet"
    address_path = root / "normalised/addresses.parquet"
    ann_path = root / "normalised/announcements.parquet"
    truth_path = Path("ground_truth") / run_id / "chain_txs.parquet"
    tx = pl.read_parquet(tx_path)
    addresses = pl.read_parquet(address_path)
    truth = pl.read_parquet(truth_path)
    rows = build_rows(tx, truth, addresses)
    base_ids = [r["txid"] for r in rows]
    y = np.asarray([r["y"] for r in rows], dtype=int)
    base_x = np.asarray([r["x"] for r in rows], dtype=np.float32)
    times = np.asarray([r["time"] for r in rows], dtype=np.int64)

    t0 = tx.select("txid", "first_seen_us")
    ann = pl.read_parquet(ann_path).select(
        "txid", "peer_ip", "observer_ip", "asn", "geo_country", "peer_seen_count", "seen_us"
    ).join(t0, on="txid", how="inner").filter(
        (pl.col("seen_us") >= pl.col("first_seen_us"))
        & (pl.col("seen_us") <= pl.col("first_seen_us") + 5_000_000)
    )
    net = ann.group_by("txid").agg(
        pl.len().alias(NETWORK_FEATURES[0]),
        pl.col("peer_ip").n_unique().alias(NETWORK_FEATURES[1]),
        pl.col("observer_ip").n_unique().alias(NETWORK_FEATURES[2]),
        pl.col("asn").n_unique().alias(NETWORK_FEATURES[3]),
        pl.col("geo_country").n_unique().alias(NETWORK_FEATURES[4]),
        pl.col("peer_seen_count").max().alias(NETWORK_FEATURES[5]),
        (pl.col("seen_us").max() - pl.col("seen_us").min()).alias(NETWORK_FEATURES[6]),
    )
    net_by_tx = {r["txid"]: [r.get(f) or 0 for f in NETWORK_FEATURES]
                 for r in net.iter_rows(named=True)}
    net_x = np.asarray([net_by_tx.get(txid, [0] * len(NETWORK_FEATURES))
                        for txid in base_ids], dtype=np.float32)

    first, last = int(times.min()), int(times.max())
    c1, c2 = int(first + .6 * (last - first)), int(first + .8 * (last - first))
    fit, val, test = times < c1, (times >= c1) & (times < c2), times >= c2
    results = {}
    for name, x, feature_names in (
        ("chain_only", base_x, CHAIN_FEATURES),
        ("chain_plus_network_5s", np.column_stack((base_x, net_x)),
         CHAIN_FEATURES + NETWORK_FEATURES),
    ):
        train = lgb.Dataset(x[fit], label=y[fit], feature_name=feature_names)
        model = lgb.train({
            "objective": "binary", "verbosity": -1, "num_threads": 4, "seed": 42,
            "num_leaves": 15, "min_data_in_leaf": 50, "learning_rate": .05,
            "scale_pos_weight": float((y[fit] == 0).sum() / max((y[fit] == 1).sum(), 1)),
        }, train, num_boost_round=120)
        pred = model.predict(x, num_threads=4)
        cut = select_cut(y[val], pred[val])
        results[name] = {
            "validation": ranking(y[val], pred[val]),
            "test": ranking(y[test], pred[test]),
            "validation_precision_target_cut": cut,
            "test_at_validation_cut": decision_metrics(
                y[test], (pred[test] >= cut).astype(int)
            ) if cut is not None else None,
            "feature_importance_gain": dict(sorted(
                zip(feature_names,
                    map(float, model.feature_importance(importance_type="gain")),
                    strict=True), key=lambda item: item[1], reverse=True)),
        }

    result = {
        "run": run_id,
        "target": "more than one synthetic input owner; not protocol-labeled CoinJoin",
        "network_protocol": "only announcement events in [first_seen, first_seen + 5 seconds] are used",
        "split_us": [c1, c2],
        "rows": {"fit": int(fit.sum()), "validation": int(val.sum()), "test": int(test.sum())},
        "network_feature_coverage": {
            "transactions_with_any_announcement_in_5s": int((net_x[:, 0] > 0).sum()),
            "transactions_total": len(base_ids),
        },
        "network_features": NETWORK_FEATURES,
        "models": results,
        "hashes": {str(p): digest(p) for p in [tx_path, address_path, ann_path, truth_path]},
        "elapsed_seconds": time.perf_counter() - start,
        "limitations": [
            "Single synthetic seed; no real Bitcoin propagation ground truth.",
            "Five-second post-first-seen aggregation is a bounded latency snapshot, not instantaneous detection.",
            "Synthetic observer placement and peer behavior may couple to labels or simplify real propagation.",
            "Target is any multiple-owner input spend, not a specific collaborative protocol.",
            "Class-weighted scores are not calibrated probabilities.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    save(out / "network-mixer-ablation.json", result)
    log("jaal_network_mixer_ablation_complete", run=run_id, out=str(out),
        seconds=result["elapsed_seconds"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="agency-v2")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.run, args.out)
