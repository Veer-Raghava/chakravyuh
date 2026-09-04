## S01 · MAYAJAAL chain layer

**Goal.** An entity population and a real UTXO ledger, with the awkward cases emergent rather
than injected.

**Reads.** `docs/MAYAJAAL-SPEC.md` Layers 1 and 2, `run_config.json`.

**Writes.** `data/generated/<run>/chain/` (transactions, endowment, blocks) with its own
`_meta.json` beside them, and `data/generated/<run>/config.effective.json`, which is the template
plus the CLI overrides as they actually ran and is not the same file as the `run_config.json`
template at the repository root. One sibling truth directory per run:
`ground_truth/<run>/entities.parquet`, `ground_truth/<run>/campaigns.parquet` (zero rows at S01;
campaigns are Layer 4, which S02 builds), and `ground_truth/<run>/chain_txs.parquet` holding
`change_index` and `heuristic_violation` per transaction. Those two are *not* campaign columns —
`campaigns.parquet` keeps the seven columns `docs/DATA-CONTRACTS.md` section 2 freezes, and
per-transaction truth has a file of its own. The truth directory carries its own `_meta.json`, so
section 10 is satisfied on both sides and the observable manifest never names the answer key.
`tests/test_chain.py`.

**Definition of done.** `make verify-s01`, which calls `make verify-quarantine` first.

**Known traps.** Floats anywhere, including internally. A change output always at a fixed index,
which makes the change heuristic trivially perfect and therefore worthless. A normal distribution
for value. Coin selection that always spends one input, leaving the multi-input heuristic nothing
to find. Any parameter hardcoded instead of read from `run_config.json`. An `--out` whose last
component is not a plain name, or one outside the repository: both are refused before anything is
written, because the answer key directory is derived from that name.

---
