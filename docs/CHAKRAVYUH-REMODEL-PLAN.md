# CHAKRAVYUH — REMODEL PLAN (v2)

> The backend rebuild. This is the "how exactly do we change what, to what" document.
> Companion: **FRONTEND-HANDOFF-V2.md** (what DRISHTI receives). Baseline contract:
> **DATA-CONTRACTS.md** (this plan defines the *delta* from it — see §11).
>
> **Non-negotiables kept from the old world:** the eight Sanskrit layer names, the layer
> ordering (roughly), satoshis-int64 / UTC-microseconds discipline, quarantined ground truth,
> full-hash / truncated-identifier legal rules, offline-only. Everything else is on the table.
>
> **The one sentence:** we stop trying to name the exact origin *host* (physically capped at
> 5–60%, and illegal to display anyway) and instead deliver **operator-level attribution
> (ASN + region + a short calibrated shortlist)** from a **real multi-observer estimator**, run
> in an **agency-grade high-coverage regime** — so the analytics *after* MAYAJAAL win, honestly.

---

## 0 · Status & how to read this

- **Audience of the product:** NTRO — a technically sophisticated national agency. They will
  know the deanonymization literature. Overclaiming loses; calibrated strength wins.
- **Strategy (from the owner):** MAYAJAAL is a *means*. The deliverable is everything
  downstream. Tune the world so downstream succeeds impressively **in a defensible regime**,
  and *prove* defensibility with the observer-fraction curve rather than a single number.
- Each layer section below has: **Keep** / **Change** / **New** / **Why it's stronger** /
  **Why it's still defensible**.

---

## 1 · Diagnosis — what is actually weak (frank)

1. **SHASTRA aims at the wrong target.** It scores "exact origin peer named." Physics caps that
   at 11–60% (Koshy'14, Biryukov'14); the repo default (`observer_fraction=0.10`) caps it at
   ~5%. The deck's 41.5% silently assumes a ~0.70 world — **the default and the headline
   disagree.** And the truncation rules forbid ever displaying a full IP, so the target is both
   unreachable and unshowable.
2. **SHASTRA's estimator is thin.** `first_spy` = rank by earliest arrival; the "ensemble" is a
   LightGBM with ~70 positive rows at 0.10 coverage → fragile calibration, modest lift over the
   payer-linkage baseline (~0.263 vs first-seen ~0.221).
3. **BUDDHI is imbalanced and faintly circular.** ~0.6% illicit share, tiny holdout → noisy
   precision@20; labels and typology-features both trace to the planted campaigns. Mitigations
   exist (morphological detectors, time-windowing, label door) but the external-validation leg
   (Elliptic) is *planned, not built* — so the strongest defence isn't in place yet.
4. **JAAL is good but shallow.** Single graph (addresses/tx/peers). No actor-vs-transaction
   dual view, no peel-chain tracing, CoinJoin handled only as a flag.
5. **The world is calibrated pessimistically for the customer we have.** 0.10 coverage is a
   stealthy academic attacker. NTRO is not that.

None of this is dishonest. It is *miscalibrated and under-built* for the goal: impress a
sophisticated buyer.

---

## 2 · The core reframe (fixes origin end-to-end)

**Old answer key:** `true_origin_ip` — one exact host per tx.
**New answer key:** a *ladder* of attribution granularity, scored independently:

| Level | What we assert | Recoverable? | Shown to user? |
|---|---|---|---|
| L0 host | exact origin peer IP | rarely (5–60%) | never (redacted) |
| **L1 operator** | **origin ASN + as_org + net_class** | **often, in high coverage** | **yes — the hero** |
| **L2 region** | **country / geo cluster** | **usually** | **yes** |
| **L3 shortlist** | **top-k candidate peers + calibrated p** | **yes** | **yes (rings)** |

The product headline becomes **L1+L3**: "this transaction originated on **AS`nnnn` (`<operator>`,
`<net_class>`) in `<region>`; here is the ranked shortlist of candidate peers and our
confidence." L0 stays inside `packet.json` for the authorised officer only.

Why this is legitimate, not spin: (a) attribution legally *stops* at the operator anyway;
(b) candidate peers collapse onto few ASNs, so an ASN guess is right far more often than a host
guess; (c) it mirrors Chainalysis/GraphSense exactly. Why it's stronger: the metric we headline
(L1 top-1, L3 top-k coverage) is genuinely high in the demo regime, and we still publish the L0
curve as the honesty proof.

---

## 3 · MAYAJAAL v2 — the world, recalibrated

**Keep:** UTXO ledger, agent-based emergent campaigns (never stamp typologies), Dijkstra-flood
propagation with independent per-link exponential relay delays, quarantined ground truth,
awkward-case coverage, one seeded RNG, byte-determinism.

**Change:**
- **Default regime = "national vantage."** Introduce a named preset, not a bare float:
  - `observer_regime: "agency"` → `observer_fraction ≈ 0.60`, `n_observers ≈ 48`, observers
    placed with **ASN/IXP bias** (not uniform random) — they preferentially peer with
    high-degree, well-connected nodes, mirroring a monitor sitting at ISPs/IXPs. This is the
    demo default and the "advantageous scenario."
  - `observer_regime: "stealth"` → the old `0.10` academic attacker (kept for the curve/honesty).
  - Eval sweeps a **regime ladder** `{0.02, 0.05, 0.10, 0.25, 0.50, 0.60, 0.70}`.
- **Origin ground truth becomes multi-granular.** `ground_truth/origins.parquet` gains
  `true_origin_asn`, `true_origin_as_org`, `true_origin_net_class`, `true_origin_country`
  (§11). The L0 `true_origin_ip` stays but is no longer the headline scoring key.
- **Observed-origin realism.** With ASN/IXP-biased observers at 0.60 coverage, the originator's
  *own* node is observed far more often, and neighbouring relays share its ASN/region — so
  L1/L2 are recoverable for the majority. Tor (`tor_share`) and single-observer cases stay a
  deliberate minority (~8–12% combined) as the honest abstain set.
- **Adversary rework (the deep part you asked for):** campaigns get an explicit `detectability`
  knob per campaign drawn from a distribution — most campaigns emit morphology our features can
  catch (fan-out, peel, rapid-hop, structuring), a minority are *evasive* (heavy CoinJoin,
  long dwell, cross-ASN hops) and are expected to slip → this is what makes recall < 1.0
  honestly, instead of a flat low number. Campaigns route through the **dual graph** (§5) so
  both tx-level and actor-level labels exist.

**Why stronger:** the analytics now operate where they can win; morphology is present to be
found. **Why defensible:** the "agency" regime is a real capability tier, we publish the full
curve across regimes, evasive campaigns and Tor keep recall/coverage honestly below 1.0, and
`real-slice` mode (real chain topology under a synthetic network) remains available to answer
"you invented the data."

---

## 4 · SETU v2 — normalise & split (light touch)

**Keep:** the grain split (announcements = the wire; transactions/addresses = the money),
`peer_ip` rename, `net_class` enrichment, `delta_first_us` / `rank_in_tx`.

**New:**
- A per-tx **arrival matrix** view materialised for SHASTRA:
  `{txid → [(observer_id, peer_ip, seen_us)]}` — the substrate the timing estimator needs.
- `peers.parquet` gains `asn_frac_rank_one` and `as_org` rollups so the ASN prior is cheap.
- New `normalised/asn_rollup.parquet` (one row per ASN): announcement counts, distinct peers,
  net_class mix, frac_rank_one — the substrate for L1 attribution and the ASN prior.

---

## 5 · JAAL v2 — dual-graph clustering + tracing

**Keep:** `SAME_OWNER` as confidence-weighted edges that never hard-merge; the tunable dial;
0.36 as the honest multi-input anchor.

**Change → a dual graph (Elliptic++ shape):**
- **Transaction graph** (tx ◆ nodes, flow edges) — as today.
- **Actor/address graph** (address ● and cluster nodes, `SAME_OWNER`/`MEMBER_OF`) — promoted to
  a first-class scored surface so BUDDHI can score **both** a transaction *and* an actor, and we
  can show the (real, published) finding that the two queues only partly agree.

**New heuristics:**
- **Peel-chain tracer** — follows large-UTXO→small-peel+change sequences, emits a
  `peel_chain` subgraph with depth and leak-rate. (arXiv 2205.13882.)
- **CoinJoin/mixer detector** — equal-value-output symmetry + high in/out; marks the tx and
  offers **set-aside-with-reason** so CIOH is not applied across a mixer (Möser/Narayanan'19).
- **Change-address heuristic** kept but at explicitly *lower* confidence than CIOH, with
  counter-evidence attached.

**Why stronger:** actor-level scoring is what an agency wants; peel/CoinJoin are the real
laundering motifs. **Why defensible:** CoinJoin exclusion + confidence dial + never-merge is
exactly current forensic best practice.

---

## 6 · SHASTRA v2 — the real origin estimator

**Kill:** headline dependence on bare `first_spy` and on "exact host" scoring.

**New estimator stack (each independently runnable, `make compare-estimators`):**
1. `first_spy` — baseline, kept to be beaten.
2. `timing_mle` — **multi-observer maximum-likelihood source estimator.** Given the per-tx
   arrival matrix and the known relay-delay model, score each candidate peer by the likelihood
   it produced the observed arrival pattern across *all* observers (rumor-centrality / MLE on
   the propagation graph; Shah-Zaman, Fanti). Fuses arrival spread, observer geometry, and how
   often each peer/ASN is early network-wide.
3. `asn_rollup` — lifts candidate scores to **L1**: sum candidate mass by ASN, apply the ASN
   prior. This is the headline output.
4. `ensemble` — gradient-boosted blend of 1–3 + priors, **calibrated (Platt)**, trained across
   regimes so it doesn't overfit one coverage level.

**Outputs (per §11):** L3 shortlist with calibrated `p_origin` per candidate; L1
`origin_asn`/`as_org`/`net_class` with its own `p_asn`; L2 `origin_country` + `p_country`;
`margin`; `abstain` + reason (Tor / single-observer / margin-below-floor / too-few-announce).
Abstain stays first-class; `p_origin` still not renormalised (the shortfall = "maybe none").

**Why stronger:** timing-MLE is the principled method and beats first-seen; ASN rollup is
high-accuracy in the agency regime. **Why defensible:** we report L0/L1/L2/L3 accuracy
*separately*, each with its observer-fraction curve; the abstain minority is real.

---

## 7 · BUDDHI v2 — illicit risk (strong AND honest)

**Keep:** LightGBM native + class-conditional (Mondrian) conformal prediction sets, SHAP
`top_features`, strict time-windowed features, run_id-keyed label door, abstain.

**Change / New:**
- **Workhorse = gradient-boosted model** on morphological features (the field consensus: RF/GBM
  beats GNNs under honest temporal eval — Weber'19; arXiv 2604.19514). This is primary and
  stands alone.
- **Structural signal (optional, wired so it can be dropped): self-supervised graph
  embeddings.** Deep-Graph-Infomax / GraphSAGE-style unsupervised node embeddings over the JAAL
  dual graph, fed as extra columns into the GBM (the Inspection-L recipe, arXiv 2203.10465).
  Flag `model: "gbm_v2"` vs `"gbm_gnn_v2"` per row so a mixed run stays auditable.
- **External validation (the credibility kill-shot — build it, don't just plan it):** the *same*
  model recipe is trained+scored on the real, independently-labelled **Elliptic / Elliptic++**
  dataset (vendored offline), and those numbers ship next to ours in `scores/eval_report.json`
  → answers "you solved your own invention" with a real-data F1.
- **Inductive, time-ordered evaluation** (train past → test future) is the *only* reported
  protocol; we deliberately **show** the regime-shift recall behaviour rather than hide it.
- **Feature set** (morphological, an analyst could compute): fan-in/out ratios, peel-chain
  depth/leak, rapid-hop dwell, structuring (values clipped under thresholds), CoinJoin
  participation, temporal velocity/burstiness, fee-rate anomaly, plus origin-fusion
  (`mean_p_asn`, `frac_origin_abstained`) and cluster-shape (`min_edge_confidence`).
- **Headline metric = campaign-level recall** (catching 1 tx of a 40-tx chain = catching the
  chain) alongside tx-level and actor-level PR-AUC.

**Why stronger:** an honest ~0.8 illicit-F1 that *beats GNNs inductively* and *replicates on
real data* is a far better story than a fake 0.98. **Why defensible:** morphological features +
time-windowing + real-data replication + shown regime shift = nothing to hide.

---

## 8 · VAANI v2 — leads (reflect operator-level attribution)

**Keep:** ranked queue, per-lead confidence, mandatory counter-evidence (`would_clear`),
`attribution_ready`, plain-English headlines from features.

**Change:**
- Alert `origin_*` fields shift to **operator-level**: `origin_asn`, `origin_as_org`,
  `origin_net_class`, `origin_country`, `p_asn`, plus the L3 shortlist size. The lone
  `origin_peer_ip` moves to packet-only.
- `attribution_ready` is redefined for the L1 world: **true when ASN + net_class + a precise
  observed timestamp exist** (host IP no longer required to be sole gate; host, when present,
  strengthens the packet but is not the bar).
- New counter kind `cross_asn_ambiguous` (shortlist mass split across operators).

---

## 9 · PRAMAAN v2 — proof packet

**Keep:** full-hash disclosure, redacted identifiers on all rendered output, Merkle append-log,
Ed25519 signature, `replay.expected_packet_sha256` must verify, chain-of-custody.

**Change:**
- `attribution` block leads with **L1**: `origin_asn`, `as_org`, `net_class`, `geo_country`,
  `p_asn`, `margin`, then the L3 `shortlist[]` (redacted candidate displays + p). Full
  `peer_ip`/`peer_port` remain **inside `packet.json` only**, for the authorised officer.
- **`attribution_ready` becomes a real field in `packet.json`** (today the frontend derives it —
  §11 finding 2). Single source of truth.
- The `{IP · port · UTC}` hero on screen becomes **`{operator(ASN) · region · observed UTC}`**
  as the shown attribution, with host IP appearing only in the officer's machine artifact.

---

## 10 · Eval v2 — metrics & the defensibility curve

- `origin_estimator` block reports **per-granularity**: `l0_host`, `l1_asn`, `l2_region`,
  `l3_shortlist_topk`, each with `top1/topk`, `abstain_rate`, and `by_observer_fraction[]` over
  the regime ladder, split `by_traffic_type` (clear/vpn/tor).
- `recoverable_ceiling` reported per granularity (L1 ceiling ≫ L0 ceiling) — reported *first*.
- `wallet_model` reports tx-level, actor-level, **campaign-level recall**, PR-AUC/ROC-AUC,
  precision@k, conformal coverage, imbalance ratio, `baseline_beaten`, **and** the
  `elliptic_external` sub-block (real-data PR-AUC/F1).
- `clustering` reports pairwise P/R/F1 at the chosen threshold + the 0.36 anchor context.
- Parameter-holdout: train one regime, test another; report the gap.

---

## 11 · Canonical numbers v2 (make them coherent)

The old inconsistency (default 0.10 → ~5% vs headline 41.5% @ 0.70) is retired. New coherent set:

- **Demo default regime = "agency", `observer_fraction ≈ 0.60`.** All demo/fixture numbers come
  from this one regime — no silent switching.
- **Headline = L1 operator-level attribution** (target, to be confirmed by the actual run — do
  not hardcode until measured): expected **high** in the agency regime because candidates
  collapse onto few ASNs. Report L0 host-level on the same slide as the *honest* lower number.
- **Observer-fraction curve** stays the flagship honesty artifact, now drawn **per granularity**
  (L1 curve sits well above the L0 curve; L0 tracks the 11–60% literature band).
- **Funnel** (recompute from the actual agency run; keep the shape 1,000,000 → … → 1). Fix the
  stages.ts vs WorldScreen mismatch (§ frontend finding) — one source.
- **0.36** stays as the honest multi-input clustering anchor.
- **Campaign-level recall** becomes a headline number (from the run).
- **Elliptic external F1** becomes a headline number (from the real-data run).

> Rule: numbers in the deck/frontend come from `measurements/<run_id>/` of the canonical agency
> run, never hand-typed. The frontend gets a real `world.json` (§FRONTEND-HANDOFF-V2) instead of
> hardcoded constants.

---

## 12 · Frontend contract delta

See **FRONTEND-HANDOFF-V2.md** for the full per-station spec. Summary of what changes for
DRISHTI: origin outputs go multi-granular (L1/L2/L3), alerts+packet lead with operator-level
attribution, `attribution_ready` becomes a backend field, a real `world.json` replaces
hardcoded canonical numbers, and the graph gains the actor/tx dual view. DATA-CONTRACTS.md is
the frozen baseline; this remodel is a **v2 delta** on top of it (documented, not a silent edit).

---

## 13 · Phased execution (timeline-agnostic; cut from the bottom)

- **P0 — Reframe + recalibrate (highest ROI, do first).** Add observer regimes + ASN/IXP-biased
  observers; add multi-granular origin ground truth; add `asn_rollup`; implement `asn_rollup`
  estimator + `timing_mle`; re-report eval per granularity; regenerate the canonical agency run
  + fixtures. **This alone fixes the thing you hate and makes SHASTRA win.**
- **P1 — BUDDHI credibility.** Vendor Elliptic/Elliptic++ offline; build the shared model recipe;
  inductive eval; campaign-level recall; ship `elliptic_external` numbers.
- **P2 — JAAL depth.** Dual graph, peel-chain tracer, CoinJoin detector + set-aside.
- **P3 — Polish / optional.** Self-supervised GNN embeddings into BUDDHI; real-slice mode run;
  parameter-holdout appendix.

Each phase ends with: `make validate-data` green, eval regenerated, fixtures re-exported,
frontend handoff fields present, PROGRESS updated, commit.

---

## 14 · Risks & the viva answer

- **"You invented the data and solved it."** → observer-fraction curve matches the 11–60%
  literature; Elliptic external replication; real-slice mode; parameter-holdout.
- **"0.60 coverage is generous."** → it's a named *national-vantage* tier (IXP/ISP), we publish
  the full curve down to 0.02, and we headline operator-level (which is what you can act on),
  not exact host.
- **"Circular labels."** → morphological detectors read no labels; time-windowed features;
  real-data replication.
- **"GNN buzzword?"** → we *lead* with the model the literature says actually wins (GBM),
  evaluate inductively, and add SSL-GNN embeddings only as a measured add-on with
  `baseline_beaten` gating.

The posture in the room: **confident rigour.** We are strong *and* we can point to exactly where
the edges are — that beats both "95% attribution" (instantly fake to an expert) and "we're weak
but honest."


