"""Export actual frozen strong graph-context trees as portable inference artifacts."""

import json
import shutil
from pathlib import Path

import joblib
from common import digest, log

from chakravyuh.buddhi.relational_inference import FEATURES


def main():
    root = Path("research/bitcoin/results")
    frozen = joblib.load(root / "rich-relation-transfer/frozen-transforms.joblib")
    log("relational_artifact_export_started", models=["cioh", "address"])
    for mode, parent in [
        ("cioh", "temporal-hetero-extended"),
        ("address", "address-atomic-benchmark"),
    ]:
        out = root / "relational-inference-artifacts" / mode
        out.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(
            root / f"relational-summary-controls/{mode}/xgboost_distribution_features.json",
            out / "model.json",
        )
        scalers = joblib.load(root / parent / "scalers.joblib")
        mapping = frozen["calibrators"][mode]["xgboost_distribution_features"]
        manifest = dict(
            schema_version=1,
            features=list(FEATURES),
            partition_mode="address" if mode == "address" else "heuristic",
            model_sha256=digest(out / "model.json"),
            scalers={
                k: dict(mean=v.mean_.tolist(), scale=v.scale_.tolist()) for k, v in scalers.items()
            },
            platt_coefficient=float(mapping.coef_[0, 0]),
            platt_intercept=float(mapping.intercept_[0]),
            platt_dtype=str(mapping.coef_.dtype),
            exporter_sha256=digest(__file__),
            experimental=True,
            automatic_alert_threshold=None,
        )
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        log("relational_artifact_exported", mode=mode, path=str(out))


if __name__ == "__main__":
    main()
