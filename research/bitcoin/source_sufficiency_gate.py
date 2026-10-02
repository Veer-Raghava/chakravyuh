"""Observable gate for correct operator answers; no hidden source flag at inference."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import polars as pl
from causal_origin_benchmark import transaction_results
from common import digest, log, ranking
from shastra_world_transfer import label, predict
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from chakravyuh.shastra import causal

OUT = Path("research/bitcoin/results/source-sufficiency-gate")
FIELDS = (
    "candidate_mass",
    "best_candidate_p",
    "second_candidate_p",
    "n_candidates",
    "n_observers_in_tx",
    "total_announcements",
    "mean_peer_history",
    "max_payer_history",
    "p1",
    "p2",
    "separation",
    "any_tor",
    "legacy_separation",
)


def design(frame):
    x = frame.select(FIELDS).to_numpy().astype(np.float64)
    for i, name in enumerate(FIELDS):
        if name in {
            "n_candidates",
            "n_observers_in_tx",
            "total_announcements",
            "mean_peer_history",
            "max_payer_history",
        }:
            x[:, i] = np.log1p(np.maximum(x[:, i], 0))
    return x


def select_threshold(frame, p):
    scored = frame.with_columns(pl.Series("q", p)).filter(
        (pl.col("n_observers_in_tx") >= 2) & ~pl.col("any_tor")
    )
    v = (
        scored.group_by("q")
        .agg(pl.len().alias("n"), pl.col("weighted_hit").sum().alias("hits"))
        .sort("q", descending=True)
    )
    v = (
        v.with_columns(pl.col("n").cum_sum(), pl.col("hits").cum_sum())
        .filter((pl.col("n") >= 100) & (pl.col("hits") / pl.col("n") >= 0.9))
        .sort("n", descending=True)
    )
    return (
        {
            "threshold": float(v["q"][0]),
            "validation_answered": int(v["n"][0]),
            "validation_correct": int(v["hits"][0]),
        }
        if v.height
        else {"threshold": None, "validation_answered": 0, "validation_correct": 0}
    )


def metrics(data, p, threshold):
    condition = (p >= threshold) if threshold is not None else np.zeros(len(p), dtype=bool)
    condition = (
        condition & (data["n_observers_in_tx"].to_numpy() >= 2) & ~data["any_tor"].to_numpy()
    )
    y = data["weighted_hit"].to_numpy()
    n = int(condition.sum())
    hits = int(y[condition].sum())
    absent_decisions = condition & ~data["source_present"].to_numpy().astype(bool)
    return {
        "ranking_correctness": ranking(y, p),
        "answered": n,
        "correct": hits,
        "precision": hits / n if n else None,
        "coverage": n / len(data),
        "source_absent_answered": int(absent_decisions.sum()),
        "source_absent_correct": int(y[absent_decisions].sum()),
    }


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    root = Path("data/generated/agency-v2/normalised")
    bundle = joblib.load(
        "research/bitcoin/results/shastra-world-transfer/frozen-canonical-lightgbm.joblib"
    )
    c = json.loads(Path("data/generated/agency-v2/config.effective.json").read_text())
    frame = causal.candidates(
        pl.read_parquet(root / "announcements.parquet"),
        pl.read_parquet(root / "peers.parquet"),
        pl.read_parquet(root / "transactions.parquet"),
        n_observers=c["network"]["n_observers"],
    )
    truth = pl.read_parquet("ground_truth/agency-v2/origins.parquet").select(
        "txid", pl.col("true_origin_ip").alias("origin_peer_ip"), "true_origin_asn"
    )
    frame = label(frame, truth)
    tx = transaction_results(frame, predict(frame, bundle))
    first, last = int(tx["first_seen_us"].min()), int(tx["first_seen_us"].max())
    cuts = [first + int((last - first) * p) for p in (0.6, 0.65, 0.7)]
    fit = tx.filter(
        (pl.col("first_seen_us") >= cuts[0]) & (pl.col("first_seen_us") + 5_000_000 < cuts[1])
    )
    val = tx.filter(
        (pl.col("first_seen_us") >= cuts[1]) & (pl.col("first_seen_us") + 5_000_000 < cuts[2])
    )
    test = tx.filter(pl.col("first_seen_us") >= cuts[2])
    scaler = StandardScaler().fit(design(fit))
    y = fit["weighted_hit"].to_numpy()
    x = scaler.transform(design(fit))
    models = {}
    models["logistic"] = LogisticRegression(max_iter=1000, random_state=42).fit(x, y)
    models["lightgbm"] = lgb.train(
        {
            "objective": "binary",
            "num_leaves": 15,
            "min_data_in_leaf": 40,
            "learning_rate": 0.05,
            "verbosity": -1,
            "num_threads": 4,
            "seed": 42,
            "deterministic": True,
            "force_col_wise": True,
        },
        lgb.Dataset(x, label=y),
        num_boost_round=150,
    )

    def scores(name, data):
        a = scaler.transform(design(data))
        m = models[name]
        return m.predict(a, num_threads=4) if name == "lightgbm" else m.predict_proba(a)[:, 1]

    policies = {name: select_threshold(val, scores(name, val)) for name in models}
    choice = max(policies, key=lambda k: policies[k]["validation_answered"])
    result = {
        "validation_selected_model": choice,
        "fields": FIELDS,
        "cuts_us": cuts,
        "fit_transactions": fit.height,
        "validation_transactions": val.height,
        "models": {},
    }
    transfer = json.loads(Path("research/bitcoin/results/shastra-world-transfer.json").read_text())
    worlds = {
        "canonical": test,
        **{
            f"seed{w['seed']}": pl.read_parquet(w["research_score_artifact"])
            for w in transfer["worlds"]
        },
    }
    for name in models:
        result["models"][name] = {
            "policy": policies[name],
            "worlds": {
                k: metrics(data, scores(name, data), policies[name]["threshold"])
                for k, data in worlds.items()
            },
        }
        joblib.dump(models[name], OUT / f"{name}.joblib")
    joblib.dump(scaler, OUT / "scaler.joblib")
    result.update(
        {
            "seconds": time.perf_counter() - begin,
            "limitations": [
                "Exploratory reused canonical/seed test data; no confirmation claim.",
                "Parent fit ends45%, Platt ends60%; gate fits60–65%, selection65–70%.",
                "Parent .01 policy used60–70%; this is not pristine nested selection.",
                "Gate predicts operator correctness, not source-peer presence or human identity.",
                "Observed validation90% precision is not a future guarantee.",
                "No test labels used to set the gate; true source presence is diagnostic only.",
            ],
            "hashes": {
                str(p): digest(p)
                for p in (
                    Path(__file__),
                    Path("research/bitcoin/results/shastra-world-transfer.json"),
                )
            },
        }
    )
    (OUT / "report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    log(
        "source_sufficiency_gate_complete",
        validation_choice=choice,
        result=result["models"][choice],
        production_changes=False,
    )


if __name__ == "__main__":
    main()
