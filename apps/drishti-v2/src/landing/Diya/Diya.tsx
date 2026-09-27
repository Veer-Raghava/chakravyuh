import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { teardropGeometry } from "../../three/diyaGeometry";

/**
 * The diya — the guide (§2). An abstract matte-clay flame: no face, no robot,
 * never photoreal (that's the uncanny valley we avoid). A diya is how you see
 * in the dark — the whole product, in one small warm object. It drifts by the
 * lens and glows once; its words live in the DOM (DiyaHint), not here.
 *
 * ponytail: procedural teardrop + emissive glow, no matcap/HDRI (none vendored,
 * offline). Swap for a Draco .glb + warm-clay matcap when assets land.
 */
export function Diya({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const geom = useRef(teardropGeometry());
  // Keep the diya just inside the right edge on any aspect (off-screen on
  // portrait phones otherwise, where its hint would float unanchored).
  const vw = useThree((s) => s.viewport.width);
  const x = Math.min(2.4, vw / 2 - 0.85);

  useFrame((state) => {
    if (!group.current || reduced) return;
    const t = state.clock.elapsedTime;
    group.current.position.y = 0.15 + Math.sin(t * 0.8) * 0.06; // gentle float
    group.current.rotation.z = Math.sin(t * 0.5) * 0.05;
  });

  return (
    <group ref={group} position={[x, 0.15, 0.6]} scale={0.32}>
      {/* warm glow the flame casts on the paper */}
      <pointLight color={C.butter} intensity={2.2} distance={4} decay={2} position={[0, 0.4, 0.2]} />
      <mesh geometry={geom.current} position={[0, -0.4, 0]}>
        <meshStandardMaterial
          color={C.butter}
          emissive={C.coral}
          emissiveIntensity={0.6}
          roughness={0.5}
          metalness={0}
        />
      </mesh>
    </group>
  );
}
