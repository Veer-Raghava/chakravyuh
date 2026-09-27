import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { MazeSwirl } from "./MazeSwirl";
import { OrderedLattice } from "./OrderedLattice";
import { Lens } from "./Lens";
import { useScroll } from "../../scroll/ScrollContext";

/**
 * The hero visuals (§7.HERO) — lens, maze swirl, ordered lattice. Lights,
 * background and shadows now live in the director (LandingScenes) so every
 * station shares them; this component is just the hero group, which the director
 * hands off to MAYAJAAL.
 *
 * The lens (the ONE transmission glass) recedes INTO the world — shrinking and
 * dollying back — as MAYAJAAL's globe forms, and is fully culled before KAVACH
 * (slice starts 0.12) so the glass sphere never overlaps the sealed-intake beat.
 * Culling it also frees the transmission buffer (the one expensive render) so
 * every later station holds 60fps.
 *
 * The 3D diya flame is gone (removed by request); the diya *guidance* now lives
 * only as the small italic per-station line in the DOM copy. `diyaOn` is still
 * accepted (App passes it) but no longer renders anything here.
 */
export function HeroScene({
  reduced,
}: {
  reduced: boolean;
  diyaOn?: boolean;
}) {
  const visuals = useRef<THREE.Group>(null);
  const { progress } = useScroll();

  useFrame(() => {
    const p = progress.current ?? 0;
    // recede the hero visuals into the maze as MAYAJAAL rises; gone by 0.10,
    // clear of KAVACH (0.12). Position-driven, so reduced-motion needs no branch.
    const out = THREE.MathUtils.clamp((p - 0.03) / 0.07, 0, 1); // 0 @0.03 → 1 @0.10
    const v = visuals.current;
    if (v) {
      v.visible = out < 1; // frees the transmission buffer past the handoff
      v.scale.setScalar(1 - out * 0.72); // shrink toward ~0.28 as it leaves
      v.position.z = -out * 2.4; // dolly back into the world
    }
  });

  return (
    <group ref={visuals}>
      <MazeSwirl reduced={reduced} />
      <OrderedLattice reduced={reduced} />
      <Lens reduced={reduced} />
    </group>
  );
}
