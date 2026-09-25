# SESSIONS · TRACK B · DRISHTI, the console

This is the Track B companion to your existing SESSIONS.md. Same rules, same voice, same
ritual. One block per session, in order. Purpose, the prompt to paste, what a healthy session
looks like, and the one gate that decides done.

Track B was already specified in SESSIONS.md as B0–B6. This file keeps all of that and adds
two things you asked for: a short setup so Claude Code can *see* what it builds, and one new
screen — LINEAGE — that shows the data transforming through every layer with your own eyes.
That screen is the one that sells the architecture in the video.

Read this once before B0. Then never open more than one session's block at a time.

---

# WHY THIS FILE EXISTS, IN ONE PARAGRAPH

Your backend is measured by a gate. Your frontend can't be — "does this look like a tool or a
prompt" is a human judgement. So Track B replaces the byte-comparison gate with three cheap,
repeatable checks that catch drift before you do: `make verify-drishti` (types, tests, build),
the `ui-critic` subagent on the files that changed, and your own eyes at three screen sizes.
Every session ends with all three. That is the whole discipline.

---

# CONFIDENCE PHILOSOPHY · per-record yes, aggregate no

This is a hard rule for every screen, and the ui-critic checks it. There are two different
things, and only one goes on screen.

**Per-record calibration stays, always.** The conformal interval on *this* score, the ABSTAIN
tag on *this* transaction, the counter-evidence on *this* lead, the balancing arithmetic on
*this* transition. These are not weaknesses — to a forensic evaluator they are what a real
instrument looks like. A tool that only ever shows a clean confident number, and never says "I
don't know," reads as a toy. Never remove these to look stronger; removing them looks weaker.

**Aggregate self-critique never goes on any screen.** No headline or chart whose subject is how
good or bad the system is overall — no origin-accuracy range, no ceiling figure, no global
abstain-rate dashboard, no "peers often unavailable" panel. That framing is spoken-narration
material (and, delivered as discipline, it is a strength), but it is never a UI element. If a
session proposes a metrics or eval screen, the answer is no.

The test: a number on screen describes the *one record in front of you*, or it does not appear.

---

# SETUP · three decisions, made once, before B0

These are the only tooling choices for the whole track. Make them once and never revisit.

**Decision 1 — Skills: use one, refuse three.** Your `tokens.css` + `ui-critic` already encode
taste better than a generic skill. The popular design skills (taste-skill, ui-ux-pro-max) are
tuned for *marketing landing pages* — bento grids, GSAP scroll pinning, wide editorial type,
gradient heroes. That is the exact look you must NOT have. Installing them would fight your own
spec. The one skill worth keeping open is Anthropic's own `frontend-design` skill, and only for
its one idea: *commit to a deliberate direction instead of defaults.* You already committed to
"forensic instrument." So even that is a reminder, not a generator. Verdict: keep `ui-critic` as
your critic, keep `frontend-design` open as a sanity primer, ignore the rest.

**Decision 2 — MCP: install exactly one, a browser bridge.** This is the single highest-leverage
thing you can add. Claude Code writes UI it cannot see; a browser MCP lets it open the running
console, screenshot it, read the DOM, and iterate against what actually rendered instead of
against its imagination. Use **Playwright MCP** (or **chrome-devtools MCP** — either is fine;
Playwright is the more common default). Nothing else. No shadcn MCP, no Figma MCP — you have no
component library and no Figma file, so they'd add nothing. One MCP, and it must respect the
air-gap: it drives a localhost:5173 dev server, never the network.

**Decision 3 — Inspiration: gather references BEFORE B1, as images on disk.** Claude designs far
better when it can see a target than when it reads adjectives. Put 6–10 screenshots in
`apps/drishti/refs/` (git-ignored). Pull them from the sites in the appendix. You are NOT
looking for dashboards to copy — you are stealing *specific moves*: one hairline table, one
mono-numeric readout, one restrained reveal. When a session's prompt says "match the density of
refs/xxx.png", that reference does the work ten paragraphs of instruction can't.

Do all three in fifteen minutes, then start B0 and don't touch tooling again.

---

# THE RITUAL, every Track B session

Identical to Track A, with the gate swapped. If you remember nothing else: step 3 stops the
circling, step 5 defines done, step 6 is what keeps it from looking generated.

**1.** `/clear`. Fresh context every session, no exceptions.

**2.** Confirm clean `main`: `git status --short`. Track B touches `apps/drishti/**` and nothing
else, ever. Never open `src/`.

**3.** Paste that session's **Prompt 1**. It always ends with "plan first, do not write code yet."
Read the plan, say `go`, or correct one thing then `go`.

**4.** Let it build. When it stalls or wanders, use the follow-up prompt in the block.

**5.** `make verify-drishti`. Not finished until green.

**6.** Run the `ui-critic` subagent on the files that changed. Then open the console in the
browser MCP and screenshot it at 1366×768, 1440×900 and 1920×1080. The critic is not optional.

**7.** `/handoff drishti` — writes `STATE-DRISHTI.md`, leaves `STATE.md` alone. Then commit,
push and tag by hand. Claude never runs git.

```
git add apps/drishti && git status --short
git commit -m "B0 shell: <what now works>"
git push origin main
git tag b0-done && git push origin b0-done
```

**8.** `/clear` before the next session.

---

# B0 · The shell

**Purpose.** The frame, the status bar with real values, the rail, the command line. The
adapter seam and your own fixtures. Nothing visual beyond the four regions.

**Prompt 1.**

```
Read @docs/DRISHTI-SPEC.md in full and @docs/DATA-CONTRACTS.md sections 3 and 4. Read nothing
else. Do not read or edit anything under src/, and do not edit STATE.md.

Build the shell of apps/drishti. Vite, React, TypeScript, CSS Modules. No component library,
no Tailwind, no shadcn, no UI framework of any kind.

1. src/styles/tokens.css exactly as specified. Every colour and size literal lives here only.
2. Vendored IBM Plex Sans and IBM Plex Mono woff2 in public/fonts, local @font-face. No Google
   Fonts link anywhere — the venue may have no network.
3. The four-region frame: StatusBar 32px, Rail 180px, stage area, Inspector 380px,
   CommandLine 28px. Fixed to viewport, hairline separated, no page scroll, only panels scroll.
4. src/adapter/ with types.ts, fixtures.ts, api.ts, index.ts. index.ts picks source from
   VITE_SOURCE, defaults to fixtures. All adapter functions from the spec fully typed, each
   with a fixtures implementation. api.ts is a typed stub that throws "API not built yet".
5. fixtures.ts authored by you from DATA-CONTRACTS 3–9, realistic values, every identifier
   already truncated. Each function's payload is a separate exported constant, so after S04
   those constants get swapped for JSON from data/fixtures/ui/ and nothing else changes.
6. StatusBar from getManifest: run id, input sha256 truncated, rows, tx count, the stage
   lamps, merkle head, AIR-GAPPED badge.
7. Rail with the routes and keyboard hints, per-screen shortcuts in micro type at the bottom.
8. Add `make verify-drishti` to the Makefile: npm ci, npx tsc --noEmit, npx vitest run,
   npm run build.

Definition of done: `make verify-drishti` green, renders at 1366x768/1440x900/1920x1080, the
status bar shows a real hash from fixtures, ui-critic reports SHIPPABLE.

Plan first, do not write code yet.
```

**You should see** tokens.css and adapter types written before any component, and fixtures.ts
treated as a real deliverable, not empty stubs. If fixtures are hollow, every later screen is
built against nothing.

**Definition of done.** `make verify-drishti`, three resolutions, `ui-critic` SHIPPABLE.

**Follow-up, if it reaches for a library.**

```
No component library, no Tailwind, no shadcn, no icon package. Remove it and write the CSS
Module. Everything visual comes from tokens.css. If a dependency is genuinely unavoidable,
name it and the one thing it does that we cannot, and wait.
```

**Your turn.** Open it, resize through all three sizes, look for five seconds and ask the only
question that matters: does this look like a tool, or does it look like a prompt.

---

# B1 · Primitives and the chart theme

**Purpose.** The building blocks and the re-themed ECharts, so every later screen is assembly,
not invention. This is where you feed the inspiration refs.

**Prompt 1.**

```
Read @docs/DRISHTI-SPEC.md sections "Tokens", "Component inventory" and "Data honesty rules".
Look at the images in apps/drishti/refs/ — match their density and restraint, not their
colours. Read nothing else. Do not touch src/ or STATE.md.

Build the primitives: Panel, DataTable (virtualised, sortable, mono numeric columns),
MetricReadout, RangeBar for a conformal interval, HashBlock with correct truncation and copy,
Lamp, and src/styles/echarts-theme.ts with every ECharts default overridden per the spec.

Then a scratch route /_primitives rendering all of them with fixture data on one screen.

Rules: no box-shadow anywhere. No radius above 3px. Every number is mono with tabular-nums.
Truncation of IPs, addresses and txids happens in ONE shared formatter every component uses,
never inline. That formatter is display-only: data from the adapter is already truncated at
write time, so a full identifier reaching it is a pipeline bug, not something to smooth over.

Definition of done: `make verify-drishti` green, /_primitives renders everything, ui-critic
SHIPPABLE.

Plan first, do not write code yet.
```

**You should see** one shared formatter used everywhere, and the ECharts theme file written
before any chart. A single ECharts default left in place is the most recognisable
generated-dashboard tell there is.

**Definition of done.** `make verify-drishti`, `/_primitives` renders all, `ui-critic` SHIPPABLE.

**Follow-up, the theme check.**

```
Show me echarts-theme.ts and confirm every default is overridden: font family, font sizes,
axis line colour, split line colour, tooltip background, legend, grid padding, default palette.
Then open /_primitives in the browser and screenshot it so I can see the numbers are mono.
```

**Your turn.** Find one number rendered in the UI font instead of mono. That single tell, fixed
here, is worth more than anything built on top of it.

---

# B1.5 · Appearance — themes and fonts (BUILT)

**Purpose.** The light-default, multi-theme, multi-font system, layered onto the frame without
touching the four-region shell. Done as its own session before LINEAGE so the foundation was
solid and reviewed before a complex screen went on top.

**What it produced.** `tokens.css` restructured into `:root` structural tokens plus seven
`[data-theme]` colour sets and eight `[data-font]` UI-font remaps; default is Pale Sage light
with Hanken Grotesk. Twenty UI-font woff2 files vendored (no network). `theme.ts` with
localStorage persistence and `initAppearance()` before render so there is no flash. An
`Appearance` switcher in the rail footer, two hairline native selects, a11y intact. The adapter
is untouched — switching appearance changes no data.

**Two rules this carries into every session from here.** First, **numerals are always IBM Plex
Mono with tabular-nums, in every theme.** The UI font may change; numbers never do. Second,
**every new screen must look right in the light default AND in dark, checked before the gate**,
because a screen tuned only to one theme will break in the other. `--signal` stays a single
restrained accent under ~5% of pixels in every theme.

**Known small debts, recorded so they are not rediscovered.** Fira 600 is skipped — only 400/500
ship offline, so 600 would faux-bold; vendor a real FiraSans-600 woff2 if that face is chosen for
the demo. The `.head` tracking was kept at 0.08em to match the adjacent Rail convention rather
than the spec's 0.13em; changing only one would look inconsistent.

**Your turn.** Flip through all seven themes on `/_primitives` and confirm the numbers stay mono
and the accent never spreads. Pick the one or two themes the video will actually use now, so
every screen after this is tuned to look best in those.

---

# B2 · LINEAGE — the pipeline, transforming (NEW, and the reason for the video)

**Purpose.** One screen that follows a single transaction down all eight layers and shows, at
each hop, exactly what changed. This is the screen that makes the architecture *visible* instead
of described. It absorbs the old INTAKE and COLLAPSE screens as drill-ins on the KAVACH and SETU
stops, so you build one cohesive narrative instead of three loose tables. Built early, right
after primitives, because it is the spine of the demo and everything else hangs off it.

**The idea, precisely.** A horizontal spine across the top: eight stage nodes in order —
MAYAJAAL · KAVACH · SETU · JAAL · SHASTRA · BUDDHI · VAANI · PRAMAAN — each a Lamp, its mono
name, and the count flowing through it. You pick one hero transaction. The main area then shows
a two-column BEFORE | AFTER of *that one record* at the selected transition. Added fields appear
in --signal. Renamed fields are flagged, not silently swapped. Dropped or quarantined fields are
struck through with their reason. The counts on each side balance visibly. Advancing one stage
animates the diff once, 420ms, and reduced-motion jumps to the end state. Nothing is hardcoded:
every value comes from the adapter.

**Prompt 1.**

```
Read @docs/DRISHTI-SPEC.md sections "1 · INTAKE" and "2 · COLLAPSE", plus @docs/DATA-CONTRACTS.md
sections 3, 4, 5 and 8. Look at apps/drishti/refs/ for density. Read nothing else. Do not touch
src/ or STATE.md.

Build the LINEAGE screen — a per-record trace through all eight stages.

1. A horizontal spine of eight stage nodes: MAYAJAAL, KAVACH, SETU, JAAL, SHASTRA, BUDDHI,
   VAANI, PRAMAAN. Each shows a Lamp, the stage name in mono, and the count of records at that
   stage (rows_in above, rows_out below). Selected stage is marked with --signal; the rest are
   --ink-dim. Number and arrow keys move between stages.
2. A hero-record selector: choose one transaction. The whole screen follows that record.
3. The main area is a BEFORE | AFTER diff of the carried record at the selected transition:
   - fields added by this stage render in --signal with a "+ added" tag
   - a renamed field renders as `old -> new` and pulses once on entry (SETU's src_ip -> peer_ip
     is the canonical one; make it unmissable, it is the whole point of that layer)
   - dropped or quarantined fields are struck through with the stated reason
   - a visible arithmetic line proves the count balances: in == out + dropped
4. Author the adapter function getLineage(recordId) returning, per stage, the record's fields
   before and after plus the counts. All values come from a fixtures.ts constant, never from
   JSX. Flag in a code comment that S10 will back this with a real API endpoint; do not wait.
5. Stage-specific truth, from the fixture, not invented:
   - KAVACH: the sha256 taken on raw bytes, the manifest tags MAPPED / SYNTHESISED / MISSING,
     and if this record were rejected, its reason. Clicking KAVACH drills into the full INTAKE
     detail: file list with per-file SHA-256, the reject table shown WITH rows, never empty.
   - SETU: the rename, the appended geo_country and asn columns, and the grain split — the
     announcements-per-transaction figure read from the data (it lands near the run's real
     value; if a future run makes it seven, the screen says seven, never a hardcoded 9 or 14).
     Clicking SETU drills into the full COLLAPSE detail: the block splitting into transactions
     plus hatched ECHO on Space, the histogram with the mean marked from data, the sparklines.
   - JAAL: the record becomes nodes and edges; show the ANNOUNCED_BY edge appearing, labelled.
   - SHASTRA: p_origin and its interval attach, in the format "p = 0.87 [0.79, 0.92]".
   - BUDDHI: the risk score with its conformal interval; never a score without an interval.
   - VAANI: the one plain-English sentence the officer reads.
   - PRAMAAN: the signed, hash-chained packet line; the merkle head printed in full.
6. Data honesty holds everywhere: identifiers truncated, counts balance, no confidence without
   an interval. If the fixture is edited so counts don't balance, the arithmetic line renders as
   a visible failure, not three numbers that quietly don't add up.

Definition of done: `make verify-drishti` green, LINEAGE renders the hero record through all
eight stages, the SETU rename pulse and the grain-split figure both come from the fixture, the
KAVACH and SETU drill-ins render, ui-critic SHIPPABLE.

Plan first, do not write code yet.
```

**You should see** the diff engine written once and reused for all eight transitions, not eight
bespoke panels. And the counts read from the adapter, not typed in. If the grain-split number is
hardcoded it will eventually contradict the data on screen next to it — that number is the centre
of the pitch.

**Definition of done.** `make verify-drishti`, all eight stages trace, drill-ins render,
`ui-critic` SHIPPABLE.

**Follow-up, when the animation is too busy.**

```
Too much moves on stage advance. List everything that animates, cut it to two things — the added
fields fading in and the renamed field's single pulse — and show me the list. Confirm
prefers-reduced-motion jumps straight to the end state.
```

**Your turn.** Step from MAYAJAAL to PRAMAAN one stage at a time and narrate each change out loud
as if to a judge. If any transition leaves you with nothing to say, that stage's diff isn't
showing its one real idea yet. This walk IS beat 3 and beat 4 of your demo.

---

# B3 · ORIGIN, including the abstain state

**Purpose.** The screen the project exists for. The estimator fan. Build the abstain state
first, so it is never an afterthought — abstention is a third of what makes this screen credible.

**Prompt 1.**

```
Read @docs/DRISHTI-SPEC.md section "3 · ORIGIN". Read nothing else. Do not touch src/ or STATE.md.
If docs/DEMO-CASES.md does not exist yet, use your own fixtures and do not wait.

Build the ORIGIN screen.

1. The timeline fan: x axis is milliseconds since the first announcement, one horizontal lane
   per announcing peer, ticks at announcement times, redacted peer label plus ASN and country
   on the left in mono.
2. The reveal on Space, 420ms: the estimated originator's lane thickens to 2px in --signal and
   gains its probability and interval as "p = 0.87 [0.79, 0.92]" — that is the format, not the
   value. Every number comes from getOriginEstimate, including in fixtures.ts, never from JSX.
   The runner-up keeps a 1px --line-hi lane with its own p; every other lane drops to --ink-mute.
   A margin bracket between first and second. No glow, no pulse, no particles.
3. The three feature readouts with their plain-English glosses, exactly as worded in the spec.
4. The ABSTAIN state, built BEFORE the confident case. A Tor transaction greys the fan, keeps
   the lanes uniform, reads "ABSTAIN · observed peer is a Tor exit · origin not estimable".
5. The permanent one-sentence note under the fan about randomised relay delay, as worded.
6. Probabilities will not sum to 1 and the screen must never imply they should. No total, no
   percentage-of-whole, no stacked bar. That is a deliberate property of the estimator.

Definition of done: `make verify-drishti` green, the fan renders three transactions from
fixtures including one abstain, the reveal fires on Space, ui-critic SHIPPABLE.

Plan first, do not write code yet.
```

**You should see** the abstain state built first, as instructed. If the confident case appears
first, abstain ends up an afterthought.

**Definition of done.** `make verify-drishti`, three transactions including abstain, `ui-critic`
SHIPPABLE.

**Follow-up, when the reveal feels wrong.**

```
Too much is moving. List everything that changes during the 420ms reveal, cut it to three
things, show me the list. Confirm prefers-reduced-motion skips it and renders the end state.
```

**Your turn.** Fire the reveal ten times. If it isn't satisfying by the tenth, too much moves —
remove something. This one animation carries beat three of the demo.

---

# B4 · GRAPH — the fusion, and the toggle that is the money shot

**Purpose.** Both layers in one picture. The CHAIN-ONLY / NETWORK-ONLY / BOTH toggle is the
single most important interaction in the whole console — it is the visual proof of the one idea
the project is built on. Build the aggregated fallback before the GPU path.

**Prompt 1.**

```
Read @docs/DRISHTI-SPEC.md section "4 · GRAPH" and @docs/DATA-CONTRACTS.md section 5. Read
nothing else. Do not touch src/ or STATE.md.

Build the GRAPH screen. Build the aggregated fallback FIRST and the cosmos.gl GPU path second,
so a machine with no usable GPU still gets a working screen.

1. Node types by shape and border, never by colour alone. Edge types by stroke: SPENDS_TO
   solid, ANNOUNCED_BY dotted, SAME_OWNER dashed with opacity set by cluster confidence.
2. The CHAIN ONLY / NETWORK ONLY / BOTH toggle. CHAIN ONLY shows wallets and transactions only.
   NETWORK ONLY shows IPs only. BOTH snaps them together and the ANNOUNCED_BY edges — the one
   place an IP and a money movement sit in one structure — animate in. Make that snap the most
   satisfying moment on screen; it is the demo's centrepiece. Nothing else moves during it.
3. Only the estimated origin path uses --signal. Everything else is --ink-dim and --line.
4. Controls in a hairline strip: hop depth 1/2/3, value floor, time window brush, edge toggles.
5. Hover dims everything not adjacent to the hovered node.
6. Above the node cap, aggregate to clusters and say so as "AGGREGATED · N addresses in M
   clusters". Never silently show a subset.
7. SAME_OWNER never merges two nodes into one and must look visibly less certain than a real
   spend. The heuristic's measured precision is well below one; drawing it as solidly as a
   confirmed transaction would be a lie.

Definition of done: `make verify-drishti` green, the fallback renders with no GPU, the toggle
snaps CHAIN/NETWORK/BOTH, the GPU path holds 60fps at the cap, ui-critic SHIPPABLE.

Plan first, do not write code yet.
```

**You should see** the fallback working before cosmos.gl is installed, and the toggle wired
before any polish. If the GPU path is built first, the fallback becomes an untested claim — and
the fallback is the one that runs on an unfamiliar venue machine.

**Definition of done.** `make verify-drishti`, fallback with no GPU, toggle snaps, GPU 60fps,
`ui-critic` SHIPPABLE.

**Follow-up, the GPU-absent check.**

```
Disable WebGL in the browser and load the screen. It must render the aggregated fallback with a
visible note. If it shows an error or an empty canvas, the fallback isn't wired to the
capability check.
```

**Your turn.** Find a SAME_OWNER edge and confirm it looks visibly less certain than a
SPENDS_TO edge. Then flip CHAIN → NETWORK → BOTH five times and check the snap lands the same way
every time. That is the move you'll make live, in front of the room.

---

# B5 · QUEUE and the inspector

**Purpose.** The screen that proves this is a product an investigator would use, and the home of
the counter-evidence moment.

**Prompt 1.**

```
Read @docs/DRISHTI-SPEC.md section "5 · QUEUE" and @docs/DATA-CONTRACTS.md section 8. Read
nothing else. Do not touch src/ or STATE.md. If docs/DEMO-CASES.md does not exist, author an
equivalent mining-pool case in your own fixtures and move on.

Build the QUEUE screen and the inspector.

1. Virtualised table, 28px rows, hairline separated, all numerics mono. Columns per the spec,
   sortable, the conformal interval rendered as a RangeBar rather than text.
2. j and k move selection, Enter opens, Esc closes; shortcuts printed in the rail.
3. The inspector's four sections in a fixed order that never changes: WHY (SHAP bars,
   plain-English feature names, base rate marked), EVIDENCE (truncated identifiers, clickable
   through to the graph route), COUNTER-EVIDENCE in --cool with WOULD CLEAR markers, CONFIDENCE
   with the interval and the coverage figure it came from.
4. The clear interaction: status flips to CLEARED in --cool, the row leaves the queue, 420ms
   expand and 120ms flip.
5. An alert with empty counter-evidence renders a visible defect state, not an empty panel.
   Every alert is supposed to have counter-evidence; an empty one means the pipeline is wrong.
6. Never render a confidence without its interval. A score with no interval is the defect state.

Definition of done: `make verify-drishti` green, the mining-pool case opens and clears end to
end from fixtures, ui-critic SHIPPABLE.

Plan first, do not write code yet.
```

**You should see** defect states designed in from the start. A forensic tool that renders bad
data as if it were fine is worse than one that crashes.

**Definition of done.** `make verify-drishti`, mining-pool case clears end to end, `ui-critic`
SHIPPABLE.

**Follow-up, the keyboard pass.**

```
Drive the entire screen with the keyboard only and tell me every place you reached for the
mouse. Fix each. Confirm focus rings are visible everywhere and outline: none appears nowhere.
```

**Your turn.** Drive the whole screen keyboard-only, from opening the queue to clearing the
mining pool. Driving a dense tool from the keyboard is the most convincing thing a demo operator
can do.

---

# B6 · PACKET, then the polish pass

**Purpose.** The last screen, then one full pass against the never-look-like list across all
screens.

**Prompt 1.**

```
Read @docs/DRISHTI-SPEC.md section "6 · PACKET" and @docs/DATA-CONTRACTS.md section 9. Read
nothing else. Do not touch src/ or STATE.md.

Build the PACKET screen: the rendered packet on the left with truncated identifiers, the hash
chain, the signature block, a copyable replay command; the BNSS notice on the right in document
typography; three verification lamps HASH VERIFIED, SIGNATURE VALID, REPLAY MATCHED, each with
the actual command printed beneath in micro type. The merkle head prints in full here, once —
a hash is the one long string that must not be truncated. The lamps reflect what the payload
says, never what the screen assumes: a replay mismatch is a red lamp and the screen says so.

Then the polish pass across all screens:
- every screen at 1366x768, 1440x900 and 1920x1080
- no full IP, address or txid anywhere, hashes excepted
- no confidence without an interval, no alert without counter-evidence
- --signal covering under about 5% of pixels on every screen
- keyboard focus rings visible everywhere, outline: none nowhere
- prefers-reduced-motion removes every reveal and leaves the end state
- no placeholder or TODO text on any screen
- every colour and size literal still lives only in tokens.css

Definition of done: `make verify-drishti` green and ui-critic on the whole of apps/drishti/src
reports SHIPPABLE with zero blockers.

Plan first, do not write code yet.
```

**You should see** the polish pass run as a checklist with a verdict per item, not a general
tidy. Each line is something ui-critic checks independently, so vagueness just moves the work.

**Definition of done.** `make verify-drishti` and `ui-critic` on all of `apps/drishti/src` with
zero blockers.

**Follow-up, the literal sweep.**

```
Grep the whole of apps/drishti/src for hex colours, px values and font names outside tokens.css
and echarts-theme.ts and show me every hit. Each one moves into tokens.css or is justified in
one line.
```

**Your turn.** Screenshot all screens, put them side by side, look at them as one set. They
should look like views of one instrument. If one looks like it came from a different project,
it's usually padding or an extra accent colour. Fix it before these go in the deck.

---

# THE NEVER-LOOK-LIKE LIST — what "AI slop" actually means, so ui-critic can catch it

Give this list to the ui-critic as its rubric. These are the specific tells that make a UI read
as generated. Every one is banned in this project, and each maps to a rule you already have.

Generic sans everywhere with no mono for numbers. Purple-to-blue gradients. Rounded cards with
big drop shadows floating on a light-grey page. Emoji or a generic icon pack as decoration. Three
or four accent colours competing. Pill badges in five pastel colours. A "hero section" with a
huge headline — this is a tool, not a landing page. Centred everything. Bento grids. Glassmorphism
blur. Charts with ECharts or Chart.js defaults left in. Full wallet addresses or IPs on screen.
Confidence numbers with no interval. Animations that bounce, pulse, glow, or use particles. Empty
states that say nothing. Placeholder lorem text. More than one
font family beyond the vendored theme set, or numerals in anything but IBM Plex Mono. Any colour
or size literal outside tokens.css.

The positive version, in one line: **it should look like an instrument built for one expert, not
a template sold to a thousand startups.** Dense, hairline-separated, monospace numbers, one
restrained accent doing real work, motion only where it explains something.

---

# SESSION ORDER, on one screen

Everything on `main`. Tag after the gate is green; the tag is your way back.

| Session | Tag | Definition of done |
|---|---|---|
| B0 shell | `b0-done` | `verify-drishti`, three resolutions, ui-critic SHIPPABLE |
| B1 primitives | `b1-done` | `verify-drishti`, /_primitives, ui-critic SHIPPABLE |
| B1.5 appearance | `b1_5-done` | `verify-drishti`, seven themes on /_primitives, numerals stay mono, ui-critic SHIPPABLE |
| B2 LINEAGE | `b2-done` | `verify-drishti`, eight-stage trace + drill-ins, ui-critic SHIPPABLE |
| B3 ORIGIN | `b3-done` | `verify-drishti`, three transactions incl. abstain, ui-critic SHIPPABLE |
| B4 GRAPH | `b4-done` | `verify-drishti`, fallback with no GPU, toggle snaps, ui-critic SHIPPABLE |
| B5 QUEUE | `b5-done` | `verify-drishti`, mining-pool case clears, ui-critic SHIPPABLE |
| B6 PACKET + polish | `b6-done` | `verify-drishti`, ui-critic on all of apps/drishti/src, zero blockers |

Track B runs on its own fixtures from B0. After S04 it reads `data/fixtures/ui/`. After S10 it
can switch `VITE_SOURCE=api`. It never blocks on Track A.

**If the console must be cut short, the sacrifice order is: QUEUE, then PACKET, then ORIGIN's
polish.** Never cut LINEAGE or GRAPH — those two are the demo. LINEAGE sells the architecture,
GRAPH's toggle sells the one idea. Protect both.

**The two sessions that decide how the console is judged: B2 LINEAGE and B4 GRAPH.** Give both a
clear head and, if needed, two sessions each.

---

# APPENDIX · where to steal moves from (all free, all full pages)

You are not copying dashboards. You are collecting six to ten screenshots of *specific moves* —
one dense table, one mono readout, one restrained reveal — into `apps/drishti/refs/`, then telling
Claude in B1 to match their density and restraint. Ignore anything that looks like a marketing
site; you want tools.

**For whole real running tools you can open right now:** Linear (issue tables, keyboard-first
density), Vercel and Railway dashboards (dark, hairline, mono numbers), Datadog and Grafana
(dense telemetry, restrained colour), Retool and Observable (data-first layouts). These are the
closest living relatives of what you're building.

**For curated galleries of full pages:** Godly (godly.website, now "Recent"), Land-book
(land-book.com), SiteInspire (siteinspire.com), Refero (refero.design), Lapa Ninja
(lapa.ninja), Awwwards (awwwards.com), and Cosmos (cosmos.so) and Savee (savee.it) for mood
boards. Mobbin (mobbin.com) is the best for real app flows though it now gates some content.
For type, Typewolf (typewolf.com). Pinterest works too — search "forensic UI", "trading
terminal UI", "data lineage diagram", "network graph dark UI".

**One honest warning about the trendy stuff.** Most of Awwwards and Godly is agency landing-page
work — huge type, scroll animation, gradients. That is the *opposite* of what wins here. Steal
their restraint and their typography confidence, never their heroes. Your north star is a
Bloomberg terminal or an air-traffic-control screen, not a startup homepage.

---

# THE ONE-LINE VERSION

`/clear`, clean `main`, paste Prompt 1, read the plan, `go`, let it build, `make verify-drishti`
until green, run `ui-critic` and screenshot in the browser MCP, `/handoff drishti`, then commit,
push and tag by hand. Never cut LINEAGE or GRAPH.