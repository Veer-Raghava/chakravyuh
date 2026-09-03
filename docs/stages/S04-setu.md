## S04 · SETU normalise and enrich

**Goal.** Split the announcement grain from the transaction grain, derive per-transaction features,
and attach geo and ASN with a tested absent-vendor path.

**Reads.** `sealed/`, `vendor/GeoLite2` if present, a vendored Tor exit list if present.

**Writes.** `normalised/announcements.parquet` with `src_ip` renamed to `peer_ip`,
`normalised/transactions.parquet`, `addresses.parquet`, `peers.parquet` with `net_class`,
`_meta.json` recording any degradation warning. `tests/test_setu.py`.

**Definition of done.** `make verify-s04`, then `contract-auditor` reports no violations.

**Known traps.** Keeping the name `src_ip` downstream, which encourages everyone to treat the first
row as the sender. Computing transaction features by iterating rows instead of grouping. A geo
fallback that is described but never exercised, which is how a demo dies on a machine missing one
vendored file. A negative `spread_us`.

---
