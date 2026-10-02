import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.1 KAVACH — the sealed intake (§7). Read strictly TOP → BOTTOM, all in
 * frame. RAGGED raw signals (irregular size + tilt, coral — the mess of real
 * capture) fall from the top. Mid-frame they strike ONE armoured gate wearing a
 * big SHIELD crest dead-centre: at the instant each raw shape crosses the gate
 * it SEALS — flares once, snaps to a uniform rectangle, and colours to trust.
 * Below the gate the sealed rectangles stack into TWO neat vertical blocks. As
 * the station ends the two blocks RISE together into SETU's mark (left coral /
 * right blue — SETU's two halves exactly), so the cross-fade reads as KAVACH's
 * sealed output handed straight up into SETU, which then splits apart. A few
 * malformed rows peel to a "set aside" tray — held with a reason, never dropped.
 * The full SHA-256 of the raw bytes prints alongside, IN FULL (§9 / BSA 2023 §63(4)).
 */
const SLICE = STATIONS[1].slice;
const PER_COL = 5;
const COLS = 2;
const N = PER_COL * COLS; // 10 sealed chips → two vertical blocks
const BAD = 3;
const SHA = fixtures.manifest.input_sha256 as string;

const GATE_Y = 0.3; // the shield gate — dead centre of the frame
const BLOCK_Y = -1.05; // the two sealed blocks assemble low, fully in view
const SETU_Y = 0; // SETU's halves sit at y=0 — the blocks rise to meet them
const COL_X = [-0.35, 0.35]; // SETU's two half positions EXACTLY (no group offset)
const GATE_X = 0;

// deterministic per-chip randomness (no jitter frame-to-frame)
function rand(i: number, salt: number) {
  const s = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return s - Math.floor(s);
}

// a classic shield crest, extruded — the KAVACH mark, worn dead-centre on the gate
function makeShield() {
  const w = 0.16;
  const h = 0.2;
  const s = new THREE.Shape();
  s.moveTo(-w, h);
  s.lineTo(w, h);
  s.lineTo(w, -h * 0.25);
  s.quadraticCurveTo(w, -h * 0.75, 0, -h);
  s.quadraticCurveTo(-w, -h * 0.75, -w, -h * 0.25);
  s.closePath();
  return new THREE.ExtrudeGeometry(s, { depth: 0.06, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.014, bevelSegments: 1 });
}

// precomputed per-chip fall geometry (spawn high → cell in a block column)
const CHIP = Array.from({ length: N }, (_, i) => {
  const col = Math.floor(i / PER_COL);
  const row = i % PER_COL;
  const spawnX = GATE_X + (rand(i, 1) - 0.5) * 2.2;
  const spawnY = 1.85 - rand(i, 2) * 0.5; // top of frame, staggered
  const cellX = COL_X[col];
  const cellY = BLOCK_Y + (row - (PER_COL - 1) / 2) * 0.22;
  const rawSX = 0.16 + rand(i, 4) * 0.26;
  const rawSY = 0.1 + rand(i, 5) * 0.18;
  const rot = (rand(i, 3) - 0.5) * 1.5;
  const gateAt = THREE.MathUtils.clamp((spawnY - GATE_Y) / (spawnY - cellY), 0.05, 0.95); // fall-fraction at the gate
  return { col, row, spawnX, spawnY, cellX, cellY, rawSX, rawSY, rot, gateAt };
});

const rawColor = new THREE.Color(C.coral);
const sealCoral = new THREE.Color(C.coral);
const sealBlue = new THREE.Color(C.risoBlue);
const _c = new THREE.Color();

export function Kavach({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const shield = useRef<THREE.Mesh>(null);
  const flash = useRef<THREE.Mesh>(null);
  const chips = useRef<THREE.InstancedMesh>(null);
  const badChips = useRef<THREE.InstancedMesh>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const shieldGeo = useMemo(makeShield, []);
  const mats = useMemo(
    () => ({
      chip: new THREE.MeshStandardMaterial({ roughness: 0.82, transparent: true, vertexColors: false }),
      bad: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.7, transparent: true }),
      gate: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.9, transparent: true }),
      shield: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.4, metalness: 0.06, emissive: C.risoBlue, emissiveIntensity: 0 }),
      flash: new THREE.MeshBasicMaterial({ color: C.butter, transparent: true, opacity: 0 }),
    }),
    [],
  );

  useFrame((state) => {
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
    const time = reduced ? 4 : state.clock.elapsedTime;

    // sealed blocks HOLD full opacity through the rise (they do not fade with the
    // station's exit bell) so they hand off to SETU's halves with no cross-fade
    // dip — SETU pops in solid at the exact instant KAVACH hides. Seamless travel.
    mats.chip.opacity = Math.max(vis, THREE.MathUtils.smoothstep(t, 0.4, 0.6));
    mats.bad.opacity = vis * 0.9;
    mats.gate.opacity = vis;

    // the two finished blocks RISE into SETU's mark as the station ends
    const drift = reduced ? 0 : THREE.MathUtils.smoothstep(t, 0.8, 1.0);
    const driftY = drift * (SETU_Y - BLOCK_Y);
    // shield "seal pressure" tracks the main fall (peaks mid-station)
    let sealPressure = 0;

    if (chips.current) {
      for (let i = 0; i < N; i++) {
        const c = CHIP[i];
        const stagger = c.row / PER_COL; // fill bottom rows first
        const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, stagger * 0.4, 0.5 + stagger * 0.4);
        // seal happens exactly when the chip crosses the gate (monotonic in a)
        const sealed = THREE.MathUtils.smoothstep(a, c.gateAt, c.gateAt + 0.05);
        // a bright flare as it passes through the shield
        const d = (a - c.gateAt) / 0.06;
        const pop = 1 + Math.exp(-d * d) * 0.3;
        sealPressure = Math.max(sealPressure, Math.exp(-d * d));

        const x = THREE.MathUtils.lerp(c.spawnX, c.cellX, a);
        const y = THREE.MathUtils.lerp(c.spawnY, c.cellY, a) + driftY;
        dummy.position.set(x, y, THREE.MathUtils.lerp(0.06, 0, sealed));
        dummy.rotation.set(0, 0, THREE.MathUtils.lerp(c.rot, 0, sealed));
        // seal to EXACTLY one SETU half tile: 0.7 wide, 0.22 tall (×5 = 1.1), 0.4 deep
        dummy.scale.set(
          THREE.MathUtils.lerp(c.rawSX, 0.7, sealed) * pop,
          THREE.MathUtils.lerp(c.rawSY, 0.22, sealed) * pop,
          THREE.MathUtils.lerp(0.12, 0.4, sealed),
        );
        dummy.updateMatrix();
        chips.current.setMatrixAt(i, dummy.matrix);
        // left column keeps coral, right seals to trust-blue → SETU's two halves
        _c.copy(rawColor).lerp(c.col === 0 ? sealCoral : sealBlue, sealed);
        chips.current.setColorAt(i, _c);
      }
      chips.current.instanceMatrix.needsUpdate = true;
      if (chips.current.instanceColor) chips.current.instanceColor.needsUpdate = true;
    }

    // malformed rows peel from the gate to the side tray (coral, held)
    if (badChips.current) {
      for (let i = 0; i < BAD; i++) {
        const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.25 + i * 0.06, 0.6);
        dummy.position.set(THREE.MathUtils.lerp(GATE_X, 2.0, a), THREE.MathUtils.lerp(GATE_Y, -1.35 + i * 0.26, a), 0.05);
        dummy.rotation.set(0, 0, (1 - a) * 0.8 + 0.12);
        dummy.scale.set(0.4, 0.12, 0.08);
        dummy.updateMatrix();
        badChips.current.setMatrixAt(i, dummy.matrix);
      }
      badChips.current.instanceMatrix.needsUpdate = true;
    }

    // the shield glows with each seal; a butter flash-bar pulses across the gate
    if (shield.current) {
      const idle = reduced ? 0 : Math.sin(time * 0.5) * 0.08;
      shield.current.rotation.y = idle;
      shield.current.scale.setScalar(1.9 + sealPressure * 0.18);
      mats.shield.emissiveIntensity = 0.15 + sealPressure * 0.75;
    }
    if (flash.current) {
      mats.flash.opacity = sealPressure * 0.6 * vis;
      flash.current.scale.set(1, 0.5 + sealPressure * 1.4, 1);
    }
  });

  const narrow = typeof window !== "undefined" && window.innerWidth < 720;

  return (
    <group ref={group} visible={false}>
      {/* the armoured gate — warm clay slab across the middle of the flow */}
      <mesh position={[GATE_X, GATE_Y, -0.12]} material={mats.gate}>
        <boxGeometry args={[2.0, 0.32, 0.3]} />
      </mesh>
      {/* the seal flash — a butter bar that pulses across the gate as chips pass */}
      <mesh ref={flash} position={[GATE_X, GATE_Y, 0.02]} material={mats.flash}>
        <planeGeometry args={[2.0, 0.14]} />
      </mesh>
      {/* the SHIELD crest — big, dead-centre on the gate (the KAVACH mark) */}
      <mesh ref={shield} position={[GATE_X, GATE_Y, 0.18]} geometry={shieldGeo} material={mats.shield} />

      <instancedMesh ref={chips} args={[undefined, undefined, N]} material={mats.chip}>
        <boxGeometry args={[1, 1, 1]} />
      </instancedMesh>
      <instancedMesh ref={badChips} args={[undefined, undefined, BAD]} material={mats.bad}>
        <boxGeometry args={[1, 1, 1]} />
      </instancedMesh>

      {active && (
        <>
          {/* raw / locked flow labels — make the top→bottom read explicit */}
          <Html position={[-1.85, 1.55, 0.2]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", letterSpacing: "0.16em", color: "var(--coral)", whiteSpace: "nowrap" }}>RAW DATA IN</div>
          </Html>
          <Html position={[-1.85, BLOCK_Y, 0.2]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", letterSpacing: "0.16em", color: "var(--riso-blue)", whiteSpace: "nowrap" }}>LOCKED</div>
          </Html>
          <Html position={narrow ? [GATE_X, 1.95, 0.2] : [1.9, 0.55, 0.2]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", letterSpacing: "0.02em", color: "var(--ink)", textAlign: "center", opacity: 0.85, maxWidth: "min(80vw, 260px)", wordBreak: "break-all", lineHeight: 1.55 }}>
              <div style={{ color: "var(--ink-soft)", letterSpacing: "0.18em", marginBottom: 2, whiteSpace: "nowrap" }}>DATA FINGERPRINT · SHOWN IN FULL</div>
              {SHA}
            </div>
          </Html>
          <Html position={narrow ? [GATE_X, -1.7, 0.2] : [2.0, -1.35, 0.2]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--coral)", whiteSpace: "nowrap", textAlign: "center" }}>
              153 rows set aside · reason saved
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
