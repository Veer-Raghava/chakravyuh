## S01 · MAYAJAAL chain layer

**Goal.** An entity population and a real UTXO ledger, with the awkward cases emergent rather
than injected.

**Reads.** `docs/MAYAJAAL-SPEC.md` Layers 1 and 2, `run_config.json`.

**Writes.** `data/generated/<run>/` chain state, `ground_truth/entities.parquet`,
`ground_truth/campaigns.parquet` including `change_index` and `heuristic_violation`.
`tests/test_chain.py`.

**Definition of done.** `make verify-s01`

**Known traps.** Floats anywhere, including internally. A change output always at a fixed index,
which makes the change heuristic trivially perfect and therefore worthless. A normal distribution
for value. Coin selection that always spends one input, leaving the multi-input heuristic nothing
to find. Any parameter hardcoded instead of read from `run_config.json`.

---
