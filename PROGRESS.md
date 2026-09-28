# DRISHTI — build progress
Current milestone: M6b (Origin · Proof · World §11.3/11.5/11.6) — built + typechecked + built + browser-verified + /design-review passed.
Done:
  - M6b app screens (§11.3/11.5/11.6 + §12.2):
    - Origin · SHASTRA (§11.3): FULL 3D candidate-rings — tx octahedron ◆ at the maze centre, candidate
      IPs on concentric rings where radius = INVERSE likelihood (nearest centre = most likely); confidence
      shell (riso-blue) holds the shortlist; fluoro-pink announce fan from centre to each candidate (marked
      ones brighter); leader=coral, first-to-announce=butter, others=riso-blue. In-screen toggle flips to
      the "No answer available" abstain state → calm grey fog-dome over the centre (dignified, not alarming).
      DOM panel: plain-English verdict, the FIRST-SEEN TRAP note, 41.5% visibility-ceiling gauge, confidence
      dial, candidate table (origin likelihood / margin, lead + first pills). Reduced-motion = frozen spin
      (frameloop demand). All IPs masked (198.18.x.x); radius = inverse likelihood stated on-screen.
    - Proof · PRAMAAN (§11.5): court-ready SEALED DOSSIER, three-column exhibit. LEFT hash-chain spine —
      raw-capture sha256 + 6 chain-of-custody stages + merkle head + expected packet sha256, every SHA-256
      printed IN FULL (64-char, BSA 2023 §63(4)). CENTRE the finding — {announcing IP · source port ·
      observed UTC} boxed hero ONLY when attribution_ready (derived: peer_ip + peer_port + observed_at_utc
      all present), else the honest not-ready box; findMeta (operator ASN, origin likelihood, runner-up);
      findings + counter-findings (any would_clear marked). RIGHT legal — BNSS §94 production notice,
      BSA §63(4) hash disclosure, tool/code/confidence versions. Wax-seal press → enables "Generate packet
      (JSON)" (offline Blob download, no network). IP masked; hashes full; renders like the backend packet.
    - World · MAYAJAAL (§11.6 + §12.2): the synthetic-world grading screen. Canonical funnel
      (1,000,000→1); ★ interactive observer-fraction curve — native <input type=range> (keyboard + offline)
      drags f 0.02→0.50, accuracy sweeps the documented 11–60% band, pinned so default 0.10 → 41.5%
      (COMPUTED, no world fixture exists); naive first-seen baseline (22.1%) dashed for contrast; live
      observed% / attributable% readout. Four defences + offline/about panel + 8-layer glossary.
  - Verified: typecheck + vite build clean; no console errors; kill-list clean (Proof scrub()
    clustering→"same-owner grouping", cluster→"owner group"; World defence "cluster dial"→"same-owner
    dial"); all 9 Proof hashes = 64-char; IPs masked, subject truncated (addr:bc1qge…3182); curve drag
    updates readout (10%→41.5%, 30%→53.5%); DOM-checked content present. /design-review pass at mobile
    (376px: exhibit/defences/glossary collapse to 1-col, funnel wraps, 3D disc fills width) and emulated
    1440×900 (Proof 3-col exhibit, Origin 2-col canvas+panel, World funnel row) — layouts hold, no overflow.
    Screenshot lag in the preview pane worked around by DOM/computed-style reads (authoritative).

  - M6a app screens (§11.1/11.2/11.4), all reusing the shared PropertiesDrawer + AlertCard:
    - Intake · KAVACH (§11.1): calm drop/select zone → seal() → live "sealing" tally count-up
      (rows in = sealed + set aside), teal balance tick (rows_read == sealed+rejected && arithmetic_ok),
      set-aside reasons shown proudly (never hidden), full-file SHA-256 printed IN FULL (mono), provenance
      meta, one primary "Seal & continue" → Untangle. Reduced-motion = final figures immediately.
    - Untangle · SETU (§11.2): echo band (real fixture numbers — 4.9 announcements/tx, 79.6% echo,
      "41,594 announcements collapse to 8,495 real transactions"), before/after split with the
      src_ip → "the IP that told us" rename as the headline transformation, THE WIRE table (6 announcing
      IPs for one tx) + THE MONEY table, null≠0≠unknown tooltip on operator (ASN), relay lesson.
    - Leads · VAANI (§11.4): featured full AlertCard ("act on this first") + compact ranked queue
      (20 shown of 199), sort (act-on-this-first / confidence / group size), filters (attribution ready /
      grouped), per-lead drawer summary. NO global model report card (§6). would_clear wired-but-dormant
      (no counter carries it in this fixture; AlertCard renders it only when present).
  - Verified: typecheck + vite build clean; no console errors; DOM-checked all content present; mobile
    375 + desktop-pane widths show no horizontal overflow; drawer open/close (esc + ✕) works.
    /design-review pass: caught + fixed a §3 kill-list leak — the backend `subject_display` "cluster:NNN"
    rendered verbatim, plus the word "cluster" inside 15 lead headlines and the sort/filter chrome.
    Display-layer rename (data untouched): subject "cluster:616"→"group 616", headline word
    "cluster"→"owner group" (\b-guarded, never "clustering"), sort "cluster size"→"group size",
    filter "clustered"→"grouped". clusterVisible now 0; no full identifier on screen (SHA-256 stays full).
    NOTE: could not runtime-emulate prefers-reduced-motion or a true 1440 viewport here (preview pane is
    fixed-width; playwright chrome not installed) — reduced-motion verified by source guards only.

## M4 and earlier
Current milestone: M4 (globe / app-home §9) — code written + built + verified in browser.
Done:
  - M0/M1 foundation: Vite+React18+TS scaffold, tokens (§4), fixed-viewport stage (§5.2),
    useSmoothScroll (Lenis + gsap.ticker + ScrollTrigger), reduced-motion hook, landing scroll story.
  - M3 login (§8): calm Riso-Blue card over a dimmed hero-lens backdrop (reuses <Lens>), offline +
    127.0.0.1 badge, MOCKED success with fixture user (src/auth/, no network call ever). Reached from
    the landing outro via an "Enter the workstation" affordance that rises at scrollProgress > 0.95.
  - M3 shell + nav (§11.0, NO left rail): the Sutra thread (top sightline, workflow-ordered
    Globe→Intake→Untangle→Map→Origin→Leads→Proof→World; current enlarged+lit, past wax-sealed, ahead
    quiet; funnel bead rides it carrying 1,000,000→1). The Aperture (space / diya → iris blooms from
    centre, radial destinations + search, esc/select closes). TopStrip (case+run id, offline badge,
    diya). Reusable right-hand PropertiesDrawer (slides, never modal) + reusable DOM AlertCard
    (from alert.json; surfaces would_clear + attribution_ready per §6). 8 wired stub screens.
  - Verified: typecheck + vite build clean; grep "sidebar"/"left rail" = ZERO hits; no console errors;
    screenshots at 1440×900 + 390×844 (login, shell, Leads+drawer, Aperture). /design-review pass:
    fixed funnel-bead overlapping the current label; added narrow-screen guards (thread scrolls-x,
    top strip wraps) so mobile no longer overflows.
Next: the graph (§10) — two-floor JAAL; then Origin rings (§11.3).
Known issues / notes:
  - M4 globe hand-rolled in the repo's own R3F stack (NO react-globe.gl, no new dep). Matte Paper
    sphere + ink-hairline coastlines from a vendored 110m GeoJSON (public/assets/geo), located
    announcements plotted risk-tinted, fluoro-pink great-circle announce arcs on select, subtle butter
    India ring, slow breathing spin + faint pointer parallax, reduced-motion = frozen (frameloop demand).
  - Positions are COUNTRY-LEVEL ONLY (centroid + deterministic per-IP jitter) — stated on-screen.
  - unlocatedCount = 0 for this fixture set: every peer carries a geo_country, so the neutral
    "unlocated / Tor" grey bucket has no members (legend + "0 … not plotted" note stay honest). Not a
    bug — the synthetic IPs (198.18/198.19/203.0 doc+benchmark ranges) are the geolocated stand-ins; do
    not reclassify them as unlocated (that would drop the leader off the map).
  - Fixed in M4 /design-review: globe was undersized on wide viewports (camera z 4.2→3.6) so it now
    fills the frame and reads immersive on both 1440×900 and 390×844.
  - Globe interaction: grab-to-turn (pointer drag on canvasWrap → rotates grp.rotation.y, holds where
    released), continuous idle breathing spin that resumes immediately after a drag (NO pause — the
    earlier 1.5s hold-then-fade was dropped per feedback as awkward). Drag guarded by a >2px `moved`
    threshold so a click still opens the Properties drawer; a drag never selects. Reduced motion = frozen.
  - Click-to-open FIX (was broken on user's machine): setPointerCapture must NOT fire on pointerdown —
    capturing on the wrap div retargets pointerup away from the canvas, so R3F never raycasts the click.
    Now capture only after the >2px drag threshold in onMove; a plain press falls through to the dots.
    Hover cursor no longer via document.body (loses to wrap cursor:grab) — driven by React `hovering`
    state on the wrap itself, so hovering a dot flips grab→pointer. Verified in-browser: hover flips
    cursor, click opens drawer (redacted tx + pink arcs), no console errors.
  - Ambient signal field: all 171 locatable graph.json peers plotted as a faint non-interactive point
    cloud (risoBlue, one draw call) beneath the 14 bright clickable candidates; 3 unlocated.
  - Responsive FitCamera: camera distance fit to the live canvas aspect (margin 1.12) so the globe fills
    any viewport instead of a hardcoded z. Fixes "zoomed out / doesn't fit" on non-1440 screens.
  - Selection/arcs persist after the drawer closes (shows the last-inspected tx) — left intentional.
  - React is 18 (package.json), not 19 — earlier PROGRESS note was wrong.
  - Login lens backdrop reads as a dark dimmed sphere (no maze/lattice behind it, by design for the
    cooldown); acceptable but could get a subtle rim glow later.
  - Mobile: funnel bead can clip ~1 char at the first stage inside the scroll container (cosmetic).
  - No url router by choice (offline, §5.5) — current stage is in-memory ShellContext, fresh each run.
Fixture paths: apps/drishti-v2/src/data/fixtures/*.json (loader: src/data/loader.ts).
Demo machine: <fill in>
Last commit that ran green + offline: —
