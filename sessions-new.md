# CHAKRAVYUH — BUILD WORKFLOW (how you actually execute the remodel)

> The execution manual. Companion to **CHAKRAVYUH-REMODEL-PLAN.md** (what to change) and
> **FRONTEND-HANDOFF-V2.md** (what the frontend gets). This file is **how you drive Claude Code
> Opus 4.8 to do it** — exact prompts, exact verification, in what order, and how to run parts in
> parallel. Written for a solo dev on a clock. If you freeze, jump to **§12 · The linear checklist**
> and just do the next unchecked box.

---

## 0 · The one screen (read this, then start)

Six rules that make the whole thing work:

1. **One phase = one fresh session.** Start it, do the phase, `/clear`, next. Never let a session
   sprawl across phases — that's how context rots and Opus starts forgetting the contract.
2. **Always plan first.** Enter plan mode (`Shift+Tab` twice), paste the phase prompt, read the
   plan it returns, approve or correct. Never let it code before you've seen the plan.
3. **Trust gates, not promises.** When Claude says "done," you don't believe the prose — you run
   the **`make`/`pytest` gate** for that phase. Green gate = done. Red = not done. §2 + §8.
4. **PROGRESS.md is the memory.** Every session ends by updating it. Every session starts by
   reading it. That file is how a fresh session knows where you are.
5. **Parallelize only what's independent.** P0 is solo (everything depends on it). After P0, the
   backend-depth lane and the frontend-integration lane run in parallel worktrees. §6.
6. **Commit at every green gate.** A green, committed checkpoint is a save point you can return to
   with `/rewind` or `git`. Never build on top of a red gate.

**Right now, today:** do **§3 (one-time setup, ~30 min)** → then **Session P0-a (§7)**. That's it.

---

## 1 · Where you are vs where you're going

**You are not building from scratch — you are remodeling a working system.** The backend is real
and complete: all 8 layers (`mayajaal … pramaan`) plus `api/` and `eval/` are ~15k lines of real
Python with a 13-file pytest suite and a Makefile full of verification targets. The recent git
history is all *frontend* work; the backend has been stable. So this is **surgery on a live
patient**, not a greenfield. That's good news — it means there are already objective gates that
tell you whether a change worked (§2).

**"Are we using a database?" — No.** And that's correct, don't add one. The pipeline is
**Parquet files on disk** read/written with Polars/PyArrow. Each run writes to
`data/generated/<run-id>/` (chain, capture, normalised, graph, scores, signals, alerts, packets),
with the answer key in a sibling `ground_truth/<run-id>/` and scores in `measurements/<run-id>/`.
The frontend never touches any of that — it gets **static JSON fixtures**. A database would add a
network surface, a daemon, and a dependency, all of which break the "offline / air-gapped" hard
rule. Files-on-disk is the right architecture for a single-analyst forensic tool. (Minor: `duckdb`
is pinned in `pyproject.toml` but never imported — dead dependency, delete it in cleanup.)

**The seam to the frontend (unchanged, and this is the key to integration):**
```
src/chakravyuh/api/serialize.py   ← single source of truth for every payload shape
        │  (same functions called by both paths)
        ├─► api/app.py  →  FastAPI on 127.0.0.1:8000   (live, offline, no auth)
        └─► scripts/export_ui_fixtures.py  →  data/fixtures/ui/*.json
                                                     │  (copied to)
                                            apps/drishti-v2/src/data/fixtures/*.json
```
Because both the live API and the fixture files come from `serialize.py`, **fixture shape == API
shape by construction.** When you change what the backend outputs, you change `serialize.py`, and
both the API and the fixtures follow. This is why FRONTEND-HANDOFF-V2 keeps saying "the seam is
unchanged, we add fixtures, we don't move the seam."

---

## 2 · The golden rule of trust: gates, not promises

Your biggest worry — *"how do I even know it actually did what I said?"* — is already solved by
this repo, and that's rare. **You do not read Claude's summary and hope. You run the gate.** The
backend ships with objective, deterministic checks:

| Gate command | What it proves |
|---|---|
| `make validate-data` | The generated world is *honest*: value conservation, one true originator per tx, relay delays are noisy (not a clean cascade), heavy-tailed values, **and the leakage checks** (see below). Writes `data/generated/<run>/validation/report.json`. |
| `make verify` | Aggregate: runs every per-stage contract check (`verify-s00 … verify-s11`), quarantine (no answer-key leakage into observable data), replay (packet hash reproduces), determinism (same seed → same bytes). |
| `pytest` (or `make test` if present) | The 13-file unit suite across all layers. |
| `make peek` | Human-readable dump of a run's headline numbers — eyeball the actual outputs. |
| `ruff check . && mypy src` | Lint + strict types stay clean. |

**The leakage acceptance bands (this is the honesty engine — memorize it):** `validate-data`
reports, for each trivial rule, how often it alone identifies the true originator. The rule
"always guess the first announcement seen" **must score between ~0.15 and ~0.60** at the default
observer fraction. If it scores near 1.0, the relay delays aren't doing their job and the whole
benchmark is fake; if near 0, something's broken. A depth-2 decision tree on observable columns
alone is also trained and its accuracy reported — it must *not* be able to cheat. **When you tell
Claude to change MAYAJAAL, the proof it didn't break the world is that these bands still hold.**

**The trust loop, every time Claude claims a phase is done:**
1. Run the phase's gate command (§8 lists which one per phase).
2. Green → inspect the diff: `git diff --stat` then skim the real diffs. Ask Claude "show me the
   diff for X and explain why it's correct."
3. Green + diff sane → commit. That's a save point.
4. Red → paste the failure back to Claude in the *same* session and have it fix, re-gate. Do **not**
   `/clear` on a red gate (you'd lose the context of what it was doing).

If Claude ever says "the test is wrong, let me change the test" — stop and read that diff yourself.
Weakening a gate to make it pass is the one failure mode that quietly destroys the whole
credibility story. A gate may legitimately need updating when a contract genuinely changes (e.g.
new `world.json`), but you approve that consciously, never as a way to get to green.

---

## 3 · One-time setup (~30 minutes, do this first)

Do these once at the repo root before any phase. They pay for themselves in the first session.

**3.1 — Point CLAUDE.md at the remodel.** The repo's `CLAUDE.md` is the always-loaded contract, but
it currently describes the *frontend*. Add a short block at the top so every backend session loads
the new direction. Open Claude Code at `/home/void/chakravyuh` and paste:
```
Add a section to the top of ./CLAUDE.md titled "BACKEND REMODEL v2 (active work)". Keep it under
25 lines. It must say: (1) we are remodeling the backend per docs/CHAKRAVYUH-REMODEL-PLAN.md;
(2) the frozen baseline is docs/DATA-CONTRACTS.md and the frontend delta is docs/FRONTEND-HANDOFF-V2.md;
(3) the core reframe is multi-granular origin attribution — L1 operator/ASN is the hero, L0 host is
officer-only; (4) the demo default regime is observer_regime "agency" (observer_fraction ≈ 0.60);
(5) every change must keep `make validate-data` leakage bands holding and `make verify` green;
(6) keep the 8 Sanskrit layer names. Then show me the diff before writing.
```
Approve the diff. Keep it tight — CLAUDE.md is loaded into *every* session, so bloat there is a
permanent context tax. Point at the plan docs; never paste the plan into CLAUDE.md.

**3.2 — Create verification subagents** so heavy checking runs in an isolated context (it doesn't
pollute your main session). Create `.claude/agents/truth-checker.md`:
```
---
name: truth-checker
description: Runs make validate-data + make verify, reads the JSON reports, and reports ONLY what is broken (failed contracts, leakage bands out of range, determinism drift). Use after any MAYAJAAL/pipeline change.
tools: Bash, Read, Grep, Glob
model: sonnet
---
You verify the CHAKRAVYUH pipeline. Run the requested gate commands, read the report JSON under
data/generated/<run>/validation/ and measurements/<run>/, and report a terse PASS/FAIL list. For
each FAIL give the exact metric, its value, and the expected band. Do not fix anything. Do not
summarize what passed beyond a one-line "N checks passed".
```
Why sonnet, not opus: verification is mechanical and you'll run it constantly — a cheaper isolated
agent keeps your Opus budget for the real reasoning and keeps the check *out* of your main thread's
context window. Add a second agent `.claude/agents/estimator-analyst.md` (model: opus) later for
reading eval reports and judging whether L1 accuracy is genuinely strong.

**3.3 — Wire Playwright MCP** (for the frontend-integration lane only). Create `.mcp.json` at the
repo root:
```json
{ "mcpServers": { "playwright": { "command": "npx", "args": ["-y", "@playwright/mcp@latest"] } } }
```
This lets a frontend session screenshot `drishti-v2` and self-correct against the redesign intent.

**3.4 — A guardrail hook (optional but recommended).** Create `.claude/settings.json` with a
PostToolUse hook that auto-runs ruff after any Python edit, so style never drifts:
```json
{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write",
  "hooks": [ { "type": "command",
    "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q '\\.py'; then ruff check --fix $(echo \"$CLAUDE_TOOL_INPUT\" | grep -o '[^\"]*\\.py') 2>/dev/null || true; fi" } ] } ] } }
```
(Keep it non-blocking with `|| true` so a lint nit never halts a build. You can skip 3.4 if hooks
feel fiddly — it's a nicety, not load-bearing.)

**3.5 — Establish the PROGRESS discipline.** You already have `PROGRESS.md` (it tracks the
frontend). Add a `## BACKEND REMODEL` section header now so backend sessions have a home to write
to, separate from the frontend log.

---

## 4 · The session ritual (do this every single session)

Same seven beats every time. Muscle memory. If you only remember one thing: **plan → approve →
build → gate → commit → PROGRESS → /clear.**

1. **Open fresh** at the right directory (repo root, or a worktree — §6). A fresh session = clean
   context.
2. **Orient it** — first message: `Read PROGRESS.md (the BACKEND REMODEL section) and the relevant
   section of docs/CHAKRAVYUH-REMODEL-PLAN.md, then tell me in 3 lines where we are and what this
   session's goal is.` This costs ~5k tokens and prevents it from wandering.
3. **Plan mode** (`Shift+Tab` until it says ⏸ plan mode). Paste the session prompt from §7. Read
   the plan. If it's wrong or vague, say so and make it re-plan. **Approve only a plan you'd sign.**
4. **Build.** Let it execute. Watch for it inventing numbers (it must read them from
   `measurements/`, never hardcode) or weakening a gate (§2).
5. **Gate.** Run the §8 gate for this phase — ideally via the `truth-checker` subagent so the raw
   output doesn't flood your window: `Use the truth-checker subagent to run make validate-data and
   make verify on run <id> and report only failures.`
6. **Commit + PROGRESS.** Green → `git add -A && git commit -m "..."`, then have Claude append a
   dated entry to PROGRESS.md's BACKEND REMODEL section (what changed, which gate passed, the actual
   headline numbers from the run).
7. **`/clear`** (or close the session). Next phase starts clean.

**When to `/compact` instead of `/clear`:** almost never in this workflow. `/compact` summarizes and
keeps going in the *same* session — use it only if you're mid-phase, haven't hit the gate yet, and
`/context` shows you're above ~70% full. `/clear` is for *between* phases (which is most of the
time). Because each phase is scoped to one layer, you should rarely need `/compact` at all.

---

## 5 · Context management (keep Opus sharp)

The context window is everything Claude can see at once. Let it fill with stale tool output and old
phases and it gets dumber and more forgetful — exactly when you can't afford it. Rules:

- **`/context`** — run it any time to see the token breakdown (system prompt, CLAUDE.md, messages,
  tool output). Glance at it before big steps. If messages are dominating, you've been in the
  session too long — gate, commit, `/clear`.
- **Auto-compaction & microcompact happen for you.** Claude Code automatically drops stale tool
  results (microcompact) and, near the limit, summarizes the session (auto-compact). You don't
  trigger these; you *avoid needing them* by keeping sessions short.
- **One phase, one session.** This is the real lever. A phase touches one or two layers and ends at
  a gate — that's a naturally bounded chunk that fits comfortably in context. Don't chain phases.
- **Don't paste big files into chat.** Tell Claude to `Read` them itself — that way they can be
  compacted out later. Pasted text is stickier and wastes the window.
- **1M context is available but not a license to sprawl.** A huge messy context still degrades
  reasoning. Treat the discipline as the goal; the big window is just headroom for the occasional
  large-diff phase (P0 regeneration), not an invitation to run all day in one session.
- **CLAUDE.md stays lean.** It's loaded every session. Point at docs; don't inline them.

---

## 6 · Parallel lanes (git worktrees)

Running several Claude Code sessions on the same repo at once is the big time-saver — but only for
**genuinely independent** work, or they'll fight over the same files and you'll spend the saved time
resolving merge conflicts. Here's the dependency reality of this remodel:

```
        ┌─────────────────────────────────────────────┐
   P0   │ REFRAME + RECALIBRATE  (mayajaal, shastra,   │   ← SOLO. Everything below
 (solo) │ eval, serialize, regenerate canonical run)   │     depends on the new data +
        └───────────────────────┬─────────────────────┘     the new serialize shapes.
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                                ▼
  LANE A · backend depth (main tree)          LANE B · frontend integration (worktree)
  P2 JAAL dual graph / peel / CoinJoin         update apps/drishti-v2 to the v2 fixtures
  → P1 BUDDHI + Elliptic external              per FRONTEND-HANDOFF-V2 (world.json,
  → P3 SSL-GNN / real-slice / holdout          attribution block, lanes→shortlist, etc.)
  (touches: jaal/ buddhi/ eval/ vendor/)       (touches: apps/drishti-v2/** only)
```

**Why this split is safe:** Lane A is Python under `src/chakravyuh/**`; Lane B is TypeScript under
`apps/drishti-v2/**`. They do not touch the same files, so they never conflict. Lane B only needs
the **fixtures** P0 produced — it doesn't care how the backend computes them. So the moment P0 lands
and regenerates fixtures, you (or a teammate, or just a second session while you sleep) can run Lane
B in parallel with Lane A.

**Within Lane A, keep it sequential.** P2 (the dual graph + peel/CoinJoin) produces features that P1
(BUDDHI) consumes (peel-chain depth, CoinJoin participation). Running P1 and P2 in parallel means
BUDDHI wouldn't see the new features and you'd need an awkward integration merge. Do **P2 → P1 → P3**
in order in the main tree. The parallelism you want is *A ∥ B*, not splitting A.

**Worktree setup (exact commands).** A worktree is a second working directory backed by the same
repo, on its own branch — isolated files, shared history.
```bash
# from /home/void/chakravyuh, after P0 is committed on main:
git worktree add ../chakravyuh-frontend -b lane/frontend-v2   # Lane B lives here
# now you have two dirs:
#   /home/void/chakravyuh            → open Claude Code here for Lane A (backend depth)
#   /home/void/chakravyuh-frontend   → open a SECOND Claude Code here for Lane B (frontend)
```
Or use the built-in flag if your Claude Code version supports it: `claude --worktree lane/frontend-v2`
spins the worktree and the session together.

**Gotchas:**
- **Node deps:** the worktree needs its own `npm install` inside `apps/drishti-v2` (node_modules
  isn't shared). Do it once when you create the worktree.
- **Python venv:** Lane A uses the repo `.venv`; Lane B doesn't run Python, so no conflict.
- **Ports:** if you run the API (`make api`, port 8000) in Lane A and the Vite dev server in Lane B
  (usually 5173), they don't collide. Don't run two API servers on 8000 at once.
- **Merging back:** when Lane B is done, `git checkout main && git merge lane/frontend-v2`. Because
  it only touched `apps/drishti-v2/**`, the merge is clean. Then `git worktree remove ../chakravyuh-frontend`.
- **Don't** run two sessions editing `src/chakravyuh/**` at once. That's the one thing that bites.

---

## 7 · The session-by-session plan (copy-paste, nothing to add)

> # ▶▶▶ SESSIONS START HERE ◀◀◀
> Subagents + MCP are already set up. **Start with SESSION P0-a below.** Go top to bottom: P0-a →
> P0-b → P0-c → P0-d, one Claude Code session each, `/clear` between them. After P0-d commits, you
> can run Lane A and Lane B at the same time. You don't need to read the plan docs yourself — each
> PASTE block tells Claude to read them for you.

**How to use this section — the rhythm is identical for every session:**
1. **▶ Open a fresh Claude Code session** at the repo root (`cd /home/void/chakravyuh && claude`).
   For Lane B sessions, open it in the worktree instead (§6).
2. Enter **plan mode** — press `Shift+Tab` until it shows ⏸ plan mode.
3. **Copy the whole `PASTE` block** for the session and paste it. It already tells Claude which
   files to read and to plan before writing — you don't add anything.
4. Read the 3-line orientation + the plan it returns. If good, tell it `go` (this also leaves plan
   mode). If wrong, correct it and let it re-plan.
5. When it says done, **paste the `VERIFY` block.** Green → `git add -A && git commit -m "<session>: ..."`,
   then `update PROGRESS.md BACKEND REMODEL section with what changed + the gate that passed + the real numbers`.
6. **`/clear`** and move to the next session block.

`<run>` = your canonical run id — use `agency-v2` everywhere below.

### ── P0 · Reframe + recalibrate (SOLO, main tree, in this exact order) ──

**SESSION P0-a — observer regimes + biased observers** *(touches: mayajaal/network, run_config.json)*

PASTE:
```
Session P0-a of the CHAKRAVYUH backend remodel. First read PROGRESS.md (the BACKEND REMODEL section)
and docs/CHAKRAVYUH-REMODEL-PLAN.md §3, and tell me in 3 lines where we are. Then plan the task below
and show me the plan BEFORE writing any code.

Goal: implement REMODEL-PLAN §3 "Change" for MAYAJAAL. In run_config.json introduce a named
observer_regime preset system: "agency" → observer_fraction ≈ 0.60, n_observers ≈ 48, observers
placed with ASN/IXP bias (preferentially peering high-degree nodes), and "stealth" → the old 0.10
uniform academic attacker. Add the eval regime ladder {0.02,0.05,0.10,0.25,0.50,0.60,0.70}. Set the
demo default to "agency". Implement the biased observer placement in src/chakravyuh/mayajaal/network.py.
Do NOT change the relay-delay model — the noisy per-peer Poisson delays must stay exactly as they are.
Also delete the unused `duckdb` dependency from pyproject.toml. Do not hardcode any accuracy numbers.
```
VERIFY:
```
Use the truth-checker subagent to run `make validate-data` on a fresh small run and report only
failures. Confirm the "first announcement seen" leakage rule still lands in ~0.15–0.60 and the
determinism check is green.
```

**SESSION P0-b — multi-granular origin ground truth + ASN rollup** *(touches: mayajaal/export, setu)*

PASTE:
```
Session P0-b of the CHAKRAVYUH backend remodel. First read PROGRESS.md (BACKEND REMODEL section) and
docs/CHAKRAVYUH-REMODEL-PLAN.md §3, §4 and §11, and tell me in 3 lines where we are. Then plan the
task below and show me the plan BEFORE writing any code.

Goal: extend ground_truth/<run>/origins.parquet with true_origin_asn, true_origin_as_org,
true_origin_net_class, true_origin_country (keep L0 true_origin_ip but it is no longer the headline
scoring key). Add normalised/asn_rollup.parquet (one row per ASN: announcement counts, distinct
peers, net_class mix, frac_rank_one) as the substrate for L1 attribution. Add the per-tx arrival
matrix view {txid → [(observer_id, peer_ip, seen_us)]} that the timing estimator will need. Update
the relevant contract checks. Confirm NO ground-truth column leaks into any observable file (the
quarantine rule). Show me the schema diffs before writing.
```
VERIFY:
```
Use the truth-checker subagent to run `make verify-quarantine` and `make verify-contracts` and report
only failures. Confirm no answer-key column appears in any observable file and the new schemas validate.
```

**SESSION P0-c — SHASTRA real estimator stack + per-granularity eval** *(touches: shastra/estimate, eval)*

PASTE:
```
Session P0-c of the CHAKRAVYUH backend remodel. First read PROGRESS.md (BACKEND REMODEL section) and
docs/CHAKRAVYUH-REMODEL-PLAN.md §6 and §10, and tell me in 3 lines where we are. Then plan the task
below and show me the plan BEFORE writing any code.

Goal: implement the estimator stack, each independently runnable: (1) first_spy baseline kept;
(2) timing_mle — multi-observer maximum-likelihood source estimator over the arrival matrix + known
relay-delay model (rumor-centrality / MLE, Shah-Zaman style); (3) asn_rollup — lift candidate mass to
L1 with the ASN prior, this is the headline; (4) ensemble — calibrated (Platt) blend trained across
regimes. Outputs per §6: L3 shortlist with un-renormalised p_origin, L1 origin_asn/as_org/net_class +
p_asn, L2 origin_country + p_country, margin, abstain + reason. Then extend src/chakravyuh/eval to
report origin accuracy PER GRANULARITY (l0_host, l1_asn, l2_region, l3_shortlist_topk) each with
top1/topk, abstain_rate, and by_observer_fraction over the regime ladder, split by traffic type
(clear/vpn/tor). Read all numbers from the run; hardcode nothing.
```
VERIFY:
```
Run `make sweep-observer-fraction` (or the eval target). Then use the estimator-analyst subagent to
read measurements/<run>/origin_accuracy.json and confirm: the per-granularity by_observer_fraction
arrays exist, the L1 curve sits clearly above the L0 curve, L0 tracks the 11–60% band, L1 top-1 is
genuinely high at 0.60, and baseline_beaten is true.
```

**SESSION P0-d — serialize + regenerate canonical run + fixtures** *(touches: api/serialize, scripts, Makefile)*

PASTE:
```
Session P0-d of the CHAKRAVYUH backend remodel. First read PROGRESS.md (BACKEND REMODEL section),
docs/CHAKRAVYUH-REMODEL-PLAN.md §9 and §11, and ALL of docs/FRONTEND-HANDOFF-V2.md, and tell me in 3
lines where we are. Then plan the task below and show me the plan BEFORE writing any code.

Goal: update src/chakravyuh/api/serialize.py so payloads carry the new shapes: origin gets the
"attribution" block {asn,as_org,net_class,geo_country,p_asn,p_country,margin} and the shortlist
(rename the old "lanes" to "shortlist"); alerts get origin_asn/origin_as_org/origin_net_class/p_asn/
shortlist_k; packet.json gets attribution_ready as a REAL field (stop making the frontend derive it)
and an attribution block leading with L1, with peer_ip/peer_port present but marked officer-only. Add
a new world.json payload (funnel + origin_curve{l0_host,l1_asn,l3_shortlist} + headline +
literature_band + defences) sourced from measurements/<run>. Then regenerate the canonical run named
"agency-v2" end to end and re-export all UI fixtures. Fix the fixtures-ui Makefile target to point at
this run (it currently references a non-existent _sweep-0.10 run), and add a `sync-fixtures` target
that copies data/fixtures/ui/*.json into apps/drishti-v2/src/data/fixtures/. Keep redaction
(vaani.redact) byte-identical. Do not hardcode numbers.
```
VERIFY:
```
Use the truth-checker subagent to run `make verify` and report only failures. Then run `make peek` and
show me the agency-v2 headline numbers. Then open data/fixtures/ui/origin.json, alerts.json,
packet.json and world.json and confirm the shapes match docs/FRONTEND-HANDOFF-V2.md (attribution block
present, "shortlist" not "lanes", attribution_ready a real field, world.json exists).
```
> ✅ After P0-d commits, the fixtures exist — **now you can run Lane A and Lane B in parallel.**

### ── LANE A · backend depth (main tree, in this order, after P0) ──

**SESSION P2 — JAAL dual graph + peel/CoinJoin tracers** *(touches: jaal/build, jaal/cluster, jaal/view)*

PASTE:
```
Session P2 of the CHAKRAVYUH backend remodel (Lane A). First read PROGRESS.md (BACKEND REMODEL
section) and docs/CHAKRAVYUH-REMODEL-PLAN.md §5, and tell me in 3 lines where we are. Then plan the
task below and show me the plan BEFORE writing any code.

Goal: promote the actor/address graph to a first-class scored surface alongside the transaction graph
(dual graph, Elliptic++ shape). Add a serialize detail=actor view. Implement the peel-chain tracer
(large-UTXO → small-peel+change sequences, emit peel_chain subgraph with depth + leak-rate) and the
CoinJoin/mixer detector (equal-value-output symmetry + high in/out; mark the tx and offer
set-aside-with-reason so common-input-ownership is NOT applied across a mixer). Keep SAME_OWNER as
never-merging confidence-weighted edges and the 0.36 anchor. Add node fields peel_chain_id and
coinjoin. Keep the existing graph contract back-compatible.
```
VERIFY:
```
Use the truth-checker subagent to run the graph-stage verify (verify-s08 or equivalent) and
`pytest tests/test_jaal.py`, and report only failures. Confirm detail=actor serializes.
```

**SESSION P1 — BUDDHI strong + honest (Elliptic external validation)** *(touches: buddhi, eval, vendor/)*

PASTE:
```
Session P1 of the CHAKRAVYUH backend remodel (Lane A). First read PROGRESS.md (BACKEND REMODEL
section) and docs/CHAKRAVYUH-REMODEL-PLAN.md §7 and §10, and tell me in 3 lines where we are. Then
plan the task below and show me the plan BEFORE writing any code.

Goal: keep the GBM as the standalone workhorse on morphological features (fan-in/out, peel depth/leak,
rapid-hop dwell, structuring, CoinJoin participation, velocity/burstiness, fee anomaly) plus
origin-fusion features (mean_p_asn, frac_origin_abstained) and cluster-shape (min_edge_confidence).
Add campaign-level recall as the headline metric alongside tx- and actor-level PR-AUC. Enforce
inductive time-ordered eval (train past → test future) as the ONLY reported protocol. Then build the
external-validation leg: vendor the Elliptic/Elliptic++ dataset offline under vendor/, train+score the
SAME model recipe on it, and ship those numbers in the elliptic_external sub-block of the eval report.
The recipe on our data and on Elliptic must be the same code path. Do not hardcode numbers.
```
VERIFY:
```
Use the estimator-analyst subagent to read measurements/<run>/model_report.json and confirm it shows
campaign-level recall + inductive PR-AUC + a real elliptic_external F1, and that the eval is genuinely
inductive (no future leakage). Then have truth-checker run `pytest tests/test_buddhi.py`.
```

**SESSION P3 — polish (OPTIONAL — skip if time-short)** *(touches: buddhi embeddings, mayajaal real-slice)*

PASTE:
```
Session P3 of the CHAKRAVYUH backend remodel (Lane A, optional). First read PROGRESS.md (BACKEND
REMODEL section) and docs/CHAKRAVYUH-REMODEL-PLAN.md §7 and §13 (P3), and tell me in 3 lines where we
are. Then plan the task below and show me the plan BEFORE writing any code.

Goal: add self-supervised graph embeddings (Deep-Graph-Infomax / GraphSAGE over the JAAL dual graph)
as extra GBM columns, flagged model:"gbm_gnn_v2" vs "gbm_v2" per row so a mixed run stays auditable,
gated on baseline_beaten. Optionally wire real-slice mode (real chain topology under the synthetic
network) and the parameter-holdout appendix (train one regime, test another, report the gap). The GNN
add-on must be droppable without breaking the GBM path.
```
VERIFY:
```
Use the truth-checker subagent to run `make verify` and confirm baseline_beaten is still true with
embeddings on, determinism holds, and nothing regressed.
```

### ── LANE B · frontend integration (in the worktree, parallel with Lane A) ──

> Set up the worktree first (once): `git worktree add ../chakravyuh-frontend -b lane/frontend-v2`
> then `cd ../chakravyuh-frontend/apps/drishti-v2 && npm install`. Open Claude Code in
> `../chakravyuh-frontend` for all Lane B sessions.

**SESSION B1 — world.json + loader + kill hardcoded numbers**

PASTE:
```
Session B1 — DRISHTI frontend v2 integration. First read PROGRESS.md and docs/FRONTEND-HANDOFF-V2.md
§1 and §7 (step 1), and tell me in 3 lines where we are. Then plan the task below and show me the plan
BEFORE writing any code.

Goal: copy the new world.json fixture into apps/drishti-v2/src/data/fixtures/ and export it from
src/data/loader.ts. Point WorldScreen, the OriginScreen ceiling gauge, and nav/stages.ts at
world.json. Delete every hardcoded constant: CEILING=41.5, the funnel arrays, the 22.1 / 11-60 band
literals. One source, no hand-typed numbers. After building, screenshot WorldScreen and OriginScreen
with the Playwright MCP and confirm the numbers now come from the fixture.
```
VERIFY:
```
Run `npm run build` and `npm run typecheck` in apps/drishti-v2 and report failures. Screenshot
WorldScreen + OriginScreen and confirm no hardcoded 41.5/22.1 remain and numbers match world.json.
```

**SESSION B2 — origin multi-granular + Leads + Proof operator-level**

PASTE:
```
Session B2 — DRISHTI frontend v2 integration. First read PROGRESS.md and docs/FRONTEND-HANDOFF-V2.md
§2, §4, §5, §6 and §7 (steps 2-5), and tell me in 3 lines where we are. Then plan the task below and
show me the plan BEFORE writing any code.

Goal: rename lanes→shortlist in the loader + all consumers; add the attribution block. Origin rings:
tint/group candidate rings by ASN, verdict headline = operator + region (radius still = inverse
likelihood). Leads: swap origin_p / origin_peer_* for p_asn + origin_as_org + origin_net_class; keep
filters/sorts. Proof: READ attribution_ready from JSON (stop deriving it), hero becomes
{operator(ASN) · region · observed UTC}, host IP officer-only/redacted. Keep redaction maskIp()
byte-for-byte with the backend. Screenshot Origin, Leads and Proof and self-correct against intent.
```
VERIFY:
```
Run `npm run build` and `npm run typecheck` in apps/drishti-v2 and report failures. Screenshot Origin,
Leads, Proof; confirm operator-level hero, no full identifier on screen, SHA-256 hashes still full.
```

**SESSION B3 — map dual view + kill-list scrub (optional, pairs with P2)**

PASTE:
```
Session B3 — DRISHTI frontend v2 integration. First read PROGRESS.md and docs/FRONTEND-HANDOFF-V2.md
§3 and §7 (steps 6-7), and tell me in 3 lines where we are. Then plan the task below and show me the
plan BEFORE writing any code.

Goal: add the tx-graph ⇄ actor-graph toggle (detail=actor), peel-chain highlight + CoinJoin grey-out.
Re-run the kill-list scrub: "ASN" renders as "network operator (ASN)", no full identifier on screen,
hashes stay full. Also repoint the Makefile verify-drishti target from apps/drishti to apps/drishti-v2.
Screenshot the Map both ways.
```
VERIFY:
```
Run `npm run build` and `npm run typecheck` in apps/drishti-v2 and report failures. Screenshot the Map
in both tx and actor modes.
```
> When Lane B is green: `git checkout main && git merge lane/frontend-v2` then
> `git worktree remove ../chakravyuh-frontend`.


---

## 8 · Verification cheat-sheet (which gate per phase)

| Session | Gate command | Pass condition |
|---|---|---|
| P0-a | `make validate-data` | first-seen leakage rule in ~0.15–0.60; determinism green |
| P0-b | `make verify-quarantine` + `make verify-contracts` | no answer-key column in observable files; new schemas validate |
| P0-c | eval / `make sweep-observer-fraction` | per-granularity `by_observer_fraction` present; L1 curve > L0 curve; `baseline_beaten` true |
| P0-d | `make verify` + `make peek` | all stages green; fixtures match FRONTEND-HANDOFF-V2 shapes; world.json exists |
| P2 | graph stage check + `pytest tests/test_jaal.py` | dual graph + peel/CoinJoin present; `detail=actor` serializes |
| P1 | `pytest tests/test_buddhi.py` + read `model_report.json` | campaign recall + inductive PR-AUC + real `elliptic_external` F1 |
| P3 | `make verify` | `baseline_beaten` still true; nothing regresses |
| B1–B3 | `npm run build && npm run typecheck` in drishti-v2 + Playwright screenshots | builds clean; numbers from fixtures; no full identifier on screen; hashes full |

**Reading a "green" honestly:** a passing gate means the *contract* holds, not that the *idea* is
good. For the two judgment calls that matter — "is L1 origin accuracy genuinely impressive?" and "is
the Elliptic F1 real and the eval truly inductive?" — don't trust the gate alone; open the actual
numbers in `measurements/<run>/` (or have `estimator-analyst` read them) and look. Those two numbers
are your headline to NTRO; you personally need to believe them.

---

## 9 · How the finished backend reaches the frontend (the promise you made)

You promised the frontend team a clean handoff. Here's the mechanical flow, and why it's low-risk:

1. Backend work changes `serialize.py` (the single source of truth). Both the live API and the
   fixture exporter read from it, so they can't drift apart.
2. `make fixtures-ui` (repointed in P0-d to the `agency-v2` run) writes `data/fixtures/ui/*.json`.
3. Those files are copied into `apps/drishti-v2/src/data/fixtures/*.json` — the frontend imports
   them through `src/data/loader.ts`. (Consider a tiny `make sync-fixtures` target that does the
   copy, so it's one command, not manual.)
4. The frontend never runs Python and never hits a database — it reads static JSON. That's what
   makes it air-gappable and what makes the handoff a *file drop*, not an integration project.
5. **Handoff artifact:** when the backend is done, the frontend team gets (a) the regenerated
   fixtures, (b) FRONTEND-HANDOFF-V2.md as the change spec, and (c) optionally the live API on
   `127.0.0.1:8000` (`make api`) to test against. Because fixture shape == API shape, code written
   against fixtures works against the API unchanged.

If you do Lane B yourself (recommended — you already have drishti-v2), the "handoff" is just merging
`lane/frontend-v2` back to main. Either way, FRONTEND-HANDOFF-V2 is the contract both sides point at.

---

## 10 · Repo hygiene to fold in (small, high-value, do opportunistically)

These surfaced in the repo audit — none are urgent, but knock them out inside a relevant session:

- **`fixtures-ui` target points at a missing run** (`_sweep-0.10`). Fix it to the canonical
  `agency-v2` run — folded into P0-d.
- **`verify-drishti` points at the old `apps/drishti`**, not `apps/drishti-v2`. Repoint it — fold
  into Lane B.
- **`duckdb` is a pinned dependency but never imported.** Delete it from `pyproject.toml` — trivial,
  do it in P0-a while you're in the config anyway.
- **No CI.** You're solo and offline, so a full CI pipeline is overkill, but a one-line
  `make verify` run before each demo is your CI. Optionally add a `.github/workflows/verify.yml` that
  runs `make verify` on push if you ever share the repo — low priority.
- **Two frontend apps coexist** (`apps/drishti` v1, `apps/drishti-v2` v2). Once v2 is the confirmed
  keeper, delete v1 to stop future confusion — but only after Lane B merges green.

---

## 11 · When something goes wrong (don't panic, don't spiral)

- **Gate went red and Claude can't fix it in ~2 tries:** stop letting it patch incrementally. Say
  *"stop — diagnose the root cause before changing anything else, and tell me what actually broke."*
  Two failed patches means the approach is wrong, not that it needs a third tweak.
- **You want to undo the last chunk of work:** `/rewind` (or `Esc` `Esc`) restores an earlier
  checkpoint within the session. Between sessions, your commits are the checkpoints:
  `git reset --hard <last-green-commit>` (destructive — only on your own uncommitted mess) or
  `git revert` to undo a bad commit safely.
- **A session got confused / context feels poisoned:** don't fight it. `/clear`, re-orient from
  PROGRESS.md, and re-issue the phase prompt. A fresh session is cheaper than untangling a bad one.
- **A worktree got messy:** `cd` back to main, `git worktree remove --force ../chakravyuh-frontend`,
  and recreate it. The main tree is untouched.
- **Claude wants to change a test/gate to pass:** read that diff yourself before approving (§2).
- **You froze / lost the thread:** open PROGRESS.md, find the last checked box in §12, do the next
  one. That's the whole point of the checklist.

---

## 12 · The linear checklist (when you freeze, do the next box)

**Setup (once):**
- [ ] 3.1 Add the BACKEND REMODEL block to CLAUDE.md
- [ ] 3.2 Create `.claude/agents/truth-checker.md` (and later `estimator-analyst.md`)
- [ ] 3.3 Add `.mcp.json` with Playwright
- [ ] 3.4 (optional) Add the ruff PostToolUse hook in `.claude/settings.json`
- [ ] 3.5 Add a `## BACKEND REMODEL` section to PROGRESS.md
- [ ] Commit setup: `git add -A && git commit -m "workflow setup: remodel contract + agents + mcp"`

**P0 — solo, main tree (the part that fixes what you hate):**
- [ ] P0-a observer regimes + biased observers → gate `make validate-data` → commit
- [ ] P0-b multi-granular ground truth + asn_rollup → gate quarantine+contracts → commit
- [ ] P0-c timing_mle + asn_rollup + ensemble + per-granularity eval → gate sweep → commit
- [ ] P0-d serialize + regenerate agency run + fixtures → gate `make verify`+`peek` → **commit (unlocks Lane B)**

**After P0 — run these two lanes in parallel:**
- [ ] Create the frontend worktree: `git worktree add ../chakravyuh-frontend -b lane/frontend-v2` + `npm install` in it
- [ ] LANE A (main tree): P2 JAAL → P1 BUDDHI+Elliptic → P3 polish (optional), gate + commit each
- [ ] LANE B (worktree): B1 world.json → B2 origin/leads/proof operator-level → B3 map+scrub, screenshot each
- [ ] Merge Lane B: `git checkout main && git merge lane/frontend-v2` → `git worktree remove ../chakravyuh-frontend`

**Finish:**
- [ ] Full `make verify` green on main; `npm run build` green in drishti-v2
- [ ] `make peek` numbers match what the deck/frontend claim (they should — same source)
- [ ] PROGRESS.md BACKEND REMODEL section reflects reality; final commit
- [ ] Optional: delete `apps/drishti` v1; add `verify.yml` CI

> When every box is checked, the thing you hated (the 41.5% host-attribution framing) is gone,
> replaced by a strong operator-level number you can defend with a curve, a real-data replication,
> and a shortlist — and the frontend renders it exactly as promised. That's the internship pitch.