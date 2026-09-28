# DRISHTI Console — Frontend Tech Stack

The DRISHTI web console (`apps/drishti-v2`) is a React + TypeScript single-page app
whose entire visual language is real-time WebGL rendered with three.js via React
Three Fiber, scrolled with Lenis and timed with GSAP. It is **offline-first**: no
CDNs, no HDRIs, no model files — all geometry is procedural and all fonts are
vendored locally.

_Versions below are the installed (resolved) versions; `package.json` pins caret
ranges. Last verified: 2026-09-28._

## Core stack

| Layer | Technology | Version | Role |
|---|---|---|---|
| Language | TypeScript | 5.9.3 | Strict + `noUnusedLocals` / `noUnusedParameters` / `noFallthroughCasesInSwitch`; `moduleResolution: bundler`, `jsx: react-jsx`, `noEmit` |
| UI framework | React / React DOM | 18.3.1 | Component tree, `StrictMode`, `createRoot`; DOM overlay + hosts the 3D canvas |
| Build tool | Vite | 5.4.21 | Dev server (loopback `127.0.0.1:5173`, `strictPort`), production build, native ESM |
| React plugin | @vitejs/plugin-react | 4.7.0 | Fast Refresh + JSX transform |
| 3D engine | three.js | 0.171.0 | WebGL renderer, geometry, materials, instancing |
| React ↔ three | @react-three/fiber (R3F) | 8.18.0 | Declarative three in JSX: `<Canvas>`, `useFrame`, `useThree`, pointer events |
| 3D helpers | @react-three/drei | 9.122.0 | `Html`, `ContactShadows`, `AdaptiveDpr`, `AdaptiveEvents`, `MeshTransmissionMaterial`, `Line`, `QuadraticBezierLine` |
| Smooth scroll | Lenis | 1.3.26 | Inertial scroll; one normalized `progress` 0→1 written to a ref, read in `useFrame` |
| Animation | GSAP + ScrollTrigger | 3.15.0 | Shares one clock with Lenis (`autoRaf:false`); ScrollTrigger for pinning |
| GSAP hook | @gsap/react | 2.1.2 | `useGSAP` for scoped, auto-cleaned tweens |
| Types | @types/react, @types/react-dom, @types/three | 18.3.x / 0.171.0 | Type definitions (three ships `BufferGeometryUtils.d.ts`, used offline) |

## By concern

### Build & tooling
Vite 5 with native ESM (`"type": "module"`). No Babel, Webpack, or in-app ESLint
config. npm scripts:

| Script | Command | Purpose |
|---|---|---|
| `dev` | `vite` | Dev server with HMR |
| `build` | `tsc --noEmit && vite build` | Type-check, then bundle |
| `preview` | `vite preview` | Serve the production build locally |
| `typecheck` | `tsc --noEmit` | Types only |

Two tsconfigs: the app config (`include: src`) and a `composite` node config for
`vite.config.ts`.

### Rendering architecture
A single shared, fixed `<Canvas>` (camera `[0,0,5]`, fov 45) hosts the landing
page's eight scroll "stations"; a DOM overlay (copy, counters, station text) sits
on top. Deliberately **not** using drei `<ScrollControls>` — it conflicts with
Lenis + ScrollTrigger. The post-login "workstation" screens (`src/shell/screens/*`:
Globe, Map, Graph, Lead) mount their own `<Canvas>` instances.

Scroll → animation is decoupled from React: Lenis writes a single `progress` value
to a ref on each tick; scenes read `ref.current` inside `useFrame`, so there is no
React re-render per frame.

### Styling & design system
Plain **CSS Modules** (`*.module.css`) per component — no CSS framework (no
Tailwind, no styled-components). Design tokens live in `src/styles/tokens.css` +
`global.css`; a typed palette in `src/styles/palette.ts` (the `C` object) drives
both CSS and three.js materials from one source.

### Typography
Three families, **vendored offline as `.woff2`** (no Google Fonts / CDN), declared
in `public/fonts/fonts.css`:
- **Fraunces** — display
- **Hanken Grotesk** — text / UI
- **IBM Plex Mono** — all data / numeric

### State & routing
No Redux/Zustand and no router library. App phase (`landing` / `login` / `app`) is
local `useState` plus a `#landing` hash check. Cross-cutting scroll state flows
through a ref-based `ScrollContext` (does not re-render per frame); feature state
via `ShellContext`.

## Offline-first constraint
`vite.config.ts` binds loopback only (`127.0.0.1`), and the codebase forbids CDNs,
HDRI environment maps, and model files. As a result:
- All visuals are **procedural** — geometry built in code under `src/three/*.ts`
  and textures drawn on `<canvas>`.
- Fonts are self-hosted `.woff2`.
- `mergeGeometries` comes from `three/examples/jsm/utils/BufferGeometryUtils.js`
  (bundled with three, no network).

This is why three.js + R3F + instancing carry the entire visual load, with no asset
pipeline.

## Source layout (frontend)
```
src/
  main.tsx            # entry: createRoot + ScrollProvider + App
  App.tsx             # phase router (landing / login / app)
  scroll/             # Lenis + GSAP wiring, ScrollContext, reduced-motion
  stage/              # shared <Canvas> host (Stage.tsx)
  landing/            # hero + 8 scroll stations + station copy
  shell/              # post-login workstation (screens/, drawers, Sutra)
  auth/               # login screen + fixture user
  three/              # procedural geometry & models (globe, graph, lead, …)
  styles/             # palette.ts, tokens.css, global.css
  data/               # offline fixtures / loaders
```

## Notable non-choices (deliberate)
- No `<ScrollControls>` (fights Lenis + ScrollTrigger).
- No state-management or routing libraries.
- No CSS / component framework.
- No runtime network dependencies — everything ships in the bundle + `public/`.

