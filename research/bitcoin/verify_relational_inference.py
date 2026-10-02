"""Verify independent label-free NumPy port against saved scores and Torch features."""

import json
import time
from pathlib import Path

import numpy as np
import polars as pl
from common import digest, log
from relational_summary_controls import feature_matrix
from temporal_hetero_benchmark import dataset

from chakravyuh.buddhi import relational_inference as native


def main():
    started = time.perf_counter()
    root = Path("research/bitcoin/results")
    normalised = Path("data/generated/agency-v2/normalised")
    frames = {
        n: pl.read_parquet(normalised / f"{n}.parquet")
        for n in ("transactions", "addresses", "announcements", "peers")
    }
    checks = []
    log("relational_port_verification_started", modes=["cioh", "address"], windows=10)
    for mode in ("cioh", "address"):
        artifact = root / "relational-inference-artifacts" / mode
        metadata = json.loads((artifact / "manifest.json").read_text())
        graphs, _ = dataset(partition_mode=metadata["partition_mode"])
        expected = feature_matrix(graphs)
        reference = pl.read_parquet(
            root
            / f"relational-summary-controls/{mode}/xgboost_distribution_features-scores.parquet"
        )
        offset = 0
        for g in graphs:
            values, view = native.build(
                frames["transactions"],
                frames["addresses"],
                frames["announcements"],
                frames["peers"],
                metadata["scalers"],
                start_us=g["start_us"],
                end_us=g["end_us"],
                partition_mode=metadata["partition_mode"],
            )
            error = float(np.max(np.abs(values - expected[offset : offset + len(values)])))
            assert error == 0.0, (mode, g["window_id"], "feature error", error)
            scores, _, _ = native.score(
                normalised, artifact, start_us=g["start_us"], end_us=g["end_us"]
            )
            saved = reference.filter(pl.col("window_id") == g["window_id"]).sort("subject_id")
            current = scores.sort("subject_id")
            assert current["subject_id"].equals(saved["subject_id"])
            score_error = float(
                np.max(np.abs(current["risk_score"].to_numpy() - saved["score"].to_numpy()))
            )
            assert score_error == 0.0, (mode, g["window_id"], "score error", score_error)
            checks.append(
                dict(
                    mode=mode,
                    window=g["window_id"],
                    rows=len(values),
                    feature_error=error,
                    score_error=score_error,
                )
            )
            offset += len(values)
        empty, _, _ = native.score(
            normalised, artifact, start_us=g["start_us"] - 10**18, end_us=g["start_us"] - 10**18 + 1
        )
        assert empty.height == 0
    report = dict(
        checks=checks,
        seconds=time.perf_counter() - started,
        source_sha256=digest(__file__),
        inference_sha256=digest(native.__file__),
        empty_windows_passed=True,
        statement="Port correctness and SHAP reconstruction, not new model performance.",
    )
    (root / "relational-inference-replay.json").write_text(json.dumps(report, indent=2) + "\n")
    log("relational_port_verification_complete", seconds=report["seconds"])


if __name__ == "__main__":
    main()
