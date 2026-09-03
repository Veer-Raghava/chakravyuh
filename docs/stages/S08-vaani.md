## S08 · VAANI explanation

**Goal.** Turn a score into an alert carrying its cause, its confidence, and the case against
itself.

**Reads.** `scores/`, `signals/`, `graph/`, `docs/FEATURES.md`.

**Writes.** `alerts/alerts.parquet`, `alerts/evidence.parquet` with identifiers truncated at write
time, `alerts/counter.parquet` with a `would_clear` boolean, `_meta.json`. `tests/test_vaani.py`.

**Definition of done.** `make verify-s08`

**Known traps.** Counter-evidence that is technically present and always empty, which is worse than
absent because it looks finished. Truncating identifiers in the frontend rather than at write time,
which leaves the real values in the parquet where one careless `peek` puts them on a projector. A
reason string that reads as generated. Any LLM or network call in the reason path, which breaks both
determinism and the air-gapped claim.

---
