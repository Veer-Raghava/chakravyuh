## S02 · MAYAJAAL network layer

**Goal.** Gossip every transaction across a peer graph with independent per-peer relay delays,
record only what a partial observer would have seen, and export in the problem statement schema.

**Reads.** `docs/MAYAJAAL-SPEC.md` Layers 3, 4, 5 and 6, `regions.yaml`, `run_config.json`,
`ground_truth/` from S01.

**Writes.** `capture/part-*.csv.zst` sharded on time, `capture_json/`, `capture_xml/sample.xml`,
`ground_truth/origins.parquet` with exactly one true originator and a `broadcast_mode` per txid,
`validation/report.json` and `report.md`. `tests/test_network.py`.

**Definition of done.** `make verify-s02 && make validate-data`, then the `truth-checker` subagent
returns `USABLE`.

**Known traps.** A single delay per transaction, or sorting announcements before emitting them,
either of which produces a clean cascade and makes origin estimation trivially solvable. Recording
every announcement rather than only observed ones. Any ground-truth column name appearing in an
observable file. A `first announcement seen` leakage score outside roughly 0.15 to 0.6, which means
the benchmark is broken and must be fixed here rather than explained later.

---
