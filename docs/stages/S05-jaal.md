## S05 · JAAL fused graph

**Goal.** One graph holding both layers, with address clustering that carries its own confidence
instead of asserting ownership.

**Reads.** `normalised/`. Never `ground_truth/`.

**Writes.** `graph/nodes.parquet`, `graph/edges.parquet`, `graph/clusters.parquet`, `_meta.json`.
`tests/test_jaal.py`.

**Definition of done.** `make verify-s05`

**Known traps.** Union-find merging addresses into single nodes, which cannot be undone when the
heuristic was wrong and must never be done in a forensic tool. Importing ground truth inside the
stage to check as it goes, which is exactly how leakage happens by accident. A graph that only
works when Kùzu is installed. Clustering precision above 0.8, which on this data means a leak
rather than a breakthrough.

---
