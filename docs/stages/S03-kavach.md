## S03 · KAVACH intake and seal

**Goal.** Accept any file in the problem statement's shape in CSV, JSONL or XML, hash it before
parsing, seal it, and account for every row that did not make it.

**Reads.** A capture file in any of the three formats. `docs/DATA-CONTRACTS.md` sections 1 and 3.

**Writes.** `sealed/rows.parquet`, `sealed/rejected.parquet` with a reason per row,
`sealed/manifest.json`, `sealed/INPUT.sha256`, `sealed/_meta.json`. `tests/test_kavach.py`.

**Definition of done.** `make verify-s03`, then `contract-auditor` reports no violations.

**Known traps.** Detecting format from the file extension. Silently dropping bad rows, which makes
`rows_read == rows_sealed + rows_rejected` a lie. Hashing after parsing, which breaks the custody
claim at S09 invisibly. Crashing on a missing optional column instead of nulling it with a warning.

---
