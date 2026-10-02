"""Exploratory negative-class tail p-values with per-window multiplicity controls.

Uses fixed model scores and calibration negatives only, never test labels for selection.
These are conditional-assumption diagnostics, not certified guarantees for dependent,
temporally shifted Bitcoin subjects. This is not a reproduction of SCoRE or cfBH.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import polars as pl
from common import digest, log

ROOT = Path("research/bitcoin/results")


def select(p, method, alpha):
    m = len(p)
    if not m:
        return np.zeros(0, dtype=bool)
    if method == "bonferroni":
        return p <= alpha / m
    correction = np.sum(1 / np.arange(1, m + 1)) if method == "by" else 1.0
    ordered = np.sort(p)
    eligible = np.flatnonzero(ordered <= alpha * np.arange(1, m + 1) / (m * correction))
    return p <= ordered[eligible[-1]] if len(eligible) else np.zeros(m, dtype=bool)


def main():
    matched_path = ROOT / "buddhi-matched-window-benchmark.json"
    transfer_path = ROOT / "buddhi-world-transfer.json"
    matched = json.loads(matched_path.read_text())
    transfer = json.loads(transfer_path.read_text())
    score_path = Path(matched["models"]["cioh"]["xgboost"]["research_score_artifact"])
    scores = pl.read_parquet(score_path)
    # A shared positive-slope logistic transform preserves raw XGBoost ordering. Therefore
    # these tail ranks are identical to ranks from the train-only model, despite Platt fitting.
    bundle = joblib.load(transfer["frozen_model_artifact"])
    slope = float(bundle["calibrator"].coef_[0, 0])
    if slope <= 0:
        raise ValueError("calibration transform is not strictly increasing")
    negatives = np.sort(scores.filter((pl.col("phase") == "cal") & (pl.col("y") == 0))["score"])
    n = len(negatives)
    paths = {
        "canonical_validation": score_path,
        "canonical_test": Path(transfer["canonical_test"]["score_artifact"]),
        **{f"seed{w['seed']}": Path(w["score_artifact"]) for w in transfer["transfer_worlds"]},
    }
    results = {}
    for world, path in paths.items():
        data = pl.read_parquet(path)
        if world == "canonical_validation":
            data = data.filter(pl.col("phase") == "val")
        output = {}
        for window_id in data["window_id"].unique().sort():
            part = data.filter(pl.col("window_id") == window_id)
            # Conservative ties: count all calibration negatives scoring at least this high.
            p = (1 + n - np.searchsorted(negatives, part["score"].to_numpy(), side="left")) / (
                n + 1
            )
            methods = {}
            for method, alpha in (("bonferroni", 0.05), ("by", 0.1), ("bh", 0.1)):
                chosen = select(p, method, alpha)
                labels = part["y"].to_numpy()
                count, hits = int(chosen.sum()), int(labels[chosen].sum())
                methods[method] = {
                    "nominal_alpha": alpha,
                    "answered": count,
                    "correct": hits,
                    "false_alerts": count - hits,
                    "precision": hits / count if count else None,
                    "recall": hits / int(labels.sum()) if labels.sum() else None,
                }
            output[str(window_id)] = {
                "decisions": len(p),
                "positives": int(part["y"].sum()),
                "smallest_p": float(p.min()),
                "methods": methods,
            }
        results[world] = output
    out = ROOT / "snapshot-conformal-tail.json"
    out.write_text(
        json.dumps(
            {
                "calibration_negatives": n,
                "minimum_attainable_p": 1 / (n + 1),
                "positive_platt_slope": slope,
                "results": results,
                "recipe": "(1 + # calibration negatives scoring >= candidate) / (n_negatives + 1)",
                "limitations": [
                    "Not a reproduction of SCoRE or cfBH.",
                    "Null-conditional exchangeability and p-value validity are unverified.",
                    "Recurring controllers and changing snapshots introduce dependence.",
                    "BH requires suitable dependence conditions; these have not been established.",
                    "BY handles dependent valid p-values; it does not repair temporal shift.",
                    "Bonferroni requires valid p-values; no alerts does not establish utility.",
                    "Test labels are consumed only after selection for diagnostic accuracy counts.",
                    "Exploratory consumed-world analysis; no production policy change.",
                ],
                "hashes": {
                    str(path): digest(path)
                    for path in (
                        matched_path,
                        transfer_path,
                        score_path,
                        Path(transfer["frozen_model_artifact"]),
                        Path(__file__),
                        *paths.values(),
                    )
                },
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    log("snapshot_conformal_tail_complete", output=str(out), production_changes=False)


if __name__ == "__main__":
    main()
