import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.1 KAVACH — the sealed intake (§7). Ragged raw signals rain down in
 * irregular shapes (varied size, tilt — the mess of real capture) and hit one
 * armoured clay gate carrying a SHIELD crest. As each passes it is SEALED: it
 * snaps square, colours to trust-blue, and slots into ONE neat rectangular
 * block. A few malformed rows peel off to a "set aside" tray — held with a
 * reason, never dropped. Once assembled the sealed block eases toward SETU's
 * mark, so the cross-fade reads as the sealed block BECOMING SETU's block
 * (which then splits apart). The full SHA-256 of the raw bytes prints beneath,
 * in mono, IN FULL — the one identifier we never truncate (§9 / BSA 2023 §63(4)).
 */
const SLICE = STATIONS[1].slice;
const N = 20; // sealed chips (5 cols × 4 rows)
const COLS = 5;
const BAD = 3;
const SHA = fixtures.manifest.input_sha256 as string;

// where the assembled block ends up — SETU begins its split from ~[0.3,0.45];
// drifting here makes the KAVACH→SETU cross-fade read as one continuous block.
const HANDOFF = new THREE.Vector3(0.3, 0.45, 0);

// deterministic per-chip randomness (no jitter frame-to-frame)
function rand(i: number, salt: number) {
  const s = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return s - Math.floor(s);
}

// a classic shield crest, extruded — the KAVACH mark (replaces the old knob)
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
  return new THREE.ExtrudeGeometry(s, { depth: 0.05, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.012, bevelSegments: 1 });
}

const rawColor = new THREE.Color(C.coral);
const sealedColor = new THREE.Color(C.risoBlue);
const _c = new THREE.Color();

export function Kavach({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const shield = useRef<THREE.Mesh>(null);
  const chips = useRef<THREE.InstancedMesh>(null);
  const badChips = useRef<THREE.InstancedMesh>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const shieldGeo = useMemo(makeShield, []);
  const mats = useMemo(
    () => ({
      chip: new THREE.MeshStandardMaterial({ roughness: 0.6, transparent: true, vertexColors: false }),
      bad: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.7, transparent: true }),
      gate: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.9 }),
      shield: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.45, metalness: 0.05 }),
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

    mats.chip.opacity = vis;
    mats.bad.opacity = vis * 0.9;

    // choreographed seal: each chip eases from a ragged start above the gate to
    // its cell in the neat block; per-chip phase staggers the snap (kinetic).
    const drift = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.6, 1); // block → SETU mark
    if (chips.current) {
      for (let i = 0; i < N; i++) {
        const phase = i / N;
        const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, phase * 0.35, 0.5 + phase * 0.35);
        // ragged raw start — scattered above, tilted, uneven
        const sx = (rand(i, 1) - 0.5) * 2.6;
        const sy = 1.6 + rand(i, 2) * 1.4;
        const rot = (rand(i, 3) - 0.5) * 1.4;
        const rawScaleX = 0.16 + rand(i, 4) * 0.22;
        const rawScaleY = 0.08 + rand(i, 5) * 0.12;
        // neat sealed cell — uniform grid, forming one block
        const col = i % COLS;
        const row = Math.floor(i / COLS);
        const gx = (col - (COLS - 1) / 2) * 0.27 + HANDOFF.x * drift;
        const gy = ((3 - row) - 1.5) * 0.26 + HANDOFF.y * drift;
        dummy.position.set(
          THREE.MathUtils.lerp(sx, gx, a),
          THREE.MathUtils.lerp(sy, gy, a),
          0.04,
        );
        dummy.rotation.set(0, 0, THREE.MathUtils.lerp(rot, 0, a));
        dummy.scale.set(
          THREE.MathUtils.lerp(rawScaleX, 0.24, a),
          THREE.MathUtils.lerp(rawScaleY, 0.22, a),
          0.1,
        );
        dummy.updateMatrix();
        chips.current.setMatrixAt(i, dummy.matrix);
        _c.copy(rawColor).lerp(sealedColor, a);
        chips.current.setColorAt(i, _c);
      }
      chips.current.instanceMatrix.needsUpdate = true;
      if (chips.current.instanceColor) chips.current.instanceColor.needsUpdate = true;
    }

    // malformed rows peel to the side tray (coral, held — never deleted)
    if (badChips.current) {
      for (let i = 0; i < BAD; i++) {
        const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.2 + i * 0.05, 0.55);
        dummy.position.set(THREE.MathUtils.lerp(-0.6, 1.75, a), THREE.MathUtils.lerp(1.4, -1.15 + i * 0.24, a), 0.04);
        dummy.rotation.set(0, 0, (1 - a) * 0.8 + 0.12);
        dummy.scale.set(0.4, 0.11, 0.08);
        dummy.updateMatrix();
        badChips.current.setMatrixAt(i, dummy.matrix);
      }
      badChips.current.instanceMatrix.needsUpdate = true;
    }

    // the shield crest flares once as the batch seals (~t 0.4)
    if (shield.current) {
      const k = THREE.MathUtils.clamp((t - 0.34) / 0.14, 0, 1);
      const pop = reduced ? 1 : 1 + Math.sin(k * Math.PI) * 0.18;
      shield.current.scale.setScalar(pop);
      shield.current.rotation.y = reduced ? 0 : Math.sin(time * 0.4) * 0.12;
    }
  });

  const narrow = typeof window !== "undefined" && window.innerWidth < 720;

  return (
    <group ref={group} visible={false}>
      {/* the armoured gate — warm clay slab */}
      <mesh position={[0, 0, -0.1]} material={mats.gate}>
        <boxGeometry args={[2.4, 0.5, 0.35]} />
      </mesh>
      {/* the SHIELD crest — the KAVACH mark, on the right end of the gate */}
      <mesh ref={shield} position={[0.95, 0, 0.14]} geometry={shieldGeo} material={mats.shield} />

      <instancedMesh ref={chips} args={[undefined, undefined, N]} material={mats.chip}>
        <boxGeometry args={[1, 1, 1]} />
      </instancedMesh>
      <instancedMesh ref={badChips} args={[undefined, undefined, BAD]} material={mats.bad}>
        <boxGeometry args={[1, 1, 1]} />
      </instancedMesh>

      {active && (
        <>
          <Html position={narrow ? [0, 1.85, 0.2] : [-0.95, -1.1, 0.2]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", letterSpacing: "0.02em", color: "var(--ink)", textAlign: "center", opacity: 0.85, maxWidth: "min(80vw, 280px)", wordBreak: "break-all", lineHeight: 1.55 }}>
              <div style={{ color: "var(--ink-soft)", letterSpacing: "0.18em", marginBottom: 2, whiteSpace: "nowrap" }}>SHA-256 · RAW BYTES · SEALED</div>
              {SHA}
            </div>
          </Html>
          <Html position={narrow ? [0, -2.15, 0.2] : [1.75, -1.6, 0.2]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--coral)", whiteSpace: "nowrap", textAlign: "center" }}>
              153 set aside · reason: malformed
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
