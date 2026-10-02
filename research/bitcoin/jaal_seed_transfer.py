"""In-memory independent-seed transfer test for the learned change-output scorer.

Builds one second MAYAJAAL chain without exporting it to disk, then evaluates the frozen
agency-v2 train-time LightGBM on its last chronological block. Hidden ownership labels are
used only to form the research target and metrics.
"""
from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl

from chakravyuh.mayajaal import adversary, chain, config
from common import digest, ranking, save
from jaal_lab import FEATURES, candidates


def frame_from_run(run):
    owners, scripts = {}, {}
    for entity in run.population.entities:
        for address, script in zip(entity.addresses, entity.address_kinds, strict=True):
            owners[address] = entity.entity_id
            scripts[address] = script

    tx_rows = []
    first_seen = {}
    for tx in run.txs:
        for address in tx.output_addresses:
            first_seen[address] = min(first_seen.get(address, tx.time_us), tx.time_us)
        tx_rows.append({
            "txid": tx.txid, "first_seen_us": tx.time_us,
            "input_addresses": list(tx.input_addresses),
            "output_addresses": list(tx.output_addresses),
            "input_amounts": list(tx.input_sats),
            "output_amounts": list(tx.output_sats),
            "n_in": len(tx.input_addresses), "n_out": len(tx.output_addresses),
            "fee_sats": tx.fee_sats, "is_coinbase": tx.is_coinbase,
        })
    transactions = pl.DataFrame(tx_rows)
    address_rows = [
        {"address": a, "script_type": s, "first_seen_us": first_seen.get(a, 0)}
        for a, s in scripts.items()
    ]
    addresses = pl.DataFrame(address_rows)
    return transactions, addresses, owners


def run(out: Path, new_seed: int, n_txs: int):
    started = time.perf_counter()
    cfg_path = Path("data/generated/agency-v2/config.effective.json")
    cfg_sha = digest(cfg_path)
    cfg = config.load(cfg_path, seed=new_seed, n_txs=n_txs, anchor=Path("."))
    adv = adversary.Adversary(cfg=cfg, rng=random.Random(cfg.seed + 1))
    generated = chain.generate(cfg, random.Random(cfg.seed), adv.plan)
    adv.apply_typologies(generated.population)
    new_tx, new_addresses, new_owners = frame_from_run(generated)

    train_tx = pl.read_parquet("data/generated/agency-v2/normalised/transactions.parquet")
    train_addresses = pl.read_parquet("data/generated/agency-v2/normalised/addresses.parquet")
    train_truth = pl.read_parquet("ground_truth/agency-v2/entities.parquet")
    train_owners = {
        address: row["entity_id"]
        for row in train_truth.iter_rows(named=True)
        for address in row["addresses"]
    }
    train_rows, _ = candidates(train_tx, train_addresses, train_owners)
    times = np.asarray([r["time"] for r in train_rows], dtype=np.int64)
    x = np.asarray([r["x"] for r in train_rows], dtype=np.float32)
    y = np.asarray([r["y"] for r in train_rows], dtype=np.int8)
    first, last = int(times.min()), int(times.max())
    c1 = int(first + .6 * (last - first))
    c2 = int(first + .8 * (last - first))
    fit = times < c1
    model = lgb.train({
        "objective": "binary", "verbosity": -1, "num_threads": 4, "seed": 42,
        "num_leaves": 31, "min_data_in_leaf": 30, "learning_rate": .05,
    }, lgb.Dataset(x[fit], label=y[fit], feature_name=FEATURES), num_boost_round=180)

    new_rows, _ = candidates(new_tx, new_addresses, new_owners)
    new_x = np.asarray([r["x"] for r in new_rows], dtype=np.float32)
    new_y = np.asarray([r["y"] for r in new_rows], dtype=np.int8)
    new_times = np.asarray([r["time"] for r in new_rows], dtype=np.int64)
    forward = new_times >= c2
    score = model.predict(new_x[forward], num_threads=4)
    labels = new_y[forward]

    # The baseline same-seed test is scored with the same in-memory fit for an exact comparison.
    base_test = times >= c2
    base_score = model.predict(x[base_test], num_threads=4)
    base_y = y[base_test]
    result = {
        "baseline_run": "agency-v2", "transfer_seed": new_seed,
        "n_payments_requested": n_txs,
        "generated_tx_rows": len(generated.txs),
        "fit_cut_us": c1, "forward_test_start_us": c2,
        "features": FEATURES,
        "same_seed_forward_test": ranking(base_y, base_score),
        "independent_seed_forward_test": ranking(labels, score),
        "train_target_prevalence": float(y[fit].mean()),
        "new_seed_forward_target_prevalence": float(labels.mean()),
        "generator_config_sha256": cfg_sha,
        "training_inputs": {
            "transactions_sha256": digest("data/generated/agency-v2/normalised/transactions.parquet"),
            "addresses_sha256": digest("data/generated/agency-v2/normalised/addresses.parquet"),
            "entity_labels_sha256": digest("ground_truth/agency-v2/entities.parquet"),
        },
        "elapsed_seconds": time.perf_counter() - started,
        "limitations": [
            "Same generator/configuration family; tests seed robustness, not real-chain transfer.",
            "Temporal split is based on agency-v2 time cut applied to second seed.",
            "All addresses in second seed are generated in memory; no full dataset was persisted.",
            "Labels are synthetic and directly name the sender/input/output controller.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    save(out / "seed-transfer.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--txs", type=int, default=24000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.out, args.seed, args.txs)
    print(result["elapsed_seconds"], result["same_seed_forward_test"],
          result["independent_seed_forward_test"])
