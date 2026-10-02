"""Freeze matched-window XGBoost and its response policy; test full-chain seed transfer.

Research labels/score artifacts contain hidden truth. They never enter production directories.
Generated worlds omit network-capture censoring: this is a joint seed/observation shift test,
not a clean measurement of seed alone. No transfer-world data refits any model or threshold.
"""

from __future__ import annotations

import json
import random
import resource
import time
from pathlib import Path

import buddhi_snapshot_benchmark as benchmark
import joblib
import numpy as np
import polars as pl
from buddhi_snapshot_benchmark import labelled_snapshots
from common import digest, log, ranking
from jaal_partition_transfer import observable_shape
from jaal_seed_transfer import frame_from_run
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from chakravyuh.buddhi import snapshot
from chakravyuh.jaal import provenance
from chakravyuh.mayajaal import adversary, chain, config

ROOT = Path("research/bitcoin/results")
ARTIFACTS = ROOT / "buddhi-world-transfer"


def windows(tx):
    first, last = int(tx["first_seen_us"].min()), int(tx["first_seen_us"].max())
    endpoints = [first + int((last - first) * i / 10) for i in range(11)]
    return [
        (
            "fit" if i < 4 else "cal" if i < 6 else "val" if i == 6 else "test",
            endpoints[i] if i == 0 else endpoints[i] + 1,
            endpoints[i + 1],
        )
        for i in range(10)
    ]


def activity(tx, labels, campaigns):
    owners = (
        tx.select(
            "txid",
            "first_seen_us",
            pl.concat_list("input_addresses", "output_addresses").alias("address"),
        )
        .explode("address")
        .join(labels.select("owner", "address"), on="address")
    )
    return (
        owners.join(campaigns.explode("txids").rename({"txids": "txid"}), on="txid")
        .filter(pl.col("entity_ids").list.contains(pl.col("owner")))
        .select("owner", "txid", "first_seen_us")
        .unique()
    )


def matrix(frame):
    x = frame.select(snapshot.SNAPSHOT_FEATURES).to_numpy().astype(np.float64)
    x = np.nan_to_num(x, nan=0.0)
    return np.sign(x) * np.log1p(np.abs(x))


def predict(frame, bundle):
    x = bundle["scaler"].transform(matrix(frame)).astype(np.float32)
    raw = bundle["model"].predict_proba(x)[:, 1]
    raw = np.clip(raw, 1e-6, 1 - 1e-6)
    return bundle["calibrator"].predict_proba(np.log(raw / (1 - raw))[:, None])[:, 1]


def decision_counts(data, threshold):
    answered = data.filter(pl.col("score") >= threshold)
    n, hits = answered.height, int(answered["y"].sum())
    positives = int(data["y"].sum())
    return {
        "decisions": data.height,
        "positives": positives,
        "answered": n,
        "correct": hits,
        "false_alerts": n - hits,
        "precision": hits / n if n else None,
        "recall": hits / positives if positives else None,
        "coverage": n / data.height if data.height else None,
    }


def evaluate(frame, scores, threshold, name):
    data = frame.select(
        "subject_id", "window_id", "phase", "y", "owners", "illicit_fraction"
    ).with_columns(pl.Series("score", scores))
    path = ARTIFACTS / f"{name}-scores.parquet"
    data.write_parquet(path, compression="zstd")
    return {
        "pooled_subject_decisions": ranking(data["y"], data["score"]),
        "frozen_policy": decision_counts(data, threshold),
        "windows": {
            str(w): {
                "ranking": ranking(part["y"], part["score"]),
                "frozen_policy": decision_counts(part, threshold),
            }
            for w in data["window_id"].unique().sort()
            for part in [data.filter(pl.col("window_id") == w)]
        },
        "score_artifact": str(path),
        "score_sha256": digest(path),
    }


def main():
    started = time.perf_counter()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    reference_path = ROOT / "buddhi-matched-window-benchmark.json"
    policy_path = ROOT / "snapshot-alert-policy.json"
    reference = json.loads(reference_path.read_text())
    assert reference["validation_selected_cioh_model"] == "xgboost"
    policy = json.loads(policy_path.read_text())["results"]["validation_selected"]
    threshold = next(
        p["threshold"] for p in policy["policies"] if p["validation_precision_target"] == 0.9
    )
    source = Path("data/generated/agency-v2/normalised")
    tx = pl.read_parquet(source / "transactions.parquet")
    addresses = pl.read_parquet(source / "addresses.parquet")
    entities_path = Path("ground_truth/agency-v2/entities.parquet")
    campaign_path = Path("ground_truth/agency-v2/campaigns.parquet")
    labels = (
        pl.read_parquet(entities_path)
        .select(pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address"))
        .explode("address")
    )
    benchmark.ACTIVITY = activity(
        tx, labels, pl.read_parquet(campaign_path).select("entity_ids", "txids")
    )
    cuts = windows(tx)
    frame = labelled_snapshots(tx, addresses, provenance.ownership_evidence(tx), labels, 0.3, cuts)
    phase, y = frame["phase"].to_numpy(), frame["y"].to_numpy()
    fit, cal = phase == "fit", phase == "cal"
    scaler = StandardScaler().fit(matrix(frame)[fit])
    x = scaler.transform(matrix(frame)).astype(np.float32)
    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        min_child_weight=10,
        subsample=0.9,
        colsample_bytree=0.9,
        n_jobs=4,
        tree_method="hist",
        random_state=42,
    ).fit(x[fit], y[fit])
    raw = np.clip(model.predict_proba(x)[:, 1], 1e-6, 1 - 1e-6)
    calibrator = LogisticRegression(max_iter=1000, random_state=42).fit(
        np.log(raw[cal] / (1 - raw[cal]))[:, None], y[cal]
    )
    bundle = {
        "model": model,
        "scaler": scaler,
        "calibrator": calibrator,
        "features": snapshot.SNAPSHOT_FEATURES,
        "threshold": threshold,
    }
    scores = predict(frame, bundle)
    saved_path = Path(reference["models"]["cioh"]["xgboost"]["research_score_artifact"])
    saved = pl.read_parquet(saved_path).sort("window_id", "subject_id")
    replay = (
        frame.select("window_id", "subject_id", "y")
        .with_columns(pl.Series("score", scores))
        .sort("window_id", "subject_id")
    )
    assert saved.select("window_id", "subject_id", "y").equals(
        replay.select("window_id", "subject_id", "y")
    ), "canonical subjects/labels differ from preserved matched experiment"
    error = float(np.max(np.abs(saved["score"].to_numpy() - replay["score"].to_numpy())))
    if error > 1e-8:
        raise ValueError(f"canonical score replay failed: maximum error {error}")
    bundle_path = ARTIFACTS / "frozen-canonical-xgboost.joblib"
    joblib.dump(bundle, bundle_path, compress=3)
    result = {
        "canonical_replay_max_score_error": error,
        "canonical_test": evaluate(
            frame.filter(pl.col("phase") == "test"),
            scores[phase == "test"],
            threshold,
            "canonical",
        ),
        "frozen_policy_threshold": threshold,
        "transfer_worlds": [],
    }
    log(
        "buddhi_world_transfer_frozen",
        replay_max_error=error,
        threshold=threshold,
        production_changes=False,
    )
    del frame, tx, addresses, x
    cfg_path = Path("data/generated/agency-v2/config.effective.json")
    for seed in (42, 1337, 2026):
        begin = time.perf_counter()
        cfg = config.load(cfg_path, seed=seed, n_txs=24000, anchor=Path("."))
        adv = adversary.Adversary(cfg, random.Random(seed + 1))
        generated = chain.generate(cfg, random.Random(seed), adv.plan)
        tx, addresses, owners = frame_from_run(generated)
        tx = observable_shape(tx).with_columns(
            pl.col("output_amounts").list.sum().alias("total_out_sats"),
            pl.Series("fee_rate_sat_vb", [t.fee_sats / t.vsize_vb for t in generated.txs]),
        )
        labels = pl.DataFrame({"address": list(owners), "owner": list(owners.values())})
        campaigns = pl.DataFrame(
            [
                {
                    "txids": c.txids,
                    "entity_ids": [
                        generated.population.entities[i].entity_id for i in c.participants
                    ],
                }
                for c in adv.records()
            ],
            schema={"txids": pl.List(pl.String), "entity_ids": pl.List(pl.String)},
        )
        benchmark.ACTIVITY = activity(tx, labels, campaigns)
        cuts = windows(tx)
        # Keep original window IDs 7/8/9, not renumbered 0/1/2.
        all_frames = []
        for i, cut in enumerate(cuts[7:], start=7):
            part = labelled_snapshots(
                tx, addresses, provenance.ownership_evidence(tx), labels, 0.3, [cut]
            ).with_columns(pl.lit(i).alias("window_id"))
            all_frames.append(part)
        frame = pl.concat(all_frames)
        item = {
            "seed": seed,
            "tx_rows": tx.height,
            "capture_mode": "complete chain; transaction time, no network censoring",
            "cuts_us": cuts,
            "active_campaign_controllers": {
                str(i): benchmark.ACTIVITY.filter(
                    (pl.col("first_seen_us") >= start) & (pl.col("first_seen_us") <= end)
                )["owner"].n_unique()
                for i, (_, start, end) in enumerate(cuts)
            },
            **evaluate(frame, predict(frame, bundle), threshold, f"seed{seed}"),
            "seconds": time.perf_counter() - begin,
        }
        result["transfer_worlds"].append(item)
        log(
            "buddhi_world_transfer_complete",
            seed=seed,
            test_p20=item["pooled_subject_decisions"]["p_at_20"],
            policy=item["frozen_policy"],
            production_changes=False,
        )
    result.update(
        {
            "seconds": time.perf_counter() - started,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "frozen_model_artifact": str(bundle_path),
            "hashes": {
                str(p): digest(p)
                for p in (
                    reference_path,
                    policy_path,
                    saved_path,
                    entities_path,
                    campaign_path,
                    source / "transactions.parquet",
                    source / "addresses.parquet",
                    cfg_path,
                    bundle_path,
                    Path(__file__),
                    Path(snapshot.__file__),
                    Path(provenance.__file__),
                    Path(benchmark.__file__),
                )
            },
            "limitations": [
                "Seeds 1337/2026 previously explored for JAAL, not pristine research holdouts.",
                "All worlds share generator family; no real-chain validation claim.",
                "Complete-chain observables jointly change network censoring and seed; "
                "seed42 is a fresh same-seed chain, not a verified replay or independent seed.",
                "No transfer data fitted scaler, XGBoost, calibration or policy threshold.",
                "Labels and score artifacts contain quarantined research truth only.",
                "Positive means campaign participant in window, not criminal guilt.",
                "Pooled subject-window decisions repeat some controllers; "
                "per-window reports retained.",
                "Features use observed heuristic change, never generator true change index.",
            ],
        }
    )
    out = ROOT / "buddhi-world-transfer.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    log("buddhi_world_transfer_report_complete", output=str(out), production_changes=False)


if __name__ == "__main__":
    main()
