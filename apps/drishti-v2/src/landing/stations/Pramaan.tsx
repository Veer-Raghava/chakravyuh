import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";
import { head, kicker, datum } from "./panelStyle";

/**
 * ST.7 PRAMAAN — the court-ready proof (§7, the finish line). The single
 * surviving lead is pressed into a real evidence packet: a crumpled sheet of
 * warm paper (soft wrinkles the light catches) carrying a letterpress title, the
 * case metadata, the {IP · port · UTC} attribution tuple, the hash-chain of
 * every pipeline stage (full SHA-256 — nothing hidden, §6 / BSA 2023 §63(4)),
 * the full packet hash, and a red wax seal reading CHAKRAVYUH · PRAMAAN.
 *
 * A wax seal thunks down at the end — not a flourish, a claim: this is
 * reproducible and admissible. The funnel lands on 1. Not a guess. A document.
 */
const SLICE = STATIONS[7].slice;
const P = fixtures.packet;
const A = P.attribution;
const WHEN = A.observed_at_utc.slice(0, 19).replace("T", " ") + "Z";
const GEN = new Date(P.generated_at_us / 1000).toISOString().slice(0, 19).replace("T", " ") + "Z";
// truncate the peer to two octets — no full IP ever reaches the screen (§6)
const PEER = A.peer_ip.split(".").slice(0, 2).join(".") + ".x.x";
const CHAIN = P.chain_of_custody.map((c) => ({ stage: c.stage, sha: c.sha256 }));
const PACKET_SHA = P.replay.expected_packet_sha256;

// crumpled-paper page: a subdivided plane z-displaced by layered sines so the
// directional light catches soft wrinkles — reads as pressed paper, no texture
// asset, no dep, deterministic (§4 material, offline rule).
function makePaper(w: number, h: number) {
  const g = new THREE.PlaneGeometry(w, h, 28, 36);
  const pos = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z =
      (Math.sin(x * 3.1 + y * 2.3) * 0.5 +
        Math.sin(x * 7.7 - y * 5.1) * 0.26 +
        Math.sin(x * 13.9 + y * 11.3) * 0.12) *
      0.05;
    pos.setZ(i, z);
  }
  g.computeVertexNormals();
  return g;
}

const metaLabel = { ...kicker, fontSize: "8px", marginBottom: 1 } as const;
const sectionHead = { ...datum, fontSize: "9px", letterSpacing: "0.14em", color: "var(--ink)", marginTop: 9, marginBottom: 3 } as const;
const chip = { ...datum, fontSize: "7.5px", letterSpacing: "0.08em", color: "var(--ink-soft)", border: "1px solid var(--line)", borderRadius: 3, padding: "1px 5px" } as const;
const shaLine = { ...datum, fontSize: "6.5px", lineHeight: 1.35, color: "var(--ink-soft)", wordBreak: "break-all" as const };

// PLACEHOLDER_COMPONENT

export function Pramaan({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const doc = useRef<THREE.Group>(null);
  const seal = useRef<THREE.Group>(null);
  const chainRef = useRef<HTMLDivElement>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const paperGeo = useMemo(() => makePaper(2.7, 3.5), []);
  const backGeo = useMemo(() => makePaper(2.72, 3.52), []);
  const mats = useMemo(
    () => ({
      paper: new THREE.MeshStandardMaterial({ color: C.paper, roughness: 0.96, metalness: 0, transparent: true, side: THREE.DoubleSide }),
      back: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.98, transparent: true, side: THREE.DoubleSide }),
      wax: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.4, transparent: true }),
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

    // the document settles into place, with a hair of tilt easing flat
    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.45);
    if (doc.current) {
      doc.current.scale.setScalar(0.86 + 0.14 * a);
      doc.current.position.y = (1 - a) * -0.22;
      doc.current.rotation.x = (1 - a) * 0.22;
    }
    // ★ the wax seal thunks down over the back third — with a little overshoot
    const sealK = reduced ? 1 : THREE.MathUtils.clamp((t - 0.55) / 0.15, 0, 1);
    const base = THREE.MathUtils.smoothstep(sealK, 0, 1);
    const overshoot = 1 + (reduced ? 0 : Math.sin(THREE.MathUtils.clamp(sealK, 0, 1) * Math.PI) * 0.2);
    if (seal.current) seal.current.scale.setScalar(0.0001 + base * overshoot);

    mats.paper.opacity = vis;
    mats.back.opacity = vis;
    mats.wax.opacity = vis * base;

    // the hash-chain spine writes itself in once the page has settled
    if (chainRef.current) {
      const k = reduced ? 1 : THREE.MathUtils.clamp((t - 0.2) / 0.3, 0, 1);
      chainRef.current.style.opacity = String(k * vis);
    }
  });

  return (
    <group ref={group} visible={false} position={[0, 0.15, 0]}>
      {/* the crumpled paper page (+ a slightly larger deep-paper backing) */}
      <group ref={doc}>
        <mesh geometry={paperGeo} material={mats.paper} />
        <mesh geometry={backGeo} material={mats.back} position={[0, 0, -0.04]} />
      </group>
      {/* the wax seal — a coin pressed into the lower-right of the page */}
      <group ref={seal} position={[0.92, -1.42, 0.1]}>
        <mesh rotation={[Math.PI / 2, 0, 0]} material={mats.wax}>
          <cylinderGeometry args={[0.26, 0.28, 0.08, 40]} />
        </mesh>
      </group>

      {active && (
        <>
          {/* the printed packet — crisp ink over the pressed paper */}
          <Html position={[0, 0.12, 0.12]} center distanceFactor={6} pointerEvents="none">
            <div style={{ width: 300, textAlign: "left", color: "var(--ink)" }}>
              <div style={kicker}>CHAKRAVYUH · DRISHTI</div>
              <div style={{ ...head, fontSize: "23px", letterSpacing: "0.01em", marginTop: 2 }}>Evidence Packet</div>
              <div style={{ ...datum, color: "var(--ink-soft)", letterSpacing: "0.2em", marginTop: 2, fontSize: "8.5px" }}>
                TRANSACTION ORIGIN ANALYSIS
              </div>
              <div style={{ height: 1, background: "var(--line)", margin: "9px 0" }} />

              <div style={{ display: "flex", justifyContent: "space-between", gap: 14 }}>
                <div>
                  <div style={metaLabel}>CASE ID</div>
                  <div style={datum}>{P.case_id}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={metaLabel}>GENERATED · UTC</div>
                  <div style={datum}>{GEN}</div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 6, marginTop: 9, flexWrap: "wrap" }}>
                <span style={{ ...chip, color: "var(--teal)", borderColor: "var(--teal)" }}>✓ integrity</span>
                <span style={chip}>replayable</span>
                <span style={chip}>{P.legal.basis}</span>
              </div>

              <div style={sectionHead}>01 · ORIGIN ATTRIBUTION</div>
              <div style={{ ...datum, color: "var(--coral)", fontSize: "11px" }}>
                {`{ ${PEER} · port ${A.peer_port} · ${WHEN} }`}
              </div>
              <div style={{ ...datum, color: "var(--ink-soft)", marginTop: 2 }}>
                AS{A.asn} · {A.geo_country} · subject {P.subject.subject_id}
              </div>

              <div style={sectionHead}>02 · CHAIN OF CUSTODY</div>
              <div ref={chainRef} style={{ opacity: 0 }}>
                {CHAIN.map((c) => (
                  <div key={c.stage} style={{ marginBottom: 3 }}>
                    <span style={{ ...datum, color: "var(--coral)", fontSize: "8px", letterSpacing: "0.08em" }}>{c.stage}</span>
                    <div style={shaLine}>{c.sha}</div>
                  </div>
                ))}
              </div>

              <div style={{ height: 1, background: "var(--line)", margin: "9px 0" }} />
              <div style={metaLabel}>PACKET SHA-256</div>
              <div style={{ ...shaLine, color: "var(--riso-blue)" }}>{PACKET_SHA}</div>
              <div style={{ ...head, fontSize: "13px", marginTop: 9 }}>Not a guess. A document.</div>
            </div>
          </Html>

          {/* the wax-seal legend */}
          <Html position={[0.92, -1.42, 0.16]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, fontSize: "6.5px", fontWeight: 700, letterSpacing: "0.12em", color: "var(--paper)", textAlign: "center", lineHeight: 1.35 }}>
              CHAKRAVYUH
              <br />
              PRAMAAN
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

