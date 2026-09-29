import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";
import { panel, prose, kicker } from "./panelStyle";

/**
 * ST.6 VAANI (वाणी · "voice") — the plain-English lead (§7). The station is the
 * MACHINE SPEAKING: a bare risk score 0.87 is uttered into a sentence an officer
 * can act on. A flat baseline ERUPTS into a crisp equalizer of vertical bars —
 * the voice — coral and kinetic; the headline types on in sync, as if read
 * aloud. When the utterance lands the bars settle to a calm blue baseline (the
 * record is now trustworthy, not alarming) and the evidence AND the doubts fade
 * in together: what happened, the network detail, why flagged (coral), a teal
 * counter-line, and an origin line that openly admits where it abstained (§6).
 */
const SLICE = STATIONS[6].slice;
const A = fixtures.packet.attribution;
const WHEN = A.observed_at_utc.slice(0, 19).replace("T", " ") + "Z";
const HEADLINE = "High-risk lead: unusually high fees and a lot of money moved out in a short time.";
const BARS = 27;
const SPAN = 3.0;

// deterministic per-bar magnitude — a fixed vocal envelope, no frame jitter
const MAG = Array.from({ length: BARS }, (_, i) => {
  const s = Math.sin(i * 12.9898) * 43758.5453;
  const r = s - Math.floor(s);
  // taller in the middle of the utterance, tapering at the ends — reads as speech
  const env = Math.sin((i / (BARS - 1)) * Math.PI);
  return 0.35 + 0.65 * r * (0.4 + 0.6 * env);
});

const coral = new THREE.Color(C.coral);
const blue = new THREE.Color(C.risoBlue);
const _c = new THREE.Color();

export function Vaani({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const bars = useRef<THREE.InstancedMesh>(null);
  const headlineRef = useRef<HTMLSpanElement>(null);
  const caretRef = useRef<HTMLSpanElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const mats = useMemo(
    () => ({
      bar: new THREE.MeshStandardMaterial({ roughness: 0.5, transparent: true, vertexColors: false }),
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
    const time = reduced ? 3 : state.clock.elapsedTime;

    // speaking rises t 0.12→0.5; the utterance lands (bars calm) t 0.58→0.74
    const speakK = reduced ? 1 : THREE.MathUtils.clamp((t - 0.12) / 0.38, 0, 1);
    const doneK = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.58, 0.74);
    const live = speakK * (1 - doneK); // vocal energy — present only while speaking

    if (bars.current) {
      for (let i = 0; i < BARS; i++) {
        // live oscillation while speaking; settles to a low flat baseline after
        const osc = reduced ? 0.6 : 0.5 + 0.5 * Math.sin(time * 6 + i * 0.7);
        const h = 0.05 + live * MAG[i] * (0.35 + 0.85 * osc) + doneK * 0.06;
        const x = (i / (BARS - 1) - 0.5) * SPAN;
        dummy.position.set(x, h / 2, 0);
        dummy.scale.set(0.055, h, 0.055);
        dummy.rotation.set(0, 0, 0);
        dummy.updateMatrix();
        bars.current.setMatrixAt(i, dummy.matrix);
        // coral energy while speaking → calm blue trust once the record lands
        _c.copy(coral).lerp(blue, doneK);
        bars.current.setColorAt(i, _c);
      }
      bars.current.instanceMatrix.needsUpdate = true;
      if (bars.current.instanceColor) bars.current.instanceColor.needsUpdate = true;
    }
    mats.bar.opacity = vis;

    // ★ the type-on — a bare 0.87 becomes a sentence, in step with the voice
    const n = Math.floor(speakK * HEADLINE.length);
    if (headlineRef.current) headlineRef.current.textContent = HEADLINE.slice(0, n);
    if (caretRef.current) caretRef.current.style.opacity = speakK < 1 && Math.sin(time * 6) > 0 ? "1" : "0";
    // evidence + doubts fade in once the sentence has been spoken
    if (bodyRef.current) bodyRef.current.style.opacity = String(doneK * vis);
  });

  return (
    <group ref={group} visible={false} position={[0.2, 0.5, 0]}>
      {/* the voice — a crisp equalizer that IS the risk being spoken */}
      <instancedMesh ref={bars} args={[undefined, undefined, BARS]} material={mats.bar}>
        <boxGeometry args={[1, 1, 1]} />
      </instancedMesh>

      {active && (
        <>
          {/* the bare score → severity → subject, above the voice */}
          <Html position={[0, 1.15, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, whiteSpace: "nowrap" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "30px", fontWeight: 700, color: "var(--coral)", lineHeight: 1 }}>0.87</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", letterSpacing: "0.12em", color: "var(--coral)", border: "1px solid var(--coral)", borderRadius: 3, padding: "1px 5px" }}>
                {fixtures.alert.severity.toUpperCase()}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--ink-soft)" }}>{fixtures.alert.subject_display}</span>
            </div>
          </Html>

          {/* ★ the sentence, typed on in step with the voice */}
          <Html position={[0, 0.62, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-text)", fontSize: "16px", fontWeight: 500, lineHeight: 1.4, width: 360, textAlign: "center", color: "var(--ink)", minHeight: "2.2em" }}>
              <span ref={headlineRef} />
              <span ref={caretRef} style={{ color: "var(--coral)" }}>▍</span>
            </div>
          </Html>

          {/* evidence AND doubts — the same lead the officer's queue shows (§6) */}
          <Html position={[0, -0.95, 0]} center distanceFactor={6} pointerEvents="none">
            <div ref={bodyRef} style={{ opacity: 0, display: "flex", gap: 12, alignItems: "flex-start" }}>
              {/* what happened + network detail */}
              <div style={{ ...panel, width: 210 }}>
                <div style={kicker}>THE LEAD</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", lineHeight: 1.7, color: "var(--ink-soft)" }}>
                  <div>network · {fixtures.alert.origin.shortlist.find((l) => l.rank === 1)?.peer_ip_display} · port {A.peer_port}</div>
                  <div>network operator · AS{A.asn} ({A.geo_country})</div>
                  <div>first seen · {WHEN}</div>
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--coral)", marginTop: 5 }}>why flagged · high fees · large amount moved</div>
              </div>
              {/* the honest counter + abstention */}
              <div style={{ ...panel, width: 210 }}>
                <div style={{ ...kicker, color: "var(--teal)" }}>AND YET</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--teal)", lineHeight: 1.6 }}>on the other hand · this could be a shop settling daily takings</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--riso-blue)", lineHeight: 1.6, marginTop: 4 }}>origin · we could not tell for 11 of 14 steps</div>
                <div style={{ ...prose, fontSize: "10px", color: "var(--ink-soft)", marginTop: 5 }}>1 of about 20 ranked leads</div>
              </div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
