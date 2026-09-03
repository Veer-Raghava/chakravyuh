# DRISHTI · the console

The screen is what a non-technical room actually judges. This document is specific on
purpose, because "make it look good" produces the same dashboard every time and that dashboard
is instantly recognisable as generated.

## The thesis, in one line

**An instrument, not an app.** The reference points are an air traffic display, a spectrum
analyser, a link analysis workbench. Dense, quiet, hairline ruled, mono numerals, one accent
colour used rarely enough that it means something when it appears.

The feeling to aim for is that this screen was already in use before you walked in.

## What it must never look like

This list is not taste. It is the specific visual vocabulary that marks a screen as machine
generated, and the `ui-critic` subagent fails a review on any of it.

No gradient anywhere, in a background, a button, or text. No glassmorphism or `backdrop-filter`.
No `box-shadow`, at all, ever. No border radius above 3px. No purple, violet, indigo, or a
teal-to-blue pair. No emoji as an icon. No centred hero heading. No three or four evenly spaced
feature cards. No pill badge with a coloured dot that conveys nothing. No content centred in a
narrow max-width column, because this is a dense tool and it fills the viewport. No component
library, no Tailwind defaults, no shadcn, no Material. No colour literal outside the tokens
file.

One more, and it is the one that most often gives a project away: **no number set in the UI
font.** Every digit on this screen is mono with tabular figures.

## Tokens

`apps/drishti/src/styles/tokens.css`. The only place a colour or size literal may appear.

```css
:root {
  --bg:         #0A0C10;
  --bg-panel:   #10141B;
  --bg-raise:   #161B24;
  --line:       #1F2733;
  --line-hi:    #2C3746;

  --ink:        #DDE3EA;
  --ink-dim:    #8E99A8;
  --ink-mute:   #5C6675;

  --signal:     #E8913A;   /* origin, and the primary accent */
  --signal-dim: #7A4C1C;
  --cool:       #47B0C4;   /* counter-evidence, cleared, abstained */
  --alert:      #E0524B;   /* high severity only */
  --ok:         #5BB98B;   /* hash verified, replay matched */

  --font-ui:    "IBM Plex Sans", system-ui, sans-serif;
  --font-mono:  "IBM Plex Mono", ui-monospace, monospace;

  --fs-micro: 11px;  --fs-small: 12px;  --fs-body: 13px;
  --fs-lead:  15px;  --fs-big:   20px;  --fs-hero:  28px;

  --w-regular: 400;  --w-medium: 500;  --w-semi: 600;

  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 24px; --s6: 32px; --s7: 48px;
  --radius: 2px;
  --hair: 1px solid var(--line);

  --t-state: 120ms cubic-bezier(0.2, 0, 0.3, 1);
  --t-reveal: 420ms cubic-bezier(0.16, 1, 0.3, 1);
}
```

Budget rules on the palette, which are what make restraint visible.

`--signal` may cover no more than about five percent of visible pixels on any screen. It marks
the estimated originator, the selected row, and nothing else. `--alert` appears only on
severity `high`. `--cool` appears only on counter-evidence, an abstention, or a cleared lead.
Three accents total, and every one of them carries a specific meaning a viewer can learn in
ten seconds.

Typography rules. IBM Plex, both faces, because it reads institutional and technical rather
than startup, which is the correct register for a room containing an NTRO evaluator. Three
weights only. Never below 11px. Uppercase micro labels at `--fs-micro` with `letter-spacing:
0.08em` for column headers and panel titles. Everything numeric is `--font-mono` with
`font-variant-numeric: tabular-nums`, so columns of figures align and a changing value does not
make the row jitter.

## Layout

One frame, four regions, no page scroll. The frame is fixed to the viewport and only the
inside of a panel scrolls.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STATUS BAR  32px   run id · input sha256 · rows · stages · merkle head · AIR │
├────────────┬─────────────────────────────────────────┬───────────────────────┤
│            │                                         │                       │
│ RAIL       │  STAGE                                  │  INSPECTOR            │
│ 180px      │  flexible, the working surface           │  380px                │
│            │                                         │                       │
│ 6 screens  │                                         │  selected object      │
│ + keys     │                                         │  evidence + counter   │
│            │                                         │                       │
├────────────┴─────────────────────────────────────────┴───────────────────────┤
│ COMMAND LINE  28px   ⌘K, last command, timing of the last adapter call        │
└──────────────────────────────────────────────────────────────────────────────┘
```

Regions are separated by 1px hairlines in `--line`, never by shadow and never by a gap.
Panels are `--bg-panel` sitting on `--bg`, so the separation reads as a ruled instrument face
rather than as cards floating on a page. Every measurement is a multiple of 4px.

The status bar is doing product work, not decoration. Left to right: `RUN 20260903-A`, then
`SHA 4f2a…c19d` for the sealed input, then `ROWS 1,000,000`, then `TX 111,043`, then stage
lamps `L0 L1 L2 L3 L4 L5 L6` where a completed stage is `--ok` and a pending one is
`--ink-mute`, then `MERKLE 7b81…5e02`, and finally, right aligned, `AIR-GAPPED` with a small
`--ok` square. That last badge states the product thesis in the chrome of the window, which is
worth more than a slide saying the same thing.

The command line at the bottom shows the last action and how long the adapter call took, in
milliseconds, in mono. Real tools show their latency. It also makes the demo feel live.

## The six screens

Each screen is one beat of the demo and one verdict line from the deck. Nothing else exists.
Six screens that are each fully finished beat nine that are each three quarters done, and the
room can only follow six.

### 1 · INTAKE  ·  "it never breaks on their file"

The evidence of custody. A left column lists the files that were read with their byte counts
and per-file SHA-256. A centre panel shows the manifest: `rows_read`, `rows_sealed`,
`rows_rejected`, and the schema table with each PS column, the type it was coerced to, the
null count, and a `MAPPED` or `SYNTHESISED` or `MISSING` tag. A right panel is the rejects
table, one row per rejected input line with its reason.

The rejects table is the whole point of this screen. A tool that shows you what it refused and
why is a tool that was written by someone who has handled real files. Show it with rows in it,
never empty.

At the bottom of the manifest panel, one line in mono: `rows_read 1,000,000  ==  sealed
999,847  +  rejected 153`. Make the `==` visibly satisfied. That is the arithmetic that proves
nothing was silently dropped.

### 2 · COLLAPSE  ·  "one million rows is not one million events"

The screen that reframes the problem, and the one the non-technical room will remember.

Left two thirds: a horizontal bar that starts as one solid block labelled `1,000,000
ANNOUNCEMENTS` and, once, on a keypress, splits into `111,043 TRANSACTIONS` with the remaining
`888,957` restyled as `--ink-mute` hairline hatching labelled `ECHO`. Under it, a histogram of
announcements per transaction, with the mean marked at 9 and a caption `Bitcoin Core relays to
8 outbound peers by default. The originator plus its eight neighbours is the first wave anyone
sees.`

Right third: a small multiple of three sparklines, announcements per second, unique peers per
minute, and transactions per block, all mono axis labels, all hairline.

This screen is where a judge understands that the input is not a table of transactions and that
anyone who treats it as one is already wrong. Get it right and the rest of the demo is
downhill.

### 3 · ORIGIN  ·  "we can tell who sent it from who repeated it"

The technical centre of the project, and it must be legible in about eight seconds.

The main surface is a **timeline fan**. The x axis is time in milliseconds relative to the
first announcement of the selected transaction, running about 0 to 12,000 ms. Each announcing
peer is a horizontal lane, nine lanes typical, ordered by first-seen time. Each lane has a tick
at each announcement time and a redacted peer label on the left in mono, `103.x.x.x:8333`, with
its ASN and country in `--ink-dim`.

On reveal, the estimated originator's lane thickens to 2px in `--signal` and gains a right
aligned `p = 0.87  [0.79, 0.92]`. The runner-up keeps a 1px `--line-hi` lane with `p = 0.06`.
Every other lane drops to `--ink-mute`. The margin between first and second is drawn as a small
bracket between the two lanes, because margin is what the estimator is actually confident
about.

Below the fan, three feature readouts in a row, each a label and a mono value and a one-line
plain-English gloss: `FIRST-SEEN RANK 1 of 9 · saw it before anyone else we listen to`,
`SPREAD 412 ms · its announcements cluster tightly, which relays do not do`, `OBSERVER
COVERAGE 4 of 16 · twelve of our listeners never saw it, which is itself information`.

To the right, an `ABSTAIN` control that is not a button but a state readout. Pick a
Tor-broadcast transaction from the list and the whole fan greys, the lanes stay uniform, and the
panel reads `ABSTAIN · observed peer is a Tor exit · origin not estimable`. **Build the abstain
case before you build the confident case.** A tool that refuses to answer one transaction in
front of the room is more credible than a tool that answers all of them, and this is the single
highest-leverage thirty minutes of frontend work in the project.

A small note under the fan, permanent: `Announcement order is noisy by design. Bitcoin Core
delays each announcement to each peer by an independent random wait, so first-seen alone is
weak. The estimate uses order, spread, and who did not see it.` One sentence, and it inoculates
you against the sharpest question in the room.

### 4 · GRAPH  ·  "both layers, one picture"

A single fused graph, because two tabs would prove we never fused anything.

Node types are distinguished by shape and border, never by colour alone: address is a 6px
square, cluster is a 10px square with a `--line-hi` border, peer is a 6px circle, ASN is a
larger hollow circle. Edge types are distinguished by stroke: `SPENDS_TO` solid 1px,
`ANNOUNCED_BY` dotted, `SAME_OWNER` dashed with its opacity set by cluster confidence, so a
weak heuristic link visibly looks weak.

Only the estimated origin path is `--signal`. Everything else is `--ink-dim` and `--line`.

Controls are a hairline strip along the top: hop depth 1, 2, 3; a value floor slider; a time
window brush; and toggles for each edge type. Hovering a node dims everything not adjacent to
it, which is the cheapest interaction in the file and the one that makes the graph feel alive.

Two hard rules. `SAME_OWNER` never merges two nodes into one, because a heuristic at 0.36
precision must never be rendered as a fact. And the node cap is real: cosmos.gl on GPU up to
the cap in `run_config`, and above it the view aggregates to clusters and says so in the corner
as `AGGREGATED · 4,912 addresses in 318 clusters`, rather than silently showing a subset.

### 5 · QUEUE  ·  "twenty leads, ranked, each with its counter-argument"

The screen an investigator would actually use, and the one that shows this is a product.

A dense virtualised table, 28px rows, hairline separated, mono for every numeric column.
Columns: rank, case id, severity, score with its conformal interval rendered as a small
horizontal range bar, typology tags, cluster size, estimated origin ASN and country, dwell,
and status. Sort on any column. `j` and `k` move the selection, `Enter` opens it, and the
shortcuts are printed in the rail so nobody has to be told.

The inspector on the right is where the credibility lives, and it has four stacked sections in
a fixed order that never changes:

**WHY** is the SHAP attribution, as a horizontal bar chart with signed contributions, feature
names in plain language rather than column names, and the model's base rate marked.

**EVIDENCE** is the specific rows and txids that drove it, truncated, each clickable through to
the graph.

**COUNTER-EVIDENCE** is `--cool` and mandatory. It lists what argues against this lead, and
where a counter is decisive it carries a `WOULD CLEAR` marker. An alert with an empty
counter-evidence section is a bug, not a clean alert.

**CONFIDENCE** is the score, its interval, the calibration coverage figure the interval comes
from, and either the label or `ABSTAIN · insufficient evidence`.

The demo moment on this screen: open the highest-scoring lead in the queue, which is a mining
pool, read its counter-evidence out loud, and clear it. The status flips to `CLEARED` in
`--cool` and the row moves out of the queue with a 120ms state transition and no animation
flourish. Clearing your own top hit in front of the room is the strongest thing this console
does, because it demonstrates the system is built to be right rather than built to look busy.

### 6 · PACKET  ·  "it holds up in court"

Two panes. Left is the rendered packet as it will be filed, with every identifier truncated,
the hash chain, the Ed25519 signature block, and the replay command in a mono block the user
can copy. Right is the BNSS 2023 §94 production notice with the exchange and the requested
records, in document type rather than UI type, so it reads like paper.

Across the top of the right pane, three verification lamps: `HASH VERIFIED`, `SIGNATURE VALID`,
`REPLAY MATCHED`, each `--ok` when true and `--ink-mute` when not yet run, with the actual
command that was run printed under it in `--fs-micro`. The Merkle head is printed in full, once,
here, because a hash is the one long string that must not be truncated.

## Motion

Two durations and two curves exist, both in the tokens, and nothing else is permitted.

`--t-state` at 120ms is for anything that responds to the user: hover, selection, a toggle, a
row clearing. It must feel instant.

`--t-reveal` at 420ms is for exactly three moments in the entire application, listed below.
Each fires once, on an explicit keypress, never on mount and never on data arrival.

Nothing fades in on page load. Nothing has an entrance animation. No spinner spins for
decoration; where a load takes real time, show a hairline progress rule with the actual row
count climbing in mono, because a number that moves is more convincing than a spinner and it is
true.

`prefers-reduced-motion` removes the three reveals and leaves the end state.

### The three set pieces

These are the only animated moments, and they are the demo. Rehearse them.

**One, the collapse**, on COLLAPSE. The million-row block splits into transactions and echo
over 420ms, with the counter counting from 1,000,000 down to 111,043 in mono over the same
duration. Tabular figures are why this does not jitter.

**Two, the beam**, on ORIGIN. Nine equal lanes for 420ms, then eight recede to `--ink-mute`
while one thickens to `--signal` and the probability and interval appear at its right edge. No
glow, no pulse, no particle. The whole effect is one stroke width and one colour, and that
restraint is what makes it land.

**Three, the clear**, on QUEUE. The counter-evidence section expands, the status flips to
`CLEARED` in `--cool`, and the row leaves the list. 420ms for the expand, 120ms for the flip.

## Component inventory

Fourteen components, all local, all CSS Modules. If a fifteenth seems necessary, one of these
is wrong.

`StatusBar`, `Rail`, `CommandLine`, `Panel` with its uppercase micro title and optional right
slot, `DataTable` virtualised with sortable mono columns, `MetricReadout` being a micro label
plus mono value plus optional gloss, `RangeBar` for a conformal interval, `Fan` for the origin
timeline, `Histogram`, `Sparkline`, `ForceGraph` wrapping cosmos.gl, `ShapBars`, `HashBlock`
with a copy affordance and correct truncation, `Lamp` for a boolean verification state.

Charts use ECharts with every default overridden: no chart title, no legend unless two series
overlap, axis lines in `--line`, no grid lines at all or hairline only, mono tick labels at
`--fs-micro`, tooltip in `--bg-raise` with a hairline border and no shadow, no animation on
data update. ECharts out of the box looks like ECharts, and looking like ECharts is looking
generic, so budget real time for the theme file. Write it once as
`src/styles/echarts-theme.ts` and never override a chart inline.

`deck.gl` for a geo view is optional and deliberately last. A world map with arcs is the most
generic visual in this entire space and it adds nothing that the ASN table does not already say.
Build it only if everything else is finished, and if built, make it a flat hairline choropleth
with no arcs.

## The adapter, which is what makes parallel work possible

Every screen reads data through exactly one module, and no component ever fetches anything.

```
apps/drishti/src/adapter/
  types.ts        generated from docs/DATA-CONTRACTS.md, hand-checked
  fixtures.ts     reads committed JSON in src/adapter/fixtures/
  api.ts          fetch against http://127.0.0.1:8000
  index.ts        picks one from import.meta.env.VITE_SOURCE, default fixtures
```

The exported surface is fixed early and does not change: `getManifest`, `getCollapseStats`,
`listTransactions`, `getOriginEstimate(txid)`, `getGraph(params)`, `listAlerts`,
`getAlert(caseId)`, `getPacket(caseId)`. Every one returns a typed promise, and every one has a
fixtures implementation before the API exists.

This is the seam that lets two people work at once. Track B builds all six screens against
committed fixtures with zero dependency on the pipeline, and the switch to live data is one
environment variable. It also means the console still demos perfectly if the pipeline is mid-
rebuild on the morning of the presentation, which is a risk worth engineering away.

The fixtures are generated once by `make fixtures` from `data/fixtures/`, and they are
committed. They must include the awkward cases from the contract, especially an abstained
transaction, a CGNAT pair sharing one IP on different ports, a mining pool that gets cleared,
and an alert whose counter-evidence carries `WOULD CLEAR`. Fixtures that only contain the happy
path will produce a console that only handles the happy path.

## Track B build order

Front to back would leave the interesting screens unbuilt. This order front-loads the two
screens that carry the demo.

**B0 · the shell.** Vite, TypeScript, tokens, fonts, the four regions, `StatusBar` with real
values from `getManifest`, `Rail` with the six routes and their keyboard hints, `CommandLine`.
Nothing else. Done when the frame is correct at 1440x900 and at 1920x1080 and the status bar
shows a real hash from fixtures.

**B1 · primitives.** `Panel`, `DataTable`, `MetricReadout`, `RangeBar`, `HashBlock`, `Lamp`, and
the ECharts theme. Done when a scratch route renders all seven and `ui-critic` passes them.

**B2 · ORIGIN and its abstain state.** The hardest and most important screen, built second so it
gets the most attention and the most iteration. Done when the fan renders from fixtures, the
reveal fires on keypress, and a Tor transaction shows the abstain state.

**B3 · QUEUE and the inspector.** Table, the four inspector sections in fixed order, and the
clear interaction. Done when clearing the mining pool works end to end from fixtures.

**B4 · COLLAPSE and INTAKE.** Both are mostly tables and two charts, and both are quick once
the primitives exist.

**B5 · GRAPH.** Last of the six, because cosmos.gl has the most ways to eat a day, and because
the demo survives without it while it does not survive without ORIGIN. Build the aggregate
fallback first and the GPU path second.

**B6 · PACKET, then the polish pass.** Then read every screen against the never-look-like list
one final time with `ui-critic` on the whole directory.

## Keyboard, because it is the cheapest credibility in the project

A tool that is driven from the keyboard, and prints its own shortcuts, reads as software
someone uses for eight hours a day. A tool driven only by mouse clicks reads as a demo.

`1` through `6` jump to the six screens. `j` and `k` move a selection in any list. `Enter`
opens. `Esc` closes the inspector. `/` focuses filter. `⌘K` or `Ctrl+K` opens the command line
with the eight adapter calls as commands. `Space` fires the reveal on COLLAPSE and ORIGIN. `?`
shows the full map.

Print the active shortcuts for the current screen at the bottom of the rail in `--fs-micro` and
`--ink-mute`, always visible, never in a modal. Everything reachable by keyboard must also be
reachable by mouse, and every focusable element gets a visible focus ring of `1px solid
var(--signal)` with a 2px offset. Never `outline: none`.

## Performance and honesty under load

The console must never be the reason a number is wrong or a frame is dropped.

Tables are virtualised and render only the visible window. The graph is capped and says so
when it aggregates. Aggregation happens in the API or in the fixtures, never by slicing an
array in a component and hoping nobody asks. No chart is ever fed more than about two thousand
points; downsample upstream and label the downsampling in the axis caption.

Target 60fps on the demo machine at 1920x1080 with the graph open. Measure it once and record
the number in `docs/EXPLAIN.md`, because "it feels smooth" is not a measurement.

Fonts are vendored, not fetched. Put the IBM Plex woff2 files in
`apps/drishti/public/fonts/` with `font-display: swap` and a local `@font-face`. A console that
depends on Google Fonts is a console that looks broken on a venue network, and this project
claims to work air-gapped, so it has to actually do it.

## Data honesty rules, which are non-negotiable

These come from the deck's own safety rule and they apply to every screen and every fixture.

No complete IPv4 or IPv6 address is ever rendered. Octets three and four are always `x`, as in
`103.x.x.x:8333`. No complete Bitcoin address is ever rendered; use first six and last four,
as in `bc1q4f…9f4d`. No complete TXID; first eight and last four. The reason is simple: an
invented string can turn out to belong to a real person, and a forensics tool that leaks an
identifier onto a projector has failed at the thing it claims to be good at.

Hashes are the exception. A SHA-256 or a Merkle root is printed in full, once, on PACKET,
because its whole purpose is to be checkable.

No confidence value appears without its interval. No alert appears without its
counter-evidence section. No number is hardcoded in a component; if it is not from the adapter,
it does not go on screen. No lorem, no placeholder, no `TODO` visible anywhere in a screen we
might demo.

## The review loop

After every Track B session, run the `ui-critic` subagent on the files that changed. It reads
this document and reports blockers, warnings, missing requirements, and a verdict. It does not
edit and it does not praise.

Then do the harder check yourself, and it takes ten seconds. Screenshot the screen, look at it
for five seconds, and ask: does this look like it came from a tool, or like it came from a
prompt. If the answer is the second one, the usual cause is one of four things, in order of
frequency: too much padding, a radius that is too large, more than one accent colour on screen,
or numbers set in the UI font.

## The one thing to protect

If time gets short, the order of sacrifice is GRAPH first, then INTAKE, then COLLAPSE.

**ORIGIN, QUEUE and PACKET are the demo.** Origin estimation with a visible abstain state is
the technical claim, the queue with mandatory counter-evidence is the product claim, and the
packet with a verifying hash is the legal claim. Those three, finished to this standard, beat
six screens at eighty percent every time, in front of any room.