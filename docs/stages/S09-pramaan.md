## S09 · PRAMAAN evidence packet

**Goal.** A signed, hash-chained, replayable packet plus a pre-filled BNSS 2023 §94 production
notice.

**Reads.** `alerts/`, `sealed/`, every stage's `_meta.json`.

**Writes.** `packets/<case_id>/packet.json`, `packet.pdf`, `notice.pdf`, `merkle.log` append-only,
`packet.sig`. Keys in `keys/`, gitignored. `tests/test_pramaan.py`.

**Definition of done.** `make verify-s09 && make verify-replay`

**Known traps.** A replay claim that has never actually been tested byte for byte. `datetime.now()`
anywhere in the packet path, or an unsorted group-by, either of which breaks determinism invisibly.
A private key committed or written into a log line. A complete IP or wallet address rendered in
either PDF. Citing the wrong statute, which a legally literate evaluator will catch immediately.

---
