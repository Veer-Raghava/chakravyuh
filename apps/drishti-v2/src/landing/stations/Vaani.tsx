import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.6 VAANI — the plain-English lead (§7). A bare risk score floats up and
 * unfolds into the alert card an investigating officer actually reads — the same
 * component the tool's lead queue uses, previewed here. A subtle type-on makes
 * the diya seem to read it aloud.
 *
 * The card carries its own evidence AND its own doubts: what happened, the
 * network detail (earliest announce, source port, AS operator), why it's
 * flagged, a teal counter-line, and an origin line that openly admits where the
 * estimator abstained. The counter drops toward 20 ranked leads (§6).
 */
const SLICE = STATIONS[6].slice;
const A = fixtures.packet.attribution;
const WHEN = A.observed_at_utc.slice(0, 19).replace("T", " ") + "Z";
const HEADLINE = "High-risk lead — outsized fees and large outflows in a short window.";

export function Vaani({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const card = useRef<THREE.Group>(null);
  const headlineRef = useRef<HTMLSpanElement>(null);
  const caretRef = useRef<HTMLSpanElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const mats = useMemo(
    () => ({
      slab: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.9, transparent: true }),
      strip: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.6, transparent: true }),
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

    // the card unfolds from a small token as the score resolves
    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.5);
    if (card.current) card.current.scale.set(0.4 + 0.6 * a, 0.4 + 0.6 * a, 1);
    mats.slab.opacity = vis * 0.92;
    mats.strip.opacity = vis;

    // ★ the type-on — a bare 0.87 becomes a sentence an officer can act on
    const typeK = reduced ? 1 : THREE.MathUtils.clamp((t - 0.15) / 0.4, 0, 1);
    const n = Math.floor(typeK * HEADLINE.length);
    if (headlineRef.current) headlineRef.current.textContent = HEADLINE.slice(0, n);
    if (caretRef.current) caretRef.current.style.opacity = typeK < 1 && Math.sin(time * 6) > 0 ? "1" : "0";
    // the evidence + doubts fade in once the sentence has landed
    const bodyK = reduced ? 1 : THREE.MathUtils.clamp((t - 0.5) / 0.25, 0, 1);
    if (bodyRef.current) bodyRef.current.style.opacity = String(bodyK * vis);
  });

  return (
    <group ref={group} visible={false} position={[0, 0.35, 0]}>
      {/* the card as a physical object — unfolds as the score resolves */}
      <group ref={card}>
        <mesh material={mats.slab}>
          <boxGeometry args={[3.0, 2.0, 0.08]} />
        </mesh>
        {/* coral severity edge */}
        <mesh position={[-1.4, 0, 0.05]} material={mats.strip}>
          <boxGeometry args={[0.1, 2.0, 0.06]} />
        </mesh>
      </group>
      {active && (
        <Html position={[0, 0, 0.12]} center distanceFactor={6} pointerEvents="none">
          <div style={{ width: 300, textAlign: "left" }}>
            {/* score → severity → subject */}
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "22px", fontWeight: 700, color: "var(--coral)" }}>0.87</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", letterSpacing: "0.12em", color: "var(--coral)", border: "1px solid var(--coral)", borderRadius: 3, padding: "1px 5px" }}>
                {fixtures.alert.severity.toUpperCase()}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--ink-soft)" }}>
                {fixtures.alert.subject_display}
              </span>
            </div>
            {/* ★ the sentence, typed on */}
            <div style={{ fontFamily: "var(--font-text)", fontSize: "15px", fontWeight: 500, lineHeight: 1.45, minHeight: "2.6em", color: "var(--ink)" }}>
              <span ref={headlineRef} />
              <span ref={caretRef} style={{ color: "var(--coral)" }}>▍</span>
            </div>
            {/* evidence AND doubts — the same card the lead queue shows */}
            <div ref={bodyRef} style={{ fontFamily: "var(--font-mono)", fontSize: "10px", lineHeight: 1.7, marginTop: 6, opacity: 0 }}>
              <div style={{ color: "var(--ink-soft)" }}>
                network · {fixtures.alert.origin.origin_peer_display} · src port {A.peer_port} · AS{A.asn} ({A.geo_country})
              </div>
              <div style={{ color: "var(--ink-soft)" }}>first announced · {WHEN}</div>
              <div style={{ color: "var(--coral)" }}>why flagged · high fee per vByte · large amount sent</div>
              <div style={{ color: "var(--teal)" }}>counter · the same shape fits a merchant settling daily</div>
              <div style={{ color: "var(--riso-blue)" }}>origin · abstained on 11 of 14 hops</div>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}
