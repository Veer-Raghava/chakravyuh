import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.5 BUDDHI — how risky is this (§7). Clusters from the graph float up and are
 * "weighed" on a warm clay balance-scale: the flagged side (coral) sinks, but
 * the scale never hides the other pan. Each cluster's risk tints it — coral high
 * / butter mid / blue low.
 *
 * The ★ moment is the pairing: every "why flagged" factor (real SHAP weights,
 * plain words) shows at the SAME instant as a muted-teal "why it might be
 * innocent." The same shape that looks like laundering also fits a merchant
 * settling daily — you see both at once (§6). No global accuracy number anywhere.
 */
const SLICE = STATIONS[5].slice;
const NC = 5;

// real SHAP weights from the alert fixture, given plain-language factor names.
const FLAGGED = fixtures.alert.features.slice(0, 3).map((f, i) => ({
  label: ["high fee per vByte", "large amount sent", "wide origin lead"][i],
  weight: f.weight,
}));
const INNOCENT = [
  "also fits a merchant settling daily",
  "one address, linked to nothing else",
  "that relay serves 31 other subjects",
];
const RISK = [C.coral, C.coral, C.butter, C.risoBlue, C.risoBlue];

export function Buddhi({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const beam = useRef<THREE.Group>(null);
  const clusters = useRef<THREE.InstancedMesh>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const colored = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const mats = useMemo(
    () => ({
      clay: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.95 }),
      panL: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.7, transparent: true }),
      panR: new THREE.MeshStandardMaterial({ color: C.teal, roughness: 0.7, transparent: true }),
      cluster: new THREE.MeshStandardMaterial({ color: "#ffffff", roughness: 0.55, transparent: true }),
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
    const time = reduced ? 3 : state.clock.elapsedTime;

    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.5);
    // clusters descend onto the flagged pan, each tinted by its risk
    if (clusters.current) {
      if (!colored.current) {
        for (let i = 0; i < NC; i++) clusters.current.setColorAt(i, new THREE.Color(RISK[i]));
        if (clusters.current.instanceColor) clusters.current.instanceColor.needsUpdate = true;
        colored.current = true;
      }
      for (let i = 0; i < NC; i++) {
        const rx = -1.15 + (i % 2) * 0.3;
        const ry = -0.1 + Math.floor(i / 2) * 0.3;
        const drop = (1 - a) * 2.2;
        const bob = reduced ? 0 : Math.sin(time * 1.2 + i) * 0.04;
        dummy.position.set(rx, ry + drop + bob, (i % 3) * 0.12 - 0.1);
        dummy.scale.setScalar((0.16 + (i === 0 ? 0.05 : 0)) * (0.3 + 0.7 * a));
        dummy.updateMatrix();
        clusters.current.setMatrixAt(i, dummy.matrix);
      }
      clusters.current.instanceMatrix.needsUpdate = true;
    }
    mats.cluster.opacity = vis;
    mats.panL.opacity = vis;
    mats.panR.opacity = vis;

    // the beam tilts toward the flagged (coral) side as the weight lands
    const tilt = reduced ? -0.16 : -0.2 * THREE.MathUtils.smoothstep(t, 0.1, 0.6);
    if (beam.current) beam.current.rotation.z = tilt;
  });

  return (
    <group ref={group} visible={false} position={[0, 0.3, 0]}>
      {/* the fulcrum — a warm clay wedge */}
      <mesh position={[0, -0.75, 0]} material={mats.clay}>
        <coneGeometry args={[0.5, 1.0, 4]} />
      </mesh>
      {/* the beam + two pans, pivoting on the fulcrum */}
      <group ref={beam} position={[0, -0.1, 0]}>
        <mesh material={mats.clay}>
          <boxGeometry args={[2.6, 0.1, 0.16]} />
        </mesh>
        <mesh position={[-1.15, -0.42, 0]} material={mats.panL}>
          <cylinderGeometry args={[0.5, 0.5, 0.08, 28]} />
        </mesh>
        <mesh position={[1.15, -0.42, 0]} material={mats.panR}>
          <cylinderGeometry args={[0.5, 0.5, 0.08, 28]} />
        </mesh>
      </group>
      {/* clusters being weighed — risk-tinted (instanceColor) */}
      <instancedMesh ref={clusters} args={[undefined, undefined, NC]} material={mats.cluster}>
        <sphereGeometry args={[1, 16, 16]} />
      </instancedMesh>

      {active && (
        <>
          {/* ★ why flagged — real weights, plain words (coral pan) */}
          <Html position={[-1.7, 1.15, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", width: 172, textAlign: "left", lineHeight: 1.6 }}>
              <div style={{ color: "var(--coral)", fontWeight: 600, letterSpacing: "0.06em", marginBottom: 3 }}>
                WHY FLAGGED
              </div>
              {FLAGGED.map((f) => (
                <div key={f.label} style={{ color: "var(--ink)", display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span>{f.label}</span>
                  <span style={{ color: "var(--coral)" }}>+{f.weight.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </Html>
          {/* ★ why it might be innocent — shown at the same moment (teal pan) */}
          <Html position={[1.7, 1.15, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", width: 172, textAlign: "left", lineHeight: 1.6 }}>
              <div style={{ color: "var(--teal)", fontWeight: 600, letterSpacing: "0.06em", marginBottom: 3 }}>
                WHY IT MIGHT BE INNOCENT
              </div>
              {INNOCENT.map((c) => (
                <div key={c} style={{ color: "var(--teal)" }}>
                  · {c}
                </div>
              ))}
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
