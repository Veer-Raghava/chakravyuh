import { ContactShadows } from "@react-three/drei";
import { C } from "../styles/palette";
import { HeroScene } from "./Hero/HeroScene";
import { Mayajaal } from "./stations/Mayajaal";
import { Kavach } from "./stations/Kavach";
import { Setu } from "./stations/Setu";
import { Jaal } from "./stations/Jaal";
import { Shastra } from "./stations/Shastra";
import { Buddhi } from "./stations/Buddhi";
import { Vaani } from "./stations/Vaani";
import { Pramaan } from "./stations/Pramaan";

/**
 * The landing director (§7). One continuous fixed-stage space: the hero hands
 * off to the eight pipeline stations, each owning a scroll slice (see
 * stations.ts) and rising into focus / resolving / dissolving as the next
 * rises — no hard cuts. Lights, background and shadows are shared here so every
 * station is lit the same "warm paper diorama" way (§4.3); no HDRI (offline).
 */
export function LandingScenes({
  reduced,
  diyaOn,
}: {
  reduced: boolean;
  diyaOn: boolean;
}) {
  return (
    <>
      <color attach="background" args={[C.paper]} />
      <hemisphereLight args={[C.paper, C.ink, 0.9]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[3, 4, 5]} intensity={1.1} color="#fff6e8" />

      <HeroScene reduced={reduced} diyaOn={diyaOn} />
      <Mayajaal reduced={reduced} />
      <Kavach reduced={reduced} />
      <Setu reduced={reduced} />
      <Jaal reduced={reduced} />
      <Shastra reduced={reduced} />
      <Buddhi reduced={reduced} />
      <Vaani reduced={reduced} />
      <Pramaan reduced={reduced} />

      <ContactShadows
        position={[0, -1.9, 0]}
        opacity={0.28}
        scale={12}
        blur={2.6}
        far={5}
        color={C.ink}
      />
    </>
  );
}
