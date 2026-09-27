import * as THREE from "three";
import { mulberry32, latLonToVec3 } from "./globe";

/**
 * Geo helpers for the app-home globe (§9). Distinct from `globe.ts` (the landing
 * MAYAJAAL scene). Everything here is offline-safe: the coastline GeoJSON is a
 * vendored local asset, positions come from a committed country-centroid table.
 *
 * HONESTY (a hard rule): the fixtures carry only `geo_country` — a country code,
 * never lat/lon. So a point's position is COUNTRY-LEVEL ONLY: the country's
 * centroid plus a small deterministic per-IP jitter so peers in one country don't
 * stack. We never claim street precision. Unlocated / Tor peers get NO centroid
 * (null) and live in the neutral off-globe "no fixed place" cluster instead.
 */

/** Country centroids (lat, lon in degrees) for the codes our fixtures use, plus a
 *  few common neighbours so a new fixture country still lands somewhere sensible.
 *  Approximate population/area centroids — country-level by design. */
export const COUNTRY_CENTROIDS: Record<string, [number, number]> = {
  IN: [22.5, 79.0],
  JP: [36.2, 138.2],
  US: [39.5, -98.35],
  DE: [51.2, 10.4],
  NL: [52.2, 5.3],
  GB: [54.0, -2.0],
  FR: [46.6, 2.4],
  SG: [1.35, 103.8],
  RU: [61.5, 105.0],
  CN: [35.9, 104.2],
  BR: [-10.3, -53.2],
  CA: [56.1, -106.3],
  AU: [-25.7, 134.5],
};

/** FNV-1a string hash → 32-bit seed. Deterministic per IP. */
function hashStr(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/**
 * Country centroid + deterministic per-IP jitter (±~3.5°) so multiple peers in the
 * same country spread into a small readable cluster instead of one stacked dot.
 * Returns null for unknown/unlocated countries — the caller keeps those off-globe.
 */
export function locate(country: string | null, ipSeed: string): { lat: number; lon: number } | null {
  if (!country) return null;
  const c = COUNTRY_CENTROIDS[country];
  if (!c) return null;
  const rnd = mulberry32(hashStr(ipSeed));
  const jLat = (rnd() - 0.5) * 7; // ±3.5°
  const jLon = (rnd() - 0.5) * 7;
  return { lat: c[0] + jLat, lon: c[1] + jLon };
}

/** A polyline of sphere positions for one coastline feature. */
export type CoastLine = Float32Array;

/**
 * Load the vendored coastline GeoJSON (LineString features, [lon,lat] pairs) and
 * project every vertex onto a sphere of `radius`. Same-origin fetch of a bundled
 * asset — works fully offline. Resolves to [] on any failure so the globe still
 * renders (sphere + points), never hard-fails.
 */
export async function loadCoastlines(url: string, radius: number): Promise<CoastLine[]> {
  try {
    const res = await fetch(url);
    if (!res.ok) return [];
    const gj = (await res.json()) as {
      features: { geometry: { type: string; coordinates: [number, number][] } }[];
    };
    const scratch = new THREE.Vector3();
    const lines: CoastLine[] = [];
    for (const f of gj.features) {
      const coords = f.geometry?.coordinates;
      if (f.geometry?.type !== "LineString" || !coords || coords.length < 2) continue;
      const arr = new Float32Array(coords.length * 3);
      for (let i = 0; i < coords.length; i++) {
        const [lon, lat] = coords[i];
        latLonToVec3(lat, lon, radius, scratch);
        arr[i * 3] = scratch.x;
        arr[i * 3 + 1] = scratch.y;
        arr[i * 3 + 2] = scratch.z;
      }
      lines.push(arr);
    }
    return lines;
  } catch {
    return [];
  }
}
