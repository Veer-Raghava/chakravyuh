"""Isolation Forest, trained autoencoder and label-independent auxiliary risk fusion."""

from __future__ import annotations

import json
import time
from pathlib import Path

import buddhi_snapshot_benchmark as benchmark
import joblib
import numpy as np
import polars as pl
import torch
from buddhi_world_transfer import activity, matrix, windows
from common import digest, log, ranking
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from chakravyuh.jaal import provenance

OUT = Path("research/bitcoin/results/aml-anomaly-benchmark")


def metric(y, p, probability=False):
    r = ranking(y, p)
    if not probability:
        r.pop("brier", None)
    return r


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.manual_seed(42)
    root = Path("data/generated/agency-v2/normalised")
    tx = pl.read_parquet(root / "transactions.parquet")
    addresses = pl.read_parquet(root / "addresses.parquet")
    labels = (
        pl.read_parquet("ground_truth/agency-v2/entities.parquet")
        .select(pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address"))
        .explode("address")
    )
    benchmark.ACTIVITY = activity(
        tx,
        labels,
        pl.read_parquet("ground_truth/agency-v2/campaigns.parquet").select("entity_ids", "txids"),
    )
    frame = benchmark.labelled_snapshots(
        tx, addresses, provenance.ownership_evidence(tx), labels, 0.3, windows(tx)
    )
    bundle = joblib.load(
        "research/bitcoin/results/buddhi-world-transfer/frozen-canonical-xgboost.joblib"
    )
    x = bundle["scaler"].transform(matrix(frame)).astype(np.float32)
    phase = frame["phase"].to_numpy()
    fit = phase == "fit"
    cal = phase == "cal"
    test = phase == "test"
    val = phase == "val"
    y = frame["y"].to_numpy()
    # Raw parent output prevents reuse of its Platt-calibration labels in the stacking inputs.
    raw = bundle["model"].predict_proba(x)[:, 1]
    raw = np.clip(raw, 1e-6, 1 - 1e-6)
    parent = np.log(raw / (1 - raw))
    signals = {}
    models = {}
    for name, mask in (("isolation_all", fit), ("isolation_known_negative", fit & (y == 0))):
        model = IsolationForest(n_estimators=200, max_samples=1024, n_jobs=4, random_state=42)
        model.fit(x[mask])
        signals[name] = -model.score_samples(x)
        models[name] = model
        joblib.dump(model, OUT / f"{name}.joblib")
    net = torch.nn.Sequential(
        torch.nn.Linear(x.shape[1], 64),
        torch.nn.ReLU(),
        torch.nn.Linear(64, 8),
        torch.nn.ReLU(),
        torch.nn.Linear(8, 64),
        torch.nn.ReLU(),
        torch.nn.Linear(64, x.shape[1]),
    )
    opt = torch.optim.AdamW(net.parameters(), lr=0.001, weight_decay=0.001)
    training = torch.tensor(x[fit])
    for _ in range(40):
        for ids in torch.randperm(len(training)).split(2048):
            opt.zero_grad()
            loss = torch.mean((net(training[ids]) - training[ids]) ** 2)
            loss.backward()
            opt.step()
    net.eval()
    with torch.no_grad():
        signals["autoencoder_all"] = np.concatenate(
            [
                torch.mean((net(torch.tensor(b)) - torch.tensor(b)) ** 2, dim=1).numpy()
                for b in np.array_split(x, 20)
            ]
        )
    torch.save(net.state_dict(), OUT / "autoencoder.pt")
    result = {}
    scores = {}
    for name, p in signals.items():
        result[name] = {"validation": metric(y[val], p[val]), "test": metric(y[test], p[test])}
        scores[name] = p
    # Fusion trains on the later calibration block only; classifiers/anomaly encoders fit earlier.
    for name, cols in (
        ("parent_only", [parent]),
        ("parent_if", [parent, signals["isolation_all"]]),
        ("parent_ae", [parent, signals["autoencoder_all"]]),
        ("parent_if_ae", [parent, signals["isolation_all"], signals["autoencoder_all"]]),
    ):
        z = np.column_stack(cols)
        scaler = StandardScaler().fit(z[cal])
        z = scaler.transform(z)
        model = LogisticRegression(max_iter=1000, random_state=42).fit(z[cal], y[cal])
        p = model.predict_proba(z)[:, 1]
        result[name] = {
            "validation": metric(y[val], p[val], True),
            "test": metric(y[test], p[test], True),
            "coefficients": model.coef_.tolist(),
        }
        scores[name] = p
        joblib.dump({"model": model, "scaler": scaler}, OUT / f"{name}.joblib")
    for name, p in scores.items():
        frame.select("subject_id", "window_id", "phase", "y").with_columns(
            pl.Series("score", p)
        ).write_parquet(OUT / f"{name}-scores.parquet", compression="zstd")
    report = {
        "models": result,
        "validation_selected_fusion": max(
            (k for k in result if k.startswith("parent_")),
            key=lambda k: (result[k]["validation"]["p_at_20"], result[k]["validation"]["ap"]),
        ),
        "seconds": time.perf_counter() - begin,
        "autoencoder": {
            "layers": [x.shape[1], 64, 8, 64, x.shape[1]],
            "epochs": 40,
            "batch_size": 2048,
            "learning_rate": 0.001,
            "weight_decay": 0.001,
            "parameters": sum(p.numel() for p in net.parameters()),
        },
        "limitations": [
            "Consumed canonical synthetic world, no independent anomaly confirmation.",
            "High reconstruction/IF score means unusual features, not illicitness.",
            "Known-negative IF uses training labels; all-data IF/AE do not filter by labels.",
            "Fusion fit uses later cal labels and raw parent scores, not recycled Platt outputs.",
            "No claim that source absence and AML novelty are the same task.",
            "No canonical anomaly/default/model promotion.",
        ],
        "hashes": {
            str(p): digest(p)
            for p in (
                Path(__file__),
                Path(
                    "research/bitcoin/results/buddhi-world-transfer/frozen-canonical-xgboost.joblib"
                ),
            )
        },
    }
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    log(
        "aml_anomaly_benchmark_complete",
        selected=report["validation_selected_fusion"],
        models=result,
        production_changes=False,
    )


if __name__ == "__main__":
    main()
