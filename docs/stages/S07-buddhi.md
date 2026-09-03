## S07 · BUDDHI models

**Goal.** A LightGBM baseline over the fused features with `p_origin` as an input, class-conditional
conformal calibration, and a strictly time-ordered evaluation.

**Reads.** `signals/`, `graph/`. Ground truth only inside `src/chakravyuh/eval/`.

**Writes.** `scores/wallet_scores.parquet`, `scores/calibration.parquet`,
`scores/eval_report.json` with `by_observer_fraction`, `by_traffic_type` and `baseline_beaten`,
`docs/FEATURES.md` with a plain-English gloss per feature. `tests/test_buddhi.py`.

**Definition of done.** `make verify-s07`

**Known traps.** A random train-test split. Features computed over the full time range even when the
rows are split correctly, which is where leakage actually lives. Reporting overall conformal
coverage while the minority class is badly under-covered. Starting the GNN in this session, which is
out of scope and will consume it. Precision-at-20 above 0.9, which means leakage rather than skill.

---
