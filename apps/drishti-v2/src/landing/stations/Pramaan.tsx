import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.7 PRAMAAN (प्रमाण · "proof") — the finish line (§7). The whole run
 * (1,000,000 → 1) resolves here into ONE admissible artifact. The last shards
 * of the maze spiral inward through the contracting chakravyuha rings and are
 * swallowed as a single crisp PROOF CARD assembles on top — the one surviving
 * document. A cute round wax seal thunks down on its corner with a press-twist.
 *
 * The card is a real DOM document (crisp, full-opacity, fits on screen); the
 * rings + shards are the 3D "maze compressing" behind it. HARD RULES:
 * identifiers truncated on screen (IP two-octet masked, txid/addr prefix…suffix)
 * while the packet SHA-256 prints IN FULL (§9 / BSA 2023 §63(4)). Every value
 * comes from the packet fixture — nothing invented.
 */
const SLICE = STATIONS[7].slice;
const P = fixtures.packet;
const A = P.attribution;
const utc = (us: number) => new Date(us / 1000).toISOString().slice(0, 19).replace("T", " ") + "Z";
const GEN = utc(P.generated_at_us);
const PEER = A.peer_ip.split(".").slice(0, 2).join(".") + ".x.x"; // two-octet mask
const ORIGIN_TX = "da4daa38…8b27";
const SUBJECT = P.subject.subject_id;
const PACKET_SHA = P.replay.expected_packet_sha256;
const ROWS = P.input.rows_sealed.toLocaleString("en-IN");

const SHARDS = 30;
const RINGS = [2.95, 2.35, 1.8];

function rand(i: number, salt: number) {
  const s = Math.sin(i * 12.9898 + salt * 78.233) * 43758.5453;
  return s - Math.floor(s);
}

// each shard: a maze remnant that spirals inward and is swallowed by the proof
const SHARD = Array.from({ length: SHARDS }, (_, i) => ({
  ang: (i / SHARDS) * Math.PI * 2 + rand(i, 7),
  r0: 2.0 + rand(i, 1) * 1.1,
  ySquash: 0.55 + rand(i, 2) * 0.35,
  z0: (rand(i, 3) - 0.5) * 0.8,
  size: 0.09 + rand(i, 4) * 0.1,
  stagger: rand(i, 5) * 0.26,
  coral: i % 2 === 0,
}));

const coral = new THREE.Color(C.coral);
const blue = new THREE.Color(C.risoBlue);
const _c = new THREE.Color();
const _o = new THREE.Object3D();

// one engraved fact line on the proof card
function Row({ k, v, accent }: { k: string; v: string; accent?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 10, lineHeight: 1.85, borderBottom: "1px dotted var(--line)" }}>
      <span style={{ color: "var(--ink-soft)", letterSpacing: "0.02em", whiteSpace: "nowrap" }}>{k}</span>
      <span style={{ color: accent ? "var(--coral)" : "var(--ink)", fontWeight: accent ? 600 : 400 }}>{v}</span>
    </div>
  );
}

export function Pramaan({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const shards = useRef<THREE.InstancedMesh>(null);
  const ringRefs = useRef<(THREE.Mesh | null)[]>([]);
  const cardRef = useRef<HTMLDivElement>(null);
  const sealRef = useRef<HTMLDivElement>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const mats = useMemo(
    () => ({
      shard: new THREE.MeshStandardMaterial({ roughness: 0.5, transparent: true, vertexColors: false }),
      ring: new THREE.MeshBasicMaterial({ color: C.line, transparent: true }),
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

    // the chakravyuha rings rotate + contract, then fade as the proof locks in
    const ringFade = reduced ? 0 : 1 - THREE.MathUtils.smoothstep(t, 0.4, 0.62);
    RINGS.forEach((_, i) => {
      const m = ringRefs.current[i];
      if (!m) return;
      const contract = reduced ? 0.85 : 1 - 0.5 * THREE.MathUtils.smoothstep(t, 0.15, 0.6);
      m.scale.setScalar(contract);
      m.rotation.z = reduced ? 0 : time * (0.15 + i * 0.08) * (i % 2 ? -1 : 1);
    });
    mats.ring.opacity = vis * ringFade * 0.55;

    // the last shards spiral inward and shrink to nothing at the core
    if (shards.current) {
      for (let i = 0; i < SHARDS; i++) {
        const s = SHARD[i];
        const inK = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.04 + s.stagger, 0.5 + s.stagger);
        const r = s.r0 * (1 - inK);
        const ang = s.ang + (reduced ? 0 : time * 0.5 + inK * 3.2); // swirl
        _o.position.set(Math.cos(ang) * r, Math.sin(ang) * r * s.ySquash, THREE.MathUtils.lerp(s.z0, 0.05, inK));
        _o.rotation.set(ang, ang * 0.5, 0);
        _o.scale.setScalar(s.size * (1 - inK) + 0.001);
        _o.updateMatrix();
        shards.current.setMatrixAt(i, _o.matrix);
        _c.copy(s.coral ? coral : blue);
        shards.current.setColorAt(i, _c);
      }
      shards.current.instanceMatrix.needsUpdate = true;
      if (shards.current.instanceColor) shards.current.instanceColor.needsUpdate = true;
    }
    mats.shard.opacity = vis * (1 - THREE.MathUtils.smoothstep(t, 0.55, 0.72));

    // ★ the proof card assembles — crisp, full opacity, then holds till the exit
    if (cardRef.current) {
      const form = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.3, 0.54);
      const exit = reduced ? 1 : 1 - THREE.MathUtils.smoothstep(t, 0.9, 1.0);
      cardRef.current.style.opacity = String(form * exit);
      cardRef.current.style.transform = `scale(${(0.93 + 0.07 * form).toFixed(3)})`;
    }

    // ★ the cute wax seal thunks down with a crisp overshoot + press-twist
    if (sealRef.current) {
      const sealK = reduced ? 1 : THREE.MathUtils.clamp((t - 0.6) / 0.12, 0, 1);
      const base = THREE.MathUtils.smoothstep(sealK, 0, 1);
      const overshoot = 1 + (reduced ? 0 : Math.sin(THREE.MathUtils.clamp(sealK, 0, 1) * Math.PI) * 0.22);
      const exit = reduced ? 1 : 1 - THREE.MathUtils.smoothstep(t, 0.9, 1.0);
      sealRef.current.style.opacity = String(base * exit);
      sealRef.current.style.transform = `scale(${(0.0001 + base * overshoot).toFixed(3)}) rotate(${((1 - base) * -28 - 8).toFixed(1)}deg)`;
    }
  });

  return (
    <group ref={group} visible={false}>
      {/* the contracting chakravyuha rings — the maze closing around the proof */}
      {RINGS.map((r, i) => (
        <mesh key={i} ref={(m) => (ringRefs.current[i] = m)} rotation={[1.15, 0, 0]} material={mats.ring}>
          <torusGeometry args={[r, 0.012, 8, 90]} />
        </mesh>
      ))}

      {/* the last maze shards, spiralling in to be swallowed by the proof */}
      <instancedMesh ref={shards} args={[undefined, undefined, SHARDS]} material={mats.shard}>
        <boxGeometry args={[1, 1, 1]} />
      </instancedMesh>

      {/* ★ THE PROOF CARD — the single surviving artifact, a crisp DOM document */}
      {active && (
        <Html position={[0.15, 0.4, 0.2]} center distanceFactor={5} pointerEvents="none" zIndexRange={[20, 0]}>
          <div
            ref={cardRef}
            style={{
              opacity: 0,
              width: 300,
              padding: "18px 20px 22px",
              background: "var(--paper)",
              border: "1.5px solid var(--ink)",
              borderRadius: 6,
              boxShadow: "0 18px 40px -12px rgba(27,23,18,0.35), 0 2px 0 var(--line)",
              fontFamily: "var(--font-mono)",
              color: "var(--ink)",
              position: "relative",
            }}
          >
            {/* authority accent bar */}
            <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 4, background: "var(--riso-blue)", borderRadius: "6px 6px 0 0" }} />

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{ letterSpacing: "0.2em", fontSize: 9.5, color: "var(--ink-soft)" }}>PRAMAAN · प्रमाण</span>
              <span style={{ letterSpacing: "0.14em", fontSize: 9, color: "var(--riso-blue)", fontWeight: 600 }}>ADMISSIBLE</span>
            </div>

            <div style={{ fontFamily: "var(--font-display)", fontSize: 34, lineHeight: 1.0, margin: "10px 0 3px" }}>One proof.</div>
            <div style={{ fontSize: 9.5, color: "var(--ink-soft)", letterSpacing: "0.03em", marginBottom: 12 }}>
              1,000,000 signals → <span style={{ color: "var(--coral)", fontWeight: 600 }}>1</span> court-ready document
            </div>

            <Row k="origin tx" v={ORIGIN_TX} />
            <Row k="announcing IP · port" v={`${PEER} · ${A.peer_port}`} />
            <Row k="network operator" v={`AS${A.asn} · ${A.geo_country}`} />
            <Row k="operator likelihood" v={A.p_asn.toFixed(4)} accent />
            <Row k="subject" v={SUBJECT} />
            <Row k="rows sealed" v={ROWS} />

            <div style={{ marginTop: 11 }}>
              <div style={{ fontSize: 8, letterSpacing: "0.14em", color: "var(--ink-soft)", marginBottom: 3 }}>PACKET SHA-256 · IN FULL (BSA 2023 §63(4))</div>
              <div style={{ fontSize: 9, lineHeight: 1.5, color: "var(--riso-blue)", wordBreak: "break-all" }}>{PACKET_SHA}</div>
            </div>

            <div style={{ marginTop: 10, paddingTop: 8, borderTop: "1px solid var(--line)", display: "flex", justifyContent: "space-between", fontSize: 8, color: "var(--ink-soft)", letterSpacing: "0.03em" }}>
              <span>{P.case_id}</span>
              <span>reproducible · seed 42</span>
            </div>
            <div style={{ fontSize: 8, color: "var(--ink-soft)", marginTop: 2 }}>generated · {GEN}</div>

            {/* ★ the cute round wax seal — thunks onto the corner, embossed check */}
            <div
              ref={sealRef}
              style={{
                position: "absolute",
                right: -22,
                bottom: -22,
                width: 62,
                height: 62,
                borderRadius: "50%",
                background: "radial-gradient(circle at 36% 32%, #ff8a6e 0%, var(--coral) 42%, #d24e33 100%)",
                boxShadow: "inset 0 3px 6px rgba(255,255,255,0.35), inset 0 -4px 8px rgba(120,30,15,0.5), 0 6px 14px -4px rgba(27,23,18,0.45)",
                display: "grid",
                placeItems: "center",
                opacity: 0,
                transformOrigin: "center",
              }}
            >
              {/* soft scalloped wax edge */}
              <div style={{ position: "absolute", inset: 5, borderRadius: "50%", border: "1.5px dashed rgba(255,255,255,0.35)" }} />
              {/* embossed check — approved & sealed */}
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none" style={{ filter: "drop-shadow(0 1px 0 rgba(120,30,15,0.6))" }}>
                <path d="M5 13l4 4L19 7" stroke="#fbe9df" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}
