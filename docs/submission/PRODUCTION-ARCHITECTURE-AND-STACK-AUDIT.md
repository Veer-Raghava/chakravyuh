# Production architecture and stack audit

Reviewed 2 October 2026. Scope: the current source tree, current DRISHTI v2, supplied six-slide `docs/sih_ppt.pdf`, saved experiment artifacts and the R47 replay. This is a status audit, not a claim that every research result has been promoted. Source hashes and observed environment versions are in `research/bitcoin/results/submission-audit/`.

## The answer your team needs

**The main application still uses the 33-feature LightGBM pipeline. The strongest research improvements are implemented as optional modules and a working World-screen investigation viewer, but are not all wired into the main ingestion → active Leads → signed Proof path.** Presenting the entire product as a temporal GNN, or as the 329-feature XGBoost engine, would misdescribe today's default.

This does not erase the work. We have two executable paths: a complete legacy stage pipeline with signed packets, and a newer label-free CPU graph-context scorer with evidence-diverse queues and a local interactive viewer. Their remaining connection is an engineering release task. Preserve that distinction in the PPT and portal text.

## Actual architecture

```text
Evaluator capture under data/                 MAYAJAAL synthetic test harness
 CSV / JSON / JSONL / XML                              │
              │                              observations + separate truth
              ▼                                      │
          KAVACH ◄────────────────────────────────────┘
      hash originals, parse, reject/account, seal
              │
             SETU
  transaction bodies + announcement events + enrichment
              │
        ┌─────┴──────────────────────────────────────┐
        ▼                                            ▼
       JAAL                                  optional decision-window view
 facts + ownership hypotheses                  address / TX / announcer
        │                                            │
      SHASTRA                               frozen 329-feature XGBoost
 source candidates + ASN + typologies              + TreeSHAP
        │                                            │
       BUDDHI                                  evidence-diverse queue
 33-feature LightGBM + SHAP                     + evidence JSON
        │                                            │
        VAANI                                  World local viewer
 reasons + counter-evidence                    (working optional lane)
        │
       PRAMAAN
 signed canonical JSON + PDFs + custody hashes
        │
     DRISHTI v2: views stage artifacts and archived packets
```

DRISHTI is a cross-cutting interface, not an extra inference stage. MAYAJAAL is a generator/test harness; operational ingestion does not require generating a new world. Eight Sanskrit names can be retained as the overall project vocabulary without claiming eight consecutive transformations of a real capture.

## Research-to-product integration matrix

| Finding / implementation | Actual status | Main-route gap / release action |
| --- | --- | --- |
| Preserve ownership hypotheses instead of deleting addresses | Original JAAL graph retains addresses and weighted links | Legacy connected-component subject view still affects downstream scoring |
| Timestamp every ownership claim and rebuild as-of partitions | `jaal/provenance.py`, tested snapshot APIs | Persist and consume this ledger in default JAAL/BUDDHI stage outputs |
| Detect at address level without assuming perfect clusters | `buddhi/snapshot.py` address mode; trained models and corruption-isolation test | Make this an explicitly versioned production representation |
| Rich typed graph context helps trees | 329-feature native XGBoost inference port implemented | Main BUDDHI CLI still defaults to 33-feature LightGBM |
| Frozen inference without truth labels | Optional causal/relational inference and isolated replay work | Default training-oriented BUDDHI entry point is not a frozen-model service |
| Avoid overlapping evidence in a 20-lead queue | `vaani/investigation.py` label-free Jaccard selection | Main VAANI still orders surviving subjects by legacy risk score |
| Signed positive/negative TreeSHAP with margin reconstruction | New engine verified; World viewer displays model effects | Legacy explanations keep only five largest absolute contributions |
| Causal SHASTRA history and frozen answer policy | Implemented research/causal APIs and transfer studies | Default stage retains historical feature recipe; policy not generally transferable |
| Trained temporal typed graph learning | Saved trained weights, scores and replay; custom mean encoder + GRU | Research lane only; no default production GNN |
| Exact saved evidence across all run views | Eight operational exports; 758 focus traces checked against source | New research queues intentionally remain separate from archived signed cases |
| Truly disconnected installed runtime | Browser offline checks and stripped CPU replay | Complete offline installer/wheel bundle still needs a clean-host gate |

**Recommendation:** integrate the validated representation, model-artifact and evidence interfaces before increasing neural complexity. Do not change the approved detector silently based on hardware. The default remains LightGBM until the next engine clears the release gates below.

## What was actually learned from models

On the consumed canonical address-window protocol, the richer CPU graph-context XGBoost has AP **0.3148**, compared with local-only XGBoost **0.0538**. R47 retrained the custom temporal typed GRU: AP **0.2879**, pooled P@20 **0.95**; shuffled relations reduced AP to **0.0778**. These are useful relational results. They do not establish that the GNN is the best operational detector. Pooled ranking across windows differs from a daily/window review queue; R47's per-window P@20 is 0.65, 1.00 and 0.00, with no positives in the last window. The richer tree and neural comparisons must retain their own validation selection records, representation and feature budgets.

The two 329-feature evidence-diversity transfer tests improved suspicious **controller-window** retrieval from **11 to 33** and **9 to 16** over three future windows. Repeated controllers across windows are possible. This is the best compact investigator-workload story; never call it 33 criminals or a measured reduction in investigation hours.

Our public Elliptic experiment found graph-summary LightGBM AP **0.6566** versus local LightGBM **0.6366** under that experiment's matched split. A separate existing Elliptic procedure reports AP 0.778296 and F1 0.766174. They are different recipes/evaluation setups. Do not pick their best numbers and present a common leaderboard. Elliptic evaluates transaction classification, not observed IP-origin recovery.

The R47 neural experiment ran on CPU in **26.36 seconds** at the tested size. Earlier extended experiments used about 1.45 GiB process RSS. A separate stripped 329-feature 20-lead replay took **2.69 seconds** and **788.8 MiB** peak process RSS. These are observed workloads, not promises for arbitrary capture sizes or the complete application. GPU access can support future experiments; the trained small graph model did not require CUDA.

## Final stack for the PPT

| Area | Actually used | Status / wording |
| --- | --- | --- |
| Backend | Python 3.11; Polars 1.17.1; PyArrow 18.1.0; rustworkx 0.15.1 | Core pipeline; Parquet/JSON filesystem artifacts, no required database server |
| Local API | FastAPI 0.115.6; Uvicorn 0.32.1 | Read-only, loopback; frontend primarily uses exported fixtures |
| Default AML | LightGBM 4.5.0; MAPIE 0.9.1; SHAP 0.46.0 | 33 inputs, native booster, class-conditional prediction sets |
| Optional tested CPU engine | XGBoost 3.2.0; NumPy; SciPy; frozen scalers/Platt calibration | 329-feature graph context; working CLI and World viewer, not default |
| Trained neural research | CPU PyTorch, custom typed message passing and window GRU | No requirement for PyTorch Geometric; not canonical HGT/TGN/TGAT |
| Frontend | React 18; TypeScript 5; Vite 5; Three.js 0.171; R3F 8; drei 9 | Use package/lock files, not old CLAUDE stack aspirations |
| Motion / styling | GSAP 3.13; Lenis 1.3; CSS Modules; local fonts | Fraunces / Hanken Grotesk / IBM Plex Mono; no CDN |
| Integrity | SHA-256; canonical JSON; local Ed25519 implementation; Merkle-root log | Signature and replay checks; trusted key custody remains operational responsibility |
| PDF | Project's `pramaan/pdflib.py` and `documents.py` | **Remove ReportLab logo** |
| Enrichment | Local ASN/GeoIP/Tor/VPN lists; optional downloaded GeoLite-compatible CSV snapshots | No live geolocation lookup; geography is network context |
| Deployment | Linux; prepared local Python/Node environment; built frontend | **Remove Docker/Arch as claimed core components**; no verified shipped container image |

PyTorch Geometric and ReportLab are not installed in the inspected environment and are not imported by the core product. XGBoost imports as 3.2.0, but its distribution metadata is absent; this is another reason to package and verify the optional dependency explicitly rather than treating the current environment as a reproducible installer. Exact runtime inventory accompanies this audit.

## Corrections required before saying “final”

1. Persist the availability-time ledger and use causal address/window features in the approved engine. Preserve the legacy run/model for comparison.
2. Add XGBoost/NumPy/SciPy and all optional runtime requirements to an explicit reproducible offline environment. Validate on a clean Linux host with network disabled, not just an already prepared laptop.
3. Bind active lead objects to capture ID, window, representation, model hash, enrichment snapshot and queue policy. Route the new evidence queue to active case navigation with no metric mixing.
4. Add a PRAMAAN adapter for new engine cases; sign their own provenance and exact score/evidence, not an old archived LightGBM packet. Test signed JSON/PDF downloads and replay.
5. Separate detection score, ownership weight, source ranking, answer policy and conformal set. The legacy ±15% score band is not a conformal probability interval.
6. Apply source policies only in their validated observation regimes. Unsupported observation conditions can still support AML leads, but do not justify a reliable source assertion.
7. Repair the existing API quarantine test: `serialize.world` reads evaluation measurements for the research dashboard. Separate evaluation presentation from inference interfaces and make the guard match the intended boundary.
8. Run full stage/contracts/quarantine/replay checks plus browser verification. This checkpoint passed focused checks, not a full `make verify` release.

## Product choice

One approved CPU engine with visible artifact/version provenance is the right investigator-facing design. A research comparison screen can show saved challengers. A Standard/Advanced GPU switch today would suggest two validated production engines when we have one legacy default and a separate candidate lane.

The best feature to sell is **observable evidence stays useful even when ownership or source attribution is uncertain**. That is an implemented research direction with actual local inference, rather than a promise that a fancier architecture can recover missing observations.
