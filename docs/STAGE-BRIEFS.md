# STAGE BRIEFS

Twelve briefs, one per session. Machine-facing and deliberately terse. S00 splits this file into
`docs/stages/S00-skeleton.md` through `S11-demo.md`, one file per brief, changing no wording.

The human-facing version of all of this, with the prompts and the reasoning, is `SESSIONS.md`.
This file is what Claude reads at the start of a session. Every "Definition of done" is an exact
shell command, on purpose, so a stage cannot be declared finished by opinion.

---

## S00 · Skeleton and contracts

**Goal.** The full directory tree, dependency pinning, the Makefile, `scripts/peek.py`, the
fixture set, the contract tests, and this file split into per-stage briefs. No pipeline logic.

**Reads.** `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACTS.md`, `docs/STAGE-BRIEFS.md`.

**Writes.** The tree with `__init__.py` and a one-line ownership docstring per package.
`pyproject.toml` with exact pins. `Makefile` with `setup`, `fixtures`, `verify`, `verify-s00`
through `verify-s11`, `verify-determinism`, `verify-contracts`, `verify-replay`, `validate-data`,
`peek`, `api`, `demo`, `demo-full`, `demo-reset`, `clean`. `scripts/peek.py`. `data/fixtures/`
with the ~200 row capture in CSV, JSONL and XML at seed 42 plus `fixtures/README.md`.
`tests/test_contracts.py`. `docs/stages/*.md`. Empty `docs/EXPLAIN.md` and `docs/DECISIONS.md`.

**Definition of done.** `make verify-s00`

**Known traps.** Missing `__init__.py`, so nothing imports. Fixtures containing only the happy
path, which silently poisons every later stage. A `verify-sNN` stub that exits zero instead of
failing with a clear message, which lets a stage pass before it exists. `peek.py` printing a full
identifier.

---

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

## S07 · BUDDHI models

**Goal.** A LightGBM baseline over the fused features with `p_origin` as an input, class-conditional
conformal calibration, and a strictly time-ordered evaluation.

**Reads.** `signals/`, `graph/`. Ground truth only inside `src/chakravyuh/eval/`.

**Writes.** `scores/wallet_scores.parquet`, `scores/calibration.parquet`,
`scores/eval_report.json` with `by_observer_fraction`, `by_traffic_type` and `baseline_beaten`,
`docs/FEATURES.md` with a plain-English gloss per feature. `tests/test_buddhi.py`.

**Definition of done.** `make verify-s07`

**Known traps.** A random train-test split. Features computed over the full time range even when the
rows are split correctly, which is where leakage actually lives. Reporting overall conformal
coverage while the minority class is badly under-covered. Starting the GNN in this session, which is
out of scope and will consume it. Precision-at-20 above 0.9, which means leakage rather than skill.

---

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

## S10 · Scale

**Goal.** One million capture rows end to end, resumable, with recorded timings.

**Reads.** Everything. **Writes.** A full run under `data/generated/`, `docs/PERF.md` with
per-stage wall clock and peak memory plus the machine specs, `docs/DEMO-RUN.md` naming the
precomputed artifact paths.

**Definition of done.** `make demo-full` from an empty data directory, and `docs/PERF.md` exists
with per-stage timings.

**Known traps.** Optimising before profiling. A run that is not resumable, which turns any failure
into a full restart. Validation checks only ever run at fixture scale, when distribution checks fail
differently at a million rows. Losing determinism at scale through parallelism with unordered
reduction. Making live regeneration the demo path.

---

## S11 · Demo hardening

**Goal.** One command starts everything from precomputed artifacts, every optional dependency has a
tested fallback, and the five beats run cold and offline.

**Reads.** `docs/DEMO-RUN.md`, `docs/DEMO-CASES.md`, `docs/DRISHTI-SPEC.md`.

**Writes.** `make demo`, `make demo-reset`, fallback tests for Kùzu absent, GeoLite2 absent, no GPU
and no model file, an airplane-mode test wired into `verify`, and `docs/DEMO-SCRIPT.md` with the
five beats, the exact keystrokes, the three demo txids and the one line spoken per beat.

**Definition of done.** `make demo` from a cold start with networking disabled, and every fallback
test passing.

**Known traps.** A demo that needs the network for a font, which is why the fonts are vendored. A
layout that breaks at 1366x768, which is what venue projectors often are. A demo that can only be
run once because there is no reset. Beats that only work in one order. A fallback that is described
in a document rather than proven by a test.