import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";
import { panel, prose, kicker, datum } from "./panelStyle";

/**
 * ST.5 BUDDHI — how risky is this (§7). A single risk DIAL: a clean semicircular
 * gauge, blue (low) on the right through butter to coral (high) on the left. A
 * needle swings up from neutral and SETTLES into the coral arc — the reading is
 * a dial, not a verdict. Around it, the two sides show at the SAME instant:
 * "why flagged" (real SHAP weights, plain words, coral) beside "why it might be
 * innocent" (the counter-findings, teal). No global accuracy number anywhere;
 * every counter carries its honest would_clear (§6).
 */
const SLICE = STATIONS[5].slice;

// real SHAP weights from the alert fixture, given plain-language factor names.
const FLAGGED = fixtures.alert.features.slice(0, 3).map((f, i) => ({
  label: ["high fee per vByte", "large amount sent", "wide origin lead"][i],
  weight: f.weight,
}));
// the counter-findings (why it might be innocent) — with honest would_clear.
const INNOCENT = fixtures.alert.counters.slice(0, 3).map((c, i) => ({
  label: ["may be a merchant settling daily", "origin margin too thin to act on", "relay shared by 31 subjects"][i],
  wouldClear: c.would_clear,
}));
// severity → dial reading (categorical in the fixture; shown as a reading, not a %)
const READING = fixtures.alert.severity === "high" ? 0.78 : fixtures.alert.severity === "med" ? 0.5 : 0.24;
const ZONE = Math.PI / 3;

export function Buddhi({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const needle = useRef<THREE.Group>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const mats = useMemo(
    () => ({
      low: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.7, transparent: true }),
      mid: new THREE.MeshStandardMaterial({ color: C.butter, roughness: 0.7, transparent: true }),
      high: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.7, transparent: true }),
      needle: new THREE.MeshStandardMaterial({ color: C.ink, roughness: 0.6, transparent: true }),
      hub: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.9, transparent: true }),
    }),
    [],
  );

  useFrame(() => {
    const g = group.current;
    if (!g) return;
    const p = progress.current ?? 0;
    const { t, vis } = local(p, SLICE);
    g.visible = vis > 0.01;
    const on = vis > 0.02;
    if (on !== activeRef.current) {
      activeRef.current = on;
      setActive(on);
    }
    if (!g.visible) return;

    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.4);
    g.scale.setScalar(0.85 + 0.15 * a);

    // needle swings from up-neutral (π/2) to the reading angle, with a crisp
    // settle overshoot. angle: 0 = right(low) … π = left(high).
    const target = READING * Math.PI;
    const k = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.2, 0.7);
    const overshoot = reduced ? 0 : Math.sin(THREE.MathUtils.clamp((t - 0.2) / 0.5, 0, 1) * Math.PI) * 0.12;
    if (needle.current) needle.current.rotation.z = THREE.MathUtils.lerp(Math.PI / 2, target + overshoot, k);

    mats.low.opacity = vis;
    mats.mid.opacity = vis;
    mats.high.opacity = vis;
    mats.needle.opacity = vis;
    mats.hub.opacity = vis;
  });

  return (
    <group ref={group} visible={false} position={[0, 0.45, 0]}>
      {/* the gauge arc — three zones, low(blue) → mid(butter) → high(coral) */}
      <mesh rotation={[0, 0, 0]} material={mats.low}>
        <torusGeometry args={[1.35, 0.05, 10, 28, ZONE]} />
      </mesh>
      <mesh rotation={[0, 0, ZONE]} material={mats.mid}>
        <torusGeometry args={[1.35, 0.05, 10, 28, ZONE]} />
      </mesh>
      <mesh rotation={[0, 0, 2 * ZONE]} material={mats.high}>
        <torusGeometry args={[1.35, 0.05, 10, 28, ZONE]} />
      </mesh>

      {/* the needle — pivots at the hub, base at centre */}
      <group ref={needle}>
        <mesh position={[0.6, 0, 0.02]} material={mats.needle}>
          <boxGeometry args={[1.2, 0.045, 0.045]} />
        </mesh>
      </group>
      <mesh position={[0, 0, 0.04]} material={mats.hub}>
        <cylinderGeometry args={[0.12, 0.12, 0.08, 24]} />
      </mesh>

      {active && (
        <>
          {/* the reading — a dial, not a verdict */}
          <Html position={[0, -0.55, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ textAlign: "center", whiteSpace: "nowrap" }}>
              <div style={{ ...datum, color: "var(--coral)", fontWeight: 600, letterSpacing: "0.06em", fontSize: "13px" }}>
                RISK READING · {fixtures.alert.severity.toUpperCase()}
              </div>
              <div style={{ ...prose, fontSize: "11px", color: "var(--ink-soft)", marginTop: 2 }}>a dial, not a verdict · same-owner confidence 0.36 (tunable)</div>
            </div>
          </Html>

          {/* ★ why flagged — real weights, plain words (coral) */}
          <Html position={[-2.35, 1.1, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...panel, width: 182 }}>
              <div style={{ ...kicker, color: "var(--coral)" }}>WHY FLAGGED</div>
              {FLAGGED.map((f) => (
                <div key={f.label} style={{ marginTop: 5 }}>
                  <div style={{ ...datum, display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ color: "var(--ink)" }}>{f.label}</span>
                    <span style={{ color: "var(--coral)" }}>+{f.weight.toFixed(2)}</span>
                  </div>
                  {/* weight as a small coral bar — instantly legible */}
                  <div style={{ height: 3, background: "var(--line)", borderRadius: 2, marginTop: 2 }}>
                    <div style={{ height: 3, width: `${Math.min(100, (f.weight / 1.5) * 100)}%`, background: "var(--coral)", borderRadius: 2 }} />
                  </div>
                </div>
              ))}
            </div>
          </Html>

          {/* ★ why it might be innocent — shown at the same moment (teal) */}
          <Html position={[2.35, 1.1, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...panel, width: 182 }}>
              <div style={{ ...kicker, color: "var(--teal)" }}>WHY IT MIGHT BE INNOCENT</div>
              {INNOCENT.map((c) => (
                <div key={c.label} style={{ ...datum, color: "var(--teal)", lineHeight: 1.5, marginTop: 4 }}>
                  · {c.label}
                  <span style={{ color: "var(--ink-soft)", marginLeft: 4 }}>{c.wouldClear ? "· would clear" : ""}</span>
                </div>
              ))}
              <div style={{ ...prose, fontSize: "10px", color: "var(--ink-soft)", marginTop: 6 }}>
                no single doubt clears this, but every one is shown
              </div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
