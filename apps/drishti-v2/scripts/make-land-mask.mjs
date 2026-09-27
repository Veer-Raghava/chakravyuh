#!/usr/bin/env node
// make-land-mask.mjs — turn real coastline data into the equirectangular land
// mask MAYAJAAL's globe reads. Zero dependencies (Node 18+ built-ins only).
//
// The globe auto-upgrades from procedural continents to real ones the moment
// src/assets/land-mask.png exists (convention: land = light, ocean = dark). This
// script produces that PNG from GeoJSON coastline data — the same Natural Earth
// data globe.gl draws — so you get precise continents WITHOUT adding globe.gl,
// which ships its own WebGL canvas and fetches at runtime and so can't share this
// page's one scroll-driven R3F stage.
//
// Run it where you HAVE network (this repo's sandbox blocks fetch), from the
// apps/drishti-v2 folder:
//   node scripts/make-land-mask.mjs                 # fetch 110m land, 1024x512
//   node scripts/make-land-mask.mjs --width 2048 --height 1024
//   node scripts/make-land-mask.mjs --src ./ne_50m_land.json   # a local file
// Then commit src/assets/land-mask.png and reload — the globe swaps itself.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { deflateSync } from "node:zlib";

const DEFAULT_SRC =
  "https://raw.githubusercontent.com/martynafford/natural-earth-geojson/master/110m/physical/ne_110m_land.json";

const arg = (name, fb) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fb;
};

const SRC = arg("src", DEFAULT_SRC);
const W = parseInt(arg("width", "1024"), 10);
const H = parseInt(arg("height", "512"), 10);
const OUT = resolve(arg("out", "src/assets/land-mask.png"));
const LAND = 236; // light → isLand (loadLandMaskSampler thresholds at avg >= 128)
const OCEAN = 24; //  dark → ocean

async function loadGeo(src) {
  if (existsSync(src)) return JSON.parse(readFileSync(src, "utf8"));
  const res = await fetch(src); // Node 18+ global fetch
  if (!res.ok) throw new Error(`fetch ${src} -> HTTP ${res.status}`);
  return res.json();
}

// Every polygon (array of rings) from any GeoJSON shape, each with a lon/lat bbox
// for a cheap skip test. Ring = [[lon,lat], ...]; a polygon's holes ride with it.
function collectPolygons(geo) {
  const out = [];
  const bbox = (rings) => {
    let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity;
    for (const r of rings) for (const p of r) {
      if (p[0] < a) a = p[0];
      if (p[1] < b) b = p[1];
      if (p[0] > c) c = p[0];
      if (p[1] > d) d = p[1];
    }
    return [a, b, c, d];
  };
  const add = (g) => {
    if (!g) return;
    if (g.type === "Polygon") out.push({ rings: g.coordinates, bb: bbox(g.coordinates) });
    else if (g.type === "MultiPolygon") for (const p of g.coordinates) out.push({ rings: p, bb: bbox(p) });
    else if (g.type === "GeometryCollection") g.geometries.forEach(add);
  };
  if (geo.type === "FeatureCollection") geo.features.forEach((f) => add(f.geometry));
  else if (geo.type === "Feature") add(geo.geometry);
  else add(geo);
  return out;
}

// Even-odd point-in-polygon across all rings of one polygon (holes cancel out).
function inPolygon(lon, lat, rings) {
  let inside = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1];
      const xj = ring[j][0], yj = ring[j][1];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
  }
  return inside;
}

function rasterize(polys) {
  const gray = Buffer.alloc(W * H, OCEAN);
  for (let j = 0; j < H; j++) {
    const lat = 90 - ((j + 0.5) / H) * 180; // row 0 = north pole
    for (let i = 0; i < W; i++) {
      const lon = -180 + ((i + 0.5) / W) * 360;
      for (const { rings, bb } of polys) {
        if (lon < bb[0] || lon > bb[2] || lat < bb[1] || lat > bb[3]) continue;
        if (inPolygon(lon, lat, rings)) { gray[j * W + i] = LAND; break; }
      }
    }
  }
  return gray;
}

// --- minimal 8-bit grayscale PNG encoder (built-in zlib, no deps) ------------
const CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
const crc32 = (buf) => {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};
const chunk = (type, data) => {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const t = Buffer.from(type, "ascii");
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([t, data])), 0);
  return Buffer.concat([len, t, data, crc]);
};
function encodePNG(gray, w, h) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 0; // color type 0 = grayscale (10..12 = compression/filter/interlace = 0)
  const raw = Buffer.alloc(h * (w + 1)); // one filter byte (0 = none) per scanline
  for (let j = 0; j < h; j++) gray.copy(raw, j * (w + 1) + 1, j * w, j * w + w);
  const idat = deflateSync(raw);
  return Buffer.concat([sig, chunk("IHDR", ihdr), chunk("IDAT", idat), chunk("IEND", Buffer.alloc(0))]);
}

(async () => {
  try {
    const polys = collectPolygons(await loadGeo(SRC));
    if (!polys.length) throw new Error("no Polygon/MultiPolygon found in source");
    const gray = rasterize(polys);
    mkdirSync(dirname(OUT), { recursive: true });
    writeFileSync(OUT, encodePNG(gray, W, H));
    let land = 0;
    for (const v of gray) if (v > 128) land++;
    console.log(`wrote ${OUT} — ${W}x${H}, ${polys.length} polygons, ${((100 * land) / (W * H)).toFixed(1)}% land`);
  } catch (err) {
    console.error(`make-land-mask failed: ${err.message}`);
    console.error("If it was the fetch, run this on a networked machine, or pass --src ./local.geojson");
    process.exit(1);
  }
})();
