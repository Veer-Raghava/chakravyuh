import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";

/**
 * Order, resolved — the SAME scattered signal field, but connected (§7.HERO).
 * Behind the clear lens the coral noise resolves into an organic ordered
 * NETWORK: nodes on a jittered triangular lattice, wired to their neighbours.
 * Not rings, not a target, not a grid — a settled connection map, the product's
 * whole thesis in one image: the eye that makes the maze legible.
 *
 * Sits just behind the lens so refraction magnifies it. On scroll the network
 * tightens a touch as the coral noise fades — clarity completing, no camera move.
 */
const R = 0.86; // fits inside the lens rim
const STEP = 0.15;

function buildNetwork() {
  // Jittered triangular lattice inside a disc — ordered but organic, never a grid.
  const nodes: [number, number][] = [];
  let row = 0;
  for (let y = -R; y <= R; y += STEP * 0.866) {
    const offset = (row % 2) * (STEP / 2);
    for (let x = -R; x <= R; x += STEP) {
      const px = x + offset;
      // deterministic organic jitter so the lattice breathes, stays reproducible
      const jx = Math.sin(px * 12.9 + y * 7.1) * STEP * 0.24;
      const jy = Math.cos(px * 7.7 + y * 11.3) * STEP * 0.24;
      const nx = px + jx;
      const ny = y + jy;
      if (nx * nx + ny * ny <= R * R) nodes.push([nx, ny]);
    }
    row++;
  }

  // Wire each node to nearby neighbours → a triangulated web.
  // ponytail: O(n²) neighbour scan, fine at ~120 nodes / build-time only.
  const linkDist = STEP * 1.55;
  const segs: number[] = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i][0] - nodes[j][0];
      const dy = nodes[i][1] - nodes[j][1];
      if (dx * dx + dy * dy <= linkDist * linkDist) {
        segs.push(nodes[i][0], nodes[i][1], 0, nodes[j][0], nodes[j][1], 0);
      }
    }
  }

  const pts = new Float32Array(nodes.length * 3);
  nodes.forEach(([x, y], i) => {
    pts[i * 3] = x;
    pts[i * 3 + 1] = y;
    pts[i * 3 + 2] = 0;
  });
  return { points: pts, lines: new Float32Array(segs) };
}

export function OrderedLattice({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const { progress } = useScroll();
  const { points, lines } = useMemo(buildNetwork, []);

  useFrame((_, delta) => {
    const g = group.current;
    if (!g) return;
    if (!reduced) g.rotation.z -= delta * 0.02; // slow, calm
    const p = progress.current ?? 0;
    const settle = reduced ? 0 : Math.min(p / 0.5, 1);
    const s = 1 - settle * 0.08; // tighten slightly as noise clears
    g.scale.set(s, s, 1);
  });

  return (
    <group ref={group} position={[0, 0, -0.7]}>
      {/* connections — the "structured, connected" read */}
      <lineSegments>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[lines, 3]} />
        </bufferGeometry>
        <lineBasicMaterial color={C.risoBlue} transparent opacity={0.55} />
      </lineSegments>
      {/* nodes — the resolved signals */}
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[points, 3]} />
        </bufferGeometry>
        <pointsMaterial
          color={C.risoBlue}
          size={0.035}
          sizeAttenuation
          transparent
          opacity={0.95}
          depthWrite={false}
        />
      </points>
    </group>
  );
}
