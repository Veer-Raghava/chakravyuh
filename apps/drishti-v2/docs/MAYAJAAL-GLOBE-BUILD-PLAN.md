# MAYAJAAL — Globe + Interaction · Build Plan

> Scope: **only** ST.0 MAYAJAAL. The other seven stations, the funnel, the
> stage, and the scroll machinery are untouched. Offline/air-gapped and
> `prefers-reduced-motion` support are preserved. This is a plan — no code has
> been changed.

## Decisions locked (from review)

| Decision | Choice |
|---|---|
| Globe look | **Stylized Earth** — recognizable continents from a committed land-mask |
| Interaction | **Pointer parallax + hover-highlight** — must never capture scroll |
| Caustic "illusion-net" shader | **Retired** — globe becomes the centerpiece |
| Transition smoothness | **Deferred** — out of scope this task (see §9) |

## 1. Why this fits the narrative

Mayajaal's copy already reads: *"A world we built to test this… ~4,000 nodes ·
realistic P2P gossip · one transaction, seen ~14 times — 93% of what you capture
is echo."*

A rotating **Earth of peer nodes** with glowing **great-circle gossip arcs**,
where a single transaction floods outward to ~14 peers, makes both "the world"
and "the echo (the *maya* / illusion)" literal and global. The ~4,000 peer
nodes are placed **on land** so they simultaneously *are* the globe silhouette
**and** the network — one layer, two readings.

<!-- PLACEHOLDER_PLAN -->

## 2. Prerequisite asset (the one external thing)

Stylized Earth needs a land mask. The build box is offline, so this file must be
**committed by hand** — it cannot be fetched during build:

- `src/assets/land-mask.png` — a small **equirectangular grayscale land mask**
  (land = light, ocean = dark), ~512×256 or smaller (a few KB). Source must be
  public-domain / CC0 (e.g. NASA Blue Marble land mask, or Natural Earth
  rasterized to a bitmap). Keep it tiny; it is only sampled for land/ocean.
- **Graceful fallback:** if the asset is missing, the loader degrades to an
  abstract uniform dotted sphere (the "abstract globe" option) so the build and
  demo never hard-fail. This fallback is a hard requirement, not a nicety.

## 3. Visual composition

- Globe radius **~1.8** at origin. Camera stays exactly as-is (`z=5`, `fov 45`).
- Slight axial tilt (~23°) and a slow auto-spin give it life.
- Layers, back to front:
  1. (optional) faint solid/wireframe sphere for body + a soft fresnel rim.
  2. **~4,000 peer nodes** placed on land — the primary layer, one `<points>`
     draw call. Riso-blue base; the current "hot" gossip source flares coral.
  3. **Glowing gossip arcs** — pooled great-circle curves lifted off the surface.
- Palette: land/nodes `riso-blue` + `ink-soft`; hot source + arcs `coral`→`butter`
  glow. **`fluoro-pink` stays reserved for JAAL** — do not use it here.

## 4. Geometry build (`useMemo`, once — never allocate in `useFrame`)

1. **Land sampling:** load `land-mask.png`, draw to an offscreen canvas, read
   pixels once. For each candidate node, sample `isLand(lat, lon)`; keep only
   land points (plus a sparse ocean scatter if we want faint "cable" hints).
2. **Peer nodes (~4,000):** fibonacci-sphere candidates filtered to land →
   `lat/lon → vec3(R)`. Store `position` (sphere) **and** a `scatter` position
   (reuse the retired shader's scattered-cloud idea) so the globe can *assemble*
   on scroll. One `BufferGeometry`, one `<points>`.
3. **Arc pool (K ≈ 48):** each arc = two node indices; build ~24 points by
   `slerp(a, b)` then push outward by a `sin`-over-param height profile → a curve
   arching above the surface. Prefer **one merged line geometry** (per-arc vertex
   ranges) or a small pool of curve objects to keep draw calls low.

## 5. Animation + the gossip simulation (`useFrame`)

Driven by the existing `local(p, SLICE)` → `{ t, vis }`:

- **Assemble** (t ≈ 0→0.4): nodes lerp `scatter → sphere` via `smoothstep(t,0,0.5)`
  — "the world we built" coming together. (Clean reuse of the old scatter idea,
  without the caustic shader.)
- **Hold:** the gossip simulation runs.
- **Dissolve:** `vis → 0` fades every material; nodes may drift out slightly.
- **Auto-rotate:** `globe.rotation.y += delta * rate` (frozen when `reduced`).
- **Gossip flood — "one tx seen ~14 times":** a light scheduler picks a random
  source node every ~2.5 s and fires **~14 arcs** from it to nearby/random peers;
  each arc runs a highlight pulse source→dest over ~0.8 s, then fades. Arcs are
  recycled from the K-pool; cap concurrent pulses. The source node flares coral;
  receivers blink. This *is* the "93% echo" made visible.
- All opacities ride `vis`.

<!-- PLACEHOLDER_PLAN2 -->

## 6. Interaction — parallax + hover (must NOT capture scroll)

The canvas is fixed and scroll is driven by Lenis on the window, so the golden
rule is: **never `preventDefault` a wheel/touch event and never pointer-capture.**

- **Parallax:** read the R3F pointer (`state.pointer`, already -1..1). Target a
  small tilt `= pointer · maxAngle`; damp `globe.rotation` toward
  `autoSpinY + tilt`. Pure read — scroll is unaffected.
- **Hover-highlight:** raycast against the node layer (a drei/three points
  threshold, or a low-poly invisible pick layer if points-picking is flaky). On
  hover: flare that node and emphasize/spawn its arcs to neighbors; clear on out.
- **Gate to active:** only run raycasting/parallax when `vis > ~0.2`, so hidden
  stations never grab the pointer or burn frames.

## 7. Reduced motion

Freeze auto-spin, pulse travel, and parallax (clamp tilt to center). Render the
globe fully **assembled** (`a = 1`) with one representative flood lit statically —
everything visible and legible, no motion. Mirrors the existing station pattern.

## 8. Files touched

- **Rewrite** `src/landing/stations/Mayajaal.tsx` — new globe. Keep the
  `Mayajaal({ reduced })` export, `SLICE = STATIONS[0].slice`, the
  `useScroll` + `local` + `visible`-gating pattern. Delete the caustic
  `vert`/`frag` (this retires the shader).
- **Add** `src/assets/land-mask.png` — the prerequisite asset (§2).
- **Add** `src/three/globe.ts` — helpers: fibonacci sphere, `latLonToVec3`,
  `greatCircleArc(a, b, lift)`, and the land-mask loader/sampler with fallback.
  Keeps `Mayajaal.tsx` lean and mirrors `src/three/diyaGeometry.ts`.
- **No changes** to `LandingScenes`, `FunnelCounter`, `Stage`, `ScrollContext`,
  or any other station.
- `stations.ts`: copy stays accurate as written. *Optional* one-line tweak to
  Mayajaal's `diya` to nod at the globe — flag only, not required.

## 9. Deferred — transition smoothness (NOT this task)

Captured for a later pass, per your call to skip it now. Two root causes were
found while reviewing:

1. **Dip-to-empty at every boundary.** Adjacent slices don't overlap, and the
   `local()` visibility bell hits **0** at both the end of one station and the
   start of the next — so there's a brief flash of near-empty paper at each
   junction (fade-out-to-nothing, then fade-in), which reads as a blink/pause.
2. **No spatial motion.** Every station sits at the origin and the camera is
   fixed at `z=5` for the whole page, so beats cross-fade *in place* — a
   slideshow of dissolves with no motion for the eye to follow.

The fix (when we take it up): overlap the visibility bells so neighbors truly
cross-fade, and add a small per-station enter/exit drift (± a subtle camera
move). The same overlap must be applied to `StationCopy` and `FunnelCounter`.

## 10. Risks / watch-list

- **Offline asset** (§2) is the only thing needing a committed file — fallback
  keeps the build green if it's absent.
- **Points hover** can be finicky (raycast threshold); fall back to a small
  invisible instanced pick layer if needed.
- **Glow on paper:** additive blending washes to white on the Paper background
  (the retired shader's own frag warns about this) — carry brightness in the
  **alpha**, normal blend, same lesson.
- **Interaction vs scroll:** verify wheel + touch scroll still work while the
  pointer is over the canvas.

## 11. Verification

- `npm run build` (tsc + vite) green.
- Scroll through: globe assembles → gossips → dissolves; funnel holds 1,000,000.
- `prefers-reduced-motion`: static assembled globe, still legible.
- Pointer: parallax tilts, hover highlights, **scroll still works**; other
  stations unaffected.
- Watch FPS during a flood on the demo machine (target 60).
