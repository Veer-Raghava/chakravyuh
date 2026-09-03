## S06 · SHASTRA origin estimator

**Goal.** Per transaction, a calibrated `P(originator)` for each announcing peer, with a runner-up,
a margin, and an explicit abstain. Plus typology heuristics and entity typing.

**Reads.** `normalised/`, `graph/`. Ground truth only inside `src/chakravyuh/eval/`.

**Writes.** `signals/origin_estimates.parquet` one row per candidate peer per txid,
`signals/typology_hits.parquet`, `signals/entity_types.parquet`, `_meta.json`, the recorded
first-seen baseline accuracy. `tests/test_shastra.py`.

**Definition of done.** `make verify-s06`, which asserts the real estimator beats the recorded
first-seen baseline on top-1 accuracy at `observer_fraction` 0.10.

**Known traps.** Renormalising `p_origin` to sum to one, which destroys the ability to express
"none of these peers is the originator". Building abstention later, which means never. Skipping the
baseline, which leaves no way to know whether the sophistication helped. Reporting a single accuracy
number instead of a curve over `observer_fraction` split by traffic type. Touching ground truth
outside `eval/`.

---
