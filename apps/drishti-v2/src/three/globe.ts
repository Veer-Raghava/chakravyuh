import * as THREE from "three";

/**
 * Globe helpers for ST.0 MAYAJAAL — the stylized Earth of peer nodes (§1–4 of
 * MAYAJAAL-GLOBE-BUILD-PLAN.md). Pure, allocation-light, offline-safe: no binary
 * asset is required. If `src/assets/land-mask.png` is committed, the caller
 * samples it via `loadLandMaskSampler`; otherwise `proceduralIsLand` synthesizes
 * organic continents so the build and demo never hard-fail. Mirrors the
 * "procedural, swap-later" spirit of diyaGeometry.ts.
 */

/** Deterministic PRNG (seed 42 theme) so the scatter cloud is reproducible. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const GOLDEN = Math.PI * (3 - Math.sqrt(5));

/** Unit direction for point `i` of `n` on a fibonacci sphere (even coverage). */
export function fibonacciSphereDir(i: number, n: number, out: THREE.Vector3): THREE.Vector3 {
  const y = 1 - (i / (n - 1)) * 2; // 1 → -1
  const r = Math.sqrt(Math.max(0, 1 - y * y));
  const theta = GOLDEN * i;
  return out.set(Math.cos(theta) * r, y, Math.sin(theta) * r);
}

/** lat/lon (degrees) → position on a sphere of the given radius. */
export function latLonToVec3(latDeg: number, lonDeg: number, radius: number, out: THREE.Vector3): THREE.Vector3 {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;
  const cl = Math.cos(lat);
  return out.set(radius * cl * Math.cos(lon), radius * Math.sin(lat), radius * cl * Math.sin(lon));
}

// module-scope scratch — greatCircleArc runs per gossip pulse, never allocates.
const _va = new THREE.Vector3();
const _vb = new THREE.Vector3();
const _vp = new THREE.Vector3();

/**
 * Great-circle arc between two unit directions `a`,`b`, arching above the
 * surface: `segments+1` points written into `out` from `offset`. Each point is
 * a slerp of a→b pushed to `radius + lift·sin(π·u)` — hugs the sphere, bulges
 * at the midpoint. Falls back to a normalized lerp when a≈b or antipodal.
 */
export function greatCircleArc(
  a: THREE.Vector3,
  b: THREE.Vector3,
  segments: number,
  radius: number,
  lift: number,
  out: Float32Array,
  offset = 0,
): void {
  _va.copy(a).normalize();
  _vb.copy(b).normalize();
  const dot = THREE.MathUtils.clamp(_va.dot(_vb), -1, 1);
  const omega = Math.acos(dot);
  const so = Math.sin(omega);
  for (let i = 0; i <= segments; i++) {
    const u = i / segments;
    if (so < 1e-4) {
      _vp.copy(_va).lerp(_vb, u).normalize();
    } else {
      const s0 = Math.sin((1 - u) * omega) / so;
      const s1 = Math.sin(u * omega) / so;
      _vp.set(_va.x * s0 + _vb.x * s1, _va.y * s0 + _vb.y * s1, _va.z * s0 + _vb.z * s1);
    }
    const r = radius + lift * Math.sin(u * Math.PI);
    const o = (offset + i) * 3;
    out[o] = _vp.x * r;
    out[o + 1] = _vp.y * r;
    out[o + 2] = _vp.z * r;
  }
}

/** Soft round sprite for the peer nodes — no hard square points, no asset. */
export function makeDotTexture(size = 64): THREE.CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d")!;
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.45, "rgba(255,255,255,0.9)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

// --- procedural continents (fallback when no land-mask.png is committed) -----

function hash3(i: number, j: number, k: number): number {
  // integer bit-mangle (no Math.sin) — fast enough to paint a texture per pixel.
  let n = (Math.imul(i, 374761393) + Math.imul(j, 668265263) + Math.imul(k, 1274126177)) | 0;
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  n ^= n >>> 16;
  return (n >>> 0) / 4294967296; // 0..1
}
function smoother(t: number): number {
  return t * t * t * (t * (t * 6 - 15) + 10);
}
function valueNoise3(x: number, y: number, z: number): number {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const xf = x - xi, yf = y - yi, zf = z - zi;
  const u = smoother(xf), v = smoother(yf), w = smoother(zf);
  const c000 = hash3(xi, yi, zi), c100 = hash3(xi + 1, yi, zi);
  const c010 = hash3(xi, yi + 1, zi), c110 = hash3(xi + 1, yi + 1, zi);
  const c001 = hash3(xi, yi, zi + 1), c101 = hash3(xi + 1, yi, zi + 1);
  const c011 = hash3(xi, yi + 1, zi + 1), c111 = hash3(xi + 1, yi + 1, zi + 1);
  const x00 = c000 + (c100 - c000) * u, x10 = c010 + (c110 - c010) * u;
  const x01 = c001 + (c101 - c001) * u, x11 = c011 + (c111 - c011) * u;
  const y0 = x00 + (x10 - x00) * v, y1 = x01 + (x11 - x01) * v;
  return y0 + (y1 - y0) * w; // 0..1
}
function fbm(x: number, y: number, z: number): number {
  let f = 0, amp = 0.5, freq = 1;
  for (let o = 0; o < 4; o++) {
    f += amp * valueNoise3(x * freq, y * freq, z * freq);
    freq *= 2;
    amp *= 0.5;
  }
  return f; // ~0..0.94
}

export type LandSampler = (dir: THREE.Vector3) => boolean;

// Approximate continent lobes (center lat/lon in degrees; rlat/rlon are angular
// half-extents). Not survey-accurate — a *stylized* Earth (the locked "Stylized
// Earth" decision), recognizable by where the landmasses sit: Americas left,
// Africa/Europe center, Asia right, Australia low-right, Antarctica capping the
// south. Committing src/assets/land-mask.png swaps this for the real thing.
type Lobe = { lat: number; lon: number; rlat: number; rlon: number };
const LOBES: Lobe[] = [
  { lat: 46, lon: -100, rlat: 26, rlon: 32 }, // North America
  { lat: 63, lon: -95, rlat: 15, rlon: 42 }, //  northern Canada spread
  { lat: -20, lon: -60, rlat: 30, rlon: 15 }, // South America
  { lat: 10, lon: 18, rlat: 22, rlon: 19 }, //   Africa (north)
  { lat: -18, lon: 25, rlat: 20, rlon: 16 }, //  Africa (south)
  { lat: 52, lon: 22, rlat: 12, rlon: 27 }, //   Europe
  { lat: 52, lon: 95, rlat: 28, rlon: 47 }, //   Asia
  { lat: 22, lon: 80, rlat: 14, rlon: 12 }, //   India
  { lat: -25, lon: 134, rlat: 12, rlon: 18 }, // Australia
  { lat: 72, lon: -42, rlat: 11, rlon: 19 }, //  Greenland
];

/**
 * Stylized continents: union of elliptical lobes with noise-roughened coasts, so
 * the globe reads as Earth (right landmasses, ragged shores, a few islands) with
 * no binary asset. ~30% coverage. Antarctica is a solid southern cap.
 */
export const proceduralIsLand: LandSampler = (dir) => {
  const len = Math.hypot(dir.x, dir.y, dir.z) || 1;
  const lat = (Math.asin(THREE.MathUtils.clamp(dir.y / len, -1, 1)) * 180) / Math.PI;
  if (lat < -72) return true; // Antarctica cap
  const lon = (Math.atan2(dir.z, dir.x) * 180) / Math.PI;
  let best = Infinity;
  for (const L of LOBES) {
    let dlon = lon - L.lon;
    dlon = ((dlon + 540) % 360) - 180; // wrap to -180..180
    const nx = dlon / L.rlon;
    const ny = (lat - L.lat) / L.rlat;
    const d = nx * nx + ny * ny;
    if (d < best) best = d;
  }
  const wob = (fbm(dir.x * 2.4 + 5, dir.y * 2.4 + 9, dir.z * 2.4 + 2) - 0.47) * 1.25;
  return best < 1 + wob;
};

/** Equirectangular UV for a direction — the land canvas and the sphere share this
 *  exact map so painted continents line up with the peer nodes. */
export function dirToUV(x: number, y: number, z: number): [number, number] {
  const len = Math.hypot(x, y, z) || 1;
  const lat = Math.asin(THREE.MathUtils.clamp(y / len, -1, 1)); // -π/2..π/2
  const lon = Math.atan2(z, x); // -π..π
  return [lon / (2 * Math.PI) + 0.5, 0.5 - lat / Math.PI];
}

/** Rewrite a sphere's UVs to the equirectangular map `dirToUV` uses, so a canvas
 *  painted by `buildLandCanvas` wraps the sphere aligned with the nodes. */
export function assignEquirectUV(geo: THREE.BufferGeometry): void {
  const pos = geo.attributes.position;
  const uv = new Float32Array(pos.count * 2);
  for (let i = 0; i < pos.count; i++) {
    const [u, v] = dirToUV(pos.getX(i), pos.getY(i), pos.getZ(i));
    uv[i * 2] = u;
    uv[i * 2 + 1] = v;
  }
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
}

/**
 * Paint an equirectangular stylized-Earth texture from an `isLand` predicate:
 * ocean fill, land fill lightly shaded by noise so continents aren't flat. Use
 * `tex.flipY = false` on the resulting CanvasTexture — row 0 is the north pole.
 */
export function buildLandCanvas(
  isLand: LandSampler,
  w: number,
  h: number,
  ocean: [number, number, number],
  land: [number, number, number],
): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  const img = ctx.createImageData(w, h);
  const data = img.data;
  const dir = new THREE.Vector3();
  for (let j = 0; j < h; j++) {
    const lat = (0.5 - (j + 0.5) / h) * Math.PI; // +π/2 north → -π/2 south
    const cl = Math.cos(lat);
    const sl = Math.sin(lat);
    for (let i = 0; i < w; i++) {
      const lon = ((i + 0.5) / w - 0.5) * 2 * Math.PI;
      dir.set(cl * Math.cos(lon), sl, cl * Math.sin(lon));
      const o = (j * w + i) * 4;
      if (isLand(dir)) {
        const s = 0.86 + 0.14 * fbm(dir.x * 6 + 1, dir.y * 6 + 4, dir.z * 6 + 7);
        data[o] = land[0] * s;
        data[o + 1] = land[1] * s;
        data[o + 2] = land[2] * s;
      } else {
        data[o] = ocean[0];
        data[o + 1] = ocean[1];
        data[o + 2] = ocean[2];
      }
      data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return canvas;
}

/**
 * Sample a committed equirectangular land mask (convention: land = light,
 * ocean = dark — MAYAJAAL-GLOBE-BUILD-PLAN.md §2). Draws once to an offscreen
 * canvas and returns a per-direction `isLand`. Resolves to `null` on any
 * failure so the caller keeps the procedural fallback (never hard-fails).
 */
export function loadLandMaskSampler(url: string): Promise<LandSampler | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const w = img.width, h = img.height;
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return resolve(null);
        ctx.drawImage(img, 0, 0);
        const data = ctx.getImageData(0, 0, w, h).data;
        resolve((dir) => {
          const lat = Math.asin(THREE.MathUtils.clamp(dir.y, -1, 1)); // -π/2..π/2
          const lon = Math.atan2(dir.z, dir.x); // -π..π
          let u = lon / (2 * Math.PI) + 0.5;
          const v = THREE.MathUtils.clamp(0.5 - lat / Math.PI, 0, 1);
          u -= Math.floor(u);
          const px = Math.min(w - 1, (u * w) | 0);
          const py = Math.min(h - 1, (v * h) | 0);
          const idx = (py * w + px) * 4;
          return (data[idx] + data[idx + 1] + data[idx + 2]) / 3 >= 128;
        });
      } catch {
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = url;
  });
}
