"""Replay saved scores through the label-free inference module and verify TreeSHAP sums."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import polars as pl
from buddhi_world_transfer import windows
from common import digest, log

from chakravyuh.buddhi import causal_inference

ROOT = Path("research/bitcoin/results")


def main():
    begin = time.perf_counter()
    normalised = Path("data/generated/agency-v2/normalised")
    model = ROOT / "causal-inference-artifact"
    expected = pl.read_parquet(ROOT / "buddhi-matched-window-benchmark-scores/cioh-xgboost.parquet")
    rows = []
    tx = pl.read_parquet(normalised / "transactions.parquet")
    # Labels are only in the saved comparison file, never passed to the inference function.
    for window_id, (_, start, end) in enumerate(windows(tx)):
        scores, _, _ = causal_inference.score(normalised, model, start_us=start, end_us=end)
        old = expected.filter(pl.col("window_id") == window_id).select("subject_id", "score")
        joined = scores.join(old, on="subject_id")
        assert joined.height == scores.height == old.height
        error = float(np.max(np.abs(joined["risk_score"].to_numpy() - joined["score"].to_numpy())))
        assert error < 1e-12, (window_id, error)
        assert "y" not in scores.columns and "owner" not in scores.columns
        rows.append({"window": window_id, "rows": joined.height, "max_score_error": error})
    first = int(tx["first_seen_us"].min())
    empty, _, _ = causal_inference.score(normalised, model, start_us=first - 1000, end_us=first - 1)
    assert empty.height == 0
    assert len(empty.columns) == 27
    report = {
        "windows": rows,
        "seconds": time.perf_counter() - begin,
        "source_sha256": digest(__file__),
        "inference_sha256": digest(causal_inference.__file__),
        "model_manifest_sha256": digest(model / "manifest.json"),
        "tree_shap_margin_sums_checked_by_inference": True,
        "empty_window_checked": True,
        "limitations": [
            "Exact score replay is implementation verification, not independent model evaluation.",
            "Standard stages/dashboard remain unchanged; optional XGBoost dependency required.",
        ],
    }
    (ROOT / "causal-inference-replay.json").write_text(json.dumps(report, indent=2) + "\n")
    log("causal_inference_replay_verified", windows=rows)


if __name__ == "__main__":
    main()
