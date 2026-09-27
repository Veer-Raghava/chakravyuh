# DRISHTI — build progress
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
