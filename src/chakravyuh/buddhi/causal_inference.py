"""Opt-in offline causal AML scoring with explicit windows and portable frozen artifacts.

This experimental entry point does not replace the standard stage. XGBoost is an optional
runtime dependency loaded only when this engine is invoked. Scores rank observed leads;
their calibration on synthetic history does not establish future-world probabilities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl
from numpy.typing import NDArray
from scipy.special import expit

from chakravyuh.buddhi import snapshot
from chakravyuh.jaal import provenance


def transform(
    table: pl.DataFrame, means: NDArray[np.float64], scales: NDArray[np.float64]
) -> NDArray[np.float32]:
    """Frozen signed-log and fit-only scaling, in the versioned feature order."""
    width = len(snapshot.SNAPSHOT_FEATURES)
    if means.shape != (width,) or scales.shape != (width,):
        raise ValueError("feature scaler width differs from the causal feature schema")
    if not np.isfinite(means).all() or not np.isfinite(scales).all() or (scales <= 0).any():
        raise ValueError("feature scaler must be finite with positive scales")
    values = table.select(snapshot.SNAPSHOT_FEATURES).to_numpy().astype(np.float64)
    values = np.nan_to_num(values, nan=0.0)
    values = np.sign(values) * np.log1p(np.abs(values))
    return ((values - means) / scales).astype(np.float32)


def score(
    normalised: Path, model_dir: Path, *, start_us: int, end_us: int
) -> tuple[pl.DataFrame, snapshot.Snapshot, dict[str, object]]:
    """Infer only from observation artifacts; model metadata fixes the ownership recipe."""
    import xgboost as xgb

    metadata = json.loads((model_dir / "manifest.json").read_text())
    if metadata.get("schema_version") != 1:
        raise ValueError("unsupported causal model artifact version")
    if metadata.get("features") != list(snapshot.SNAPSHOT_FEATURES):
        raise ValueError("model feature names/order differ from the causal feature schema")
    model_path = model_dir / "model.json"
    model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if metadata.get("model_sha256") != model_hash:
        raise ValueError("model digest differs from its manifest")
    transactions = pl.read_parquet(normalised / "transactions.parquet")
    addresses = pl.read_parquet(normalised / "addresses.parquet")
    view = snapshot.build(
        transactions,
        addresses,
        provenance.ownership_evidence(transactions),
        start_us=start_us,
        end_us=end_us,
        threshold=float(metadata["ownership_threshold"]),
    )
    x = transform(
        view.table,
        np.asarray(metadata["scaler_mean"], dtype=np.float64),
        np.asarray(metadata["scaler_scale"], dtype=np.float64),
    )
    if len(x):
        model = xgb.Booster(params={"nthread": 4})
        model.load_model(model_path)
        matrix = xgb.DMatrix(x)
        raw = model.predict(matrix)
        contributions = model.predict(matrix, pred_contribs=True)
        margin = model.predict(matrix, output_margin=True)
    else:
        raw = np.empty(0, dtype=np.float32)
        contributions = np.empty((0, len(snapshot.SNAPSHOT_FEATURES) + 1), dtype=np.float32)
        margin = raw
    clipped = np.clip(raw, 1e-6, 1 - 1e-6)
    logits = np.log(clipped / (1 - clipped))
    if metadata.get("platt_dtype") not in ("float32", "float64"):
        raise ValueError("unsupported Platt arithmetic precision")
    dtype = np.dtype(metadata["platt_dtype"])
    calibrated = expit(
        logits.astype(dtype) * np.asarray(metadata["platt_coefficient"], dtype=dtype)
        + np.asarray(metadata["platt_intercept"], dtype=dtype)
    )
    if not np.allclose(contributions.sum(axis=1), margin, atol=1e-4, rtol=1e-4):
        raise ValueError("TreeSHAP contributions do not reconstruct the raw model margin")
    columns: list[pl.Series] = [pl.Series("raw_score", raw), pl.Series("risk_score", calibrated)]
    columns.extend(
        pl.Series(f"shap_margin_{name}", contributions[:, i])
        for i, name in enumerate(snapshot.SNAPSHOT_FEATURES)
    )
    columns.append(pl.Series("shap_margin_bias", contributions[:, -1]))
    scores = (
        view.table.select("subject_id")
        .with_columns(columns)
        .sort(["risk_score", "subject_id"], descending=[True, False])
    )
    run_metadata: dict[str, object] = {
        "engine": "experimental-causal-xgboost",
        "xgboost_version": xgb.__version__,
        "feature_schema": list(snapshot.SNAPSHOT_FEATURES),
        "calibration_precision": metadata["platt_dtype"],
        "inference_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_sha256": {
            name: hashlib.sha256((normalised / name).read_bytes()).hexdigest()
            for name in ("transactions.parquet", "addresses.parquet")
        },
        "model_sha256": model_hash,
        "artifact_manifest_sha256": hashlib.sha256(
            (model_dir / "manifest.json").read_bytes()
        ).hexdigest(),
        "start_us": start_us,
        "end_us": end_us,
        "ownership_threshold": metadata["ownership_threshold"],
        "score_meaning": "historically calibrated campaign-activity ranking; shift unvalidated",
        "explanation_space": "TreeSHAP contributions to raw model log-odds, including bias",
        "subject_semantics": "inferred address group at window end; not verified controller",
    }
    return scores, view, run_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalised", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--start-us", type=int, required=True)
    parser.add_argument("--end-us", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new directory")
    scores, view, metadata = score(
        args.normalised, args.model, start_us=args.start_us, end_us=args.end_us
    )
    args.output.mkdir(parents=True)
    scores.write_parquet(args.output / "scores.parquet")
    view.members.write_parquet(args.output / "members.parquet")
    view.edges.write_parquet(args.output / "ownership_edges.parquet")
    (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
