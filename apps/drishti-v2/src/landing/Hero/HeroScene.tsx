import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { MazeSwirl } from "./MazeSwirl";
import { OrderedLattice } from "./OrderedLattice";
import { Lens } from "./Lens";
import { Diya } from "../Diya/Diya";
import { useScroll } from "../../scroll/ScrollContext";

/**
 * The hero visuals (§7.HERO) — lens, maze swirl, ordered lattice, diya. Lights,
 * background and shadows now live in the director (LandingScenes) so every
 * station shares them; this component is just the hero group, which the director
 * hands off to MAYAJAAL. Past the top it hides itself entirely (frees the lens's
 * transmission buffer — the one expensive render) so later stations stay at 60fps.
 */
export function HeroScene({
  reduced,
  diyaOn,
}: {
  reduced: boolean;
  diyaOn: boolean;
}) {
  const group = useRef<THREE.Group>(null);
  const { progress } = useScroll();

  useFrame(() => {
    const g = group.current;
    if (!g) return;
    // hero owns only the very top; MAYAJAAL takes over as we descend into the maze
    g.visible = (progress.current ?? 0) < 0.22;
  });

  return (
    <group ref={group}>
      <MazeSwirl reduced={reduced} />
      <OrderedLattice reduced={reduced} />
      <Lens reduced={reduced} />
      {diyaOn ? <Diya reduced={reduced} /> : null}
    </group>
  );
}
