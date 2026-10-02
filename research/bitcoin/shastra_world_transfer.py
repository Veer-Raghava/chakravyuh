"""Frozen causal source-ASN policy transfer to fresh simulated P2P captures.

No raw CSV/JSON/XML export. Hidden source truth attaches only after feature construction.
Offline peer enrichment uses the repository's fixed vendor lookup, not true node classes.
"""

from __future__ import annotations

import argparse
import json
import random
import resource
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import polars as pl
from causal_origin_benchmark import FEATURES, logit, transaction_results
from common import digest, log, ranking
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from chakravyuh.mayajaal import adversary, chain, config, network, writers
from chakravyuh.setu import normalise
from chakravyuh.setu.enrich import Enricher
from chakravyuh.shastra import causal

ROOT = Path("research/bitcoin/results")
ARTIFACTS = ROOT / "shastra-world-transfer"


def design(frame):
    x = frame.select(FEATURES).to_numpy().astype(np.float32)
    for i, name in enumerate(FEATURES):
        if name not in {
            "peer_frac_rank_one",
            "asn_frac_rank_one",
            "mle_logscore",
            "is_tor_exit",
            "is_hosting",
        }:
            x[:, i] = np.log1p(np.maximum(x[:, i], 0))
    return np.column_stack([x, np.eye(6, dtype=np.float32)[frame["net_class_code"].to_numpy()]])


def label(frame, truth):
    return (
        frame.join(truth, on="txid")
        .with_columns((pl.col("peer_ip") == pl.col("origin_peer_ip")).cast(pl.Int8).alias("y"))
        .sort("txid", "peer_ip")
    )


def predict(frame, bundle):
    x = bundle["scaler"].transform(design(frame)).astype(np.float32)
    raw = bundle["model"].predict(x, num_threads=4)
    return bundle["calibrator"].predict_proba(logit(raw)[:, None])[:, 1]


def evaluate(frame, scores, threshold, boundary, name):
    tx = transaction_results(frame, scores).filter(pl.col("first_seen_us") >= boundary)
    answered = tx.filter(
        (pl.col("legacy_separation") >= threshold)
        & (pl.col("n_observers_in_tx") >= 2)
        & ~pl.col("any_tor")
    )
    candidates = frame.filter(pl.col("first_seen_us") >= boundary)
    test_scores = scores[frame["first_seen_us"].to_numpy() >= boundary]
    path = ARTIFACTS / f"{name}-tx-scores.parquet"
    tx.write_parquet(path, compression="zstd")
    # Includes the observed-candidate denominator. Transactions entirely unobserved are
    # reported separately by the world runner, rather than silently assigned a prediction.
    return {
        "test_transactions_with_candidates": tx.height,
        "candidate_test": ranking(candidates["y"], test_scores),
        "source_in_five_second_candidates": float(tx["source_present"].mean()),
        "l0_top1": float(tx["l0_hit"].mean()),
        "l0_top3": float(tx["l0_hit3"].mean()),
        "l1_direct_top1": float(tx["l1_hit"].mean()),
        "l1_direct_top3": float(tx["l1_hit3"].mean()),
        "l1_prior_weighted_top1": float(tx["weighted_hit"].mean()),
        "policy_answered": answered.height,
        "policy_correct": int(answered["weighted_hit"].sum()),
        "policy_precision": float(answered["weighted_hit"].mean()) if answered.height else None,
        "policy_coverage": answered.height / tx.height,
        "research_score_artifact": str(path),
        "research_score_sha256": digest(path),
    }


def main(seeds):
    started = time.perf_counter()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    source = Path("data/generated/agency-v2/normalised")
    cfg_path = Path("data/generated/agency-v2/config.effective.json")
    reference_path = ROOT / "causal-origin-benchmark.json"
    reference = json.loads(reference_path.read_text())
    policy = next(
        p
        for p in reference["models"]["lightgbm"]["policies"]["policies"]
        if p["aggregation"] == "legacy_separation" and p["blanket_tor"]
    )
    threshold = policy["validation_selected_floor"]
    registry = json.loads(cfg_path.read_text())["network"]["n_observers"]
    observable = causal.candidates(
        pl.read_parquet(source / "announcements.parquet"),
        pl.read_parquet(source / "peers.parquet"),
        pl.read_parquet(source / "transactions.parquet"),
        n_observers=registry,
    )
    truth_path = Path("ground_truth/agency-v2/origins.parquet")
    truth = pl.read_parquet(truth_path).select(
        "txid", pl.col("true_origin_ip").alias("origin_peer_ip"), "true_origin_asn"
    )
    frame = label(observable, truth)
    t = frame["first_seen_us"].to_numpy()
    first, last = int(t.min()), int(t.max())
    fit_end, cal_end, test_start = [first + int((last - first) * p) for p in (0.45, 0.6, 0.7)]
    decision = frame["decision_us"].to_numpy()
    fit, cal = decision < fit_end, (t >= fit_end) & (decision < cal_end)
    scaler = StandardScaler().fit(design(frame)[fit])
    x, y = scaler.transform(design(frame)).astype(np.float32), frame["y"].to_numpy()
    params = dict(reference["models"]["lightgbm"]["parameters"])
    rounds = params.pop("rounds")
    model = lgb.train(params, lgb.Dataset(x[fit], label=y[fit]), num_boost_round=rounds)
    raw = model.predict(x, num_threads=4)
    calibrator = LogisticRegression(C=1, max_iter=1000, random_state=42).fit(
        logit(raw[cal])[:, None], y[cal]
    )
    bundle = {
        "model": model,
        "scaler": scaler,
        "calibrator": calibrator,
        "threshold": threshold,
        "features": FEATURES,
    }
    canonical = evaluate(frame, predict(frame, bundle), threshold, test_start, "canonical")
    assert canonical["policy_answered"] == policy["test_answered"]
    assert canonical["policy_correct"] == policy["test_correct"]
    assert (
        abs(canonical["l1_direct_top1"] - reference["models"]["lightgbm"]["l1_direct_top1"]) < 1e-12
    )
    bundle_path = ARTIFACTS / "frozen-canonical-lightgbm.joblib"
    joblib.dump(bundle, bundle_path, compress=3)
    result = {
        "canonical_replayed_policy_and_ranking": canonical,
        "threshold": threshold,
        "worlds": [],
    }
    log("shastra_world_transfer_frozen", threshold=threshold, production_changes=False)
    del frame, observable, x, raw
    enricher = Enricher()
    for seed in seeds:
        begin = time.perf_counter()
        cfg = config.load(cfg_path, seed=seed, n_txs=24000, anchor=Path("."))
        adv = adversary.Adversary(cfg, random.Random(seed + 1))
        generated = chain.generate(cfg, random.Random(seed), adv.plan)
        log("shastra_world_network_started", seed=seed, chain_rows=len(generated.txs))
        net = network.build(cfg, generated, random.Random(seed + 2))
        nodes, observers, capture = net.topology.nodes, net.topology.observers, net.capture
        ann = pl.DataFrame(
            {
                "row_id": list(range(len(capture))),
                "txid": [generated.txs[i].txid for i in capture.tx_index],
                "peer_ip": [nodes[i].ip for i in capture.src_node],
                "observer_ip": [observers[i].ip for i in capture.observer],
                "seen_us": capture.time_us,
            }
        )
        observed_nodes = (
            pl.DataFrame(
                {
                    "peer_ip": [nodes[i].ip for i in capture.src_node],
                    "capture_asn": [nodes[i].asn for i in capture.src_node],
                },
                schema={"peer_ip": pl.String, "capture_asn": pl.Int32},
            )
            .group_by("peer_ip")
            .agg(pl.col("capture_asn").drop_nulls().first())
        )
        facts = normalise.peer_facts(sorted(ann["peer_ip"].unique().to_list()), enricher)
        peers = observed_nodes.join(facts, on="peer_ip").select(
            "peer_ip", pl.coalesce("capture_asn", "v_asn").alias("asn"), "net_class"
        )
        transactions = pl.DataFrame(
            {
                "txid": [t.txid for t in generated.txs],
                "input_addresses": [list(t.input_addresses) for t in generated.txs],
            }
        )
        frame = causal.candidates(ann, peers, transactions, n_observers=cfg.network.n_observers)
        # Only this research label door reads originating node/entity information.
        truth = writers._origins(cfg, generated, net).select(
            "txid", pl.col("true_origin_ip").alias("origin_peer_ip"), "true_origin_asn"
        )
        frame = label(frame, truth)
        first, last = int(frame["first_seen_us"].min()), int(frame["first_seen_us"].max())
        boundary = first + int((last - first) * 0.7)
        world = {
            "seed": seed,
            "network_rows": len(capture),
            "chain_rows": len(generated.txs),
            "origins": len(net.origins),
            "unobserved_origins": sum(o.observed_by_n == 0 for o in net.origins),
            "n_observers": cfg.network.n_observers,
            "observer_fraction": cfg.network.observer_fraction,
            "test_start_us": boundary,
            "offline_enrichment_classes": peers.group_by("net_class").len().to_dicts(),
            **evaluate(frame, predict(frame, bundle), threshold, boundary, f"seed{seed}"),
            "seconds": time.perf_counter() - begin,
        }
        result["worlds"].append(world)
        log(
            "shastra_world_transfer_complete",
            seed=seed,
            precision=world["policy_precision"],
            coverage=world["policy_coverage"],
            production_changes=False,
        )
        # Save each completed world so later interruption never discards a completed result.
        (ARTIFACTS / f"seed{seed}-summary.json").write_text(
            json.dumps(world, indent=2, sort_keys=True, allow_nan=False) + "\n"
        )
    result.update(
        {
            "seconds": time.perf_counter() - started,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "model_artifact": str(bundle_path),
            "enrichment_warnings": enricher.warnings,
            "hashes": {
                str(p): digest(p)
                for p in (
                    reference_path,
                    cfg_path,
                    truth_path,
                    bundle_path,
                    Path(__file__),
                    Path(causal.__file__),
                    source / "announcements.parquet",
                    source / "peers.parquet",
                    source / "transactions.parquet",
                )
            },
            "limitations": [
                "Same generator family; seeds previously used for JAAL. No real-network claim.",
                "Model, scaler, calibration and answer threshold never fitted on transfer worlds.",
                "Five-second source-peer candidates differ from full-capture source presence.",
                "Fixed offline enrichment may miss Tor nodes whose seed-dependent IP changed.",
                "ASN attribution targets a network node/operator, not human identity.",
                "Coverage uses observed transactions; unobserved origins are reported separately.",
                "ASN metadata is treated as static; mutable lookups need as-of versions.",
                "Canonical test period reused; seed transfer is exploratory simulator evidence.",
            ],
        }
    )
    out = ROOT / "shastra-world-transfer.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    log("shastra_world_transfer_report_complete", output=str(out), production_changes=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[1337, 2026])
    main(parser.parse_args().seeds)
