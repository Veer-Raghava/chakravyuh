import * as THREE from "three";

/**
 * The diya (oil-lamp flame) as a procedural low-poly teardrop — abstract, no
 * face (§2). No binary asset, no tooling, works offline. Swap for a real
 * Draco-compressed .glb later; only this file changes when the model lands.
 * (Moved into src from public/ so Vite bundles it rather than serving raw.)
 */
export function teardropGeometry(segments = 24): THREE.LatheGeometry {
  const points: THREE.Vector2[] = [];
  const steps = 16;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps; // 0 = base center, 1 = tip
    const radius = Math.sin(t * Math.PI * 0.5) * (1 - t) * 1.6;
    const y = t * 2.2;
    points.push(new THREE.Vector2(Math.max(radius, 0.0001), y));
  }
  return new THREE.LatheGeometry(points, segments);
}
