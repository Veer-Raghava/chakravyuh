import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";

/**
 * ST.2 SETU — untangling network from money (§7). A sealed blue block splits
 * like a bridge opening: money (coral) streams left, network (blue) streams
 * right, a small clay bridge between them. The ★ moment: the column labelled
 * "src_ip" floats up and re-labels itself to "the IP that told us," a
 * strike-through crossing the wrong reading. The site's cleverest twelve words,
 * made physical — a relay can never again be mistaken for a sender (§6).
 */
const SLICE = STATIONS[2].slice;
const N = 12;

export function Setu({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const left = useRef<THREE.Mesh>(null);
  const right = useRef<THREE.Mesh>(null);
  const money = useRef<THREE.InstancedMesh>(null);
  const net = useRef<THREE.InstancedMesh>(null);
  const oldLabel = useRef<HTMLSpanElement>(null);
  const newLabel = useRef<HTMLSpanElement>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const mats = useMemo(
    () => ({
      money: new THREE.MeshBasicMaterial({ color: C.coral, transparent: true }),
      net: new THREE.MeshBasicMaterial({ color: C.risoBlue, transparent: true }),
      halfL: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.85, transparent: true }),
      halfR: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.85, transparent: true }),
    }),
    [],
  );

  useFrame((state) => {
    const g = group.current;
    if (!g) return;
    const p = progress.current ?? 0;
    const { t, vis } = local(p, SLICE);
    g.visible = vis > 0.01;
    // mount the DOM labels only while on-slice (drei <Html> stays in the DOM
    // even when its 3D parent is hidden, so gate it explicitly)
    const on = vis > 0.02;
    if (on !== activeRef.current) {
      activeRef.current = on;
      setActive(on);
    }
    if (!g.visible) return;
    const time = reduced ? 2 : state.clock.elapsedTime;

    const sep = THREE.MathUtils.smoothstep(t, 0, 0.6) * 0.95;
    if (left.current) left.current.position.x = -0.35 - sep;
    if (right.current) right.current.position.x = 0.35 + sep;

    mats.money.opacity = vis * 0.9;
    mats.net.opacity = vis * 0.9;
    // the two halves arrive ALREADY SOLID (they are KAVACH's risen blocks handed
    // straight in) — full opacity from t=0, fading only as the station ends. This
    // keeps the Kavach→Setu handoff seamless: no cross-fade dip at the boundary.
    const solid = reduced ? 1 : 1 - THREE.MathUtils.smoothstep(t, 0.86, 1.0);
    mats.halfL.opacity = solid;
    mats.halfR.opacity = solid;

    // token streams drift outward from the split
    if (money.current) {
      for (let i = 0; i < N; i++) {
        const d = (time * 0.35 + i * 0.25) % 2.2;
        dummy.position.set(-0.9 - sep - d, -0.6 + (i % 4) * 0.35, 0.05);
        dummy.scale.set(0.28, 0.09, 0.05);
        dummy.updateMatrix();
        money.current.setMatrixAt(i, dummy.matrix);
      }
      money.current.instanceMatrix.needsUpdate = true;
    }
    if (net.current) {
      for (let i = 0; i < N; i++) {
        const d = (time * 0.35 + i * 0.25) % 2.2;
        dummy.position.set(0.9 + sep + d, -0.6 + (i % 4) * 0.35, 0.05);
        dummy.scale.set(0.28, 0.09, 0.05);
        dummy.updateMatrix();
        net.current.setMatrixAt(i, dummy.matrix);
      }
      net.current.instanceMatrix.needsUpdate = true;
    }

    // ★ the rename — src_ip struck through, "the IP that told us" rising
    const kflip = reduced ? 1 : THREE.MathUtils.clamp((t - 0.4) / 0.2, 0, 1);
    if (oldLabel.current) {
      oldLabel.current.style.opacity = String((1 - 0.72 * kflip) * vis);
      oldLabel.current.style.textDecoration = kflip > 0.3 ? "line-through" : "none";
    }
    if (newLabel.current) newLabel.current.style.opacity = String(kflip * vis);
  });

  return (
    <group ref={group} visible={false}>
      {/* the two halves of the split block */}
      <mesh ref={left} material={mats.halfL} position={[-0.35, 0, 0]}>
        <boxGeometry args={[0.7, 1.1, 0.4]} />
      </mesh>
      <mesh ref={right} material={mats.halfR} position={[0.35, 0, 0]}>
        <boxGeometry args={[0.7, 1.1, 0.4]} />
      </mesh>
      {/* small clay bridge (Ram Setu) spanning the gap */}
      <mesh position={[0, -0.65, 0]}>
        <boxGeometry args={[1.2, 0.12, 0.5]} />
        <meshStandardMaterial color={C.paperDeep} roughness={0.95} />
      </mesh>

      <instancedMesh ref={money} args={[undefined, undefined, N]} material={mats.money}>
        <planeGeometry args={[1, 1]} />
      </instancedMesh>
      <instancedMesh ref={net} args={[undefined, undefined, N]} material={mats.net}>
        <planeGeometry args={[1, 1]} />
      </instancedMesh>

      {/* ★ the rename moment — DOM text, screen-reachable */}
      {active && (
        <Html position={[0, 1.15, 0]} center distanceFactor={6} pointerEvents="none">
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "13px",
              whiteSpace: "nowrap",
              textAlign: "center",
              letterSpacing: "0.02em",
            }}
          >
            <span ref={oldLabel} style={{ color: "var(--ink-soft)" }}>
              src_ip
            </span>
            <span
              ref={newLabel}
              style={{
                color: "var(--riso-blue)",
                fontWeight: 600,
                opacity: 0,
                marginLeft: 8,
              }}
            >
              the IP that told us
            </span>
          </div>
        </Html>
      )}
    </group>
  );
}
