"""Export the known local frozen research fit into a label-free portable model artifact."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import xgboost
from common import digest, log


def main():
    source = Path("research/bitcoin/results/buddhi-world-transfer/frozen-canonical-xgboost.joblib")
    bundle = joblib.load(source)
    output = Path("research/bitcoin/results/causal-inference-artifact")
    output.mkdir(exist_ok=True)
    bundle["model"].save_model(output / "model.json")
    manifest = {
        "schema_version": 1,
        "features": list(bundle["features"]),
        "ownership_threshold": 0.3,
        "model_sha256": digest(output / "model.json"),
        "scaler_mean": bundle["scaler"].mean_.tolist(),
        "scaler_scale": bundle["scaler"].scale_.tolist(),
        "platt_coefficient": float(bundle["calibrator"].coef_[0, 0]),
        "platt_intercept": float(bundle["calibrator"].intercept_[0]),
        "platt_dtype": bundle["calibrator"].coef_.dtype.name,
        "parent_bundle_sha256": digest(source),
        "exporter_sha256": digest(__file__),
        "xgboost_version": xgboost.__version__,
        "target": "in-window observed synthetic campaign participation",
        "experimental": True,
        "automatic_confident_alert_threshold": None,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    log("causal_model_artifact_exported", output=str(output), model_sha256=manifest["model_sha256"])


if __name__ == "__main__":
    main()
