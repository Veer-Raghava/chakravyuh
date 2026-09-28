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
 * ST.4 SHASTRA ★ THE HONESTY FLEX (§7). One transaction hangs at the top; below
 * it sits a bench of small "computers" — each a candidate origin (an announcing
 * IP). A coral scan-line sweeps the bench; as it passes, each screen wakes with
 * that candidate's origin likelihood. Then the leading candidate lifts, glows
 * coral, and a beam snaps up to the transaction: THIS one, most likely, is where
 * it began. The rest settle back, dim and blue — considered, not chosen.
 *
 * The ★ moment is the ceiling bar: only 41.5% of transactions even contain a
 * recoverable answer, so a full-width bar splits 41.5% "possible" (coral) from
 * 58.5% "unknowable" (calm grey), with a dignified grey "no answer available"
 * card beside it — abstention is a correct output, not a failure (§6).
 */
const SLICE = STATIONS[4].slice;
// The recoverable ceiling, read from world.json (FRONTEND-HANDOFF-V2 §1) — one source
// with WorldScreen, OriginScreen + the landing funnel. The bar + labels derive from it.
const CEIL_POSSIBLE = fixtures.world.recoverable_ceiling;
const POSSIBLE_PCT = (CEIL_POSSIBLE * 100).toFixed(1); // "41.5"
const UNKNOWABLE_PCT = ((1 - CEIL_POSSIBLE) * 100).toFixed(1); // "58.5"
const BAR_W = 3.4;
const MAXC = 7;

type Cand = { ip: string; p: number; rank: number; asn: number; geo: string; port: number; x: number; lead: boolean };

function buildCands() {
  const lanes = [...fixtures.origin.shortlist].sort((a, b) => a.rank - b.rank).slice(0, MAXC);
  const pmax = Math.max(...lanes.map((l) => l.p_origin));
  const n = lanes.length;
  // order along the bench by rank so the scan reveals a tidy descending row
  const cands: Cand[] = lanes.map((l, i) => ({
    ip: l.peer_ip_display,
    p: l.p_origin / pmax, // normalised brightness 0→1
    rank: l.rank,
    asn: l.asn,
    geo: l.geo_country,
    port: l.peer_port,
    x: (i - (n - 1) / 2) * Math.min(0.78, 4.6 / n),
    lead: l.rank === 1,
  }));
  const lead = cands.find((c) => c.lead) ?? cands[0];
  const runnerUp = cands.find((c) => c.rank === 2) ?? cands[1] ?? cands[0];
  return { cands, lead, runnerUp };
}

const BENCH_Y = -0.15;
const TX = new THREE.Vector3(0, 1.5, 0);
const LEAD_P = (fixtures.origin.shortlist.find((l) => l.rank === 1)?.p_origin ?? 0).toFixed(3);
const dimBlue = new THREE.Color(C.risoBlue).multiplyScalar(0.5);
const litBlue = new THREE.Color(C.risoBlue);
const litCoral = new THREE.Color(C.coral);
const _c = new THREE.Color();

export function Shastra({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const txRef = useRef<THREE.Mesh>(null);
  const scanRef = useRef<THREE.Mesh>(null);
  const beamRef = useRef<THREE.Mesh>(null);
  const compRefs = useRef<(THREE.Group | null)[]>([]);
  const coralSeg = useRef<THREE.Mesh>(null);
  const greySeg = useRef<THREE.Mesh>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const { cands, lead, runnerUp } = useMemo(buildCands, []);

  // one screen material per computer so each can be tinted independently
  const screenMats = useMemo(
    () => cands.map(() => new THREE.MeshStandardMaterial({ color: C.risoBlue, emissive: C.risoBlue, emissiveIntensity: 0.1, roughness: 0.5, transparent: true })),
    [cands],
  );
  const mats = useMemo(
    () => ({
      tx: new THREE.MeshStandardMaterial({ color: C.ink, roughness: 0.7, transparent: true }),
      body: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.9, transparent: true }),
      scan: new THREE.MeshBasicMaterial({ color: C.coral, transparent: true, opacity: 0 }),
      beam: new THREE.MeshStandardMaterial({ color: C.coral, emissive: C.coral, emissiveIntensity: 0.3, roughness: 0.5, transparent: true }),
      possible: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.6, transparent: true }),
      unknowable: new THREE.MeshStandardMaterial({ color: C.line, roughness: 0.9, transparent: true }),
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

    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.4);
    if (txRef.current) txRef.current.scale.setScalar(0.24 * a + 0.0001);

    // the scan-line sweeps the bench over t 0.1→0.5
    const scanX = -2.5 + 5 * THREE.MathUtils.clamp((t - 0.1) / 0.4, 0, 1);
    if (scanRef.current) {
      scanRef.current.position.x = scanX;
      const near = t > 0.1 && t < 0.55;
      mats.scan.opacity = (near ? 0.55 : 0) * vis;
    }
    // leading lifts + beam to tx over t 0.55→0.75
    const liftK = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0.55, 0.75);

    cands.forEach((c, i) => {
      const grp = compRefs.current[i];
      if (!grp) return;
      // each computer rises into place, then the scan wakes its screen
      const woke = reduced ? 1 : THREE.MathUtils.smoothstep(scanX, c.x - 0.2, c.x + 0.2);
      const lift = c.lead ? liftK * 0.55 : 0;
      const bob = reduced ? 0 : Math.sin(time * 1.1 + i) * 0.02;
      grp.position.set(c.x, BENCH_Y + lift + bob, 0);
      grp.scale.setScalar(a);
      grp.visible = a > 0.02;
      // screen tint: lit by likelihood; leading turns coral once chosen
      const m = screenMats[i];
      const chosen = c.lead ? liftK : 0;
      _c.copy(dimBlue).lerp(litBlue, woke * (0.4 + 0.6 * c.p)).lerp(litCoral, chosen);
      m.color.copy(_c);
      m.emissive.copy(_c);
      m.emissiveIntensity = 0.1 + woke * (0.3 + 0.5 * c.p) + chosen * 0.4;
      m.opacity = vis;
    });
    mats.body.opacity = vis;
    mats.tx.opacity = vis;

    // beam from the leading computer up to the transaction
    if (beamRef.current) {
      const from = new THREE.Vector3(lead.x, BENCH_Y + liftK * 0.55 + 0.18, 0);
      const to = TX.clone().multiplyScalar(a);
      const mid = from.clone().lerp(to, 0.5);
      const len = from.distanceTo(to);
      beamRef.current.position.copy(mid);
      beamRef.current.scale.set(0.03, len * liftK + 0.0001, 0.03);
      beamRef.current.rotation.z = Math.atan2(to.y - from.y, to.x - from.x) - Math.PI / 2;
      mats.beam.opacity = vis * liftK;
    }

    // ★ the ceiling bar — 41.5% possible | 58.5% unknowable
    const kCeil = reduced ? 1 : THREE.MathUtils.clamp((t - 0.5) / 0.3, 0, 1);
    const coralW = CEIL_POSSIBLE * BAR_W;
    const greyW = (1 - CEIL_POSSIBLE) * BAR_W;
    if (coralSeg.current) {
      coralSeg.current.scale.set(coralW * kCeil + 0.0001, 0.16, 0.1);
      coralSeg.current.position.x = -BAR_W / 2 + (coralW * kCeil) / 2;
    }
    if (greySeg.current) {
      greySeg.current.scale.set(greyW * kCeil + 0.0001, 0.16, 0.1);
      greySeg.current.position.x = -BAR_W / 2 + coralW + (greyW * kCeil) / 2;
    }
    mats.possible.opacity = vis * kCeil;
    mats.unknowable.opacity = vis * kCeil;
  });

  return (
    <group ref={group} visible={false} position={[0, 0.25, 0]}>
      {/* the transaction under scrutiny */}
      <mesh ref={txRef} position={TX} material={mats.tx}>
        <octahedronGeometry args={[0.9]} />
      </mesh>

      {/* the scan-line sweeping the bench */}
      <mesh ref={scanRef} position={[0, BENCH_Y, 0.25]} material={mats.scan}>
        <planeGeometry args={[0.05, 0.9]} />
      </mesh>

      {/* the beam from the chosen computer to the transaction */}
      <mesh ref={beamRef} material={mats.beam}>
        <boxGeometry args={[1, 1, 1]} />
      </mesh>

      {/* the bench of candidate "computers" — one per candidate origin */}
      {cands.map((_c, i) => (
        <group
          key={i}
          ref={(el) => {
            compRefs.current[i] = el;
          }}
        >
          {/* monitor body */}
          <mesh position={[0, 0.02, 0]} material={mats.body}>
            <boxGeometry args={[0.34, 0.26, 0.07]} />
          </mesh>
          {/* screen face — tinted by likelihood */}
          <mesh position={[0, 0.05, 0.045]} material={screenMats[i]}>
            <planeGeometry args={[0.26, 0.17]} />
          </mesh>
          {/* little stand */}
          <mesh position={[0, -0.16, 0]} material={mats.body}>
            <boxGeometry args={[0.12, 0.04, 0.05]} />
          </mesh>
        </group>
      ))}

      {/* ★ the ceiling bar — 41.5% possible | 58.5% unknowable */}
      <mesh ref={coralSeg} position={[0, -1.65, 0]} material={mats.possible}>
        <boxGeometry args={[1, 1, 1]} />
      </mesh>
      <mesh ref={greySeg} position={[0, -1.65, 0]} material={mats.unknowable}>
        <boxGeometry args={[1, 1, 1]} />
      </mesh>

      {active && (
        <>
          {/* leading candidate readout */}
          <Html position={[0, 2.25, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, whiteSpace: "nowrap", textAlign: "center", color: "var(--coral)", letterSpacing: "0.03em" }}>
              most likely origin · {lead.ip} · AS{lead.asn} · {lead.geo} · p={LEAD_P}
            </div>
          </Html>
          {/* shortlist — a set you can act on, not one name */}
          <Html position={[2.5, 0.7, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...panel, width: 168 }}>
              <div style={{ ...kicker, color: "var(--riso-blue)" }}>SHORTLIST · 90% CONF</div>
              <div style={{ ...datum, color: "var(--riso-blue)", lineHeight: 1.5 }}>
                sender ∈ {`{ ${runnerUp.ip} · ${lead.ip} }`}
              </div>
              <div style={{ ...prose, fontSize: "11px", color: "var(--ink-soft)", marginTop: 4 }}>
                a set you can act on — not one name
              </div>
            </div>
          </Html>
          {/* ceiling-bar labels */}
          <Html position={[-0.995, -2.1, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, whiteSpace: "nowrap", color: "var(--coral)", fontWeight: 600 }}>{POSSIBLE_PCT}% possible</div>
          </Html>
          <Html position={[0.705, -2.1, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, whiteSpace: "nowrap", color: "var(--ink-soft)" }}>{UNKNOWABLE_PCT}% unknowable</div>
          </Html>
          {/* the dignified grey "no answer" card — abstention as a correct output */}
          <Html position={[-2.55, 0.7, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...panel, width: 158, color: "var(--ink-soft)" }}>
              <div style={{ ...kicker, color: "var(--ink-soft)" }}>NO ANSWER AVAILABLE</div>
              <div style={{ ...datum, color: "var(--ink-soft)", lineHeight: 1.5 }}>reason · margin below floor</div>
              <div style={{ ...prose, fontSize: "11px", color: "var(--ink)", marginTop: 4 }}>this is a correct output</div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
