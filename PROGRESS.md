# DRISHTI — build progress
Current milestone: M1 (scroll stage + hero lens + diya) — code written, awaiting deps + verify
Done: M0 foundation folded into M1 — Vite+React19+TS scaffold, tokens (§4), fixed-viewport
  stage (§5.2: fixed Canvas + spacer + shared scrollProgress ref via ScrollProvider),
  useSmoothScroll (Lenis autoRaf:false + gsap.ticker + ScrollTrigger married), reduced-motion hook.
Next: `npm install` (blocked in agent sandbox — network denied), then typecheck/build + /design-review.
Known issues:
  - Deps NOT installed: agent sandbox blocks registry.npmjs.org. User must run `npm install`.
  - Not yet typechecked/built/run — no verification done. Watch for drei v10 prop drift on
    MeshTransmissionMaterial (anisotropicBlur) and R3F v9 bufferAttribute typing.
  - React pinned to 19 (R3F v9 + drei v10 require it) — deviates from CLAUDE.md "React 18".
  - No matcap/HDRI vendored: diya + lights are manual meshStandardMaterial + rig, not matcap/Environment.
Fixture paths: apps/drishti-v2/src/data/fixtures/*.json (loader: src/data/loader.ts) — M1 touches none.
Demo machine: <fill in>
Last commit that ran green + offline: —
