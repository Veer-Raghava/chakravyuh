## S02 · MAYAJAAL network layer

**Goal.** Gossip every transaction across a peer graph with independent per-peer relay delays,
record only what a partial observer would have seen, and export in the problem statement schema.

**Reads.** `docs/MAYAJAAL-SPEC.md` Layers 3, 4, 5 and 6, `regions.yaml`,
`data/generated/<run>/config.effective.json` and `data/generated/<run>/chain/`. Never
`ground_truth/`. The entity population S02 needs is not loaded from the answer key; it is derived
by calling the same builder S01 used, with the same seed, which is why the seed is recorded in
`config.effective.json`.

**Writes.** `capture/part-*.csv.zst` sharded on time, `capture_json/`, `capture_xml/sample.xml`,
`ground_truth/<run>/origins.parquet` with exactly one true originator per announced txid and a
`broadcast_mode` per txid, `validation/report.json` and `report.md`. `tests/test_network.py`.

Announced, not simply on the chain. A coinbase transaction is minted by the miner inside its own
block and is never relayed as a loose transaction, so it has no originating peer and gets no row
here. An answer key that invented one would be asking S03 to attribute a broadcast that never
happened.

**Definition of done.** `make verify-s02 && make validate-data`, then the `truth-checker` subagent
returns `USABLE`.

**Required test, because a byte gate cannot see this.** The population S02 derives must equal
`ground_truth/<run>/entities.parquet` field for field, and `tests/test_network.py` must assert
that. Deriving the population a second time from the same seed is the price of not reading the
answer key, and the risk it buys is silent drift: change an entity builder and the two copies
disagree, every schema check still passes, and every announcement is then attributed to an entity
that does not exist in the answer key. The test is the only thing that notices. It is a test, so it
may read `ground_truth/`; nothing under `src/` may.

**Known traps.** A single delay per transaction, or sorting announcements before emitting them,
either of which produces a clean cascade and makes origin estimation trivially solvable. Recording
every announcement rather than only observed ones. Any ground-truth column name appearing in an
observable file. A `first announcement seen` leakage score outside roughly 0.15 to 0.6, which means
the benchmark is broken and must be fixed here rather than explained later.

---
