import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.7 PRAMAAN — the court-ready proof (§7, the finish line). The single
 * surviving lead is pressed into a document: a hash-chain spine carrying the
 * FULL SHA-256 of every pipeline stage (kavach→vaani, printed in full — nothing
 * hidden, §6), the seizure tuple, the legal basis, and a one-command replay.
 *
 * A wax seal thunks down at the end — not a flourish, a claim: this is
 * reproducible and admissible. The funnel lands on 1. Not a guess. A document.
 */
const SLICE = STATIONS[7].slice;
const A = fixtures.packet.attribution;
const WHEN = A.observed_at_utc.slice(0, 19).replace("T", " ") + "Z";
// truncate the peer to two octets — no full IP ever reaches the screen (§6)
const PEER = A.peer_ip.split(".").slice(0, 2).join(".") + ".x.x";
const CHAIN = fixtures.packet.chain_of_custody.map((c) => ({ stage: c.stage, sha: c.sha256 }));

export function Pramaan({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const doc = useRef<THREE.Group>(null);
  const seal = useRef<THREE.Group>(null);
  const chainRef = useRef<HTMLDivElement>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const mats = useMemo(
    () => ({
      paper: new THREE.MeshStandardMaterial({ color: C.paper, roughness: 0.9, transparent: true }),
      rule: new THREE.MeshStandardMaterial({ color: C.line, roughness: 0.8, transparent: true }),
      wax: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.45, transparent: true }),
    }),
    [],
  );

  useFrame(() => {
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

    // the document settles into place
    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.45);
    if (doc.current) {
      doc.current.scale.setScalar(0.85 + 0.15 * a);
      doc.current.position.y = (1 - a) * -0.25;
    }
    // ★ the wax seal thunks down over the back third — with a little overshoot
    const sealK = reduced ? 1 : THREE.MathUtils.clamp((t - 0.55) / 0.15, 0, 1);
    const base = THREE.MathUtils.smoothstep(sealK, 0, 1);
    const overshoot = 1 + (reduced ? 0 : Math.sin(THREE.MathUtils.clamp(sealK, 0, 1) * Math.PI) * 0.18);
    if (seal.current) seal.current.scale.setScalar(0.0001 + base * overshoot);

    mats.paper.opacity = vis;
    mats.rule.opacity = vis * 0.8;
    mats.wax.opacity = vis * base;

    // the hash-chain spine writes itself in once the page has settled
    if (chainRef.current) {
      const k = reduced ? 1 : THREE.MathUtils.clamp((t - 0.2) / 0.3, 0, 1);
      chainRef.current.style.opacity = String(k * vis);
    }
  });

  return (
    <group ref={group} visible={false} position={[0, 0.2, 0]}>
      {/* the document itself */}
      <group ref={doc}>
        <mesh material={mats.paper}>
          <boxGeometry args={[2.7, 3.5, 0.06]} />
        </mesh>
        {/* header + footer rules */}
        <mesh position={[0, 1.35, 0.04]} material={mats.rule}>
          <boxGeometry args={[2.3, 0.02, 0.02]} />
        </mesh>
        <mesh position={[0, -1.62, 0.04]} material={mats.rule}>
          <boxGeometry args={[2.3, 0.02, 0.02]} />
        </mesh>
      </group>
      {/* the wax seal — a coin pressed flat against the page */}
      <group ref={seal} position={[0.85, -1.3, 0.05]}>
        <mesh rotation={[Math.PI / 2, 0, 0]} material={mats.wax}>
          <cylinderGeometry args={[0.34, 0.34, 0.08, 32]} />
        </mesh>
      </group>
      {active && (
        <>
          {/* header */}
          <Html position={[0, 1.72, 0.1]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", textAlign: "center", whiteSpace: "nowrap" }}>
              <div style={{ fontSize: "12px", fontWeight: 700, letterSpacing: "0.14em", color: "var(--coral)" }}>PRODUCTION NOTICE</div>
              <div style={{ fontSize: "9px", color: "var(--ink-soft)", marginTop: 2 }}>case {fixtures.packet.case_id} · {fixtures.packet.legal.basis}</div>
            </div>
          </Html>
          {/* ★ the hash-chain spine — every stage, full SHA-256 */}
          <Html position={[0, 0.5, 0.1]} center distanceFactor={6} pointerEvents="none">
            <div ref={chainRef} style={{ fontFamily: "var(--font-mono)", width: 250, fontSize: "7px", lineHeight: 1.5, textAlign: "left", opacity: 0 }}>
              <div style={{ fontSize: "9px", color: "var(--ink)", letterSpacing: "0.06em", marginBottom: 4 }}>CHAIN OF CUSTODY</div>
              {CHAIN.map((c) => (
                <div key={c.stage} style={{ marginBottom: 3 }}>
                  <span style={{ color: "var(--coral)" }}>{c.stage}</span>
                  <div style={{ color: "var(--ink-soft)", wordBreak: "break-all" }}>{c.sha}</div>
                </div>
              ))}
            </div>
          </Html>
          {/* the seizure tuple */}
          <Html position={[0, -0.72, 0.1]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--ink)", whiteSpace: "nowrap" }}>
              {`{ ${PEER} · port ${A.peer_port} · ${WHEN} }`}
            </div>
          </Html>
          {/* the seal stamp */}
          <Html position={[0.85, -1.3, 0.12]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "8px", fontWeight: 700, letterSpacing: "0.1em", color: "var(--paper)", textAlign: "center" }}>SEALED</div>
          </Html>
          {/* footer — replay + the closing line */}
          <Html position={[-0.55, -2.05, 0.1]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", width: 250, fontSize: "8px", lineHeight: 1.6, textAlign: "left", color: "var(--ink-soft)" }}>
              <div style={{ color: "var(--riso-blue)", wordBreak: "break-all" }}>replay · {fixtures.packet.replay.command}</div>
              <div style={{ color: "var(--ink)", marginTop: 4, fontSize: "11px" }}>Not a guess. A document.</div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
