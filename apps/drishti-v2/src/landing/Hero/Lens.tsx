import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { MeshTransmissionMaterial } from "@react-three/drei";
import * as THREE from "three";
import { useScroll } from "../../scroll/ScrollContext";

/**
 * The hero lens — the eye of DRISHTI. The ONE MeshTransmissionMaterial glass
 * object on the whole site (§4.3: one hero glass max). It floats over the coral
 * maze-swirl; refraction pulls the ordered blue lattice behind it into focus,
 * so the product's whole thesis is one image: the eye that makes the maze legible.
 *
 * On first scroll the lens tips forward as the camera begins to descend into
 * the maze (§7.HERO). Reduced-motion: it sits still, already resolved.
 */
export function Lens({ reduced }: { reduced: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  const { progress } = useScroll();

  useFrame((state, delta) => {
    const m = ref.current;
    if (!m) return;
    const p = progress.current ?? 0;
    const tip = reduced ? 0 : Math.min(p / 0.5, 1); // 0→1 across the descent

    // Tip forward slightly as we dolly in — stays centred.
    m.rotation.x = THREE.MathUtils.damp(m.rotation.x, tip * 0.3, 4, delta);

    // A breathing idle drift so the glass feels alive before any scroll.
    if (!reduced) {
      const t = state.clock.elapsedTime;
      m.rotation.z = Math.sin(t * 0.15) * 0.04;
    }
  });

  return (
    <mesh ref={ref} scale={[1.15, 1.15, 0.5]}>
      <sphereGeometry args={[1, 96, 96]} />
      {/* Clear refractive glass — no frost. High thickness + ior bends and
          magnifies the ordered rings behind it; the chaos further back reads
          only around the rim. "See through" is literal (§7.HERO). */}
      <MeshTransmissionMaterial
        transmission={1}
        thickness={2.6}
        roughness={0}
        ior={1.7}
        chromaticAberration={0.03}
        anisotropicBlur={0}
        distortion={0}
        distortionScale={0}
        temporalDistortion={0}
        samples={16}
        resolution={1024}
        backside
        backsideThickness={1.1}
        attenuationDistance={8}
        attenuationColor="#ffffff"
      />
    </mesh>
  );
}
