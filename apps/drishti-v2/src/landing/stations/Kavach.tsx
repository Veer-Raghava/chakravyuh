import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.1 KAVACH — the sealed intake (§7). Signals stream down and hit one
 * armoured clay gate with a coral wax-seal that stamps each batch (one
 * satisfying thunk). Sealed rows glow blue and pass; malformed rows peel off
 * into a "set aside" tray — held with a reason, never dropped. The full
 * SHA-256 of the raw bytes prints beneath the seal, in mono, IN FULL — the one
 * identifier we never truncate (§9 / BSA 2023 §63(4)).
 */
const SLICE = STATIONS[1].slice;
const ROWS = 22;
// real hash of the raw input bytes — authentic, printed in full (never invented,
// never truncated). "We hash the raw bytes BEFORE we read them" (§7).
const SHA = fixtures.manifest.input_sha256 as string;

export function Kavach({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const seal = useRef<THREE.Mesh>(null);
  const good = useRef<THREE.InstancedMesh>(null);
  const bad = useRef<THREE.InstancedMesh>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const mats = useMemo(
    () => ({
      good: new THREE.MeshBasicMaterial({ color: C.risoBlue, transparent: true }),
      bad: new THREE.MeshBasicMaterial({ color: C.coral, transparent: true }),
    }),
    [],
  );

  useFrame((state) => {
    const g = group.current;
    if (!g) return;
    const p = progress.current ?? 0;
    const { t, vis } = local(p, SLICE);
    g.visible = vis > 0.01;
    const on = vis > 0.02; // gate the DOM (Html) with the slice — see Setu note
    if (on !== activeRef.current) {
      activeRef.current = on;
      setActive(on);
    }
    if (!g.visible) return;
    const time = reduced ? 4 : state.clock.elapsedTime;

    // fade the whole beat with the slice bell
    mats.good.opacity = vis;
    mats.bad.opacity = vis * 0.9;

    // good rows fall through the gate on a loop; glow-blue-and-pass reads as flow
    if (good.current) {
      for (let i = 0; i < ROWS; i++) {
        const y = 2.2 - (((time * 0.6 + i * 0.32) % 3.2)); // wrap top→bottom
        dummy.position.set(-0.05 + Math.sin(i * 2.1) * 0.12, y, 0.02);
        dummy.scale.set(0.9, 0.1, 0.05);
        dummy.updateMatrix();
        good.current.setMatrixAt(i, dummy.matrix);
      }
      good.current.instanceMatrix.needsUpdate = true;
    }
    // a few malformed rows peel off to the side tray (never deleted)
    if (bad.current) {
      for (let i = 0; i < 3; i++) {
        const y = -1.1 + i * 0.22;
        dummy.position.set(1.5, y, 0.02);
        dummy.scale.set(0.55, 0.1, 0.05);
        dummy.updateMatrix();
        bad.current.setMatrixAt(i, dummy.matrix);
      }
      bad.current.instanceMatrix.needsUpdate = true;
    }

    // the seal thunk — one accent pulse as the station resolves (~t 0.3)
    if (seal.current) {
      const k = THREE.MathUtils.clamp((t - 0.28) / 0.12, 0, 1);
      const pop = reduced ? 1 : 1 + Math.sin(k * Math.PI) * 0.22;
      seal.current.scale.setScalar(pop);
    }
  });

  // narrow screens can't fit the world-pinned data labels beside the diorama;
  // lift the hash above the gate and drop the tray below it so nothing collides
  // with the bottom copy or clips off-screen. (computed on mount — resize is rare)
  const narrow = typeof window !== "undefined" && window.innerWidth < 720;

  return (
    <group ref={group} visible={false}>
      {/* the armoured gate — warm clay slab */}
      <mesh position={[0, 0, -0.1]}>
        <boxGeometry args={[2.4, 0.55, 0.35]} />
        <meshStandardMaterial color={C.paperDeep} roughness={0.9} metalness={0} />
      </mesh>
      {/* coral wax-seal — a small stamp pressed on the right end of the gate,
          clear of the falling rows (never a giant disc over the animation) */}
      <mesh ref={seal} position={[0.92, 0, 0.16]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.2, 0.22, 0.1, 40]} />
        <meshStandardMaterial color={C.coral} roughness={0.5} />
      </mesh>

      <instancedMesh ref={good} args={[undefined, undefined, ROWS]} material={mats.good}>
        <planeGeometry args={[1, 1]} />
      </instancedMesh>
      <instancedMesh ref={bad} args={[undefined, undefined, 3]} material={mats.bad}>
        <planeGeometry args={[1, 1]} />
      </instancedMesh>

      {/* full SHA-256 beneath the seal — DOM, mono, never truncated */}
      {active && (
        <>
          <Html
            position={narrow ? [0, 1.75, 0.2] : [0.55, -1.0, 0.2]}
            center
            distanceFactor={6}
            pointerEvents="none"
          >
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                letterSpacing: "0.02em",
                color: "var(--ink)",
                textAlign: "center",
                opacity: 0.85,
                // full 64-char hash: wrap instead of overflowing narrow screens
                maxWidth: "min(80vw, 280px)",
                wordBreak: "break-all",
                lineHeight: 1.55,
              }}
            >
              <div
                style={{
                  color: "var(--ink-soft)",
                  letterSpacing: "0.18em",
                  marginBottom: 2,
                  whiteSpace: "nowrap",
                }}
              >
                SHA-256 · RAW BYTES · SEALED
              </div>
              {SHA}
            </div>
          </Html>
          {/* the set-aside tray label */}
          <Html position={narrow ? [0, -2.15, 0.2] : [1.5, -1.55, 0.2]} center distanceFactor={6} pointerEvents="none">
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                color: "var(--coral)",
                whiteSpace: "nowrap",
                textAlign: "center",
              }}
            >
              153 set aside · reason: malformed
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
