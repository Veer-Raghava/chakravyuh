# DRISHTI · The Redesign Plan

*A complete creative + technical blueprint for rebuilding the DRISHTI frontend as a bright,
editorial, playful-but-serious 3D experience — without shipping AI slop.*

Companion file: **DRISHTI-BUILD-SESSIONS.md** (the copy-paste prompts you hand to Claude Code,
session by session). Read this file first, then work from that one.

---

## 0 · HOW TO USE THIS DOCUMENT

You are lost, you have ADHD, and you have one of the best models in the world sitting idle. So
this plan is built to remove *decisions*, not add them. Every section ends with a concrete
"what you actually do" line. You never have to invent anything — you approve or you tweak.

The plan has three layers, in order of how much you need to internalise them:

1. **The concept (§1–§3)** — the one idea, the story, the words. Read these properly, once.
   This is the soul. If you only understand this, Claude Code can do the rest.
2. **The system (§4–§5)** — the exact colors, fonts, libraries, and architecture. You skim
   these and trust them; they're already decided and sourced from real award-winning work.
3. **The surfaces (§6–§13)** — screen by screen, shot by shot. You read the one you're about
   to build, paste the matching prompt from the sessions file, and go.

**A promise and a warning up front.** Everything the old spec (`DRISHTI-SPEC.md`) forbade —
motion, 3D, scroll, color, a hero, a story — this plan embraces. But the old spec was *right
about one thing*, and it's the thing you actually care about too: it hated slop. It just fought
slop by removing everything. We're going to fight slop the harder, better way — by adding
things *with craft and intention*. Bright and animated is not the opposite of serious. Bright
and animated **done lazily** is the opposite of serious. That distinction is the entire game,
and this document is mostly about staying on the right side of it.

---

## 1 · WHY THE CURRENT FRONTEND FEELS WRONG (and the one rule that fixes it)

You already feel it, so this section isn't here to convince you — it's here to name the problem
precisely, because a named problem is a solvable one. There are exactly three things wrong, and
they're the same three things wrong with almost every AI-built interface.

**1. It has no front door.** The current build drops you straight into an instrument panel. That
is correct for a tool you use every day and *fatal* for a tool a judge sees for ninety seconds.
There is no moment that says *here is what this is, here is why it's hard, here is why we're the
only ones who solved it honestly*. The most important asset you have — the story of the maze, the
ceiling, the honest "I don't know" — is nowhere on the screen. You built the engine and forgot the
windshield.

**2. It speaks in code.** "Chakravyuh Console." "LINEAGE." "Observer coverage." "LightGBM." These
are the names *you* use with *your teammates*. On screen they read as jargon a government officer
has to decode before they can act. Every unexplained word is a small tax on trust, and you're
charging it constantly.

**3. It performs doubt instead of earning it.** This is the subtle one. Your honesty is your best
feature — but the current build shows it as *weakness*: bad model scores, coverage gaps, hedged
language sitting there looking unfinished. Honesty shown badly looks like a bug. Honesty shown well
looks like rigour. Same fact, opposite impression. (We fix exactly this in §6.)

### The anti-slop north star

Here is the single most important thing in this entire document, and it is counter-intuitive:

> **Cream backgrounds, a serif headline, lots of whitespace and one big word is *the new slop*.**

In 2023 slop was purple gradients and glassmorphism. In 2026 slop is *tasteful minimalism* —
because that's what every AI now reaches for by default. Restraint is no longer a signal of taste;
it's the path of least resistance. So we do **not** win by being minimal. We win by being *crafted*,
and craft has four concrete moves that no default-mode model will make for you:

1. **One owned metaphor, carried everywhere.** Ours is *vision piercing a maze* (§2). Every screen,
   every transition, every icon is a variation on that one idea. Slop has no metaphor; it has
   decoration. The test: could you swap our visuals onto a different product? If yes, we failed.

2. **Custom 3D that carries data, not 3D that decorates.** A floating abstract blob is slop. A
   funnel whose *height is literally the row count dropping from 1,000,000 to 1* is craft. Every 3D
   object on the landing page must be *the data*, not a mascot standing next to the data.

3. **At least one signature custom shader.** One thing on the site that could not have been pulled
   from a library — a bespoke GLSL effect that becomes the thing people remember. (Ours: the
   "illusion-net" caustic dissolve, §7 station 0.) You only need one. One is the difference between
   "nice template" and "who made this?"

4. **Intentional asymmetry and hierarchy.** Slop centres everything and sizes everything the same.
   We commit to a grid with a deliberate bias, one dominant element per view, and typography that
   ranges hard from tiny mono labels to enormous display. Confidence is visible in the *spacing*.

> **What you do with this section:** nothing to build yet. Just hold the north star. Every time
> Claude Code produces something and you're unsure if it's good, ask the one question: *is this
> crafted around our metaphor, or is it a tasteful default?* If it's a default, send it back.

---

## 2 · THE CREATIVE CONCEPT — the world we're building

This is the section to read twice. Everything else is execution.

### The one idea

There is a story hiding inside your own project name, and it's better than anything we could
invent. Your system is called **CHAKRAVYUH** — the spiral, many-ringed battle formation from the
Mahabharata. Dronacharya arranged an army into rotating rings within rings, and almost no one alive
knew how to break it. Abhimanyu, sixteen, knew how to *enter* it — but not how to get out. He
fought ring by ring to the centre and died there, killed by **a partial answer he mistook for a
complete one.**

That is Bitcoin. Money walks *into* the maze easily — through mixers, peel chains, rings of
addresses, relays echoing across the network. An investigator can follow every hop and still never
walk back out to a name. And the classic failure — "the first IP is the sender" — is Abhimanyu's
death exactly: an answer that feels complete, takes you deep, and collapses.

So the maze is the problem. What's the hero?

> **DRISHTI — दृष्टि — "vision, sight, the eye that sees."**

DRISHTI is the interface. It is literally named *vision*. It is the eye that looks into the
chakravyuha and — this is the whole soul of the design — **sees clearly, including seeing where it
cannot see.** The tool's superpower isn't a confident answer. It's clear sight: it shows you the
41.5% it can reach and it shows you the 58.5% that is genuinely dark, and it never pretends the dark
part is light.

```
   CHAKRAVYUH  =  the maze        (the system, the engine, the problem)
   DRISHTI     =  the eye         (the interface, what the user touches, the hero of the site)

   the brand line:   "See through the noise."
   the long line:    "A million signals. One clear view. And the honesty to say when there's none."
```

This resolves your jargon problem cleanly. You stop saying "Chakravyuh Console" (two hard words, no
meaning to an outsider). The product the officer *uses* is **DRISHTI**. CHAKRAVYUH is the name of the
engine underneath — it appears in the story on the landing page, where it's explained, and nowhere
as UI chrome. One word to remember, and it means "sight." Perfect for a thing you look at.

### Why this beats a generic "crypto forensics" concept

Because it's *yours* and it's *true*. It's grounded in the actual hard fact of the project (the maze
you can't exit, the partial answer that kills), it's culturally rooted (built in India, for an
Indian agency, under Indian law — the Sanskrit isn't decoration, it's provenance), and it gives us
one visual metaphor — **an eye resolving order out of a swirling maze** — that we can carry into
every single screen. That is craft-move #1 from §1, locked.

### The emotional arc we're staging

The landing page is not a feature list. It's a change of feeling, in four beats:

```
   1. AWE       "look at this beautiful, terrifying mess"   → the maze, a million signals swirling
   2. TENSION   "you can't just walk in and grab a name"    → the trap, first-seen collapses
   3. CLARITY   "watch it resolve, ring by ring"            → the 8 layers, the funnel to one
   4. TRUST     "and here's the part nobody else has"       → the honesty, the ceiling, the packet
```

By the time the login card appears at the bottom, the visitor should feel two things at once: *this
is beautiful* and *these people are serious*. That double feeling — playful surface, rigorous spine
— is the entire brief, and the arc is how we earn it.

### The guide: a small character called DRISHTI's eye ("the Diya")

You asked for a helper that walks users through. Here's the design that won't become Clippy.

The guide is **not human, not a robot, not a face.** It's a small, warm, matte-clay **flame — a
diya** (the little oil lamp). Thematically exact: a diya is *how you see in the dark*, which is the
whole product. It's a soft rounded 3D shape, hand-made looking, never photoreal (photoreal +
near-human = the uncanny valley we avoid). It floats at the edge of the screen and does three
things, sparingly:

- **On the landing page:** it *leads the eye* — drifting to the next station just before you reach
  it, brightening when the important number appears. It narrates in at most one short line per
  station, and only the first time.
- **In the app:** it's a dismissible helper. Click it for a one-line "what am I looking at" on any
  screen. It brightens near things that need attention (a high-confidence lead), dims when it has
  nothing useful to add. It has a visible **off switch** and remembers being off (in memory, not
  localStorage — see §5).
- **Its personality:** calm, precise, a little dry. It never says "Great job!" It says useful things
  or nothing. Think a good field guide, not a cheerleader. The rule: *if the line doesn't help the
  user do the next thing, the diya doesn't say it.*

> **What you do with this section:** internalise the two names (CHAKRAVYUH = maze/engine, DRISHTI =
> eye/interface), the four-beat arc, and the diya. When you paste prompts later, this vocabulary is
> what makes Claude Code build one coherent thing instead of eight pretty unrelated screens.

---

## 3 · THE VOCABULARY — every word on screen, decided

Slop reason #2 was "speaks in code." We fix it here, once, with a table. The rule: **the layer's
Sanskrit name is allowed exactly once per screen, always paired with a plain-English gloss the first
time it appears. After that, use the plain word.** The Sanskrit is flavour and memorability; the
plain word is what the officer actually reads.

### The layer names, each with its permanent one-line gloss

| On screen (once) | Plain gloss (always) | Never say |
|---|---|---|
| **MAYAJAAL** | "the world we built to test this" / "synthetic data engine" | "the simulator", "fake data" |
| **KAVACH** | "the sealed intake" / "evidence intake" | "ingestion layer", "the parser" |
| **SETU** | "untangling network from money" / "the bridge" | "normalisation", "ETL" |
| **JAAL** | "the connection map" / "the fused graph" | "the graph layer", "link analysis" |
| **SHASTRA** | "who sent it — or honestly, we don't know" / "origin estimate" | "the estimator", "conformal engine" |
| **BUDDHI** | "how risky is this" / "risk scoring" | "the classifier", "LightGBM", "the model" |
| **VAANI** | "the plain-English lead" / "the alert" | "explainability layer", "NLG" |
| **PRAMAAN** | "the court-ready proof" / "evidence packet" | "the export", "report generator" |
| **DRISHTI** | (the product name — needs no gloss) | "the console", "the dashboard app" |

### Words to kill on sight

These appear in the current build and must not survive. Left column out, right column in.

```
   "Chakravyuh Console"        →   "DRISHTI"  (or nothing — it's the whole app)
   "LINEAGE"                   →   "How it works"  /  "The pipeline"
   "Observer coverage: 10%"    →   "Listening to ~10% of the network"  (§6 reframes this)
   "LightGBM"                  →   "risk model"  (mention the tech only in a tooltip/About)
   "src_ip / peer_ip"          →   "announcing IP"  /  "the IP that told us"
   "p_origin"                  →   "origin likelihood"
   "conformal prediction set"  →   "shortlist"  (with the guarantee explained in plain words)
   "ABSTAIN"                   →   "No answer available"  /  "Not enough evidence"
   "cluster"                   →   "likely same owner"  (keep "cluster" only in expert view)
   "ASN"                       →   "network operator"  (ASN in parens)
   "TXID"                      →   "transaction ID"  (txid label fine next to mono value)
   "quarantine"                →   "set aside"  /  "held back, with reason"
```

### Placeholder / filler text to remove entirely

Do a search-and-destroy pass. Anything in this shape is out:

- Lorem-ipsum, "Feature coming soon", "Lorem", greeked paragraphs of any kind.
- Empty stat cards showing "—" or "0" with no data behind them.
- Generic hero copy like "Powerful analytics for the modern investigator." (Say the real thing:
  "We name the IP behind a Bitcoin transaction — or we tell you when nobody can.")
- Any "Learn more →" that links nowhere.
- Decorative feature cards with an icon + two words + a sentence of nothing. (Slop signature.)

### The tone of the writing itself

Short. Concrete. Numbers with sources. Never a claim the backend can't back. The voice is *a calm
expert who has nothing to prove* — because the numbers do the proving. Read §6 for how the honest
numbers become the flex rather than the apology.

> **What you do with this section:** keep this table open while reviewing any screen Claude Code
> builds. If a word on the left column is visible, it's a bug. This is a five-minute check per screen
> and it's the single highest-leverage thing separating "government tool that feels considered" from
> "AI demo with placeholder text still in it."

---

## 4 · THE DESIGN SYSTEM — colors, type, material, motion

Skim this and trust it. Every value here is chosen to hit "bright editorial playground" while
staying legible as an intelligence tool. It's decided; you approve or nudge.

### 4.1 Palette — "Riso Paper Pop"

The move is *warm paper + a few loud, flat, printed-ink colors*, like a good risograph poster. Warm
(not white) background is what makes it feel editorial and human instead of clinical. The loud
colors are used **flat and confident**, never as gradients (gradients = slop).

```
   ROLE            NAME            HEX        USE
   ─────────────────────────────────────────────────────────────────────────
   background      Paper           #F6EFE0    the warm off-white everything sits on
   ink             Ink             #1B1712    near-black text; NEVER pure #000
   primary         Coral           #FF6B4A    the maze, energy, the hero accent
   authority       Riso Blue       #2E5EAA    data, trust, the "serious" anchor
   warmth          Butter          #F5C542    highlights, the diya's glow
   signal (rare)   Fluoro Pink     #FF48B0    <5% of any screen — the "look here" color
   ─────────────────────────────────────────────────────────────────────────
   support neutrals
   paper-deep      #ECE3D0    cards / raised surfaces on the paper
   ink-soft        #5A5048    secondary text, labels
   line            #D8CDB8    hairlines, dividers, grid
```

**The critical rule for feeling serious:** the deeper you go into the *tool*, the more **Riso Blue**
dominates and the less Coral/Pink you see. Marketing/landing = high color, playful. Analysis
dashboards = blue-anchored, restrained, data-forward. Same palette, different mix per surface. This
one rule is how "playful" and "government intelligence tool" coexist without fighting. (See §6, §10,
§11.)

**Semantic colors** (used ONLY for data meaning, never decoration):
```
   risk high     Coral #FF6B4A          abstain / no-answer   ink-soft #5A5048 (deliberately quiet)
   risk medium   Butter #F5C542         confidence fill       Riso Blue #2E5EAA
   risk low      Riso Blue #2E5EAA      counter-evidence      a muted teal #3E7C77
```
Note abstain is *grey, calm, not alarming*. "We don't know" is a normal, dignified state — the color
says so.

### 4.2 Typography

Three families, all open-source and **vendored as woff2** (offline requirement, §5). All variable
where possible.

```
   DISPLAY   Fraunces           the headlines. Variable — use high optical size,
                                a little WONK and SOFT for that warm editorial character.
                                This is the "voice". Big. 64–140px on the landing.

   TEXT      Hanken Grotesk     body, UI, buttons, most labels. Clean, humanist, calm.
                                (Space Grotesk is the alt if you want more character.)

   DATA      IBM Plex Mono      every number, hash, IP, address, txid. Tabular figures ON.
                                Monospace for data is a real forensic signal, not a style choice —
                                it makes columns align and identifiers scannable.
```

**The type rule that creates hierarchy (craft-move #4):** commit to a *wide* range. Tiny mono
labels (11–12px, letter-spaced, uppercase) sitting under enormous Fraunces display (up to 140px on
the hero). The jump between them is the confidence. Mid-sized everything is the slop signature —
avoid a page where everything is 16–24px.

### 4.3 Material language (the 3D look)

This is what makes the 3D feel *tactile and made*, not chrome-and-glass generic. Rules for every 3D
object:

```
   ✔ matcap materials            cheap, gorgeous, tactile — the default for most objects
   ✔ soft clay / ceramic feel    slightly subsurface, warm, hand-made
   ✔ MeshTransmissionMaterial    ONE hero glass object max (the eye / lens) — expensive, use once
   ✔ AccumulativeShadows +
     RandomizedLight             soft contact shadows so objects feel like they sit on the paper
   ✔ subtle bloom                luminanceThreshold high, so only the diya glow & signals bloom
   ─────────────────────────────────────────────────────────────────────────
   ✘ NO chrome / mirror-metal    reads as generic 3D-render slop
   ✘ NO photoreal humans/faces   uncanny valley
   ✘ NO literal glassmorphism UI  frosted panels are 2023 slop
   ✘ NO rainbow iridescence      unless it IS data (the maze caustics, §7)
```

The palette lives in the 3D too: paper-colored ground plane, coral/blue/butter clay objects, one
glass lens. It should look like *a beautifully lit paper diorama*, not a video game.

### 4.4 Motion

Motion must **explain**, never just delight. Every animation answers "what is happening to the
data?" Rules:

- **Easing:** one custom ease for entrances (a confident `expo.out`-ish curve), one for exits. Don't
  use twelve different eases — consistency reads as intention.
- **Scroll = time/process.** On the landing, scrolling *is* the data moving through the pipeline.
  Down = forward through the funnel. This is the core interaction (§7).
- **Reduced motion:** `gsap.matchMedia` with a `prefers-reduced-motion` branch that swaps the 3D
  scroll-choreography for clean cross-fades and static hero renders. Non-negotiable for a govt tool.
- **The 60fps floor.** If a scene can't hold framerate, it gets simpler, not prettier. §5 covers the
  perf guardrails (AdaptiveDpr, PerformanceMonitor, GPU detect).

### 4.5 Layout grid

A 12-column grid with a **deliberate left or right bias per view** (not everything centred — see
craft-move #4). One dominant element per screen. Generous margins on the paper. Hairline dividers in
`line #D8CDB8`. Data-dense app screens tighten the grid; marketing screens breathe.

> **What you do with this section:** paste the palette hexes, the three font names, and the material
> rules verbatim into the design-tokens prompt (§13, Session 1). After that, you never pick a color
> or font again — you just reference the token names.

---

## 5 · THE TECH STACK — decided, sourced, offline-safe

You chose well already. This locks it and adds the three or four wiring details that are easy to get
wrong and expensive to debug.

### 5.1 The stack

```
   React 18 + Vite + TypeScript          app shell, fast HMR, typed data contracts
   React Three Fiber (R3F v9)            React renderer for Three.js — all 3D scenes
   @react-three/drei (v10)               helpers: Environment, matcap, shadows, Html, etc.
   @react-three/postprocessing (v3)      bloom, the one custom shader pass
   GSAP 3.13+  (now fully free)          all timeline animation; SplitText, ScrollTrigger,
                                         ScrollSmoother all included
   @gsap/react (useGSAP)                 React-safe GSAP hook, auto-cleanup
   Lenis 1.3.x (lenis/react)             smooth scroll — the backbone of the landing
   react-globe.gl  (or r3f-globe)        the 3D transaction globe (§9)
   react-force-graph                     the temporal/dynamic graph (§10)
   CSS Modules                           styling. NO Tailwind, NO component library —
                                         they push you toward the templated defaults we're avoiding
```

> **A note on the graph library.** The playbook's build used `cosmos.gl` (GPU, 10k+ nodes). For a
> demo-scale forensic graph (a few hundred to a few thousand nodes) with *temporal growth* and rich
> per-node interaction, **react-force-graph** is the friendlier choice and integrates with R3F/React
> cleanly. If real runs push past ~5,000 visible nodes, swap to cosmos.gl behind the same data
> contract. Decide in §10; either way the JSON contract (§5.4) doesn't change.

### 5.2 The wiring that's easy to break

**Lenis ↔ GSAP ScrollTrigger** must be married by hand or scroll and animation desync:

```js
const lenis = new Lenis({ autoRaf: false })              // we drive the loop, not Lenis
lenis.on('scroll', ScrollTrigger.update)                 // ST recalcs on every scroll tick
gsap.ticker.add((time) => lenis.raf(time * 1000))        // one clock for both
gsap.ticker.lagSmoothing(0)                              // don't let GSAP fudge frame timing
```

**The fixed-viewport stage** (the "screen stays still, content rises through it" effect you asked
for). Do NOT use drei's `<ScrollControls>` — it fights Lenis and ScrollTrigger pinning. Instead:

```
   • one full-screen, position:fixed  <Canvas>  that never scrolls
   • a tall empty "scroll spacer" div  (e.g. 800vh)  that provides the scroll distance
   • a single shared scrollProgress ref (0→1), updated from Lenis/ScrollTrigger
   • every 3D scene reads that ref inside useFrame() to drive its own choreography
```

This gives you *one continuous processing space* — no hard section jumps, exactly the ToL /
united-carriers feel. Content and 3D rise, resolve, and fade in place as `scrollProgress` advances.

### 5.3 Performance guardrails (bake in from day one)

```
   useDetectGPU          on load; tier 0–1 devices get the reduced-motion / low scene
   <PerformanceMonitor>  drei; drop DPR or effects if fps sags
   <AdaptiveDpr />       auto-lower resolution under load
   dpr={[1, 2]}          cap devicePixelRatio
   <Instances>           any repeated object (the million signals, the node swarm) is instanced
   Draco-compressed glTF  for any imported model; lazy-load per station
   frameloop="demand"    on the globe & graph when idle (re-render only on interaction)
```

### 5.4 The data contract (frontend ↔ backend)

The backend hands the frontend **static JSON fixtures** produced by the pipeline — the frontend
never talks to a live model, which is perfect for an offline demo. The graph contract is already
frozen (from the playbook):

```json
{
  "run_id": "s02-final",
  "stats":   { "n_nodes": 1234, "n_edges": 5678, "n_clusters": 90 },
  "nodes":   [{ "id":"n_00001","type":"address","label":"bc1q4f…9f4d",
               "layer":"chain","cluster_id":"c_012","size":3,"risk":null }],
  "edges":   [{ "source":"n_00001","target":"n_00042","type":"input","weight":1 }],
  "clusters":[{ "id":"c_012","confidence":0.36,"size":8,"label":"cluster 12" }]
}
```

Build every screen against a **sample fixture** at a known path; the real pipeline drops the real
file at the same path in the same shape. Integration is "one wire." You'll define parallel fixtures
for the globe (§9), the alert queue (§11), and the packet (§11) — all listed in §14.

### 5.5 Offline & accessibility (both are NTRO requirements, not nice-to-haves)

```
   OFFLINE
   • all fonts vendored as woff2 in /public/fonts — NO Google Fonts link, NO CDN, anywhere
   • all 3D assets, matcaps, HDRIs bundled locally
   • the app must load and run with networking fully disabled (test this)
   • dev server / any API binds to 127.0.0.1 only

   ACCESSIBILITY
   • prefers-reduced-motion branch (gsap.matchMedia) — full static fallback
   • <Canvas fallback={…}> for no-WebGL machines — a clean 2D version that still shows the data
   • all data also present in the DOM (screen-reader reachable), not trapped in the canvas
   • keyboard focus order, visible focus rings, WCAG-AA contrast (Ink on Paper passes; check Coral)
```

> **What you do with this section:** hand §5.1–§5.2 to Claude Code in Session 0 (project scaffold).
> The Lenis/ScrollTrigger snippet and the "no ScrollControls" rule will save you a full day of
> desync debugging. Everything else here is a checklist you re-run before the demo.

---

## 6 · HONESTY, SHOWN RIGHT — the "smart split"

Your instinct to remove the weak-looking displays was correct. Your worry that removing them makes
you dishonest was *also* correct. Both are true, and the resolution is a split: **remove the
self-critique that only makes you look unfinished; keep — and reframe — the honesty that makes you
look rigorous.** Here's the exact line.

### REMOVE (system-level self-critique — reads as "our tool is bad")

```
   ✘ Global model report cards        ("LightGBM: 0.61 F1") — a lone number that invites attack
   ✘ Model-vs-model comparisons       nobody outside the team cares which model lost
   ✘ "Observer coverage: 10%" shown    as a limitation/apology with no framing
      as a bare stat
   ✘ Raw accuracy percentages          especially any single global accuracy number
   ✘ Any panel titled like a           "Limitations", "Known issues", "Coverage gaps" as UI chrome
      confession
```

These don't make you honest — they make you look like you're grading yourself in public and getting
a C. The honesty that matters isn't *"our system scores X"*. It's *"this specific lead is worth
this much, and here's why it might be wrong."* That's per-case, and it's gold.

### KEEP & REFRAME (per-case honesty — reads as "these people are serious")

```
   ✔ Per-lead confidence              a filled bar + "origin likelihood 0.41", never bare
   ✔ The shortlist, not a name        "true sender is in this set of 2 with 90% confidence"
   ✔ "No answer available"            shown as a calm, dignified, GREY state — a correct output
   ✔ Counter-evidence per alert       "reasons this may be innocent" beside "why flagged"
   ✔ Why-flagged (SHAP) per alert     the 3 features that drove this score, plain-language
   ✔ Cluster confidence 0.36          shown as evidence-with-a-dial, not a failing grade (below)
```

### The three reframes that turn "weakness" into "flex"

These are the heart of the smart split. Each takes an honest number the old build apologised for and
makes it the most impressive thing on the screen.

**1. The 41.5% ceiling → your single best flex.** Don't hide that you only solve 41.5%. *Lead with
it.* On the landing (§7, station SHASTRA) put up a bar:

```
   ALL TRANSACTIONS
   ████████████████████████████████████████████████████████
   ├──────── 41.5% ────────┤├──────────── 58.5% ───────────┤
    an answer is possible      genuinely unknowable — and
    (we get close to this)     we SAY so, every time
```
Framing line on screen: *"Only 41.5% of transactions even contain the answer. We're the only tool
that tells you which is which."* A competitor claiming 95% is now visibly lying. Your honesty is the
weapon.

**2. Cluster confidence 0.36 → a dial, not a defect.** The old build showed 0.36 like a bad test
score. Reframe: it's the *published* precision of this heuristic in real law-enforcement use, and a
0.9 would mean you're leaking. Show it as an adjustable **confidence threshold slider** on the graph
(§10): the analyst drags it, clusters merge/split live. Now 0.36 isn't your grade — it's a *control
the expert operates*. On-screen: *"Ownership is a probability you can tune, never a claim we force."*

**3. "10% coverage" → "one agency's realistic reach," with a curve.** Never show 10% as a bare
apology. Show the **observer-fraction curve** (§12 flex): as you watch more of the network, success
climbs across the published 11–60% range. On-screen: *"Tell us your coverage, we'll tell you what's
achievable"* — which reframes a limitation as *methodological authority nobody else has.*

### The truncation rule (identity protection — a hard requirement, and a credibility signal)

No complete identifier ever appears on any screen. This is both an NTRO/legal requirement and, as
the playbook notes, a detail that *makes you look serious* because most teams splash full wallet
addresses everywhere. Enforce it **in the data/fixture layer** so the full value never reaches the
browser:

```
   IPv4        first two octets           203.0.xx.xx
   IPv6        first two hextets          2001:0db8:…
   address     first 6 + last 4           bc1q4f…9f4d
   txid        first 8 + last 4           4a7f2c91…8b3e
   SHA-256 hashes / Merkle roots          PRINTED IN FULL — BSA 2023 §63(4) requires it;
                                          a truncated hash proves nothing
```

> **What you do with this section:** treat the REMOVE list as a deletion checklist and the three
> reframes as *features to build* (they map to §7, §10, §12). The mental model: you're not hiding
> weakness, you're relocating honesty from the system level (where it looks bad) to the per-case
> level (where it looks rigorous) — and turning the three biggest "weak" numbers into the three
> proudest moments on the site.

---

## 7 · THE LANDING — the scroll story, shot by shot

This is the piece you care about most, so it's the most detailed. It's a single vertical
scroll-driven journey through the CHAKRAVYUH pipeline, staged in the fixed-viewport stage from §5.2.
**The through-line is a funnel:** a number in the top corner starts at **1,000,000 raw signals** and
counts down at every station until it reaches **1 court-ready proof.** That descending number is the
spine — it's craft-move #2 (3D that *is* the data) expressed as the whole page.

```
   THE FUNNEL (top-corner counter, always visible, animates as you scroll)
   1,000,000  →  999,847  →  111,043  →  24,626  →  … →  20  →  1
     signals      sealed      untangled   real txs        leads   proof
   MAYAJAAL      KAVACH        SETU        JAAL     …    VAANI   PRAMAAN
```

### 7.0 Mechanics recap

The `<Canvas>` is fixed and full-screen. A tall spacer drives `scrollProgress` (0→1). Each station
owns a slice of that range (e.g. station 0 = 0.00–0.11). Within its slice a station *rises into
focus, resolves its idea, and dissolves* as the next rises — no hard cuts, one continuous space. The
diya drifts ahead of the reader. Text blocks are `<Html>` or DOM overlays pinned to the stage,
appearing/leaving with the 3D. All copy uses the §3 vocabulary.

### 7.HERO — before you scroll (scrollProgress 0.00)

```
   VISUAL   A large, calm glass lens/eye (MeshTransmissionMaterial — the one hero glass object)
            floating over Paper. Behind it, barely visible, a slow-swirling coral maze of light.
            Through the lens, the swirl resolves into crisp order. That's the whole product in
            one image: the eye that makes the maze legible.
   TYPE     Fraunces, huge (up to 140px):   "See through the noise."
            Sub, Hanken:  "DRISHTI reads the wire behind every Bitcoin transaction — and names the
                           IP that sent it. Or tells you, honestly, when no one can."
   MONO     tiny, top:  "CHAKRAVYUH · two-layer attribution · offline · built for NTRO"
   DIYA     drifts in, settles by the lens, glows once. Line: "Scroll. I'll show you the maze."
   MOTION   the maze swirl loops slowly; on first scroll input the lens tips and we descend INTO it.
```

### 7.STATION 0 · MAYAJAAL — "a world we built to test this" (0.00–0.12)

The signature-shader moment (craft-move #3). This is where the visitor feels AWE.

```
   IDEA     Before we can trace anything, we needed data where we already know every answer —
            because that data doesn't exist in the world. So we built a whole simulated Bitcoin
            universe. This station shows that universe as a living thing.
   VISUAL   The camera is now inside the maze. A vast field of ~thousands of INSTANCED glowing
            points (the signals) drifts and gossips — little arcs of light jump peer to peer.
            ★ SIGNATURE SHADER: a custom GLSL "illusion-net" — caustic, water-like light rippling
            across the whole field (this is the maya/illusion made literal). It's the one effect
            that couldn't come from a library; it's what people screenshot.
   DATA     The counter reads 1,000,000. A label: "~4,000 nodes · realistic P2P gossip ·
            Bitcoin Core's real relay timing." One line pulls a single signal and shows its echo:
            "one transaction, seen ~14 times — 93% of what you capture is echo."
   CHOREO   as you scroll, the swirling field slowly organises from chaos toward a faint lattice —
            the first hint that order is possible.
   COPY     "MAYAJAAL — the world we built. Every signal here has a true origin we secretly know,
            so we can grade ourselves honestly. No real dataset on earth has that answer key."
   DIYA     "This whole world is synthetic — and that's the point. Watch what we do with it."
   FLEX     this is your data-synthesis flex (§12) previewed. It's also just beautiful.
```

### 7.STATION 1 · KAVACH — "the sealed intake" (0.12–0.24)

```
   IDEA     Every byte that enters is hashed and sealed before anything touches it. Tamper-evident.
   VISUAL   The swirling signals stream downward and hit a single armoured "gate" — a warm clay
            slab with a coral wax-seal that stamps each incoming batch. Sealed rows glow blue and
            pass; bad rows peel off to the side into a small, clearly-labelled "set aside" tray
            (never deleted — held with a reason). A full SHA-256 hash prints beneath the seal,
            in mono, IN FULL (the one thing we never truncate).
   DATA     counter ticks 1,000,000 → 999,847.  Beside the tray: "153 rows set aside · reason:
            malformed · nothing dropped silently."
   COPY     "KAVACH — the sealed intake. We hash the raw bytes BEFORE we read them, so a court can
            prove this is exactly the file we received. Bad rows are set aside with a reason, never
            quietly dropped."
   DIYA     "Notice the hash is shown in full. That's the one identifier we never hide — the law
            requires it."
   MOTION   the seal-stamp is a satisfying single thunk (one accent motion); rows sort visibly.
```

### 7.STATION 2 · SETU — "untangling network from money" (0.24–0.36)

The TENSION beat begins: the visitor learns *why the obvious answer is wrong.*

```
   IDEA     Each row secretly holds two different things glued together — what the MONEY did, and
            what the NETWORK saw. SETU pulls them apart. And it renames one column, which encodes
            the single most important truth in the whole project.
   VISUAL   A sealed blue block arrives and splits down the middle like a bridge opening. Left
            stream = money (coral tokens: amounts, addresses, txids). Right stream = network (blue
            tokens: IPs, ports, timestamps). Between them, a literal small clay bridge (Ram Setu).
   ★ MOMENT The column labelled "src_ip" floats up large, and with a physical CLICK re-labels
            itself to "peer_ip / the IP that told us." A strike-through animates over the wrong
            reading. This is the site's cleverest 12 words made visual.
   DATA     counter 999,847 → 111,043 (raw observations resolving toward structure). Micro-callout:
            "1 transaction ≈ 14 announcements. The first IP you see is almost always a relay — an
            echo, not the sender."
   COPY     "SETU — the bridge between the money and the wire. We renamed one column: src_ip became
            'the IP that told us.' Now nobody downstream can mistake a relay for a sender. We
            designed the wrong answer to be impossible to say out loud."
   DIYA     "This rename is the whole trap, defused. Remember it — it comes back at the graph."
```

### 7.STATION 3 · JAAL — "the connection map" ★ THE CENTREPIECE (0.36–0.52)

Give this station the most scroll distance. It's the payoff and it previews the app's core screen.

```
   IDEA     Fuse both worlds into ONE graph: addresses, transactions, and the IPs that announced
            them, all in a single structure. This is the only place in any public Bitcoin tool
            where an IP and a money-movement are first-class connected objects.
   VISUAL   The two streams from SETU weave together into a living force-directed graph that
            assembles in 3D in front of you. Three node shapes only (§10): ● address, ◆ tx,
            ▲ peer. Three edge types. The ANNOUNCE edge (peer→tx, the fusion) draws LAST and in
            fluoro pink — the rarest color, saved for the most important line on the whole site.
   ★ MOMENT the graph finishes assembling and the camera pulls back; the announce edges light up
            across the whole web at once. On-screen, a single sentence, then a half-second of
            silence (no new text): "This edge is the entire project."
   DATA     counter 111,043 → 24,626 (deduped real transactions). A cluster gently haloes with a
            "likely same owner · confidence 0.36" tag — shown as a dial, not a grade (§6 reframe 2).
   COPY     "JAAL — the connection map. IPs, wallets and transactions in one web. Addresses that
            likely share an owner glow together — but 'likely' is a number you can tune, never a
            claim we force. In the tool, this whole map is yours to explore."
   DIYA     "Pink lines = 'this IP told us about this money.' That link is why DRISHTI exists."
```

### 7.STATION 4 · SHASTRA — "who sent it — or honestly, we don't know" (0.52–0.66)

The honesty flex. The most important reframe on the site (§6 reframe 1).

```
   IDEA     For each transaction we estimate a probability per candidate IP — and we ABSTAIN when
            the evidence can't support any answer. Abstention is a correct output, not a failure.
   VISUAL   One transaction pulled forward. Candidate peers arrange in a ring around it (the
            chakravyuha rings, literal). Bars fill with each candidate's origin likelihood. Most
            transactions can't be solved: those collapse into a calm grey "no answer available"
            card — dignified, not alarming.
   ★ MOMENT the ceiling bar animates in, full width:
              ████████████████████████████████████████████████
              ├──── 41.5% possible ────┤├──── 58.5% unknowable ────┤
            Framing: "Only 41.5% of transactions even contain the answer. Anyone claiming 95% is
            lying. We tell you which is which."
   DATA     shortlist example: "true sender is in { 203.0.xx.xx , 198.51.xx.xx } — 90% confidence.
            Not a single name. A shortlist you can act on."
   COPY     "SHASTRA — origin estimate, held to the strictest method in the system. It names a
            suspect only when the math supports it, gives you a shortlist when it's unsure, and
            says 'no answer' when the sender never showed up in the capture. A confident wrong name
            destroys an investigation. We refuse to give you one."
   DIYA     "The grey cards aren't failures. Knowing when to stay silent is the whole skill."
```

### 7.STATION 5 · BUDDHI — "how risky is this" (0.66–0.76)

```
   IDEA     Score wallets and clusters for risk — calibrated, time-honest, and always carrying the
            case against itself.
   VISUAL   Clusters from JAAL float up and get "weighed" — a clay balance-scale metaphor, warm.
            Each cluster's risk tints it (coral high / butter mid / blue low). A peel-chain
            example animates: 14 hops shaving value across days, ending at an exchange.
   DATA     no global accuracy number anywhere (§6 REMOVE). Instead, per-cluster: three plain-
            language "why flagged" factors with little +weights (SHAP, plain words).
   ★ MOMENT beside every "why flagged," a muted-teal "why it might be innocent" appears at the same
            time. "This same pattern also fits a merchant settling daily. You see both at once."
   COPY     "BUDDHI — risk scoring that shows its reasoning and argues against itself. Every flag
            arrives with the reasons it might be wrong, in the alert, not in a footnote."
   DIYA     "An honest tool shows you the exculpatory evidence at the same moment as the damning
            evidence — not in cross-examination."
```

### 7.STATION 6 · VAANI — "the plain-English lead" (0.76–0.87)

```
   IDEA     Turn a score into a sentence an officer can act on. The number becomes a voice.
   VISUAL   A risk score "0.87" floats up and unfolds into a clean alert card (the real component
            from §11 QUEUE, previewed). The card literally speaks — a subtle type-on animation, as
            if the diya is reading it aloud.
   DATA     counter drops toward 20 (ranked leads). The card carries: what, pattern, network
            detail (AS operator, earliest announce time, src port), why-flagged, counter-evidence,
            and an origin line that openly says "abstained on 11 of 14 hops."
   COPY     "VAANI — the voice. A risk score means nothing to an investigating officer. This turns
            it into a ranked, plain-English lead that carries its own evidence and its own doubts."
   DIYA     "Twenty leads, ranked. Not a thousand maybes. Triage is a race against hours."
```

### 7.STATION 7 · PRAMAAN — "the court-ready proof" (0.87–1.00)

The TRUST beat closes. The funnel reaches 1.

```
   IDEA     Package one lead into a signed, hash-chained, byte-for-byte replayable evidence file
            that pre-fills the exact legal notice an Indian investigator serves on an ISP.
   VISUAL   The top lead descends onto a warm "press" that binds it into a single glowing document
            object. A hash-chain visibly links each pipeline stage (full SHA-256 strings, in mono).
            A stamp reads "BNSS 2023 §94 · production notice · ready."
   ★ MOMENT the counter lands on 1. A single line: "One million signals. One court-ready proof.
            And an honest 'we don't know' for everything in between."
   DATA     the packet shows: the tuple that actually identifies a subscriber behind CGNAT —
            { IP · source port · exact UTC timestamp } — the thing an ISP can act on.
   COPY     "PRAMAAN — valid proof. We don't hand you a wallet address. We hand you an IP, a source
            port and an exact timestamp — the three values an ISP needs to name one subscriber —
            and the whole chain re-runs to byte-identical output if the defence demands it."
   DIYA     "This is the finish line: not a guess, a document. Ready when you are."
```

### 7.OUTRO → the login card

As PRAMAAN settles, the fixed stage gently zooms back out to the calm hero lens — the eye closing on
a clear view. The maze is gone; the paper is quiet. The **login card rises into the centre** (§8).
The diya moves beside it: *"Everything past here is real case data. Sign in and I'll take you to the
map."* The transition from marketing-bright to tool-restrained (the color shift from §4.1) begins
right here — Coral recedes, Riso Blue takes over.

> **What you do with this section:** this is 8 station-prompts for §13. Build them one at a time,
> each against the previous station's exit state. Resist the urge to build all 8 before seeing one
> work end-to-end. Station 3 (JAAL) and Station 4 (SHASTRA) are the two that must be perfect; if
> time runs short, the others can simplify to strong 2D+light-3D and the page still lands.

---

## 8 · THE LOGIN — the threshold

Small screen, big job: it's the gate between the public story and the real tool, and it should feel
like *stepping through the lens.*

```
   LAYOUT   a single calm card centred on quiet Paper. The hero lens sits behind it, dimmed. No
            marketing copy left — the color has shifted to Riso-Blue-dominant (§4.1). This visual
            cooldown tells the user, without words, "you're entering the serious part."
   CARD     DRISHTI wordmark · "Sign in to the workstation" · fields (Hanken) · one primary button
            in Riso Blue. A small line: "Runs fully offline. Case data never leaves this machine."
   SECURITY Because this guards sensitive data, show — quietly — that it's real: an offline badge,
            a "127.0.0.1" indicator, no "forgot password to our cloud" nonsense. Don't over-design
            it; a govt login should look sober. This is the ONE screen that's allowed to be plain.
   DIYA     rests at the card's corner, dim: "I'll be on the other side."
   AFTER    successful login → the 3D globe (§9) flies in, as if the eye has pulled back to see the
            whole planet of transactions.
```

Note: real auth is the backend's job. The frontend just needs the screen + a mocked success path
for the demo (a fixture user). Do not build anything that phones home.

---

## 9 · THE GLOBE — the world of transactions

After login, the payoff you asked for: a 3D interactive globe (you liked globe.gl) showing
transactions worldwide, clickable for detail. This is the app's "home" — the establishing shot.

```
   LIBRARY  react-globe.gl (three.js under the hood; integrates with the R3F look). frameloop
            on-demand when idle for perf.
   PLANET   NOT a photoreal earth (that reads generic). A Paper-colored matte globe with coastlines
            in ink hairlines — an editorial, printed-map feel consistent with §4. Land is quiet;
            the DATA is the color.
   DATA     announcement points where IPs geolocate (from the geo/ASN enrichment). Arcs between
            src/dst peers for a selected transaction. Density heat where activity clusters. India
            gently emphasised (it's the operational focus) without hiding the global picture.
   COLOR    points: risk-tinted (coral/butter/blue). Selected transaction's arcs: fluoro pink.
            Abstained/unknown-origin points: grey — visible but calm.
   CLICK    click a point/arc → a side panel slides in (not a modal) showing, per your request:
              sender (origin likelihood + shortlist, or "no answer available")
              receiver(s)
              transaction ID (truncated 4a7f2c91…8b3e)
              fee, amount, timestamp (mono)
              announcing IP (203.0.xx.xx), source port, network operator (ASN)
              → a "Open in map" button jumps to this tx inside the graph (§10)
              → a "Build proof" button jumps to the packet (§11 PRAMAAN)
   TRUNCATE every identifier truncated per §6; hashes (if shown) in full.
   EMPTY    if a tx has no located IP: the panel says "announced only from unlocated / Tor exits —
            no origin available," honestly, in grey.
   DIYA     "Each dot is an IP we heard. Click one — I'll show you who was talking to whom."
   MOTION   slow idle auto-rotate; snaps to face a clicked point. Reduced-motion: no auto-rotate.
```

The globe is *establishing context*, not deep analysis — keep it uncluttered. Deep work happens in
the graph (§10). One click from globe → graph is the key flow.

---

## 10 · THE GRAPH — the centrepiece of the whole tool

This is the heart of DRISHTI and the screen a judge will spend the longest looking at, so it gets
landing-level depth. The old build's graph felt *random* — a hairball you couldn't read. The fix is
not "prettier nodes"; it's giving the graph a **spatial grammar** so that *where a thing sits means
something.* A graph is intuitive when position carries meaning. Six upgrades: the two-floor layout
(10.0, the big idea), de-cluttered look (10.1), temporal growth (10.2), the properties panel (10.3),
legible clusters (10.4), and filters/focus + path-trace (10.5).

### 10.0 The core idea — two floors, one fusion (this is what makes it intuitive, not random)

The NTRO problem, in one sentence, is *"correlate the network layer with the blockchain layer."* So
we don't draw one flat cloud of mixed nodes — **we build the graph as two stacked horizontal floors
in 3D, and the correlation is the only thing that crosses between them.**

```
    ▲   ▲      ▲         ▲     ▲          THE NETWORK FLOOR  (upper)   "the wire"
      ▲    ▲       ▲   ▲     ▲            peers / announcing IPs ▲ — who was talking
   ─ ─│─ ─ ┊ ─ ─ ─ ─│─ ─ ┊ ─ ─│─ ─ ─
      ┋    ┊        ┋   ┊     ┋           ← FLUORO-PINK ANNOUNCE THREADS are the ONLY
   ─ ─┋─ ─ ┊ ─ ─ ─ ─┋─ ─ ┊ ─ ─┋─ ─ ─       edges that cross floors: "this IP told us
      ●───◆───●      ◆───●     ◆──●         about this money." The fusion, made physical.
   ●──◆        ●────◆      ●───◆           THE MONEY FLOOR  (lower)   "the blockchain"
        money flows  left ──────▶ right   addresses ● + transactions ◆ — what moved
```

Three deliberate spatial rules turn a random blob into a diagram anyone reads in five seconds:

```
   1. HEIGHT = LAYER.   Network peers live on the upper floor, money on the lower floor. The whole
                        product's magic — fusing wire and chain — is literally the vertical pink
                        threads stitching the two floors together. This is the money shot: viewed
                        from the side, DRISHTI's entire thesis is one picture.
   2. LEFT→RIGHT = FLOW/TIME. On the money floor, value flows left (sources) to right (sinks /
                        exchanges). A 14-hop peel chain visibly steps downstream. Time and money
                        move the same direction, so "follow the money" is a real direction on screen.
   3. CENTRE = FOCUS.   Whatever you're investigating sits centre-stage; context arranges around it.
                        (Focus mode, 10.5, makes this literal — the subject rises and its
                        neighbourhood orbits it in rings, the chakravyuha again.)
```

**Three readable camera presets** (a small control, bottom-right — not free-fly chaos):

```
   ◈ SIDE-ON     the two floors + pink threads between them. THE pitch shot. Default for "explain".
   ◈ TOP-DOWN    collapses to a clean 2D link map for dense reading / screenshots.
   ◈ ISOMETRIC   a gentle 3/4 view (the working default) — both floors legible, depth visible.
```

Everything below (look, time, properties, clusters, filters) operates inside this two-floor space.
The floors are the reason it never feels random: a peer is *up*, money is *down*, the answer is the
thread between them.

### 10.1 The look (de-cluttered by design)

```
   THREE node shapes, nothing more:   ● address    ◆ transaction    ▲ peer (IP)
   THREE edge types, nothing more:    → input   → output   → announce (fusion, fluoro pink)
```
A forensic graph that needs a twelve-item legend is a graph nobody reads under pressure. Node
*color* = risk (coral/butter/blue/grey-for-unknown). Node *size* = importance (degree or amount).
Cluster membership = a soft translucent hull behind grouped nodes, not extra lines. Background is
Paper; hairline grid; the whole thing reads like an editorial diagram, not a hairball.

### 10.2 Temporal / dynamic growth (your "grows as packets arrive" request)

The graph is not dumped all at once. It **builds over time using the real announcement timestamps.**

```
   • a TIME SCRUBBER along the bottom (mono timestamps, IST). Play / pause / speed.
   • as the playhead advances, nodes and edges APPEAR at the moment they were observed — the pink
     announce threads drop from the upper network floor onto the money floor as each peer "tells
     us," so you literally watch the gossip rain down across the two floors in real observed order.
   • the announce edges arriving out of order visualises WHY first-seen fails — the eye sees a
     distant relay light up before the true origin. The graph teaches the core insight by motion.
   • react-force-graph incremental add (nodes/links appended, layout re-heats gently). For big runs
     swap to cosmos.gl (§5.1) behind the same data + timestamp field.
   • reduced-motion: scrubber still works, but jumps discretely instead of animating the layout.
```
This is craft-move #2 again: the motion *explains the science*, it's not decoration.

### 10.3 The properties panel (your "properties button" request)

Select any node or edge → a right-hand **Properties** panel (slides, never a modal that hides the
graph):

```
   TRANSACTION ◆     txid 4a7f2c91…8b3e · amount · fee · timestamp · script type
                     inputs / outputs (addresses, truncated) · fee rate
                     origin estimate: likelihood bar OR shortlist OR "no answer available"
   ADDRESS ●         address bc1q4f…9f4d · balance-ish role · cluster + confidence
                     risk score with why-flagged + counter-evidence (§6)
   PEER ▲            announcing IP 203.0.xx.xx · source port · network operator (ASN) · geo
                     "announced N transactions · earliest 03:47:12 IST"
                     ⚠ label: "this is an IP that told us — usually a relay, not the sender"
   EDGE (announce)   fluoro pink · "peer told us about this tx at <time>, delay from first-seen …"
```
Every panel has a "Build proof" action → §11 PRAMAAN, and a "Center on globe" action → §9.

### 10.4 Cluster significance made legible (your "clearer clusters" request)

The old build showed clusters but not *why they matter.* Fix:

```
   • the confidence THRESHOLD SLIDER (§6 reframe 2): drag it, hulls merge/split live. The analyst
     sees clustering is a tunable probability, not a fixed claim. Default sits at 0.36.
   • each cluster hull carries a small tag: "likely same owner · confidence 0.36 · 8 addresses".
   • click a cluster → panel explains the EVIDENCE: "grouped because these 8 addresses were spent
     together as inputs (common-input-ownership)" — the plain-language why, not just a boundary.
   • significance cue: risky clusters pull visual weight (size, a coral hull tint); benign ones
     recede. The eye is drawn to what matters without a wall of labels.
```

### 10.5 Filters, focus & the plain-language path-trace (anti-clutter + "never random")

```
   • filter chips: by node type, by risk band, by "has origin answer / abstained", by cluster.
   • search: paste a (truncated) id → graph focuses & fades the rest.
   • "focus mode": double-click a node → it rises to centre-stage and its neighbourhood orbits it in
     concentric rings (the chakravyuha, literal), everything else dims to ink-soft. One thing at a
     time — how a govt user avoids overwhelm. Escape returns to the two-floor overview.
   • ★ PATH-TRACE ("explain this connection"): click node A, then node B → DRISHTI draws the path
     between them AND narrates it in one plain sentence: "This address funded this transaction, which
     the IP 203.0.xx.xx announced at 03:47:12 IST." Turns a tangle into a story. This is the single
     feature that makes a judge say "oh, I get it" — nothing on screen is ever unexplained.
   • "why is this here?" — every node/edge, on hover, gives a one-line reason it exists in this view
     (matched a filter, in the focused neighbourhood, on the traced path). Nothing is decorative.
   • a legend that's always visible but tiny (3 shapes, 3 edges, 2 floors) — the whole vocabulary in
     a corner.
```

> **What you do with this section:** this maps to two sessions in §13 — one for the static graph +
> properties + clusters, one for temporal growth + filters. Build against the frozen JSON (§5.4) plus
> a per-node `first_seen` timestamp for the scrubber. Get the static version beautiful first; add
> time last.

---

## 11 · THE DASHBOARDS — every app screen, redesigned

Inside the tool the mix flips (§4.1): **Riso Blue anchors, color is used only for data meaning,
motion is minimal and functional.** Playful lives on the landing; the workstation is calm, dense,
and confident. Every existing feature survives — we reorganise and rename (§3), we don't remove
capability. "Dumbed down to a government-employee level" means *fewer decisions per screen and
plain labels*, not fewer features.

### 11.0 The app shell + navigation — "the Thread" (NO left rail)

There is **no left vertical sidebar.** A rail is the single most templated element in every
government dashboard on earth — it's the app-side equivalent of the cream-serif slop we killed on
the landing. We replace it with navigation that *is the metaphor*: a thread out of the maze.

**The core idea.** The whole problem is a chakravyuha — *easy to enter, near-impossible to exit.*
The way you survive a labyrinth is a thread (Ariadne's thread; the way back out). So DRISHTI's
navigation is a single glowing **thread — "the Sutra"** — that runs across the very top of the app
and stitches the case's journey together in the exact order an officer works it. You don't "go to a
tab"; you *follow the thread through the maze.* Intuitive because it maps 1:1 to the real workflow;
on-brand because it's the way out of the labyrinth; and it doubles as three things at once.

```
   THE THREAD (the Sutra) — a slim horizontal sightline across the top, ALWAYS visible
   ────────────────────────────────────────────────────────────────────────────────────────
     ◉ Globe   ─ Intake ─ Untangle ─●Map● ─ Origin ─ Leads ─ Proof        [World ◈]
       home      KAVACH    SETU      JAAL   SHASTRA  VAANI   PRAMAAN       MAYAJAAL
     ────────────────────── the thread ──────────[■ 24,626]──────────────────────────
                                                   ↑ the funnel bead rides the thread
   ────────────────────────────────────────────────────────────────────────────────────────
```

What the thread carries, all in one element:

```
   1. NAVIGATION   each stage is a plain-English word + a tiny mono Sanskrit tag. Click to travel.
   2. WHERE YOU ARE the current stage is enlarged (the wide type-scale, craft-move #4) and lit; a
                    bright bead sits on it. Past stages carry a small wax-seal tick (done, sealed);
                    stages with no data yet are quiet ink-soft (reachable but visibly not-yet-run).
   3. THE FUNNEL    the counter from the landing (§7) lives as the BEAD on the thread — 1,000,000 at
                    Intake shrinking to 1 at Proof for the loaded run. The story's spine becomes the
                    tool's navigation. Same object, marketing → workstation, unbroken.
```

The thread is workflow-ordered, not alphabetised: Globe (home / establishing shot) → the seven
pipeline stops in the order you actually work a case → the World (MAYAJAAL) as an ambient "about the
engine" destination pinned at the far right. Reduced-motion: the bead jumps instead of sliding.

**The Aperture — the "very cool" power move (the signature nav gesture).** Press `space` (or click
the persistent lens-glyph / the diya in the corner) and an **iris blooms open from the centre of the
screen** — the chakravyuha rings made literal — with every destination arranged as a radial ring you
can jump to instantly, plus a search field ("go to tx / address / IP…"). It's DRISHTI opening its
eye: `drishti` = sight, the aperture = the pupil, the rings = the maze. It's never *required* (the
thread covers everyone), but it's the gesture power users live in and the one judges remember. Closes
on `esc` or selection. This is the app-side equivalent of the landing's signature shader: one
memorable, owned, on-brand interaction.

```
   THE APERTURE (press space) — a radial quick-switcher, iris-opening from centre
                         ╭───────────────╮
                    Leads             Origin
                 ╱                          ╲
              Proof        ◉ search…         Map
                 ╲                          ╱
                  World              Untangle
                         ╰── Intake · Globe ──╯
```

**The rest of the shell** (deliberately quiet — Riso-Blue-anchored, §4.1):

```
   • a persistent thin TOP STRIP above/holding the thread: case id + run id (mono), the offline
     "OFFLINE · 127.0.0.1 · no external calls" badge (§12.1), and the diya (dismissible helper).
   • ONE dominant panel per screen (craft-move #4); supporting panels stay quiet.
   • the reusable right-hand PROPERTIES / DETAIL DRAWER (slides, never a modal) — the same pattern
     on every screen, so the user learns it once. It is the app's spine of interaction.
   • the reusable ALERT CARD component (first seen at landing station 6, §7 VAANI) — one component,
     used in Leads, in the drawer, and in the packet. Build it once, reuse everywhere.
   • no chrome the user doesn't need: no breadcrumbs, no duplicate menus, no settings gear graveyard.
```

Navigation targets (plain name · Sanskrit tag · what it is):
```
   Globe       · —        · the world of transactions, the app home (§9)
   Intake      · KAVACH   · load & seal a dataset (§11.1)
   Untangle    · SETU     · network vs money, the rename (§11.2)
   Map         · JAAL     · the graph — the main workspace (§10)
   Origin      · SHASTRA  · who sent it / abstain (§11.3)
   Leads       · VAANI    · the ranked alert queue (+ BUDDHI risk under the hood) (§11.4)
   Proof       · PRAMAAN  · build the court packet (§11.5)
   World       · MAYAJAAL · the synthetic-world flex (§11.6 / §12)
```

### 11.1 Intake (KAVACH) — "load & seal a dataset"

```
   PURPOSE   pick a capture file, watch it get sealed, see what passed vs set-aside.
   DOMINANT  a clean drop/select zone → on load, a live "sealing" readout: rows in, rows sealed,
             rows set aside (with reasons, grouped). The full SHA-256 of the file, in mono, in full.
   KEEP-ALL  format auto-detect result, unit-detection (BTC vs sats) result, the balance check
             (rows_in == sealed + set_aside) shown as a reassuring green tick, provenance meta.
   GOVT-EASE one primary action ("Seal & continue"), everything else is a readout, not a control.
   HONEST    set-aside rows are shown proudly ("nothing dropped silently"), never hidden.
```

### 11.2 Untangle (SETU) — "network vs money"

```
   PURPOSE   show the split of one messy row into announcements vs transactions, and the rename.
   DOMINANT  a before/after: one raw row on the left; on the right, the two clean tables it becomes.
             The src_ip → "the IP that told us" rename shown as the headline transformation.
   KEEP-ALL  the echo ratio (≈14 announcements per tx), geo/ASN enrichment, null-vs-"unknown"
             distinction (a tiny tooltip explains why null ≠ unknown for the curious).
   GOVT-EASE mostly a readout screen; the lesson ("the first IP is usually a relay") stated plainly.
```

### 11.3 Origin (SHASTRA) — "who sent it, or honestly we don't know" ★ FULL 3D

This is the screen where the chakravyuha stops being a metaphor and becomes the literal interface.
Finding the sender *is* fighting to the centre of the maze — so we build it in full 3D as concentric
rings, and it is the app's second signature 3D moment after the graph. It is also the per-case
honesty engine, so it stays Riso-Blue-calm even while being spectacular.

```
   THE CANDIDATE RINGS (3D, the transaction at the centre of the maze)

                        ·  ·  ·  ·  ·  ·  ·         ← outer rings: unlikely candidates,
                     ·      ▲      ▲       ·           small, dim (distant relays — the
                   ·    ▲                ▲  ·          ones naive "first-seen" would wrongly
                  ·   ▲     ╭────────╮      ·          pick, sitting far from truth)
                  ·        │  ◆ TX   │   ▲   ·
                  ·   ▲    │ (centre)│       ·      ← inner ring: the SHORTLIST — 2 candidates,
                   ·   ▲    ╰────────╯   ▲  ·          bright Riso-Blue, wrapped in a translucent
                     ·     ▲      ▲     ·              "confidence shell": true sender is INSIDE
                        ·  ·  ·  ·  ·  ·                this shell, 90%.
```

```
   DOMINANT   a 3D field of concentric rings around the selected transaction (◆) at dead centre.
              Each candidate IP (▲, clay peers) sits on a ring; RING RADIUS = inverse likelihood —
              the most probable origin sits closest to the centre/truth, unlikely relays orbit far
              out. Candidate size + a small bar also encode likelihood. You read "who's most likely"
              as pure distance-to-centre: the answer is the thing nearest the middle of the maze.
   THREE      the screen resolves to exactly one of three honest shapes, and the 3D says which:
   SHAPES       ① A NAME — one candidate breaks to the innermost ring, lit, with its likelihood.
                ② A SHORTLIST — 2–3 candidates glow on the inner ring inside a translucent
                  confidence shell ("the true sender is in this set of 2 · 90%"). A shortlist you
                  can act on, not a single fragile name.
                ③ NO ANSWER — the centre is wrapped in a calm GREY fog-dome: the maze has closed
                  over its own middle. "No answer available — the originator never appeared in the
                  capture." Dignified, literal, never alarming. Grey = correct, not failure.
   ★ THE FAN   the 3D announcement fan: candidate IPs fire announcement threads toward the centre
              along a time axis, in real observed order. You WATCH the earliest thread arrive from a
              far-out relay — and see that the naive "first-seen = sender" pick lands on the OUTER
              ring, nowhere near the illuminated centre. The chakravyuha trap (a partial answer that
              looks complete) shown in one motion. This replaces the old ORIGIN timeline — same
              evidence, now the star of the screen instead of a strip chart.
   ★ THE       the 41.5% ceiling as a physical VISIBILITY GAUGE wrapping the scene: an aperture/
   CEILING    horizon ring showing how much of the maze's centre is even illuminated for this class
              of transaction. When origin is unknowable it's mostly dark — you SEE why we abstain.
   CONFIDENCE shown as a DIAL around the whole ring system (§6 reframe 2), never a letter grade.
   KEEP-ALL   every capability of the old screen survives — candidate probabilities, the
              announcement timeline (now the 3D fan), the abstain reason (explicit, on the fog-dome)
              — but the "observer coverage" apology stat is GONE (§6 REMOVE); coverage lives only as
              the interactive curve on the World screen (§12.2), reframed as authority.
   GOVT-EASE  the big answer is always one of the three shapes above, readable in a glance with zero
              jargon. A small "?" toggle explains the 41.5% ceiling in one plain sentence on demand.
   HONEST     confidence, shortlist, abstain — shown as rigour: calm, blue, spatial, never as
              weakness. This screen is the emotional heart of the "smart split" (§6), in 3D.
   REDUCED    prefers-reduced-motion: rings render statically with the same radius=likelihood
   MOTION     mapping, the fan becomes a static labelled arc diagram, no orbit animation.
```

The 2D drawer still opens on any candidate for the raw per-IP detail (port, ASN, announce time,
truncated IP) — the rings are the *understanding*, the drawer is the *record*.

### 11.4 Leads (VAANI + BUDDHI) — "the ranked queue"

```
   PURPOSE   the triage list — the screen an officer lives in. ~20 ranked leads, not 1,000 maybes.
   DOMINANT  a ranked list of alert cards. Each card (the component previewed at landing station 6):
               risk (colored), what it is, the pattern (e.g. "peel chain, 14 hops"),
               network detail (ASN, earliest announce, src port),
               why-flagged (3 SHAP factors, plain words),
               counter-evidence (muted teal, "why it might be innocent"),
               origin line (name / shortlist / "abstained on N hops").
   KEEP-ALL  sorting (risk, recency, confidence), filtering (type, has-origin, cluster), the SHAP
             detail on expand. BUDDHI's risk scoring feeds this but is never shown as a model report
             card (§6 REMOVE) — only as per-lead reasoning.
   GOVT-EASE default sort = "act on this first." Each card answers "what do I do next" in one line.
   ACTION    each card → "Open in map" (§10) · "Build proof" (§11.5).
```

### 11.5 Proof (PRAMAAN) — "build the court packet" ★ THE ARTIFACT NTRO ACTUALLY PRESENTS

This is the culmination — the one screen a room full of NTRO officers and, eventually, a court will
stare at. It is the most important surface in the entire product, and the current build gets it
*exactly wrong*: a dark two-column developer console (`P(ORIGIN) 0.87`, raw fields, a full IP
`103.21.244.17` printed in the clear) that looks like debug output, not evidence. We rebuild it as
what it actually is: **a court-ready exhibit — a sealed forensic dossier on warm Paper**, an object
with physical weight, not a dashboard. PRAMAAN means *valid proof*; the screen must feel like proof.

**What was wrong with the old packet screen, fixed here:**

```
   OLD (the screenshot)                         NEW (this redesign)
   ────────────────────────────────────────────────────────────────────────────────────────
   dark "Instrument" console, debug feel     →  warm-Paper legal exhibit, printed & bound feel
   "P(ORIGIN) 0.87" (jargon, bare number)    →  a plain-English finding an officer can read aloud
   full IP 103.21.244.17 printed in clear    →  103.21.xx.xx on screen (§6); full value ONLY inside
                                                the encrypted payload the ISP receives, never rendered
   hash chain as a flat list                 →  a living hash-chain SPINE binding the whole document
   two flat columns of fields                →  finding (centre) · custody spine (left) · legal
                                                notice (right) — one dominant exhibit, not a form dump
   "verified" as a text label                →  a physical wax-seal that PRESSES down on generation
```

```
   THE EXHIBIT (warm Paper, editorial, tactile — the serious end of the app)

   ┌───────────────────────────────────────────────────────────────────────────────────────┐
   │  DRISHTI · EVIDENCE PACKET                       CASE-2026-0917 · run s02-final · offline│
   │ ┌─hash-chain spine─┐  ┌──── THE FINDING ─────────────┐  ┌── BNSS 2023 §94 NOTICE ──────┐│
   │ │ raw file    ●────│  │ Most likely origin:          │  │ To: <ISP / network operator> ││
   │ │  SHA-256 …full…  │  │  the subscriber behind        │  │ You are required to produce  ││
   │ │ sealed      ●────│  │  ┌──────────────────────────┐ │  │ subscriber records for:      ││
   │ │  SHA-256 …full…  │  │  │ 103.21.xx.xx : 54331     │ │  │  IP ……… source port ………      ││
   │ │ untangled   ●────│  │  │ 2026-09-17 03:47:12 UTC  │ │  │  window …… UTC ……             ││
   │ │  SHA-256 …full…  │  │  └──────────────────────────┘ │  │ Legal basis: BNSS 2023 §94   ││
   │ │ graph       ●────│  │  origin likelihood 0.87 ·     │  │ Evidence cert: BSA 2023      ││
   │ │  SHA-256 …full…  │  │  shortlist of 2 · 90% conf.   │  │  §63(4) — hashes disclosed   ││
   │ │ origin      ●────│  │                               │  │  in full above.              ││
   │ │  SHA-256 …full…  │  │  ⚠ reasons this may be wrong: │  │                              ││
   │ │ packet      ◈SEAL│  │   · relay could be a VPN exit │  │ [ pre-filled · officer signs]││
   │ └──────────────────┘  │   · single-observer window    │  └──────────────────────────────┘│
   │  ← custody, stage by  │   (teal counter-findings, IN  │   provenance: generated offline · │
   │    stage, full hashes │    the exhibit — court-honest)│   deterministic · re-runs byte-   │
   │                       └───────────────────────────────┘   identical · code v… · seed …    │
   │                                   [ Generate packet · PDF / JSON ]   ◈ deterministic replay ✓│
   └───────────────────────────────────────────────────────────────────────────────────────────┘
```

```
   DOMINANT     the exhibit itself, centred, with physical presence: soft paper thickness, a real
                clay WAX-SEAL that presses down with one satisfying thunk when you generate — coral
                while assembling, turning Riso-Blue "sealed · deterministic · verified" when done.
   THE FINDING  stated like a legal exhibit, not a metric. The hero is the { IP · source port · exact
                UTC timestamp } TUPLE — boxed and highlighted — because under CGNAT that tuple is the
                ONLY thing that resolves to one human subscriber. Likelihood/shortlist/confidence sit
                below it in plain words. This is the whole product's output, phrased for a judge.
   ABSTAIN      if the lead abstained on origin, the finding box reads, without apology: "No origin
                asserted — evidence insufficient (originator never appeared in the capture). This
                packet documents the transaction and network evidence without naming a sender."
                The §94 notice then omits the origin tuple and says so. We NEVER fabricate a sender
                to fill a form. Honesty survives all the way into the legal artifact.
   CUSTODY      the hash-chain SPINE down the left binds every pipeline stage (raw file → sealed →
   SPINE        untangled → graph → origin → packet), each with its FULL SHA-256 in mono (BSA 2023
                §63(4) requires full hashes — the one thing we never truncate). You can see custody
                is unbroken from the bytes we received to the proof we produced.
   COUNTER-     "reasons this attribution may be wrong" (muted teal) sits INSIDE the exhibit beside
   FINDINGS     the finding — a defensive, court-ready move nobody else makes. Damning and
                exculpatory evidence in the same document, as it should be.
   LEGAL NOTICE the right panel is the pre-filled BNSS 2023 §94 production notice — reads like the
                actual form an Indian officer serves on an ISP, fields filled from the tuple, ready
                to sign. BSA §63(4) hash disclosure referenced. Feels recognised, not generated.
   PROVENANCE   a footer stamp: "generated offline · 127.0.0.1 · deterministic · re-runs to
                byte-identical output · code v… · seed …" — the sovereignty + reproducibility flex
                (§12.1) landing exactly where it matters most.
   GOVT-EASE    one button: "Generate packet (PDF / JSON)." Everything else is a readout of the
                exhibit. The officer's only job is to read it and sign.
   TRUNCATION   every human-facing identifier truncated (§6): IP 103.21.xx.xx, address bc1q4f…9f4d,
                txid 4a7f2c91…8b3e. Full values live ONLY in the encrypted machine payload the ISP
                consumes — never rendered on screen. SHA-256 hashes printed in full.
   3D TOUCH     restrained but tactile — the seal is a 3D clay stamp under soft shadow, the spine has
                depth, the paper has thickness. It looks pressed and bound, not rendered in a browser.
```

### 11.6 Data (MAYAJAAL) — "the world we built" (the flex screen, §12)

Covered as a flex in §12 — a screen that shows off the synthetic-data engine and the observer-
fraction curve. It doubles as the honest-methodology showcase.

> **What you do with this section:** each subsection is one build prompt (§13). Build the shared
> shell + drawer first (§11.0), then the screens in nav order. Reuse the alert-card and
> properties-drawer components everywhere — consistency is most of the "considered" feeling.

---

## 12 · THE FLEXES — the three things nobody else has

You asked to flex the best features. These are the three, each given a deliberate on-screen moment
so a judge can't miss them.

### 12.1 Offline / air-gapped — "sovereign by design"

The flex: this runs with the wifi *off*, on a Linux box, and no case data ever touches a foreign
cloud — which is the entire reason NTRO can't just buy Chainalysis.

```
   • a small persistent "OFFLINE · 127.0.0.1 · no external calls" badge in the shell (§11.0).
   • on the landing, one quiet line near PRAMAAN: "Sovereign by design. Runs air-gapped. Your case
     data never leaves this machine."
   • THE DEMO MOVE (put this in your talk track): turn the wifi off, the whole tool keeps working.
     Fonts, assets, data — all local. Build so this is literally true (§5.5).
   • an "About / provenance" panel stating: offline, Linux, no foreign dependency, auditable,
     deterministic, Indian legal formats (BNSS/BSA). This is the sovereignty argument, on a screen.
```

### 12.2 Data synthesis (MAYAJAAL) — "we built the measuring stick"

The flex: the hardest part of this problem is that no dataset with a ground-truth answer key can
exist in the real world — so you built one. This is arguably a bigger contribution than the tool.

The **Data screen (§11.6)** is its showcase:
```
   • a living view of the synthetic world (echoes the landing station 0, calmer): entity mix
     (individual 55% … ransomware 1%), ~4,000 nodes, real gossip timing.
   • ★ THE OBSERVER-FRACTION CURVE: an interactive chart. Drag observer_fraction 0.02→0.50 and
     watch achievable accuracy sweep the published 11–60% band. On-screen: "One knob reproduces the
     entire range of published results. Tell us your coverage, we'll tell you what's achievable."
     This turns "10% coverage" from an apology into methodological authority (§6 reframe 3).
   • the four defences, as calm bullets (parameter holdout, real-slice mode, report-the-curve,
     cross-check vs Elliptic) — framed as rigour, honest about what's built vs specified.
   • the "criminals are agents, not templates" point, with the emergent-campaign-length story.
```
This screen is also your answer to the inevitable "you solved your own invention" attack — so it's a
flex AND a shield.

### 12.3 Dynamic network-packet analysis / simulation — "watch the gossip"

The flex: DRISHTI doesn't show a static blockchain snapshot; it shows the *wire* — packets arriving
over time — which is what "traffic" in the problem title actually means.

```
   • the TEMPORAL GRAPH (§10.2): the time scrubber replaying announcements in real observed order
     is itself the flex. You literally watch a transaction gossip across the network, relays
     lighting up out of order — the visual proof of why first-seen fails.
   • an optional "live capture" demo mode on the Data screen: a simulated packet feed streams in,
     the graph grows, leads surface in the queue in real time. (Simulated from a fixture with
     timestamps — no real network. Safe for an offline demo.)
   • the payoff line: "This is network traffic, not a blockchain snapshot. We read the wire — the
     only layer that leads to a person."
```

> **What you do with this section:** these three map to (12.1) the shell badge + about panel,
> (12.2) the Data screen, (12.3) the temporal graph + optional live-capture mode. The observer-
> fraction curve (12.2) and the temporal scrubber (12.3) are the two highest-impact flex builds —
> prioritise them over the live-capture mode, which is a nice-to-have.

---

## 13 · THE BUILD ORDER — how to actually make this with Claude Code

The sequencing matters as much as the content. Build **the spine before the spectacle**: get the
system (tokens, shell, data contracts, one 3D scene working) solid, then layer on stations and
polish. The exact copy-paste prompts live in the companion file **DRISHTI-BUILD-SESSIONS.md**; this
is the map of what each session does and why it's in this order.

```
   PHASE 0 — FOUNDATION  (get the machine running before any beauty)
   S0  Scaffold        Vite + React + TS, R3F, drei, GSAP, Lenis, folder structure, CSS Modules.
                       Lenis↔ScrollTrigger wiring (§5.2). Perf guardrails (§5.3). Offline setup.
   S1  Design tokens   Palette hexes, vendored fonts (woff2), type scale, material presets,
                       motion eases (§4). One "kitchen-sink" page proving every token renders.
   S2  Fixed stage     The fixed <Canvas> + tall spacer + shared scrollProgress ref (§5.2).
                       Prove: scrolling moves a single test object through the viewport smoothly.
   S3  Data contracts  Define + commit all fixture shapes (graph, globe, queue, packet) + samples
                       (§5.4, §14). Everything downstream builds against these.

   PHASE 1 — THE STORY  (the landing — your priority; build station by station)
   S4  Hero + diya     The lens/eye, the maze swirl, headline, the diya character + its behaviour.
   S5  Station 0 shader ★ the signature illusion-net GLSL + instanced signal field (MAYAJAAL).
   S6  Stations 1–2    KAVACH seal + SETU split/rename. Wire the funnel counter.
   S7  Station 3 JAAL   ★ the assembling fused graph + the announce-edge reveal. (centrepiece)
   S8  Station 4 SHASTRA ★ the ceiling bar + candidate ring + abstain cards. (honesty flex)
   S9  Stations 5–7    BUDDHI / VAANI / PRAMAAN + the funnel landing on 1 + outro to login.

   PHASE 2 — THE TOOL   (behind the login)
   S10 Login + shell   §8 login, §11.0 app shell, nav, the shared Properties drawer + alert card.
   S11 Globe           §9 react-globe.gl, click→panel, truncation, globe→graph flow.
   S12 Graph static    §10.1/10.3/10.4 look + properties + clusters + threshold slider.
   S13 Graph temporal  §10.2 time scrubber + incremental growth + §10.5 filters/focus.
   S14 Screens         §11.1–11.5 Intake, Untangle, Origin, Leads, Proof (reuse drawer + card).
   S15 Data / flexes   §11.6 + §12 observer-fraction curve + about/offline panel + live-capture.

   PHASE 3 — POLISH
   S16 Reduced-motion  gsap.matchMedia fallbacks, <Canvas> no-WebGL fallback, DOM a11y (§5.5).
   S17 Vocab + honesty  the §3 kill-list pass + §6 REMOVE checklist across every screen.
   S18 Perf + offline   run with wifi off; GPU-tier test; 60fps audit; Draco/instancing pass.
```

### Rules for working with Claude Code on this

The S0–S18 list above is the *content map* (what gets built, in what order). It is **not** how you
paste prompts. The companion file **DRISHTI-BUILD-SESSIONS.md** groups these into a handful of
milestone sessions with a repeatable ritual, a visual self-correction loop, and one fully worked
example — because 18 disconnected copy-paste prompts is *not* how you get quality out of Claude Code.
The rules that matter:

- **`CLAUDE.md` does the heavy lifting, not the prompt.** The world, vocabulary, tokens, and rules
  live in a `CLAUDE.md` at the repo root that Claude Code auto-loads every session. Your prompts stay
  short and point at plan sections — you never re-paste the world.
- **Plan before build.** For any milestone, ask Claude Code to produce a short plan first (plan
  mode), approve/tweak it, then let it build. Cheaper and far more accurate than diving in.
- **Give it eyes — the visual loop.** Wire the Playwright MCP so Claude Code screenshots the running
  app, compares against the intent + reference images, and self-corrects before handing back. This is
  the single biggest quality unlock for a design-heavy 3D build.
- **One milestone per fresh context, then `/clear` + commit.** Keep the context window focused; a
  running `PROGRESS.md` carries state across sessions. This is how you stay token-efficient.
- **Always build against a fixture** (§5.4). The JSON contract is the seam; real data drops in later.
- **After each milestone, run the two-question review:** (1) crafted around the vision-in-a-maze
  metaphor, or a tasteful default (§1)? (2) any §3 kill-list word visible? Send back on either.

> **What you do with this section:** open DRISHTI-BUILD-SESSIONS.md, start at S0, and go in order.
> Phases 0–1 are the priority; if you run out of time, a perfect landing + login + globe + static
> graph is a complete, impressive demo on its own.

---

## 14 · ASSETS & REFERENCES — what to gather before you build

### 14.1 Fonts (download the woff2, vendor into /public/fonts — no CDN)

```
   Fraunces         (variable)   — display. github/fonts.google — OFL.
   Hanken Grotesk   (variable)   — text/UI. OFL.  (alt: Space Grotesk)
   IBM Plex Mono                 — data/numbers. OFL.
```

### 14.2 3D / material assets (bundle locally)

```
   • a small set of matcap textures (warm clay, ceramic) — matcaps.github.io style packs.
   • one HDRI / lightformer setup for soft studio light (drei <Environment> + <Lightformer>).
   • the diya model: a simple low-poly flame/lamp — commission or model a primitive; keep it
     abstract (no face). Draco-compress.
   • coastline/geo data for the globe (a lightweight GeoJSON) for the matte editorial earth.
```

### 14.3 Data fixtures you must produce (with the backend team)

```
   graph.json        the frozen contract (§5.4) + a per-node first_seen timestamp for §10.2.
   globe.json        located announcements: {lat,lng,risk,txid_trunc,ip_trunc,port,asn,ts,arcs[]}.
   leads.json        ~20 ranked alerts: risk, pattern, network detail, SHAP factors,
                     counter-evidence, origin (name/shortlist/abstain).
   packet.json       one lead's hash-chain (full hashes), config, seed, BNSS §94 fields, tuple.
   world.json        entity mix, node/edge counts, and the observer-fraction→accuracy curve points.
```
Truncate all identifiers in the fixtures **at write time** (§6). Keep hashes full.

### 14.4 Reference sites (the feel to match — study, don't copy)

```
    https://spade.com/                 the actual site which is functionaly similar to ours.
   tolxfujifilmworkshop.onrender.com   the fixed-viewport rise-through-center scroll you want.
   spade.com                           editorial type + confident color + tactile motion.
   unitedcarriers.com                  scroll choreography, one continuous space.
   shader.se                           custom-shader craft; the "who made this?" bar.
```
For each: capture *one specific thing* to steal (a transition, a type treatment, a material) — not
the whole vibe. Copying a whole reference is how you get a well-made version of someone else's slop.

---

## 15 · RISKS, TRADEOFFS & THE HONEST RECOMMENDATION

### 15.1 The real risks

```
   1. SCOPE.  This is a lot for a hackathon. The 8-station 3D landing alone is days of work.
              → Mitigation: the plan is ordered so Phases 0–1 (landing) + login + globe + static
                graph = a complete demo. Everything after is upside. Build in order; stop anywhere
                after S12 and you still have something excellent.

   2. PERF.   8 heavy 3D scenes + a globe + a live graph can tank framerate on a demo laptop.
              → Mitigation: perf guardrails from day one (§5.3); the 60fps floor rule (simpler,
                not prettier); test on the ACTUAL demo machine early.

   3. THE UNCANNY / SLOP TRAP.  R3F makes it easy to produce generic chrome-blob 3D — the exact
              slop we're avoiding.  → Mitigation: the material rules (§4.3) + the two-question
              review (§13). If it looks like a stock render, it is one.

   4. TIME ON THE SHADER.  A custom GLSL shader (station 0) can eat unbounded time.
              → Mitigation: timebox it. If it's not working in one session, ship a strong
                instanced-particle + bloom version and revisit only if time remains. One signature
                shader is the goal, not five.

   5. OFFLINE REGRESSIONS.  It's easy to accidentally add a CDN font or asset and break air-gap.
              → Mitigation: the wifi-off test (§5.5, §18) is a hard gate before the demo.
```

### 15.2 Tradeoffs I made for you (so you don't have to relitigate them)

```
   • react-force-graph over cosmos.gl for the demo (friendlier, richer interaction at demo scale;
     swap behind the contract only if you exceed ~5k visible nodes). §5.1
   • CSS Modules over Tailwind (Tailwind nudges toward templated defaults — the slop we avoid). §5.1
   • DRISHTI as the product name, CHAKRAVYUH as the engine (kills the "Console" jargon cleanly). §2
   • the diya as a non-human flame (helper you asked for, without the Clippy/uncanny risk). §2
   • honesty relocated (system-level removed, per-case kept & reframed) — your "smart split". §6
```

### 15.3 The one honest recommendation

If you do nothing else from this plan, do this: **build the landing story and the honest-ceiling
flex, and brand the whole thing DRISHTI — the eye that sees through the maze.** That single coherent
idea — *vision piercing the chakravyuha, and honest enough to show where it can't see* — is what
separates this from AI slop. The 3D, the globe, the graph are all beautiful expressions of it, but
the idea is the thing. A judge will forget your framerate. They will remember that you were the only
team honest enough to show the 58.5% you can't solve — and confident enough to make it the most
beautiful screen in the room.

Now open **DRISHTI-BUILD-SESSIONS.md** and start at S0.

---

## 16 · NTRO COVERAGE MATRIX — the bare minimum, then how we exceed it

The brief above is creative; this section is the compliance backbone. **Every capability NTRO's
problem statement (SIH26146) asks for is listed here, mapped to the exact screen that delivers it,
and paired with the move that takes us past "met" into "nobody else did this."** Use it two ways:
(1) before the demo, walk this table top to bottom and confirm each row is visibly true on screen;
(2) in the pitch, this is your "we did everything they asked — here's the proof" slide.

```
   NTRO REQUIREMENT                     WHERE IT LIVES (must be visible)        HOW WE EXCEED IT
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R1  Ingest bulk metadata in          Intake · KAVACH (§11.1)                 hash-BEFORE-parse seal
       CSV / JSON / XML, at scale                                               (tamper-evident); rows
                                                                                set-aside WITH REASON,
                                                                                never silently dropped;
                                                                                balance check tick.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R2  Correlate NETWORK layer          Untangle · SETU (§11.2) does the        the fusion is a
       (IP, port, timing) WITH          split + the src_ip→"IP that told us"    FIRST-CLASS object (the
       BLOCKCHAIN layer                 rename; Map · JAAL (§10) fuses them      pink announce thread);
       (wallet, txid, amount)           as the two-floor graph; the pink        the two-FLOOR layout
                                        announce edge IS the correlation.       makes the correlation
                                                                                literally visible; the
                                                                                relay-trap is designed
                                                                                to be unsayable.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R3  AI/ML — detect anomalies         Leads · VAANI (§11.4) ranked queue;     calibration over
       & suspicious patterns            BUDDHI risk under the hood; JAAL        accuracy; per-lead
                                        cluster hulls (§10.4)                   why-flagged (SHAP) +
                                                                                counter-evidence in the
                                                                                same card.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R4  Cluster / group related          Map · JAAL clusters + confidence        0.36 shown as a TUNABLE
       entities                         threshold slider (§10.4)                dial, not a grade;
                                                                                plain-language evidence
                                                                                ("spent together as
                                                                                inputs").
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R5  Attribute ORIGIN /               Origin · SHASTRA (§11.3, full 3D)       ABSTAIN as a correct
       identify the source                                                      output; SHORTLIST when
                                                                                unsure; the honest
                                                                                41.5% ceiling; refuses
                                                                                to fabricate a name.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R6  Generate RANKED, EXPLAINABLE     Leads · VAANI (§11.4) — ~20 ranked      "act on this first"
       leads / alerts                   cards, each self-explaining             default sort; each card
                                                                                answers "what do I do
                                                                                next" in one line.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R7  Dashboard / link-analysis        the whole app: Globe (§9) + the         temporal GROWTH (watch
       VISUALIZATION                    two-floor 3D graph (§10) + Origin       gossip spread) + 3D
                                        rings (§11.3)                           fusion + path-trace
                                                                                narration; intuitive,
                                                                                not a hairball.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R8  EVIDENCE for each flag /         per-lead why-flagged + counter-         court-ready: hash-chain
       auditable output                 evidence (§11.4); Proof · PRAMAAN       custody, deterministic
                                        packet (§11.5)                          byte-identical replay,
                                                                                pre-filled BNSS §94 +
                                                                                BSA §63(4).
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R9  OFFLINE, runs on Linux,          offline badge in the shell (§11.0);     air-GAPPED demo (wifi
       data sovereignty                 About/provenance panel + wifi-off       off, still works);
                                        demo (§12.1); §5.5 offline setup        vendored fonts/assets;
                                                                                127.0.0.1 only; the
                                                                                sovereignty argument as
                                                                                a screen.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   R10 Identity / data protection       truncation enforced at write time      truncate in the FIXTURE
       (handling sensitive PII)         everywhere (§6); full values never      layer so the full value
                                        reach the browser                       never reaches the
                                                                                browser at all.
   ─────────────────────────────────────────────────────────────────────────────────────────────
   BONUS  data with a ground-truth      World · MAYAJAAL (§11.6, §12.2) +       we BUILT the measuring
          answer key (unsolved in       the observer-fraction curve            stick — arguably a bigger
          the field)                                                            contribution than the
                                                                                tool; also our shield
                                                                                against "you solved your
                                                                                own invention."
```

### 16.1 Cross-document consistency checklist (run before every demo)

Because this world spans three files (this plan, `CLAUDE.md`, `DRISHTI-BUILD-SESSIONS.md`), drift is
the enemy. These invariants must hold identically everywhere:

```
   ☐ NO left vertical rail anywhere — navigation is the top Thread + the Aperture (§11.0). Grep the
     codebase and all three docs for "sidebar" / "left rail" and kill survivors.
   ☐ Vocabulary: every §3 kill-list word is glossed or gone. Same gloss for a term in all files.
   ☐ Truncation (§6, §11.5): NO full IP / address / txid on any screen. SHA-256 in full. This was
     visibly violated in the old packet (103.21.244.17) — confirm it's fixed to 103.21.xx.xx.
   ☐ The funnel number is ONE object: 1,000,000→1 on the landing (§7), the same bead on the tool's
     Thread (§11.0). Same figures (1,000,000 · 999,847 · 111,043 · 24,626 · … · 20 · 1).
   ☐ The three signature 3D moments are present and distinct: the illusion-net shader (landing §7
     st.0), the two-floor fusion graph (§10), the Origin candidate-rings (§11.3).
   ☐ Honesty split (§6): NO system-level accuracy/coverage report cards; per-case confidence,
     shortlist, grey abstain, counter-evidence, cluster dial all present and reframed as rigour.
   ☐ Offline (§5.5, §12.1): no CDN/Google-Fonts link anywhere; wifi-off run passes.
   ☐ Every NTRO row R1–R10 above is visibly demonstrable in under 10 minutes of clicking.
```

---

*DRISHTI · the interface to CHAKRAVYUH · SIH26146 · offline two-layer Bitcoin attribution · built for NTRO*