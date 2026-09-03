# ARCHITECTURE

Locked. Changing anything here means changing `docs/DATA-CONTRACTS.md`, which means
breaking the parallel frontend track. Do not change it casually.

## Shape

Eight stages in a line, each one a separate Python package, each one reading Parquet from
the previous stage's directory and writing Parquet to its own. No stage imports another
stage. There is no shared mutable state, no database that everything talks to, and no
orchestration framework. The Makefile is the orchestrator.

This is deliberately boring, and the reason is that it buys four things we need. A stage
can be rebuilt without touching its neighbours. Any intermediate result can be inspected
with one command. Two people can work at once. And the whole run is resumable, which
matters when a one million row run takes minutes rather than seconds.

## Stages

| L | Package | Reads | Writes | Owns |
|---|---|---|---|---|
| L- | `mayajaal` | nothing, or `vendor/btc-graph/` | `data/generated/<run>/capture/` and `ground_truth/` | data generation, both modes |
| 0 | `kavach` | a capture file in CSV, JSON or XML | `sealed/` | schema-tolerant intake, hashing, manifest |
| 1 | `setu` | `sealed/` | `normalised/` | type coercion, geo and ASN enrichment, splitting announcements from transactions |
| 2 | `jaal` | `normalised/` | `graph/` | the fused graph, address clustering with confidence |
| 3 | `shastra` | `normalised/`, `graph/` | `signals/` | origin-vs-relay estimation, typology heuristics, entity typing |
| 4 | `buddhi` | `signals/`, `graph/` | `scores/` | LightGBM, conformal calibration, optional GNN |
| 5 | `vaani` | `scores/`, `signals/` | `alerts/` | SHAP attribution, counter-evidence, natural language reason |
| 6 | `pramaan` | `alerts/`, `sealed/` | `packets/` | evidence packet, Merkle log, Ed25519 signature, PDF, BNSS notice |
| 7 | `apps/drishti` | the read-only API over `alerts/`, `graph/`, `signals/` | nothing | the console |

## Dataflow

```
                 ┌──────────────────────────────────────────────┐
  MAYAJAAL ──────▶ capture/*.csv.zst        ground_truth/*.parquet
   (L-)          └───────┬──────────────────────────┬───────────┘
                         │                          │ never read by src/
                         ▼                          │ except eval/
  KAVACH   L0    sealed/{rows.parquet, manifest.json, INPUT.sha256}
                         │
                         ▼
  SETU     L1    normalised/{announcements.parquet, transactions.parquet,
                             addresses.parquet, peers.parquet}
                         │
              ┌──────────┴───────────┐
              ▼                      ▼
  JAAL   L2  graph/{nodes,edges,     │
             clusters}.parquet       │
              │                      │
              └──────────┬───────────┘
                         ▼
  SHASTRA  L3   signals/{origin_estimates, typology_hits, entity_types}.parquet
                         │
                         ▼
  BUDDHI   L4   scores/{wallet_scores, calibration, eval_report}.parquet
                         │
                         ▼
  VAANI    L5   alerts/{alerts.parquet, evidence.parquet, counter.parquet}
                         │
                         ▼
  PRAMAAN  L6   packets/<case_id>/{packet.json, packet.pdf, notice.pdf,
                                   merkle.log, packet.sig}
                         │
                         ▼
  DRISHTI  L7   http://127.0.0.1:8000  →  React console
```

## Six rules that hold this together

**1. Ground truth is quarantined.** Everything under `ground_truth/` is readable by exactly
one place, `src/chakravyuh/eval/`. No stage may import it, and no stage may take a path
argument that could point at it. A test asserts this by grepping the source tree. If a
label leaks into a feature, every number we publish becomes a lie, and it will happen by
accident rather than on purpose, which is why it needs a mechanical guard.

**2. One row in, is one announcement, not one transaction.** `sealed/rows.parquet` is at
announcement granularity, exactly as the capture arrives. SETU is where that splits: one
row per announcement in `announcements.parquet`, one row per TXID in
`transactions.parquet`. Everything downstream must be explicit about which grain it works
at, and every function name says it. `score_wallets` not `score`, `rank_announcements` not
`rank`.

**3. Confidence travels with every claim.** No stage emits a bare assertion. A cluster edge
carries the heuristic that produced it and a confidence. An origin estimate carries a
probability and the runner-up. A wallet score carries a conformal interval and may carry
`ABSTAIN` instead of a label. Anything that cannot produce a confidence does not belong in
the pipeline.

**4. Every artifact is content-addressed.** Each stage writes `_meta.json` beside its
outputs containing the input hashes, the code version, the seed, the parameters, and the
SHA-256 of each file it wrote. PRAMAAN chains these into the Merkle log. This is what makes
the replay claim true rather than aspirational, and it costs about twenty lines per stage.

**5. Determinism is a test, not an intention.** `make verify-determinism` runs the same
seed twice into two directories and diffs the hashes. It must produce identical bytes. Any
non-determinism found later is a bug with a known reproduction, which is much cheaper than
one found the night before a demo.

**6. Fallbacks are built, not planned.** Every optional dependency has a working path
without it, and a test that exercises that path. Kùzu missing means the Cypher panel
disappears and nothing else changes. No GPU means cosmos.gl falls back to a capped node
count. No GeoLite2 in `vendor/` means geo columns are null and the pipeline still completes
with a warning in `_meta.json`. A demo that has one hard dependency has one way to die.

## Where the interesting part lives, and why

The origin estimator is in SHASTRA at L3, before the models at L4, and that ordering is a
design claim rather than an accident.

Origin estimation is not a classification of wallets. It is a per transaction inference over
the announcement set, using first-seen order, the spread of announcement times, which
observers saw it and which did not, and the peer's own history of appearing early. Its
output, `P(originator)` per announcing peer, then becomes a **feature** for L4. So the
network layer informs the risk model rather than sitting beside it.

That is the difference between fusion and a dashboard with two tabs. If the estimator sat
after the model, the model would be scoring wallets in ignorance of who actually transmitted
anything, and the two layers would never really meet.

Entity typing also lives at L3, before scoring, for the same structural reason. A mining
pool must be identified as a mining pool before anything ranks it as suspicious, not
explained away afterwards.