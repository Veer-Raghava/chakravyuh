# DRISHTI · BUILD PLAYBOOK

*How to actually build DRISHTI with Claude Code — the workflow, not just a pile of prompts.*
*Companion to **DRISHTI-REDESIGN-PLAN.md** (the design bible) and **CLAUDE.md** (the repo contract).*

---

## WHY THIS REPLACES "18 SEPARATE PROMPTS"

The old version of this file was 18 standalone copy-paste prompts. That is *not* how you get quality
out of Claude Code, and it wastes tokens. The current best practice (2026) is different, and this
file is built around it:

- **Context is the scarce resource, not the model.** Every prompt re-reads the whole conversation.
  Long, meandering sessions get expensive and dumb. So we work in **focused milestones**, each in a
  fresh context, and `/clear` between them.
- **The world lives in `CLAUDE.md`, auto-loaded every session** — so prompts are short and never
  re-paste the design system. (This is the single biggest change.)
- **Plan before build.** Ask for a plan, approve it, then build. Catches wrong turns before they cost
  tokens.
- **Give Claude eyes.** A design-heavy 3D site built blind is a gamble. We wire the **Playwright MCP**
  so Claude Code screenshots the running page, compares it to the intent + reference images, and
  **self-corrects** before handing back. This is the difference between "template" and "who made
  this?".
- **A running `PROGRESS.md`** carries state across sessions so a fresh context (or a new teammate)
  picks up instantly.

> Read this once, top to bottom. Then you live in Part B (the ritual) and Part C (the milestones),
> using Part D (the worked example) as your template. Part E is for handing this to a new teammate.

Sources this workflow is based on (Claude Code docs + widely-used community practice):
Anthropic "Advanced Patterns: Subagents, MCP, Scaling"; code.claude.com "large codebases";
alexop.dev "CLAUDE.md vs Skills vs Subagents (2026)"; the Playwright-MCP visual-loop guides
(jimmc414 visual-dev gist, design-loop, visual-eyes). Full links at the bottom.

---

## PART A · ONE-TIME SETUP (do this once, ~30–45 min, before any building)

### A1 · Put the contract where Claude Code reads it
If you have a monorepo (`apps/` for the frontend, other folders for the backend), everything below
lives with the **frontend app** — open Claude Code *in the frontend folder* and put `CLAUDE.md` at
that folder's root. (Claude Code auto-loads the `CLAUDE.md` nearest where you launch it, so a
frontend-scoped contract won't confuse it with backend code.)
1. Copy **`CLAUDE.md`** (already written, in this folder) to the **root of your frontend app**.
   Claude Code auto-loads it every session — this is what makes it "understand exactly."
2. Copy **`DRISHTI-REDESIGN-PLAN.md`** and the backend's **`DATA-CONTRACTS.md`** into the app (e.g.
   `/docs`), so prompts can say "build §10 per the plan, shapes per DATA-CONTRACTS" and Claude can
   open them. Keep DATA-CONTRACTS read-only (it's frozen — the same deny you set in the backend's
   `.claude/settings.json`).
3. Create an empty **`PROGRESS.md`** at the app root (template in A5). This is the cross-session
   memory: what's done, what's next, known issues.

### A2 · Give Claude Code eyes (the visual loop — the important one)
This is what turns blind coding into design. Add the **Playwright MCP** so Claude can open the
running app in a real browser, screenshot it, read the console, and self-correct.

```
# from the repo root, once:
claude mcp add playwright -- npx @playwright/mcp@latest
# then, inside Claude Code, confirm it's connected:
/mcp
```
Then add a short **`.claude/commands/design-review.md`** slash command so you can trigger the loop in
one word (contents in A4). If you prefer zero setup, you can also just tell Claude in-session:
"use the Playwright MCP to open http://127.0.0.1:5173, screenshot it, and compare to the intent."

### A3 · Gather the offline assets + fixtures (block the build if missing)
Per plan §14 — nothing here may come from a CDN at runtime. Plain terms: these are files you drop into
folders *once*, so the app has everything it needs with the wifi off. What each one is and where to get it:

```
   /public/fonts   The 3 typefaces as .woff2 files (Fraunces, Hanken Grotesk, IBM Plex Mono — all
                   free/OFL). Download from Google Fonts / Fontsource ONCE, commit the .woff2 files,
                   and load them with local @font-face. (We download them so the app never calls
                   Google at runtime — that's the offline rule, not an anti-Google thing.)
   /public/assets  A few 3D bits: 1–2 "matcap" images (a matcap is just a small sphere photo that
                   fakes lighting — grab warm clay/ceramic ones from a free matcap gallery); one
                   lightformer/HDRI for soft light; the diya (a small low-poly flame model, either
                   made in Blender or a free CC0 model, exported as Draco-compressed .glb); and a
                   coastline GeoJSON for the globe (free from Natural Earth). If you don't have the
                   diya yet, a stylised cone/teardrop mesh is a fine stand-in — don't let it block you.
   /public/refs    Screenshots you give Claude as visual targets: the 4 study sites from plan §14.4,
                   AND your OLD packet screenshot saved as "packet-BEFORE.png — we are replacing this".
                   Claude's /design-review compares its output to these.
   /src/data       The JSON the frontend renders. THESE ARE NOT INVENTED — they mirror the backend's
                   committed data/fixtures (seed 42, ~25 txs) from DATA-CONTRACTS.md. Export the
                   backend artifacts (graph nodes/edges, origin_estimates, alerts + counter, one
                   packet.json, the observer-fraction curve, the funnel counts) to a handful of JSON
                   files here, plus a typed loader. Identifiers are already truncated by the backend
                   (§9). Make sure the awkward cases (single-peer tx, >15 announcements, Tor peer,
                   shared IP on two ports, equal-value outputs, peel chain, null ASN, rejected row,
                   IPv6) survive into the fixtures — they're how the UI gets proven, not just the
                   pretty rows.
```

### A4 · The `design-review` command (paste into `.claude/commands/design-review.md`)
```
Open the current screen in the browser via the Playwright MCP (http://127.0.0.1:5173, the route we
just built). Take a screenshot at 1440×900 AND 390×844. Then critique your own output against:
- the intent for this screen in DRISHTI-REDESIGN-PLAN.md,
- the reference images in /public/refs,
- CLAUDE.md's "definition of done" and anti-slop north star.
List concrete gaps (spacing, hierarchy, color mix, whether the 3D carries data, any kill-list word
visible, any full identifier visible, framerate/console errors). Fix the top issues, re-screenshot,
and repeat until it passes. Show me the before/after screenshots and the diff.
```

### A5 · `PROGRESS.md` template
```
# DRISHTI — build progress
Current milestone: M0
Done: —
Next: M0 foundation
Known issues: —
Fixture paths: /src/data/*.json (loader: /src/data/load.ts)
Demo machine: <fill in — the laptop you'll present on>
Last commit that ran green + offline: —
```

---

## PART B · THE RITUAL (repeat this for every milestone — memorise it)

Each milestone is one focused session in a fresh context. The loop is always the same seven steps:

```
   1. START CLEAN     open Claude Code in the frontend app (CLAUDE.md auto-loads). Find the current
                      milestone in PROGRESS.md, go to its entry in Part C.
   2. PASTE + PLAN    copy that milestone's ``` prompt block, paste it, hit enter. It replies with a
                      short PLAN (no code — the prompt tells it to). Read the plan. Nudge if wrong.
                      THEN reply "go". (The prompt already carries "read PROGRESS.md + the plan
                      section" and "plan first", so you don't hand-type any of that.)
   3. BUILD           it builds against fixtures. You don't watch every line.
   4. SEE IT          run /design-review (Part A4). Claude screenshots the running app, critiques vs
                      the plan + refs, and self-corrects. You look at the before/after it shows you.
   5. TWO-QUESTION    (a) crafted around the vision-in-a-maze metaphor, or a tasteful default (§1)?
      REVIEW          (b) any §3 kill-list word or full identifier visible? Send back on either.
   6. CHECKPOINT      update PROGRESS.md (done / next / issues). Commit: "M<n>: <what shipped>".
   7. CLEAR           /clear  before the next milestone. Fresh context = cheaper + sharper.
```

Two rules that save the most tokens and pain:
- **Never carry a broken state across `/clear`.** Commit green, or write the blocker into PROGRESS.md
  so the next session starts informed.
- **If Claude drifts off-style twice, don't keep nudging — stop and re-anchor:** "Re-read CLAUDE.md's
  anti-slop north star and the §<n> intent, then tell me your plan again." Re-grounding beats ten
  small corrections.

### When to reach for a subagent
For **research or noisy exploration** (e.g. "figure out the best way to wire react-force-graph into
R3F with our two-floor layout"), ask Claude to use a **subagent** so the investigation doesn't fill
your main context: "Spin up a subagent to research X and report back just the recommendation." Keep
the main session for building.

---

## PART C · THE MILESTONES (8 focused sessions, not 18 prompts)

Each milestone = one session in a fresh context. **Each one below is a single ready-to-paste prompt.**
When you start a milestone: `/clear`, open Claude Code in the app, **copy the whole ``` block, paste
it, hit enter**. It will reply with a short plan (no code yet). Read the plan; if it's right, reply
**`go`** and it builds, then self-reviews. That's the whole move — you never assemble tags in a hurry.
(The prompts already say "plan first" and "then /design-review", so pasting + `go` runs the Part B
ritual for you.) The **Done when** line is your eyeball check. Old S-numbers are noted so nothing from
the plan is lost. Bigger milestones (M2, M5, M6) come as two paste-blocks (a/b) — commit and `/clear`
between them; that's fine.

### M0 · Foundation & design system  (old S0+S1+S3)
**Goal:** the machine runs, the design tokens exist, the fixtures + loader exist. No story yet.
**Stop value:** the foundation everything else stands on.

▶ Paste this, read the plan it returns, then reply `go`:
```
Milestone M0 — foundation, design system, fixtures. CLAUDE.md is loaded; follow it. First read
DRISHTI-REDESIGN-PLAN.md §5 (stack + wiring), §4 (tokens), §5.4/§14.3 (fixtures), and DATA-CONTRACTS.md
(the frozen backend shapes our JSON mirrors).

Build:
1. Scaffold Vite + React 18 + TypeScript with R3F v9, drei v10, postprocessing v3, GSAP + @gsap/react,
   Lenis. CSS Modules only — no Tailwind, no component library. Use the /src layout from §5. Fully
   offline: no CDN / Google Fonts, dev server binds 127.0.0.1 only.
2. Wire Lenis↔GSAP ScrollTrigger EXACTLY per §5.2 in one useSmoothScroll() hook, and add the perf-
   guardrail Canvas wrapper per §5.3 (useDetectGPU, PerformanceMonitor, AdaptiveDpr, dpr [1,2]).
3. Implement §4 tokens: colours as CSS vars + a typed TS export; vendored woff2 @font-face for
   Fraunces / Hanken Grotesk / IBM Plex Mono; the wide type scale; the matcap-clay + one glass-lens
   material presets; the GSAP eases.
4. Add a /tokens kitchen-sink route: every colour swatch, every type size, a clay sphere and a glass
   lens under soft shadow.
5. Build a typed fixture loader over /src/data and load our fixtures. They mirror the backend
   data/fixtures (seed 42): money is satoshis int64 (format to BTC only at display), times are UTC
   microseconds (_us, convert only at render), identifiers already truncated (DATA-CONTRACTS §9), and
   the awkward cases from DATA-CONTRACTS §11 are present.

Give me a short plan first — files, your Lenis/GSAP wiring approach, the material presets, and how the
loader is typed. Don't write code yet. When I reply `go`: build it, then run /design-review on /tokens
and show me before/after.
```
**Done when:** blank Paper page scrolls smoothly, console-clean, loads with wifi off; `/tokens` shows
the whole system; fixtures typecheck. Screenshot `/tokens`.

### M1 · The stage & the hero  (old S2+S4)  ← Part D walks through this exact one, step by step
**Goal:** the fixed-viewport scroll stage + the hero lens + the diya guide.
**Stop value:** the front door — already a striking standalone hero.

▶ Paste this, read the plan it returns, then reply `go`:
```
Milestone M1 — the scroll stage, the hero lens, the diya. CLAUDE.md is loaded; follow it. Read
PROGRESS.md and DRISHTI-REDESIGN-PLAN.md §5.2, §7.HERO, and §2 (the diya).

Build:
1. The fixed-viewport stage per §5.2: ONE fixed full-screen <Canvas>, a tall scroll spacer, and a
   shared scrollProgress ref (0→1) via context driving useFrame. Reuse the useSmoothScroll() hook from
   M0 — do NOT re-wire Lenis. Do NOT use drei <ScrollControls>.
2. The hero per §7.HERO: a MeshTransmissionMaterial lens over a slow coral maze-swirl that resolves
   into order THROUGH the lens; the Fraunces headline "See through the noise.", the sub, and the mono
   tag. On first scroll the lens tips and the camera begins to descend.
3. The diya per §2: an abstract matte-clay flame (no face), drifts in, says ONE calm line on first
   arrival then stays silent until scrolled, dismissible, with its off-state in in-memory React state
   (never localStorage).
4. Reduced-motion (prefers-reduced-motion via gsap.matchMedia): a static hero, no swirl animation.

Give me a short plan first — files, your approach to the lens material and the scrollProgress ref, and
where you touch fixtures. Don't write code yet. When I reply `go`: build it, then run /design-review at
1440×900 and 390×844 and show me before/after.
```
**Done when:** 60fps scroll; the lens genuinely refracts the swirl into order; the diya drifts, speaks
once, dismisses and stays dismissed; reduced-motion shows a static hero. Screenshot both sizes.

### M2 · The landing story  (old S5–S9; two paste-blocks 2a/2b)
**Goal:** the 8 scroll stations + the funnel counter (1,000,000→1) + the outro to login.
**Stop value:** ★ a complete, stunning standalone pitch page (a valid stopping point on its own).

▶ M2a — paste this, read the plan, reply `go`:
```
Milestone M2a — landing stations 0–3, in the fixed stage, each choreographed to its scrollProgress
slice per §7. CLAUDE.md loaded. Read PROGRESS.md and DRISHTI-REDESIGN-PLAN.md §7.
- st.0 MAYAJAAL: ★ the instanced signal field + the custom GLSL "illusion-net" shader (timebox per
  §15 — if it stalls, ship a strong instanced + bloom version and move on). Mount the funnel counter
  here reading 1,000,000.
- st.1 KAVACH: the sealing/intake beat.
- st.2 SETU: the split, with the src_ip → "the IP that told us" rename shown.
- st.3 ★ JAAL: the assembling two-floor fused graph, the fluoro-pink announce edges lighting LAST.
Wire the funnel counter to decrement across stations using the canonical numbers.
Plan first, don't code yet. On `go`: build, then /design-review each station.
```

▶ M2b — paste this, read the plan, reply `go`:
```
Milestone M2b — landing stations 4–7 + the outro, per §7. CLAUDE.md loaded. Read PROGRESS.md and §7.
- st.4 ★ SHASTRA: the 41.5% ceiling bar + a candidate ring + grey abstain cards (the honesty flex).
- st.5 BUDDHI: clay balance; why-flagged shown WITH its teal counter-evidence; NO global accuracy number.
- st.6 VAANI: the score unfolds into the reusable alert card.
- st.7 PRAMAAN: the packet presses, hash-chain spine, BNSS §94 stamp; the funnel counter lands on 1.
- OUTRO: camera zooms back to the calm lens, the login card rises, colour shifts Coral → Riso-Blue.
Reduced-motion = cross-fades, no scroll-scrub. Plan first, don't code yet. On `go`: build, then
/design-review; confirm reduced-motion.
```
**Done when:** one continuous scroll from awe → trust; the funnel counter is fully wired to the
canonical numbers; stations 3 & 4 are perfect; kill-list clean. Screenshot every station.

### M3 · Login + shell + navigation  (old S10, with the NEW nav)
**Goal:** the login threshold, then the app shell with **the Thread + the Aperture** (NO left rail),
the shared Properties drawer, and the reusable Alert card.
**Stop value:** the product's frame — establishes the whole tool.

▶ Paste this, read the plan, reply `go`:
```
Milestone M3 — login, then the app shell + navigation. CLAUDE.md loaded (note the NO-left-sidebar hard
rule). Read PROGRESS.md and DRISHTI-REDESIGN-PLAN.md §8 (login) and §11.0 (nav).
1. Login per §8: one calm Riso-Blue card, the dimmed hero lens behind, an offline + 127.0.0.1 badge,
   success MOCKED with a fixture user (no network call ever). On success → the shell.
2. The shell + navigation per §11.0 EXACTLY — NO left sidebar:
   - The Thread ("Sutra"): a slim TOP sightline, workflow-ordered
     Globe → Intake → Untangle → Map → Origin → Leads → Proof → World; current stage enlarged + lit,
     done stages sealed; it carries the funnel bead (the 1,000,000→1 counter for the run).
   - The Aperture: press `space` (or click the lens/diya) → a radial iris quick-switcher blooms from
     centre (the chakravyuha rings) with search.
3. The reusable right-hand Properties drawer (slides, never a modal) and the reusable Alert card
   (reuse the VAANI card). Wire nav between empty screen stubs for now.
Plan first, don't code yet. On `go`: build, then /design-review; also grep the source for "sidebar"
and "left rail" and confirm zero hits.
```
**Done when:** login → shell works; the Thread reads as the workflow and carries the counter; the
Aperture blooms/closes; drawer + card are reusable; grep confirms zero "sidebar"/"left rail".
Screenshot the shell + the open Aperture.

### M4 · The globe  (old S11)
**Goal:** the app home — a matte editorial Paper globe of transactions, click → drawer → graph.
**Stop value:** ★ landing + login + globe = the whole product established.

▶ Paste this, read the plan, reply `go`:
```
Milestone M4 — the globe (the app home). CLAUDE.md loaded. Read PROGRESS.md and DRISHTI-REDESIGN-PLAN.md
§9. Use react-globe.gl.
- A Paper-coloured MATTE globe with ink-hairline coastlines (NOT photoreal), frameloop on-demand when
  idle.
- Plot located announcements from the globe fixture (risk-tinted; grey for unlocated / Tor); fluoro-
  pink arcs for a selected tx; India gently emphasised.
- Click a point/arc → the shared Properties drawer (not a modal): sender (origin likelihood + shortlist,
  or a dignified "No answer available"), receivers, truncated txid, fee/amount/timestamp in mono
  (sats→BTC and _us→IST only at display), announcing IP redacted to the backend format (103.x.x.x) +
  port + operator (ASN).
- "Open in map" → graph (stub the handoff); "Build proof" → packet (stub).
- Every identifier rendered per DATA-CONTRACTS §9. Reduced-motion = no auto-rotate.
Plan first, don't code yet. On `go`: build, then /design-review.
```
**Done when:** interactive globe, click → drawer flow works, truncation holds (103.x.x.x, bc1q4f…9f4d),
globe → graph handoff stubbed. Screenshot the globe + an open drawer.

### M5 · The graph — the centrepiece  (old S12+S13; two paste-blocks 5a/5b)
**Goal:** the two-floor fusion graph, static → temporal → filters/focus/path-trace. The screen a judge
stares at longest — give it the most care.
**Stop value:** ★★ **the minimum target.** Landing + login + globe + this graph = a complete, genuinely
impressive demo. If time is short, stop here and polish (M7).

▶ M5a — paste this, read the plan, reply `go`:
```
Milestone M5a — the two-floor fusion graph, static. CLAUDE.md loaded. Read PROGRESS.md and
DRISHTI-REDESIGN-PLAN.md §10.0–§10.4. Use react-force-graph inside R3F.
- THE TWO-FLOOR LAYOUT: network peers ▲ on an upper floor, money (addresses ● / tx ◆) on a lower
  floor, and the fluoro-pink ANNOUNCE threads are the ONLY edges crossing between floors. Left→right =
  flow/time. Three camera presets: side-on / top-down / isometric.
- Three node shapes, three edge types, risk colour, cluster hulls, a tiny always-on legend, Paper bg.
- The Properties drawer per §10.3, including the "this IP told us — usually a relay" warning on peers.
- The confidence-threshold slider per §10.4 that merges/splits the cluster hulls live (default 0.36 —
  a good published number, shown as a dial, never a hard merge).
Plan first, don't code yet. On `go`: build, then /design-review and verify it reads as a DIAGRAM, not a
hairball, in the side-on view.
```

▶ M5b — paste this, read the plan, reply `go`:
```
Milestone M5b — make the graph temporal + interactive, per §10.2 + §10.5. CLAUDE.md loaded. Read
PROGRESS.md and §10.2/§10.5.
- TIME SCRUBBER (mono IST clock, play/pause/speed): nodes/edges appear on first_seen, and the pink
  announce threads rain DOWN top-down so you watch gossip spread out of order — the first-seen trap,
  made visible.
- Filter chips; search-to-focus.
- Double-click FOCUS MODE: the subject rises to centre, its neighbourhood orbits in rings, the rest
  dims.
- ★ PATH-TRACE: click node A then node B → draw the path AND narrate it in one plain sentence.
- Hold 60fps (frameloop demand when idle). Reduced-motion = discrete jumps, no continuous scrub.
Plan first, don't code yet. On `go`: build, then /design-review.
```
**Done when:** side-on view shows the two floors + pink fusion threads clearly; the scrubber replays
gossip; path-trace narrates; focus mode works; 60fps. Screenshot side-on, top-down, focus mode, mid-replay.

### M6 · The screens + the flexes  (old S14+S15; two paste-blocks 6a/6b)
**Goal:** the five remaining screens (reusing drawer + card) + the World/MAYAJAAL flex screen.
**Stop value:** ★ the full tool — everything works.

▶ M6a — paste this, read the plan, reply `go`:
```
Milestone M6a — Intake, Untangle, Leads. CLAUDE.md loaded. Read PROGRESS.md and DRISHTI-REDESIGN-PLAN.md
§11.1, §11.2, §11.4. Reuse the shared Properties drawer + Alert card.
- Intake / KAVACH (§11.1): a drop zone → a live sealing readout (in / sealed / set-aside with reasons),
  the full-file SHA-256 shown IN FULL, a balance tick, one "Seal & continue".
- Untangle / SETU (§11.2): a before/after with the src_ip → "the IP that told us" rename as the
  headline, the echo ratio (~93%, ≈14 announcements/tx), and a null-vs-unknown tooltip (null ≠ 0 ≠
  unknown).
- Leads / VAANI (§11.4): a ranked alert-card queue (risk, pattern, network detail, 3 SHAP factors, the
  teal counter-evidence, the origin line). Default sort "act on this first". On each card surface the
  backend's `would_clear` counter-finding prominently ("this one doubt would close the lead"). Cards →
  Open in map / Build proof. NO global model report card anywhere (§6).
Plan first, don't code yet. On `go`: build, then /design-review.
```

▶ M6b — paste this, read the plan, reply `go`:
```
Milestone M6b — the two star screens + the flex screen. CLAUDE.md loaded. Read PROGRESS.md and
DRISHTI-REDESIGN-PLAN.md §11.3, §11.5, §11.6, §12.2.
- Origin / SHASTRA (§11.3), FULL 3D candidate-rings: the tx at the centre of the maze; candidate IPs on
  concentric rings where radius = INVERSE likelihood (most likely nearest the centre); the shortlist
  glowing in a confidence shell; a calm grey fog-dome for abstain ("No answer available"); the 3D
  announcement fan showing the first-seen trap; the 41.5% visibility gauge; confidence as a dial.
- Proof / PRAMAAN (§11.5), the court-ready SEALED DOSSIER on Paper (improve on
  /public/refs/packet-BEFORE.png): a hash-chain spine (SHA-256 IN FULL); the {IP · port · UTC} tuple as
  the boxed hero — but only when `attribution_ready` is true; if false, show the honest not-ready state
  instead. IP redacted to the backend format (103.x.x.x), address bc1q4f…9f4d. Counter-findings inside
  the exhibit (mark any `would_clear` one). Pre-filled BNSS 2023 §94 + BSA §63(4). The wax-seal press.
  Offline provenance footer. One "Generate packet (PDF/JSON)". It must render identically to the
  backend's packet.pdf.
- World / MAYAJAAL (§11.6 + §12.2): the synthetic world + ★ the interactive observer-fraction curve
  (drag 0.02→0.50, accuracy sweeps the 11–60% band) + the four defences + the offline/about panel.
Plan first, don't code yet. On `go`: build, then /design-review each screen.
```
**Done when:** all screens wired to fixtures; Origin is real 3D; the packet looks like a legal exhibit,
not a console — tuple as hero, `would_clear` visible, no full IP; the observer curve sweeps. Screenshot each.

### M7 · Polish & the offline gate  (old S16+S17+S18)
**Goal:** robustness, honesty pass, and the hard offline/perf gates.
**Stop value:** shipped — offline, robust, 60fps, screenshotted.

▶ Paste this, read the plan, reply `go`:
```
Milestone M7 — polish, honesty pass, and the hard gates. CLAUDE.md loaded. Read PROGRESS.md and
DRISHTI-REDESIGN-PLAN.md §3, §5.5, §6, §16.1.
1. Reduced-motion + fallbacks per §5.5: the gsap.matchMedia branch, a <Canvas fallback> 2D path, all
   data reachable in the DOM, keyboard focus order + WCAG-AA (check Coral on Paper).
2. Run the §3 kill-list + §6 REMOVE pass across EVERY screen; give me a diff of the text/label changes.
3. Run the §16.1 cross-document consistency checklist.
4. Turn wifi OFF and run end-to-end; fix any external request (hard gate — no CDN, no phone-home).
5. Perf: hold 60fps on the demo machine; confirm Draco / instancing / frameloop-demand / AdaptiveDpr;
   run the GPU-tier test.
6. Confirm every rendered identifier matches DATA-CONTRACTS §9 (103.x.x.x, bc1q4f…9f4d; SHA-256 full).
7. Screenshot/record every screen as the demo parachute.
Plan first, don't code yet. On `go`: do the passes and report a signed-off checklist.
```
**Done when:** reduced-motion + no-WebGL paths work; the wifi-off run passes; 60fps on the demo
machine; the full screenshot set is captured.

---

## PART D · ONE FULLY WORKED EXAMPLE (M1, start to commit)

This is what a single milestone actually looks like in practice — every step, so a first-timer can
copy the rhythm. We use **M1 (the stage + hero + diya)** because it's early and exercises the whole
loop. Every other milestone is the same seven steps from Part B.

**Assumes:** Part A is done (CLAUDE.md + plan in the repo, Playwright MCP added, fonts/refs present),
and M0 shipped (tokens + fixtures exist, `/tokens` renders).

---

**Step 1 — Start clean.** Open Claude Code in the frontend app. `CLAUDE.md` loads automatically. You
**paste M1's prompt block from Part C** (you don't type it — it's copy-paste). It boils down to:

> Milestone M1 — the scroll stage, the hero lens, the diya. Read PROGRESS.md and
> DRISHTI-REDESIGN-PLAN.md §5.2, §7.HERO, §2. [build spec…] Give me a short plan first — files,
> approach to the lens material and the scrollProgress ref, where you touch fixtures. **Don't write
> code yet.**

**Step 2 — Read the plan it gives back.** Claude replies with something like: create
`useSmoothScroll.ts`, `Stage.tsx` (fixed Canvas + spacer + `scrollProgress` context), `HeroLens.tsx`
(MeshTransmissionMaterial + a shader-swirl backdrop), `Diya.tsx` (matcap flame + drift/dismiss
state), `Hero.tsx` (headline/sub/mono). You notice it planned a fresh Lenis setup — you nudge:

> Good, but reuse the `useSmoothScroll()` hook from M0, don't re-wire Lenis. Also the diya's
> off-state must be in-memory React state, never localStorage (CLAUDE.md). Then go.

**Step 3 — Build.** It writes the files. You skim, you don't micromanage. It says the dev server is
on `http://127.0.0.1:5173`.

**Step 4 — See it (the visual loop).** You type one word:

> /design-review

Claude uses the Playwright MCP to open the page, screenshots at 1440×900 and 390×844, and critiques
its *own* work against §7.HERO + `/public/refs` + the definition of done. It reports, e.g.:

```
   Gaps I found:
   1. The lens refracts but the maze swirl behind is too faint — the "resolves to order through the
      lens" reading isn't legible. → raising swirl contrast + tightening transmission thickness.
   2. Headline is 96px; §4.2 wants the hero at the top of the scale. → 128px Fraunces, more optsz.
   3. Console: one shader warning on resize. → fixed the uniform update.
   4. Diya drifts but doesn't glow on settle. → added the one Butter glow pulse.
   [re-screenshots] Fixed 1–4. Before/after below.
```

You look at the before/after it pasted. The lens now clearly turns chaos→order. Good.

**Step 5 — Two-question review (you, by eye).**
- *Crafted around the metaphor, or a default?* The eye-resolving-the-maze reads instantly — crafted. ✓
- *Any kill-list word / full identifier visible?* Hero has no data yet — clean. ✓
One thing bugs you: the diya feels chatty. You type: *"Diya should say its one line only on first
arrival, then go silent until scrolled. Calm, not eager."* It fixes it.

**Step 6 — Checkpoint.** You type:

> Update PROGRESS.md (M1 done, next M2a, note the shader-resize fix). Then commit: "M1: fixed stage +
> hero lens + diya".

**Step 7 — Clear.** `/clear`. M1 is banked, green, screenshotted. Next session starts fresh on M2a
with a clean context and PROGRESS.md carrying the state.

---

**What this example teaches you to repeat every time:** short prompt (the world's already loaded) →
*plan first* → build → **`/design-review` so it sees and fixes its own work** → your 30-second
two-question check → commit + PROGRESS.md → `/clear`. That loop is the entire method. Nothing else
scales across a build this size without burning tokens or drifting into slop.

---

## PART E · HANDOFF RUNBOOK (for a brand-new teammate — day one)

If someone new is handed this repo, here is their whole onboarding:

```
   1. READ, in this order (about an hour):
      • CLAUDE.md                     — the contract. The world, rules, tokens, definition of done.
      • DRISHTI-REDESIGN-PLAN.md §1–§3 — the soul: why-slop, the CHAKRAVYUH/DRISHTI idea, the words.
      • DRISHTI-REDESIGN-PLAN.md §16   — the NTRO coverage matrix (what must be true).
      • DATA-CONTRACTS.md (backend)    — the frozen JSON shapes our fixtures mirror (skim; it's the
                                         source of truth for every field, unit, and truncation).
      • this file, Part B + Part D     — the ritual and the worked example.
      • PROGRESS.md                    — where the build actually is right now.
   2. SET UP (Part A): clone, `npm i`, confirm `npm run dev` serves on 127.0.0.1, confirm `/mcp`
      shows Playwright connected, confirm wifi-off still loads.
   3. FIND the next milestone in PROGRESS.md → open its entry in Part C → run the Part B ritual.
   4. NEVER: build a left sidebar; add a CDN/Google-Fonts link; print a full IP/address/txid; ship a
      global accuracy report card; leave placeholder text. (All are hard-fails — see CLAUDE.md.)
   5. WHEN STUCK on look/feel: run /design-review and read what it finds before asking a human.
```

The point of the three-file set (CLAUDE.md + plan + this playbook) is exactly this: the new person
does not need *you*. They need to read four things and run one loop.

---

## PART F · TOKEN & TIME EFFICIENCY (you said this matters)

```
   • CLAUDE.md is loaded EVERY session — keep it lean (it already is). Bloat here taxes every prompt.
   • One milestone per context, then /clear. Long sessions cost quadratically and get dumber.
   • Plan-first prevents the most expensive waste: building the wrong thing, then unbuilding it.
   • Point at plan sections ("build §10.0"); don't paste the plan into the chat.
   • Use subagents for research so exploration doesn't bloat the building context.
   • Commit at every green gate — a bad turn costs one milestone, never the whole build.
   • The /design-review loop spends a few screenshots to save many blind rebuilds. Net cheaper.
   • Timebox the one hard thing (the station-0 shader, §15 risk 4). Ship the strong fallback and move.
```

---

## THE STOP-ANYWHERE MAP

Every milestone is a complete, demo-able stopping point:

```
   after M2  → the full landing story alone. A stunning standalone pitch page.
   after M4  → landing + login + globe. The whole product established.
   after M5  → + the two-floor fusion graph. A complete, impressive demo.  ← MINIMUM TARGET
   after M6  → the full tool. Everything working, including 3D origin + the court dossier.
   after M7  → shipped: offline, robust, 60fps, screenshotted.
```

Prioritise **M0–M2 (the story)** and **M5 (the graph)**. Everything else is upside.

---

## SOURCES (the workflow research behind this file)

- Anthropic — *Claude Code Advanced Patterns: Subagents, MCP, and Scaling to Real Codebases*:
  https://resources.anthropic.com/hubfs/Claude%20Code%20Advanced%20Patterns_%20Subagents,%20MCP,%20and%20Scaling%20to%20Real%20Codebases.pdf
- Claude Code docs — *Set up Claude Code in a monorepo or large codebase*:
  https://code.claude.com/docs/en/large-codebases
- alexop.dev — *Claude Code Customization Guide (2026): CLAUDE.md vs Skills vs Subagents*:
  https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/
- dianyike/claude-code-insights — *CLAUDE.md best practices* & *subagent best practices*:
  https://github.com/dianyike/claude-code-insights
- jimmc414 — *Claude Code Visual Development Guide (Chromium + Playwright MCP)*:
  https://gist.github.com/jimmc414/2416424a8e0fd6c0b5de948f28a00b13
- tonymfer/design-loop (autonomous visual iteration) & nikolasdehor/visual-eyes (screenshot review):
  https://github.com/tonymfer/design-loop · https://github.com/nikolasdehor/visual-eyes
- sitepoint — *Claude Code Context Management Guide*:
  https://www.sitepoint.com/claude-code-context-management/

---

*DRISHTI · build playbook · companion to DRISHTI-REDESIGN-PLAN.md + CLAUDE.md · SIH26146 · for NTRO*