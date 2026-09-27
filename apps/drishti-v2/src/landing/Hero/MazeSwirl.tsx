import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";

/**
 * The noise — a soft scattered signal field behind the lens (§7.HERO). Not a
 * hard spiral: points fill a disc organically (uniform-area scatter) with a
 * gentle whole-field drift, so it reads as tasteful chaos, never a diagram.
 * Coral (energy/maze) fading to riso-blue (data) toward the calm centre.
 *
 * Normal alpha blending, NOT additive — additive over the near-white Paper
 * washes coral to white and kills the contrast. One draw call (§5.3).
 *
 * On scroll the whole field eases inward and dims as the camera descends —
 * a smooth settle, no per-point snapping.
 */
export function MazeSwirl({ reduced }: { reduced: boolean }) {
  const ref = useRef<THREE.Points>(null);
  const mat = useRef<THREE.PointsMaterial>(null);
  const { progress } = useScroll();
  const COUNT = 1800;

  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(COUNT * 3);
    const colors = new Float32Array(COUNT * 3);
    const coral = new THREE.Color(C.coral);
    const blue = new THREE.Color(C.risoBlue);
    for (let i = 0; i < COUNT; i++) {
      // uniform-area disc scatter — organic, not armed
      const radius = Math.sqrt(Math.random()) * 3.4;
      const angle = Math.random() * Math.PI * 2;
      // a faint shear so the field flows without becoming a spiral
      const flow = radius * 0.35;
      positions[i * 3] = Math.cos(angle + flow) * radius;
      positions[i * 3 + 1] = Math.sin(angle + flow) * radius;
      positions[i * 3 + 2] = -1.4 - Math.random() * 2.2;
      // coral noise, with only a faint blue drift near the calm centre
      const c = coral.clone().lerp(blue, Math.max(0, 0.3 - radius / 3));
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    return { positions, colors };
  }, []);

  useFrame((_, delta) => {
    const pts = ref.current;
    if (!pts) return;
    if (!reduced) pts.rotation.z += delta * 0.035; // slow, smooth drift
    const p = progress.current ?? 0;
    const settle = reduced ? 0 : Math.min(p / 0.5, 1);
    // ease inward slightly as we dolly in — stays present, never blanks out
    const s = 1 - settle * 0.12;
    pts.scale.set(s, s, 1);
    if (mat.current) mat.current.opacity = 0.42 * (1 - settle * 0.5);
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        ref={mat}
        size={0.05}
        vertexColors
        transparent
        opacity={0.42}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}
