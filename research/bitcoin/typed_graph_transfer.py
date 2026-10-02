"""Frozen graph-model confirmation on predeclared new P2P-world seeds 10007/20011."""

from __future__ import annotations

import argparse
import json
import random
import resource
import time
from pathlib import Path

import joblib
import numpy as np
import polars as pl
import torch
from buddhi_world_transfer import activity
from common import digest, log, ranking
from jaal_partition_transfer import observable_shape
from jaal_seed_transfer import frame_from_run
from sklearn.linear_model import LogisticRegression
from temporal_hetero_benchmark import OUT, Model, build_graphs, dataset, rollout
from xgboost import XGBClassifier

from chakravyuh.mayajaal import adversary, chain, config, network
from chakravyuh.setu import normalise
from chakravyuh.setu.enrich import Enricher

DEST = OUT / "transfer"
SEEDS = (10007, 20011)
NAMES = (
    "mlp",
    "typed_static",
    "typed_temporal_gru",
    "xgboost_local",
    "temporal_embeddings_xgboost",
)


def score(graphs, models, trees):
    results = {}
    embedding = None
    for name in ("mlp", "typed_static", "typed_temporal_gru"):
        with torch.no_grad():
            p, h = rollout(models[name], graphs)
        results[name] = p
        if name == "typed_temporal_gru":
            embedding = h
    local = np.concatenate([g["subject"].numpy() for g in graphs])
    results["xgboost_local"] = trees["xgboost_local"].predict_proba(local)[:, 1]
    results["temporal_embeddings_xgboost"] = trees["temporal_embeddings_xgboost"].predict_proba(
        np.column_stack([local, embedding])
    )[:, 1]
    return results


def calibrate(p, model):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return model.predict_proba(np.log(p / (1 - p))[:, None])[:, 1]


def main():
    begin = time.perf_counter()
    DEST.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    recipe = json.loads((OUT / "report.json").read_text())
    ownership_threshold = recipe.get("ownership_threshold", 0.3)
    # The earlier address experiment excluded all current weights with threshold1.
    # Exact replay below verifies equivalence to the now-explicit address-only API.
    partition_mode = recipe.get(
        "partition_mode", "address" if ownership_threshold == 1.0 else "heuristic"
    )
    graphs, _ = dataset(ownership_threshold, partition_mode)
    scalers = joblib.load(OUT / "scalers.joblib")
    models, trees = {}, {}
    for name in NAMES:
        if "xgboost" in name:
            trees[name] = XGBClassifier()
            trees[name].load_model(OUT / f"{name}.json")
        else:
            saved = torch.load(OUT / f"{name}.pt", weights_only=True)
            m = Model(
                {k: graphs[0][k].shape[1] for k in ("subject", "transaction", "ip")},
                saved["graph"],
                saved["temporal"],
            )
            m.load_state_dict(saved["state_dict"])
            m.eval()
            models[name] = m
    canonical = score(graphs, models, trees)
    phase = np.concatenate([np.repeat(g["phase"], len(g["y"])) for g in graphs])
    y = np.concatenate([g["y"].numpy() for g in graphs])
    cal = phase == "cal"
    calibrators = {}
    thresholds = {}
    replay_errors = {}
    for name, p in canonical.items():
        p = np.clip(p, 1e-6, 1 - 1e-6)
        calibrators[name] = LogisticRegression(max_iter=1000, random_state=42).fit(
            np.log(p[cal] / (1 - p[cal]))[:, None], y[cal]
        )
        calibrated = calibrate(p, calibrators[name])
        saved = pl.read_parquet(OUT / f"{name}-scores.parquet")
        error = float(np.max(np.abs(saved["score"].to_numpy() - calibrated)))
        replay_errors[name] = error
        assert error < 1e-7, (name, error)
        # Freeze maximum validation coverage meeting observed90% precision at >=10 decisions.
        v = (
            saved.filter(pl.col("phase") == "val")
            .group_by("score")
            .agg(pl.len().alias("n"), pl.col("y").sum().alias("hits"))
            .sort("score", descending=True)
        )
        v = (
            v.with_columns(pl.col("n").cum_sum(), pl.col("hits").cum_sum())
            .filter((pl.col("n") >= 10) & (pl.col("hits") / pl.col("n") >= 0.9))
            .sort("n", descending=True)
        )
        thresholds[name] = float(v["score"][0]) if v.height else None
    joblib.dump(
        {"calibrators": calibrators, "thresholds": thresholds}, DEST / "frozen-policies.joblib"
    )
    log(
        "typed_graph_transfer_preregistered",
        seeds=list(SEEDS),
        replay_errors=replay_errors,
        selection="canonical selected hybrid fixed; no transfer fit/selection",
        thresholds=thresholds,
    )
    worlds = []
    enricher = Enricher()
    for seed in SEEDS:
        started = time.perf_counter()
        cfg = config.load(
            Path("data/generated/agency-v2/config.effective.json"), seed=seed, anchor=Path(".")
        )
        adv = adversary.Adversary(cfg, random.Random(seed + 1))
        run = chain.generate(cfg, random.Random(seed), adv.plan)
        log("typed_graph_transfer_network_started", seed=seed)
        net = network.build(cfg, run, random.Random(seed + 2))
        cap = net.capture
        nodes = net.topology.nodes
        ann = pl.DataFrame(
            {
                "row_id": range(len(cap)),
                "txid": [run.txs[i].txid for i in cap.tx_index],
                "peer_ip": [nodes[i].ip for i in cap.src_node],
                "observer_ip": [net.topology.observers[i].ip for i in cap.observer],
                "seen_us": cap.time_us,
            }
        )
        ips = (
            pl.DataFrame(
                {
                    "peer_ip": [nodes[i].ip for i in cap.src_node],
                    "asn": [nodes[i].asn for i in cap.src_node],
                },
                schema={"peer_ip": pl.String, "asn": pl.Int32},
            )
            .group_by("peer_ip")
            .agg(pl.col("asn").drop_nulls().first())
        )
        facts = normalise.peer_facts(sorted(ann["peer_ip"].unique().to_list()), enricher)
        peers = ips.join(facts, on="peer_ip").select(
            "peer_ip", pl.coalesce("asn", "v_asn").alias("asn"), "net_class"
        )
        tx, addresses, owners = frame_from_run(run)
        tx = observable_shape(tx).with_columns(
            pl.col("output_amounts").list.sum().alias("total_out_sats"),
            pl.Series("fee_rate_sat_vb", [t.fee_sats / t.vsize_vb for t in run.txs]),
        )
        tx = tx.drop("first_seen_us").join(
            ann.group_by("txid").agg(pl.col("seen_us").min().alias("first_seen_us")), on="txid"
        )
        seen = (
            tx.select(
                "first_seen_us",
                pl.concat_list("input_addresses", "output_addresses").alias("address"),
            )
            .explode("address")
            .drop_nulls("address")
            .group_by("address")
            .agg(pl.col("first_seen_us").min())
        )
        addresses = addresses.drop("first_seen_us").join(seen, on="address")
        labels = pl.DataFrame({"address": list(owners), "owner": list(owners.values())})
        campaigns = pl.DataFrame(
            [
                {
                    "txids": c.txids,
                    "entity_ids": [run.population.entities[i].entity_id for i in c.participants],
                }
                for c in adv.records()
            ],
            schema={"txids": pl.List(pl.String), "entity_ids": pl.List(pl.String)},
        )
        graphs, _ = build_graphs(
            tx,
            addresses,
            ann,
            peers,
            labels,
            activity(tx, labels, campaigns),
            scalers,
            threshold=ownership_threshold,
            partition_mode=partition_mode,
        )
        raw = score(graphs, models, trees)
        phase = np.concatenate([np.repeat(g["phase"], len(g["y"])) for g in graphs])
        test = phase == "test"
        frame = pl.concat(
            [
                g["subjects"].with_columns(
                    pl.lit(g["window_id"]).alias("window_id"), pl.lit(g["phase"]).alias("phase")
                )
                for g in graphs
            ]
        )
        y = frame["y"].to_numpy()
        output = {}
        for name, p in raw.items():
            p = calibrate(p, calibrators[name])
            threshold = thresholds[name]
            chosen = (
                test & (p >= threshold) if threshold is not None else np.zeros(len(p), dtype=bool)
            )
            hits = int(y[chosen].sum())
            n = int(chosen.sum())
            output[name] = {
                "test": ranking(y[test], p[test]),
                "policy": {
                    "threshold": threshold,
                    "answered": n,
                    "correct": hits,
                    "precision": hits / n if n else None,
                    "coverage": n / int(test.sum()),
                },
                "windows": {
                    str(i): ranking(
                        y[frame["window_id"].to_numpy() == i], p[frame["window_id"].to_numpy() == i]
                    )
                    for i in (7, 8, 9)
                },
            }
            frame.filter(pl.col("phase") == "test").with_columns(
                pl.Series("score", p[test])
            ).write_parquet(DEST / f"seed{seed}-{name}.parquet", compression="zstd")
        world = {
            "seed": seed,
            "network_rows": len(cap),
            "seconds": time.perf_counter() - started,
            "models": output,
        }
        worlds.append(world)
        (DEST / f"seed{seed}.json").write_text(
            json.dumps(world, indent=2, sort_keys=True, allow_nan=False) + "\n"
        )
        log(
            "typed_graph_transfer_world_complete",
            seed=seed,
            models=output,
            production_changes=False,
        )
    report = {
        "worlds": worlds,
        "canonical_replay_errors": replay_errors,
        "thresholds": thresholds,
        "partition_mode": partition_mode,
        "ownership_threshold": ownership_threshold,
        "seconds": time.perf_counter() - begin,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "limitations": [
            "New seeds, same generator family; not real Bitcoin transfer.",
            "No transfer-world model/calibration/threshold fitting.",
            "All ten windows update label-free address memory; metrics use final three.",
            "Complete body availability assumed at first announcement.",
            "New captures omit malformed export/quarantine faults of historical canonical data.",
        ],
        "hashes": {
            str(p): digest(p)
            for p in (
                Path(__file__),
                Path("research/bitcoin/temporal_hetero_benchmark.py"),
                OUT / "report.json",
                OUT / "scalers.joblib",
            )
        },
    }
    (DEST / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, default=OUT)
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    args = parser.parse_args()
    OUT, SEEDS = args.model_root, tuple(args.seeds)
    DEST = OUT / "transfer"
    main()
