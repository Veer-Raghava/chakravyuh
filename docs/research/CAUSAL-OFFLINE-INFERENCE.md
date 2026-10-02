# Opt-in causal offline inference — R32 / R33

Date:2026-10-01. Implemented `src/chakravyuh/buddhi/causal_inference.py`, a working CPU scorer separate from the standard stage. No evaluation labels, owner answer keys or research modules are imported by its inference implementation. XGBoost is loaded only when this optional engine runs.

## Portable artifact

`research/bitcoin/export_causal_artifact.py` converts the known local frozen XGBoost/scaler/Platt fit into native `model.json` plus `manifest.json`. The export has23feature names in exactorder, signed-log/fit-only scaler means/scales, ownershipthreshold.30, model SHA256, calibration coefficient/intercept/**arithmetic dtype**, training target, source artifact SHA256 and runtimeXGBoost version. It has no automatic confident-alert threshold. It does not serialize training rows or answer keys into the deployed model.

The runtime verifies schema/feature order/model digest/scaler validity, builds a point-in-time ownership snapshot, transforms observations, predicts, calibrates using the exported precision and generates nativeTreeSHAP. SHAP values are **raw log-odds contributions**, includingbias; the runtime checks that they sum to raw margin. They are not additive contributions in calibrated-probability space.

## Actual verification

All ten canonical windows replayed against the earlier matched-windowXGBoostscores: maximum difference **0.0 in every window**. Combined 143,044subject-window rows;26.32s including feature construction andTreeSHAP. This is implementation replay, not new model-performance evidence.

The first verifier accidentally used the saved transfer file containing only the finalthreewindows; the row-count assertion correctly failed. It was changed to the all-ten-window matched benchmark file. The initial portable calibrator also cast arithmetic tofloat64 while the fittedsklearncalibrator used float32, producing a3.94e-8score difference. Exporting/retainingdtype fixed it exactly. These verification failures and fixes are audit entries, not concealed model improvements.

A separate subprocess actually ran the CLI in a temporary directory containing **only two observation Parquets and two model files**. It produced12,206scores, subject membership, ownership edges andrun manifest, with no stdout. There was no copied answer-key or evaluation tree. Its source imports the installed package via explicitPYTHONPATH; this is a stripped-input check, not a complete packaged-dashboard shippingtest. No network retrieval or GPU was needed.

## Run it

The optional XGBoost3.2.0dependency is installed in the current environment. A shippingpackage still needs to include it explicitly. The ordinary LightGBM stage is unaffected.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --offline --no-sync python research/bitcoin/export_causal_artifact.py

UV_CACHE_DIR=/tmp/uv-cache uv run --offline --no-sync python -m chakravyuh.buddhi.causal_inference \
  --normalised data/generated/agency-v2/normalised \
  --model research/bitcoin/results/causal-inference-artifact \
  --start-us 1767568578827584 \
  --end-us 1767617601829850 \
  --output /tmp/causal-aml-demo
```

Output must be a **new directory**; the CLI refuses an existing destination. Times above reproduce the canonicalwindow7. For anothercapture, explicitly choose an observationwindow; do not assume its timing regime matches the model's training. Source/destination identities are inferredsubjects, not verifiedpeople.

Files: `scores.parquet` containssubject ID, raw/risk scores and per-feature SHAP margin columns; `members.parquet` preserves snapshot address membership; `ownership_edges.parquet` supplies inferred relationship evidence; `manifest.json` identifiesmodel/snapshot/score semantics. No truth labels are output. Risk scores are historicallycalibrated campaign-activity scores with unvalidatedshift behavior, not guilt probabilities or a90%precisionpromise.

## Remaining integration

Persist every ownershipclaim in the standard JAAL stage; route the selected causalengine into standard BUDDHI/VAANI artifact contracts; add feature definitions and windowavailability to explanations; deduplicate alerts without hiddencontroller keys; adapt DRISHTI to versionedmodel/evidence metadata; include optionaldependencies in offline packaging. The existing APIquarantine violation still prevents a full-release-green claim. This opt-in scorer is usable, but the entireapplication remodel is not complete.
