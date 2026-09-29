# FRONTEND HANDOFF — v2 (what DRISHTI receives after the remodel)

> Companion to **CHAKRAVYUH-REMODEL-PLAN.md**. Baseline = **DATA-CONTRACTS.md** (frozen §1–§11);
> this file is the **delta** the frontend must adopt. Everything not listed here is unchanged.
>
> **The seam is unchanged:** `apps/drishti-v2/src/data/loader.ts` imports JSON fixtures from
> `apps/drishti-v2/src/data/fixtures/*.json`, produced by `scripts/export_ui_fixtures.py` off
> `src/chakravyuh/api/serialize.py`. Live API stays `127.0.0.1:8000`, no auth, offline. Fixture
> shape == API shape by construction. We add fixtures, we don't move the seam.
>
> **Unchanged & still mandatory:** satoshis-int64 / UTC-µs `_us`; `null ≠ 0 ≠ unknown`; all
> identifiers redacted on screen (IP `103.x.x.x`, addr `bc1q4f…9f4d`, txid first8+last4),
> **SHA-256 / Merkle printed in full**; full IP/port live only inside `packet.json`.

---

## 0 · The one big idea for the frontend

Origin attribution is now **multi-granular**. The screen hero is no longer "the exact IP that
sent it" — it is **"the network operator (ASN) + region, plus a ranked shortlist of candidate
peers, with confidence."** The exact host is officer-only (`packet.json`). This is the change
that ripples through Globe, Origin, Leads, and Proof.

---

## 1 · Canonical numbers — now data, not constants

**Remove hardcoded constants; add a real fixture.** Today `nav/stages.ts`, `OriginScreen`
(`CEILING=41.5`) and `WorldScreen` hardcode the funnel / 41.5% / 22.1% / 11–60% band, and
stages.ts disagrees with WorldScreen. Replace with a new fixture:

`world.json` (from the run's `origin_accuracy.json` + `scores/eval_report.json` + funnel):
```json
{
  "run_id": "", "observer_regime": "agency", "observer_fraction": 0.60,
  "protocol": "inductive_time_ordered",
  "funnel": [{"stage":"globe","layer":"MAYAJAAL","label":"signals","count":1000000}, … {"stage":"proof","layer":"PRAMAAN","count":1}],
  "recoverable_ceiling": 0.482405,
  "origin_curve": {
    "l0_host":   [{"fraction":0.02,"top1":0.0,"abstain":0.0}, …],
    "l1_asn":    [{"fraction":0.02,"top1":0.0,"abstain":0.0}, …],
    "l3_shortlist": [{"fraction":0.02,"topk":0.0,"k":5}, …]
  },
  "naive_first_seen_top1": 0.221,
  "literature_band": [0.11, 0.60],
  "headline": {"l1_top1": 0.0, "l0_top1": 0.0, "campaign_recall": 0.0,
               "elliptic_f1": 0.0, "pair_precision": 0.588},
  "defences": ["observer curve","elliptic replication","real-slice","parameter holdout"]
}
```
The World station and Origin ceiling gauge read from this. **Single source; stages.ts funnel
also reads `world.funnel`.** No number is hand-typed in the UI anymore.

**`funnel` is a pipeline, not a shrinking funnel.** It is one row per landing layer, in layer
order, and it **branches at BUDDHI**: the run's real counts are
`906,560 · 906,560 · 906,560 · 32,787 · 32,787 · 87,896 · 66,957 · 4` — owner groups scored
(87,896) is larger than transactions (32,787) because one transaction leaves several owner
groups, and ranked leads (66,957) is larger still. The UI must not plot it as a monotone
funnel or imply the counts can only fall; the honest labels are in the rows themselves.

**`recoverable_ceiling` is the honesty ceiling, not an accuracy** — the fraction of
transactions the *observed* world even contains the answer for (a run whose observers never
heard the true announcer cannot name it, however good the model is). It is read at THIS run's
`observer_fraction`, so a less-observed world reports a lower ceiling. **It replaces the
hardcoded 41.5%** everywhere that number used to appear (landing SHASTRA bar + title, World
station). Ship the run's own value; never re-type the old constant.

**`protocol` is a label, not an assumption** (§1.1) — the UI's claim about train-past /
test-future reads this string rather than asserting it.

**`layer` on each funnel row** is the Sanskrit layer name the landing already keys its eight
stations by, so one fixture count feeds both the landing and the Thread without a lookup
table in the frontend.

### 1.1 · Where each headline figure comes from

The exporter maps the run's own reports to `world.json`; it must not recompute anything.
"`eval_report.json`" below means the **run's own** `scores/eval_report.json` (the artifact the
BUDDHI stage writes and ships with the run), falling back to `measurements/<run>/model_report.json`
when a run was scored but not re-measured.

| `world` figure | source |
|---|---|
| `headline.l1_top1` | `origin_accuracy.json` → `by_granularity.l1_asn.scores.ensemble.top1` |
| `headline.l0_top1` | `origin_accuracy.json` → `by_granularity.l0_host.scores.ensemble.top1`. Both come from the per-granularity block, which is where the curves live; never synthesise an L0 figure from the L1 one |
| `headline.campaign_recall` | `eval_report.json` → `wallet_model.campaign_recall` |
| `headline.elliptic_f1` | `eval_report.json` → `elliptic_external.f1`, **only when `available` is true** (see below) |
| `headline.pair_precision` | `measurements/<run>/cluster_metrics.json` → **`pair_precision`** |
| `recoverable_ceiling` | `origin_accuracy.json` → `recoverable_ceiling` |
| `protocol` | `eval_report.json` → `protocol` |
| `naive_first_seen_top1` | `origin_accuracy.json` → `scores.first_seen.top1` |

**`pair_precision` is the observed same-owner pair precision, and the UI must label it that
way.** `cluster_metrics.json` carries its own `metric_note`: the figure is *same-cluster address
pairs restricted to the addresses the stage observed*, and it is **"not comparable to the
full-cluster 0.36/0.44 quoted in contract section 5."** Those two numbers are different
measurements. Do not present `pair_precision` as "the 0.36 dial"; the 0.36 is a SAME_OWNER
**edge-confidence** rung and belongs to the client-side union-find dial, which is unaffected.

The `origin_curve` block's three series come from `origin_accuracy.json` → `by_granularity`, keyed
`l0_host` and `l1_asn` (each with `top1` / `abstain_rate` per rung), and the shortlist series from
the `l3_shortlist_topk` block's `topk`. Every curve point is a **measured run** — the run's own
report plus its sibling `measurements/*sweep*` reports, de-duplicated by fraction and sorted. A
single measured run draws a single honest dot; nothing is interpolated or invented.

**`campaign_recall` and `tx_pr_auc` are new keys**, both required and non-null in
`wallet_model` (contract §7.1). `campaign_recall` is the headline; `tx_pr_auc` is the
transaction-grain PR-AUC, which the World screen can show beside the actor figure to make the
point that the two grains are measured separately.

**`elliptic_external` has two shapes and the UI must render both** (contract §7.3). When
`available` is false the block carries only `reason` (`dataset_not_vendored`, or
`not_run_for_this_run`). **Export `elliptic_f1` as `null` in that case, never `0.0`** — an absent
external validation and a model that scored zero on it are opposite claims, and the World screen's
defence list has to be able to drop the entry rather than print a zero. The same rule the rest of
the app already follows for a missing measurement.

**`protocol` must be surfaced as a label, not a constant.** It is the string
`inductive_time_ordered`; the UI's claim about train-past/test-future should read that value
rather than assert it, so a run that ever split differently cannot be described as this one.

---

## 2 · Origin (`/origin/{txid}`, `origin.json` / `origin-abstain.json`) — multi-granular

**Added fields** (existing ones kept for back-compat where noted):
```json
{
  "txid": "…", "txid_display": "4a7f2c91…8b3e",
  "estimator": "ensemble",
  "abstain": false, "abstain_reason": null,
  "first_seen_us": 0, "window_ms": 0,

  "attribution": {                         // NEW — the hero, operator-level (L1/L2)
    "asn": 4808, "as_org": "China Unicom", "net_class": "residential",
    "geo_country": "IN", "p_asn": 0.0, "p_country": 0.0, "margin": 0.0
  },

  "shortlist": [                           // NEW name for the L3 candidate set (was "lanes")
    { "peer_ip_display": "103.x.x.x", "peer_port": 0,
      "asn": 4808, "as_org": "…", "geo_country": "IN", "net_class": "residential",
      "p_origin": 0.0, "rank": 1, "announcements_ms": [0,0],
      "peer_ip": "…"                       // seed only, NEVER rendered
    }
  ],
  "shortlist_k": 5,

  "features": [{"label":"…","value":"…","gloss":"…"}],   // unchanged (timing_mle inputs added)
  "p_origin": 0.0, "runner_up_p": 0.0                    // kept: top candidate summary
}
```
- **Origin station candidate rings:** radius still = **inverse likelihood** from `p_origin`
  (not rank). Now **color/group candidates by ASN** — same-operator candidates share a hue so
  the "it's this operator" story reads visually. The confidence shell = the shortlist; the L1
  operator + region is the DOM verdict headline.
- **Ceiling gauge** reads `world.origin_curve.l1_asn` at the run's `observer_fraction`, not
  `41.5`. Show the L1 number as the hero and the L0 host number as the honest sub-line.
- **Abstain** unchanged behaviour (grey fog-dome, "No answer available"), reason vocab unchanged.
- `p_origin` still **not renormalised** — a shortlist summing < 1.0 is the "maybe none" signal;
  render the shortfall.

> Migration note: rename `lanes` → `shortlist` in the loader/consumers; add the `attribution`
> block. `GlobeScreen` and `OriginScreen` both consume this; Globe keeps country-level plotting
> but should tint by `attribution.net_class`/risk.

---

## 3 · Graph (`/graph`, `graph.json` / `graph-address.json`) — dual view

- Edge/node contract unchanged (`SPENDS/RECEIVES/ANNOUNCED_BY/SAME_OWNER/HOSTED_IN/MEMBER_OF`;
  `SAME_OWNER` still never merges, still carries `confidence`; dial still client-side union-find).
- **New `detail=actor`** alongside `cluster`/`address`: returns the actor/address graph as a
  first-class surface (nodes `kind:"address"|"cluster"`, scored). The Map station gains a
  tx-graph ⇄ actor-graph toggle (the "two floors" metaphor extends to two graphs).
- **New node fields (optional):** `peel_chain_id`, `coinjoin` (bool), so the Map can highlight
  a traced peel chain and grey-out set-aside CoinJoin txs.

---

## 4 · Leads queue (`/alerts`, `alerts.json`) — operator-level origin

Each alert's origin fields shift from host to operator:
```json
{ "alert_id":"…","rank":1,"severity":"high","risk_score":0.0,
  "conf_low":0.0,"conf_high":0.0,"headline":"…","subject_display":"group 616",
  "cluster_size":12,"typologies":["peel_chain"],
  "origin_asn":4808,"origin_as_org":"…","origin_country":"IN",   // as_org NEW
  "origin_net_class":"residential",                              // NEW
  "p_asn":0.0,"shortlist_k":5,                                   // NEW (replaces bare origin_p)
  "attribution_ready":true }
```
- Filters/sorts unchanged (risk / confidence / group size; attribution-ready; grouped).
- `attribution_ready` semantics updated (see §6): true when **ASN + net_class + precise
  timestamp** exist — host IP no longer the gate.
- No `origin_peer_ip` in the queue (moves to packet-only).

---

## 5 · Lead detail (`/alerts/{id}`, `alert.json`)

- `origin` nested block now the multi-granular §2 shape (operator hero + shortlist).
- `counters[]` gains kind **`cross_asn_ambiguous`** (shortlist mass split across operators);
  `would_clear` behaviour unchanged (AlertCard already renders it when present).
- `evidence` / `features` (SHAP) unchanged. `confidence` block unchanged. Actor-vs-tx: alert may
  carry `subject_kind: "actor" | "transaction"` so the card labels which queue it came from.

---

## 6 · Proof packet (`/packets/{id}`, `packet.json`) — operator hero

- **`attribution_ready` becomes a real field in `packet.json`** (today ProofScreen derives it —
  DATA-CONTRACTS finding). Frontend must **read the field**, stop deriving.
- `attribution` block, rendered form leads with operator/region:
```json
"attribution": {
  "asn": 4808, "as_org": "…", "net_class": "residential", "geo_country": "IN",
  "p_asn": 0.0, "margin": 0.0,
  "shortlist": [{"peer_ip_display":"103.x.x.x","peer_port":0,"p_origin":0.0}],
  "observed_at_utc": "2026-01-01T00:00:00Z",
  "peer_ip": "…", "peer_port": 0            // OFFICER-ONLY, present in JSON, NEVER rendered
}
```
- On-screen hero changes from `{IP · port · UTC}` to **`{operator(ASN) · region · observed
  UTC}`**; the host IP/port render only as the redacted `103.x.x.x` inside the officer note, or
  not at all on screen. `attribution_ready=false` → the existing honest not-ready box.
- Everything else (full SHA-256 chain, Merkle head, Ed25519, replay hash, BNSS/BSA legal block,
  offline Blob download) **unchanged**. Redaction `maskIp()` must still match backend
  `vaani.redact` byte-for-byte.

---

## 7 · Migration checklist for DRISHTI

1. Add `world.json` fixture + loader export `world`; point `WorldScreen`, `OriginScreen` ceiling,
   and `nav/stages.ts` funnel at it. Delete hardcoded `CEILING`, funnel arrays, band constants.
2. Rename origin `lanes` → `shortlist`; add `attribution` block; update `GlobeScreen`/
   `OriginScreen`/`AlertCard`/`ProofScreen` consumers.
3. Origin rings: tint/group candidates by ASN; verdict headline = operator + region.
4. Leads/alerts: swap `origin_p`/`origin_peer_*` → `p_asn` + `origin_as_org` + `origin_net_class`.
5. Proof: read `attribution_ready` from JSON; hero = operator·region·UTC; host IP officer-only.
6. Map: add `detail=actor` toggle + peel-chain / CoinJoin highlighting (optional, P2).
7. Re-run kill-list scrub: "ASN" → "network operator (ASN)"; no full identifier on screen;
   hashes stay full.

> All new fixtures come from the canonical **agency-regime** run (`observer_fraction ≈ 0.60`).
> One run, one set of numbers, everywhere.


