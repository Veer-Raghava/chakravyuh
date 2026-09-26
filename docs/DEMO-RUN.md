# DEMO-RUN — the precomputed artifact and how to serve it

Everything the demo shows is precomputed and committed to disk. Nothing regenerates live;
regeneration is a failure mode, not a feature, when a projector is waiting.

## The artifact

Run id: **`s10-demo`** at `data/generated/s10-demo/`.

- Produced by: `scripts/make_vendor_lists.py --out vendor/` (one-time, already done),
  then `uv run python -m chakravyuh.mayajaal --out data/generated/s10-demo --txs 24000`,
  then KAVACH → SETU → JAAL → SHASTRA → BUDDHI → VAANI, one command per stage (all
  default flags, `--score` on SHASTRA and BUDDHI). `make demo-full` runs exactly this.
- Built at the **canonical scale** (`--txs 24000`, seed 42, 20,000 entities): the demo
  shows the real model with a real holdout, not a toy cut-down. It is itself the measured
  run — there is no separate small "demo" model to explain away.
- Size: ~960k capture rows across csv + jsonl + an xml sample, 32,781 transactions,
  64,114 alerts, four signed packets under `packets/`.
- The vendor tree is populated for this run only: `net_class` is live (residential,
  mobile, vpn_suspect, tor_exit), so SETU enrichment and BUDDHI's vpn/tor features all
  exercise their real paths. This is the deployment `make verify-s04` does not assert;
  that gate stays on the empty-vendor world.

## What the model actually scored on this run

Read straight from `measurements/s10-demo/model_report.json`, holdout subjects only
(subjects whose earliest activity is at or after the time-split boundary):

- **Beats the trivial baseline.** Ranking wallets by total value received — the naive rule
  an analyst would try first — puts **zero** true illicit subjects in its top 20
  (`precision_at_20` 0.0). The model puts **10 of 20** there (`precision_at_20` 0.5)
  against a **1.85 %** base rate: a ~27× lift where an investigator actually looks.
- Global ranking is honestly modest: `roc_auc` 0.587, `pr_auc` 0.045 at a 1:53 class
  imbalance. This generator is built so that a top-of-list precision above 0.9 would be
  leakage, not skill (`docs/FEATURES.md`); the gate treats it as such. The number to
  present is top-k lift, not global AUC.
- Conformal coverage is class-conditional (Mondrian) at a 0.90 target: **0.884** achieved
  on the illicit class, 0.676 on the licit class. Every alert carries the interval, so the
  console shows what the model does not know, not a bare score.

## The demo cases

`docs/DEMO-CASES.md` names them, with ranks, merkle heads and the beat each one plays:

| beat | alert id | rank |
|---|---|---|
| flagship illicit, attributable | `alw-86c94e363f0f` | 1 |
| second illicit lead | `alw-a7177926cc03` | 2 |
| third illicit lead | `alw-95f69548c542` | 3 |
| high-risk, **not** ready to attribute | `alw-5ca3af6110cf` | 17 |

All four packets replay byte-identical via `--verify-replay`. Case selection is by role,
computed from the run at build time (top three by rank, plus the highest-ranked alert the
tool marks not-ready-to-attribute), so it never depends on a hand-copied id.

## Serving the console

```
CHAKRAVYUH_RUN=s10-demo make api       # binds 127.0.0.1:8000, read-only
```

The env var names the run id the API serves; the frontend in `apps/drishti` reads from
it (`VITE_SOURCE=api`). Serving is inference: the API never reads `ground_truth/` or
`measurements/`, and `test_api.py` proves it boots and serves with the answer key absent.
When `measurements/` is absent (the air-gapped copy), the per-alert base rate and empirical
coverage read as "not measured in this copy" rather than a faked zero; the per-subject
conformal interval and target still render, because they travel inside the run.

## The five beats

1. **The capture is sealed.** Show `data/generated/s10-demo/sealed/manifest.json` and
   `INPUT.sha256`: intake hashed and quarantined anomalies before anything downstream
   ran. One line: "everything after this point is traceable to sealed bytes."
2. **The graph fused itself.** The console's graph view, cluster level. One line: "same
   owner addresses clustered from co-spend and link evidence, every edge carrying its
   confidence."
3. **A wallet is flagged with calibrated doubt.** The alerts queue, the rank-1 case
   (`alw-86c94e363f0f`) opened. One line: "risk 0.99 with a conformal interval, and the
   counter-evidence panel is the case against our own alert."
4. **The tool says when it is not ready.** Open the rank-17 case (`alw-5ca3af6110cf`):
   high wallet risk, and yet flagged **not ready to attribute**. One line: "confident
   about the risk, honest that the evidence does not yet support a name on a notice — that
   restraint is the product."
5. **Serve the notice.** A flagship case's packet PDF and the BNSS s.94 notice PDF, then
   `--verify-replay` live: the packet regenerates byte-identically. One line: "signed,
   replayable, and legal on the first read."

## Cold-start and reset

- `make demo` serves the precomputed `s10-demo` — the API on `127.0.0.1:8000` and the
  console on `127.0.0.1:5173` — and regenerates nothing. This is the demo. It gates on the
  artifact being present and refuses (rather than rebuilds) if it is missing.
- `make demo-full` builds the whole demo artifact from an empty `data/generated/` at the
  canonical scale. This is a build step (minutes, not seconds), never run in front of the
  room.
- `make demo-reset` returns to beat one. The API is read-only and the console reloads from
  it on every route, so there is no state to wipe and nothing to restart — reset just
  confirms the servers are up and points at the beat-one URL. The demo runs twice in a row
  without a rebuild.
- Offline: no step touches the network. Fonts are vendored for the frontend; the API
  binds loopback only. `make verify-s11` proves the cold, offline, stripped-copy start.
