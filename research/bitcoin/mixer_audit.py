"""Audit the JAAL equal-output mixer set-aside against synthetic mixed-owner spends.

Research-only: reads the hidden chain answer table for labels; production code never imports it.
The target is synthetic input-owner heterogeneity, not a claim that all such spends are CoinJoin.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from chakravyuh.jaal import mixer
from common import digest, log, ranking, save


FEATURES = [
    "n_in", "n_out", "log_total_in", "log_total_out", "fee_fraction",
    "max_input_fraction", "input_amount_cv", "max_output_fraction",
    "output_amount_cv", "equal_output_count", "equal_output_fraction",
    "round_output_count", "same_script_input_fraction", "has_equal_outputs",
]


def build_rows(tx: pl.DataFrame, labels: pl.DataFrame, addresses: pl.DataFrame):
    joined = tx.join(labels.select("txid", "input_entity_ids"), on="txid", how="inner")
    script_by_address = dict(addresses.select("address", "script_type").iter_rows())
    rows = []
    for r in joined.iter_rows(named=True):
        ins = np.asarray([x for x in r["input_amounts"] if x is not None], dtype=float)
        outs = np.asarray([x for x in r["output_amounts"] if x is not None], dtype=float)
        if not len(ins) or not len(outs):
            continue
        total_in, total_out = max(float(ins.sum()), 1.), max(float(outs.sum()), 1.)
        unique_owners = set(r["input_entity_ids"])
        out_counts = {}
        for amount in outs:
            out_counts[float(amount)] = out_counts.get(float(amount), 0) + 1
        n_equal = sum(count for count in out_counts.values() if count > 1)
        script_counts = {}
        for script in (script_by_address[a] for a in r["input_addresses"]):
            script_counts[script] = script_counts.get(script, 0) + 1
        x = [
            len(ins), len(outs), np.log1p(total_in), np.log1p(total_out),
            r["fee_sats"] / total_in, float(ins.max() / total_in),
            float(ins.std() / max(ins.mean(), 1.)), float(outs.max() / total_out),
            float(outs.std() / max(outs.mean(), 1.)), n_equal,
            n_equal / len(outs), sum(int(a % 100_000 == 0) for a in outs),
            max(script_counts.values()) / len(ins), int(r["has_equal_outputs"]),
        ]
        rows.append({
            "txid": r["txid"], "time": int(r["first_seen_us"]), "x": x,
            "y": int(len(unique_owners) > 1),
            "rule": int(bool(r["has_equal_outputs"])
                         and len(outs) >= mixer.COINJOIN_MIN_OUTPUTS
                         and len(ins) >= mixer.MIXER_MIN_INPUTS),
        })
    return rows


def select_cut(y, p, target_precision=.8, min_alerts=50):
    choices = []
    for cut in np.linspace(.01, .99, 99):
        chosen = p >= cut
        if chosen.sum() >= min_alerts and y[chosen].mean() >= target_precision:
            choices.append(float(cut))
    return min(choices) if choices else None


def decision_metrics(y, p):
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=int)
    tp = int(((y == 1) & (p == 1)).sum())
    fp = int(((y == 0) & (p == 1)).sum())
    fn = int(((y == 1) & (p == 0)).sum())
    tn = int(((y == 0) & (p == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.
    recall = tp / (tp + fn) if tp + fn else 0.
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall)
            if precision + recall else 0.}


def run(run_id: str, out: Path):
    start = time.perf_counter()
    root = Path("data/generated") / run_id
    tx_path = root / "normalised/transactions.parquet"
    address_path = root / "normalised/addresses.parquet"
    label_path = Path("ground_truth") / run_id / "chain_txs.parquet"
    tx = pl.read_parquet(tx_path)
    addresses = pl.read_parquet(address_path)
    truth = pl.read_parquet(label_path)
    rows = build_rows(tx, truth, addresses)
    times = np.asarray([r["time"] for r in rows])
    y = np.asarray([r["y"] for r in rows], dtype=int)
    x = np.asarray([r["x"] for r in rows], dtype=np.float32)
    rule = np.asarray([r["rule"] for r in rows], dtype=int)
    first, last = int(times.min()), int(times.max())
    c1, c2 = int(first + .6 * (last-first)), int(first + .8 * (last-first))
    fit, val, test = times < c1, (times >= c1) & (times < c2), times >= c2

    models = {
        "logistic_balanced": make_pipeline(StandardScaler(), LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42)),
        "random_forest_balanced": RandomForestClassifier(
            n_estimators=200, min_samples_leaf=5, class_weight="balanced_subsample",
            n_jobs=4, random_state=42),
    }
    results = {
        "equal_output_rule": {
            "validation": ranking(y[val], rule[val]),
            "test": ranking(y[test], rule[test]),
        },
    }
    for name, model in models.items():
        t = time.perf_counter()
        model.fit(x[fit], y[fit])
        p = model.predict_proba(x)[:, 1]
        cut = select_cut(y[val], p[val])
        results[name] = {
            "validation": ranking(y[val], p[val]),
            "test": ranking(y[test], p[test]),
            "validation_precision_target_cut": cut,
            "test_at_validation_cut": decision_metrics(
                y[test], (p[test] >= cut).astype(int)
            ) if cut is not None else None,
            "fit_seconds": time.perf_counter() - t,
        }

    train = lgb.Dataset(x[fit], label=y[fit], feature_name=FEATURES)
    t = time.perf_counter()
    booster = lgb.train({
        "objective": "binary", "verbosity": -1, "num_threads": 4, "seed": 42,
        "num_leaves": 15, "min_data_in_leaf": 50, "learning_rate": .05,
        "scale_pos_weight": float((y[fit] == 0).sum() / max((y[fit] == 1).sum(), 1)),
    }, train, num_boost_round=120)
    p = booster.predict(x, num_threads=4)
    cut = select_cut(y[val], p[val])
    results["lightgbm_balanced"] = {
        "validation": ranking(y[val], p[val]),
        "test": ranking(y[test], p[test]),
        "validation_precision_target_cut": cut,
        "test_at_validation_cut": decision_metrics(
            y[test], (p[test] >= cut).astype(int)
        ) if cut is not None else None,
        "fit_seconds": time.perf_counter() - t,
        "feature_importance_gain": dict(sorted(
            zip(FEATURES, map(float, booster.feature_importance(importance_type="gain")),
                strict=True), key=lambda item: item[1], reverse=True)),
    }

    result = {
        "run": run_id, "target": "more than one true synthetic input owner",
        "features": FEATURES, "split_us": [c1, c2],
        "rows": {"fit": int(fit.sum()), "validation": int(val.sum()),
                 "test": int(test.sum())},
        "prevalence": {"all": float(y.mean()), "fit": float(y[fit].mean()),
                       "validation": float(y[val].mean()), "test": float(y[test].mean())},
        "rule_confusion": {
            "tp": int(((rule == 1) & (y == 1)).sum()),
            "fp": int(((rule == 1) & (y == 0)).sum()),
            "fn": int(((rule == 0) & (y == 1)).sum()),
            "tn": int(((rule == 0) & (y == 0)).sum()),
        },
        "models": results,
        "hashes": {str(p): digest(p) for p in [tx_path, address_path, label_path]},
        "elapsed_seconds": time.perf_counter() - start,
        "limitations": [
            "Synthetic collaborative-input target; not protocol-adjudicated CoinJoin labels.",
            "Temporal split is not entity-disjoint or independent-generator evaluation.",
            "Validation threshold selection has no finite-sample precision guarantee.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    save(out / "mixer-audit.json", result)
    pl.DataFrame({
        "txid": [r["txid"] for r in rows],
        "time_us": times,
        "synthetic_mixed_owner_label": y,
        "lgbm_score": p,
        "equal_output_rule": rule,
    }).write_parquet(out / "mixer-scores.parquet", compression="zstd")
    log("jaal_mixer_audit_complete", run=run_id, out=str(out),
        seconds=result["elapsed_seconds"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="agency-v2")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.run, args.out)
