"""CPU model/hybrid benchmarks using strictly prior-history SHASTRA features.

Research labels remain here. Produces aggregate metrics and hashes, never production signals.
Fixed five-second transaction decision horizon; time blocks: 0-45 fit, 45-60 calibration,
60-70 validation, 70-100 evaluation. Reused research test period requires a fresh-world test
before promotion. Static geo/network lookup facts are assumed fixed/versioned.
"""

from __future__ import annotations

import gc
import json
import pickle
import resource
import time
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import polars as pl
from common import digest, log, ranking
from sklearn.ensemble import ExtraTreesClassifier, IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from chakravyuh.shastra import causal, schema

ROOT = Path("data/generated/agency-v2")
OUT = Path("research/bitcoin/results/causal-origin-benchmark.json")
FEATURES = tuple(n for n in schema.MODEL_FEATURES if n != "net_class_code") + ("asn_frac_rank_one",)
SEED = 42
THREADS = 4


def logit(p: np.ndarray) -> np.ndarray:
    clipped = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))


def calibrate(raw: np.ndarray, y: np.ndarray, mask: np.ndarray) -> np.ndarray:
    cal = LogisticRegression(C=1.0, max_iter=1000, random_state=SEED)
    cal.fit(logit(raw[mask]).reshape(-1, 1), y[mask])
    return cal.predict_proba(logit(raw).reshape(-1, 1))[:, 1]


def neural_fit_predict(
    x: np.ndarray, y: np.ndarray, fit: np.ndarray
) -> tuple[np.ndarray, dict[str, Any]]:
    import torch

    torch.manual_seed(SEED)
    torch.set_num_threads(THREADS)
    torch.use_deterministic_algorithms(True)
    net = torch.nn.Sequential(
        torch.nn.Linear(x.shape[1], 64),
        torch.nn.ReLU(),
        torch.nn.Linear(64, 32),
        torch.nn.ReLU(),
        torch.nn.Linear(32, 1),
    )
    optimizer = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-3)
    xt = torch.from_numpy(np.ascontiguousarray(x[fit], dtype=np.float32))
    yt = torch.from_numpy(np.asarray(y[fit], dtype=np.float32))
    weight = float(np.sqrt((yt.numel() - yt.sum().item()) / max(yt.sum().item(), 1)))
    loss = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight))
    net.train()
    for _ in range(12):
        order = torch.randperm(len(xt))
        for ids in order.split(2048):
            optimizer.zero_grad()
            objective = loss(net(xt[ids]).flatten(), yt[ids])
            objective.backward()
            optimizer.step()
    net.eval()
    with torch.no_grad():
        prediction = np.concatenate(
            [
                torch.sigmoid(net(torch.from_numpy(np.ascontiguousarray(batch, dtype=np.float32))))
                .flatten()
                .numpy()
                for batch in np.array_split(x, max(1, len(x) // 8192))
            ]
        )
    return prediction, {
        "hidden": [64, 32],
        "epochs": 12,
        "batch_size": 2048,
        "learning_rate": 0.001,
        "weight_decay": 0.001,
        "positive_weight": weight,
        "device": "cpu",
        "parameters": sum(p.numel() for p in net.parameters()),
    }


def transaction_results(frame: pl.DataFrame, p: np.ndarray) -> pl.DataFrame:
    scored = (
        frame.with_columns(pl.Series("p", p))
        .with_columns(pl.col("p").sum().over("txid").alias("_sum"))
        .with_columns((pl.col("p") / pl.col("_sum").clip(lower_bound=1.0)).alias("p"))
    )
    ranked = scored.sort(["txid", "p", "peer_ip"], descending=[False, True, False])
    tx = ranked.group_by("txid", maintain_order=True).agg(
        pl.col("first_seen_us").first(),
        (pl.col("peer_ip").first() == pl.col("origin_peer_ip").first()).alias("l0_hit"),
        pl.col("origin_peer_ip").first().is_in(pl.col("peer_ip").head(3)).alias("l0_hit3"),
        pl.col("y").max().alias("source_present"),
        pl.col("p").sum().alias("candidate_mass"),
        pl.col("p").first().alias("best_candidate_p"),
        pl.col("p").slice(1, 1).first().fill_null(0.0).alias("second_candidate_p"),
        pl.col("n_candidates").first(),
        pl.col("n_observers_in_tx").first(),
        pl.col("n_announcements").sum().alias("total_announcements"),
        pl.col("peer_n_txids").mean().alias("mean_peer_history"),
        pl.col("payer_shared").max().alias("max_payer_history"),
        pl.col("is_tor_exit").any().alias("any_tor"),
        pl.col("true_origin_asn").first(),
    )
    operator = (
        scored.group_by("txid", "asn", maintain_order=True)
        .agg(
            pl.col("p").sum().alias("mass"),
            pl.col("asn_frac_rank_one").first().alias("prior"),
        )
        .with_columns((pl.col("mass") * (pl.col("prior") + 1e-12)).alias("weighted"))
    )
    op_ranked = operator.sort(["txid", "mass", "asn"], descending=[False, True, False])
    operator_tx = op_ranked.group_by("txid", maintain_order=True).agg(
        pl.col("asn").first().alias("predicted_asn"),
        pl.col("asn").head(3).alias("top3_asn"),
        pl.col("mass").first().alias("p1"),
        pl.col("mass").slice(1, 1).first().fill_null(0.0).alias("p2"),
    )
    weighted = operator.sort(["txid", "weighted", "asn"], descending=[False, True, False])
    weighted = weighted.group_by("txid", maintain_order=True).agg(
        pl.col("asn").first().alias("weighted_asn"),
        pl.col("weighted").first().alias("w1"),
        pl.col("weighted").slice(1, 1).first().fill_null(0.0).alias("w2"),
    )
    return (
        tx.join(operator_tx, on="txid")
        .join(weighted, on="txid")
        .with_columns(
            (pl.col("predicted_asn") == pl.col("true_origin_asn")).fill_null(False).alias("l1_hit"),
            pl.col("top3_asn")
            .list.contains(pl.col("true_origin_asn"))
            .fill_null(False)
            .alias("l1_hit3"),
            (pl.col("weighted_asn") == pl.col("true_origin_asn"))
            .fill_null(False)
            .alias("weighted_hit"),
            ((pl.col("p1") - pl.col("p2")) / (pl.col("p1") + pl.col("p2") + 1e-12)).alias(
                "separation"
            ),
            # exp(w1), exp(w2) produce tanh((w1-w2)/2): the legacy second-softmax flattening.
            ((pl.col("w1") - pl.col("w2")) / 2).tanh().alias("legacy_separation"),
        )
        .sort("first_seen_us", "txid")
    )


def selected_policy(tx: pl.DataFrame, val_boundary: int, test_boundary: int) -> dict[str, Any]:
    val = tx.filter(
        (pl.col("first_seen_us") >= val_boundary)
        & (pl.col("first_seen_us") + 5_000_000 < test_boundary)
    )
    test = tx.filter(pl.col("first_seen_us") >= test_boundary)
    curves = []
    for col, hit, blanket_tor in (
        ("separation", "l1_hit", False),
        ("separation", "l1_hit", True),
        ("legacy_separation", "weighted_hit", True),
    ):
        floors = (
            0.0,
            0.0025,
            0.005,
            0.01,
            0.02,
            0.04,
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            0.95,
        )

        def answered(
            data: pl.DataFrame, floor: float, col: str = col, blanket_tor: bool = blanket_tor
        ) -> pl.DataFrame:
            condition = (pl.col(col) >= floor) & (pl.col("n_observers_in_tx") >= 2)
            if blanket_tor:
                condition = condition & ~pl.col("any_tor")
            return data.filter(condition)

        eligible = []
        for floor in floors:
            a = answered(val, floor)
            if a.height >= 100 and float(a[hit].mean()) >= 0.9:
                eligible.append((a.height, floor, float(a[hit].mean())))
        choice = sorted(eligible, key=lambda row: (-row[0], row[1]))[0] if eligible else None
        a = answered(test, choice[1]) if choice else test.head(0)
        curves.append(
            {
                "aggregation": col,
                "blanket_tor": blanket_tor,
                "validation_selected_floor": choice[1] if choice else None,
                "validation_answered": choice[0] if choice else 0,
                "validation_precision": choice[2] if choice else None,
                "test_answered": a.height,
                "test_correct": int(a[hit].sum()) if a.height else 0,
                "test_precision": float(a[hit].mean()) if a.height else None,
                "test_coverage": a.height / test.height,
            }
        )
    return {
        "selection": ">=100 validation answers, >=90% observed precision; maximize coverage",
        "policies": curves,
    }


def unknown_experiment(tx: pl.DataFrame, cuts: dict[str, int]) -> dict[str, Any]:
    cols = [
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
    ]
    x = tx.select(cols).to_numpy().astype(np.float32)
    y = 1 - tx["source_present"].to_numpy()
    t = tx["first_seen_us"].to_numpy()
    decision_time = t + 5_000_000
    fit = (t >= cuts["fit"]) & (decision_time < cuts["cal"])
    cal = (t >= cuts["cal"]) & (decision_time < cuts["gate_cal"])
    val = (t >= cuts["gate_cal"]) & (decision_time < cuts["test"])
    test = t >= cuts["test"]
    model = lgb.train(
        {
            "objective": "binary",
            "num_leaves": 15,
            "min_data_in_leaf": 40,
            "learning_rate": 0.05,
            "num_threads": THREADS,
            "verbosity": -1,
            "deterministic": True,
            "force_col_wise": True,
            "seed": SEED,
        },
        lgb.Dataset(x[fit], label=y[fit]),
        num_boost_round=150,
    )
    raw = model.predict(x)
    p = calibrate(raw, y, cal)
    eligible = []
    for threshold in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.975, 0.99):
        chosen = val & (p >= threshold)
        n = int(chosen.sum())
        if n >= 50 and float(y[chosen].mean()) >= 0.90:
            eligible.append((n, threshold, float(y[chosen].mean())))
    choice = sorted(eligible, key=lambda row: (-row[0], row[1]))[0] if eligible else None
    decision = test & (p >= choice[1]) if choice else np.zeros(len(y), dtype=bool)
    novelty = IsolationForest(n_estimators=150, max_samples=512, random_state=SEED, n_jobs=THREADS)
    novelty.fit(x[t < cuts["fit"]])
    anomaly = -novelty.score_samples(x[test])
    novelty_metrics = ranking(y[test], anomaly)
    novelty_metrics.pop("brier", None)  # Isolation Forest scores are not probabilities.
    return {
        "features": cols,
        "supervised_absence": ranking(y[test], p[test]),
        "unsupervised_if_absence_ranking": novelty_metrics,
        "absence_threshold": choice[1] if choice else None,
        "test_absence_decisions": int(decision.sum()),
        "test_absence_precision": float(y[decision].mean()) if decision.any() else None,
        "warning": (
            "absent means source peer missing from five-second candidate set, "
            "not person absent from dataset"
        ),
        "stage_fit_tx": int(fit.sum()),
        "stage_cal_tx": int(cal.sum()),
        "stage_validation_tx": int(val.sum()),
    }


def main() -> None:
    started = time.perf_counter()
    normalised = ROOT / "normalised"
    config = json.loads((ROOT / "config.effective.json").read_text())
    ann = pl.read_parquet(normalised / "announcements.parquet")
    peers = pl.read_parquet(normalised / "peers.parquet")
    transactions = pl.read_parquet(normalised / "transactions.parquet")
    frame = causal.candidates(
        ann, peers, transactions, n_observers=config["network"]["n_observers"]
    )
    # Raw truth attaches only after observable feature construction. Early masks control fitting.
    truth_path = Path("ground_truth/agency-v2/origins.parquet")
    truth = pl.read_parquet(truth_path).select(
        "txid", pl.col("true_origin_ip").alias("origin_peer_ip"), "true_origin_asn"
    )
    frame = frame.join(truth, on="txid").with_columns(
        (pl.col("peer_ip") == pl.col("origin_peer_ip")).cast(pl.Int8()).alias("y")
    )
    t = frame["first_seen_us"].to_numpy()
    first, last = int(t.min()), int(t.max())
    cuts = {
        name: first + int((last - first) * frac)
        for name, frac in (("fit", 0.45), ("cal", 0.6), ("gate_cal", 0.65), ("test", 0.7))
    }
    decision = frame["decision_us"].to_numpy()
    fit = decision < cuts["fit"]
    cal = (t >= cuts["fit"]) & (decision < cuts["cal"])
    test = t >= cuts["test"]
    y = frame["y"].to_numpy()
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
    codes = frame["net_class_code"].to_numpy()
    x = np.column_stack([x, np.eye(6, dtype=np.float32)[codes]])
    scaler = StandardScaler().fit(x[fit])
    x = scaler.transform(x).astype(np.float32)
    if not np.isfinite(x).all():
        raise AssertionError("nonfinite model features")
    models: dict[str, Any] = {
        "logistic": LogisticRegression(max_iter=1000, random_state=SEED),
        "random_forest": RandomForestClassifier(
            n_estimators=120,
            max_depth=18,
            min_samples_leaf=20,
            max_samples=0.6,
            n_jobs=THREADS,
            random_state=SEED,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=120, max_depth=18, min_samples_leaf=20, n_jobs=THREADS, random_state=SEED
        ),
        "xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            min_child_weight=10,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1,
            tree_method="hist",
            n_jobs=THREADS,
            random_state=SEED,
        ),
        "lightgbm": None,
        "neural_mlp": None,
    }
    raw_predictions, calibrated, result = {}, {}, {}
    for name, model in models.items():
        begin = time.perf_counter()
        if name == "lightgbm":
            params = {
                "objective": "binary",
                "num_leaves": 31,
                "min_data_in_leaf": 40,
                "learning_rate": 0.05,
                "lambda_l2": 1,
                "num_threads": THREADS,
                "deterministic": True,
                "force_col_wise": True,
                "verbosity": -1,
                "seed": SEED,
            }
            model = lgb.train(params, lgb.Dataset(x[fit], label=y[fit]), num_boost_round=300)
            trained = time.perf_counter()
            raw = model.predict(x)
            parameters = {**params, "rounds": 300}
        elif name == "neural_mlp":
            raw, parameters = neural_fit_predict(x, y, fit)
            trained = time.perf_counter()
        else:
            model.fit(x[fit], y[fit])
            trained = time.perf_counter()
            raw = model.predict_proba(x)[:, 1]
            parameters = {
                k: (None if isinstance(v, float) and not np.isfinite(v) else v)
                for k, v in model.get_params().items()
            }
        predict_end = time.perf_counter()
        p = calibrate(raw, y, cal)
        raw_predictions[name], calibrated[name] = raw, p
        tx = transaction_results(frame, p)
        tx_test = tx.filter(pl.col("first_seen_us") >= cuts["test"])
        result[name] = {
            "parameters": parameters,
            "candidate_test": ranking(y[test], p[test]),
            "l0_top1": float(tx_test["l0_hit"].mean()),
            "l0_top3": float(tx_test["l0_hit3"].mean()),
            "l1_direct_top1": float(tx_test["l1_hit"].mean()),
            "l1_direct_top3": float(tx_test["l1_hit3"].mean()),
            "l1_prior_weighted_top1": float(tx_test["weighted_hit"].mean()),
            "policies": selected_policy(tx, cuts["cal"], cuts["test"]),
            "fit_seconds": trained - begin,
            "predict_seconds": predict_end - trained,
            # Raw parent outputs are genuinely out of fit on the gate's training block.
            # Using Platt outputs here would reuse that block's labels in parent calibration.
            "absence": (
                unknown_experiment(transaction_results(frame, raw), cuts)
                if name == "lightgbm"
                else None
            ),
        }
        if model is not None:
            result[name]["serialized_model_bytes"] = len(pickle.dumps(model))
        if name == "neural_mlp":
            result[name]["timing_note"] = (
                "fit_seconds includes neural prediction; predict_seconds is not a latency measure"
            )
        log(
            "causal_origin_model_complete",
            model=name,
            l1_direct_top1=result[name]["l1_direct_top1"],
            production_changes=False,
        )
        gc.collect()
    for name, p in (
        ("gbm_mean", 0.5 * (calibrated["lightgbm"] + calibrated["xgboost"])),
        ("logit_stack", None),
    ):
        if p is None:
            stack_x = np.column_stack(
                [logit(raw_predictions[n]) for n in ("lightgbm", "xgboost", "neural_mlp")]
            )
            stack = LogisticRegression(max_iter=1000, random_state=SEED).fit(stack_x[cal], y[cal])
            p = stack.predict_proba(stack_x)[:, 1]
        tx = transaction_results(frame, p)
        ts = tx.filter(pl.col("first_seen_us") >= cuts["test"])
        result[name] = {
            "candidate_test": ranking(y[test], p[test]),
            "l0_top1": float(ts["l0_hit"].mean()),
            "l0_top3": float(ts["l0_hit3"].mean()),
            "l1_direct_top1": float(ts["l1_hit"].mean()),
            "l1_direct_top3": float(ts["l1_hit3"].mean()),
            "policies": selected_policy(tx, cuts["cal"], cuts["test"]),
        }
    report = {
        "run": "agency-v2",
        "seed": SEED,
        "features": list(FEATURES),
        "categorical_encoding": (
            "six-way one-hot network class; numeric log transforms; scaler fits early train only"
        ),
        "horizon_us": 5_000_000,
        "boundaries_us": cuts,
        "n_candidates": frame.height,
        "n_transactions": frame["txid"].n_unique(),
        "source_in_window_test_ceiling": float(tx_test["source_present"].mean()),
        "inputs": {
            str(p): digest(p)
            for p in (
                normalised / "announcements.parquet",
                normalised / "peers.parquet",
                normalised / "transactions.parquet",
                truth_path,
            )
        },
        "models": result,
        "seconds": time.perf_counter() - started,
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "limitations": [
            "single synthetic world; reused research test time block",
            "fixed/versioned peer enrichment assumed; changing enrichment needs its own history",
            "observation horizon excludes later source announcements by design",
            "candidate presence measures source-peer coverage, not a person's dataset membership",
            "absence gate trains on raw out-of-fit parent scores, not same-block Platt outputs",
        ],
        "code_hashes": {str(p): digest(p) for p in (Path(__file__), Path(causal.__file__))},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    log(
        "causal_origin_benchmark_complete",
        output=str(OUT),
        seconds=report["seconds"],
        production_changes=True,
        note="new opt-in causal feature API; stage default unchanged",
    )


if __name__ == "__main__":
    main()
