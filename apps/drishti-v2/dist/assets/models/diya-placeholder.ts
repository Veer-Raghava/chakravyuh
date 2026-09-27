// Placeholder diya (oil-lamp flame) as a procedural low-poly teardrop.
// No binary asset, no tooling, works offline. Swap for a real Draco-compressed
// .glb in public/assets/models/ later; the app imports geometry, so only this
// file changes when the real model lands.
//
// Usage in R3F:  <mesh geometry={teardropGeometry()} material={...} />
import * as THREE from "three";

/** A flame-like teardrop: a lathe profile, pointed at top, round at the base. */
export function teardropGeometry(segments = 24): THREE.LatheGeometry {
  const points: THREE.Vector2[] = [];
  const steps = 16;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps; // 0 = base center, 1 = tip
    // radius: fat near the base (t~0.25), tapering to 0 at the tip
    const radius = Math.sin(t * Math.PI * 0.5) * (1 - t) * 1.6;
    const y = t * 2.2; // height
    points.push(new THREE.Vector2(Math.max(radius, 0.0001), y));
  }
  return new THREE.LatheGeometry(points, segments);
}
