import { Suspense, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { AdaptiveDpr } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { fixtures } from "../../data/loader";
import { usToIST } from "../../data/jaal";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import styles from "./OriginScreen.module.css";

/**
 * Origin · SHASTRA (§11.3) — "where did this transaction start?" The tx sits at the
 * centre of the maze; candidate IPs orbit on rings where RADIUS = INVERSE LIKELIHOOD
 * (most-likely nearest the centre — NOT `rank`, which isn't p-order). The confident
 * fixture is the "A NAME" shape (one clear leader, margin above the floor); the
 * abstain fixture is the dignified grey fog-dome "No answer available". The pink fan
 * replays first-seen order and marks the trap: the earliest IP to announce is usually
 * a relay, not the sender — here the earliest peer and the model's top peer happen to
 * be the same, shown honestly, not faked apart. Reduced motion = frozen rings + fan.
 */
type Lane = (typeof fixtures.origin.shortlist)[number];
// Explicit shape so the confident fixture (attribution.asn: number) and the abstain
// fixture (attribution.asn: null) share one type without a TS2352 cast error.
type Origin = Omit<typeof fixtures.origin, "attribution"> & {
  attribution: {
    asn: number | null;
    as_org: string;
    net_class: string;
    geo_country: string;
    p_asn: number;
    p_country: number;
    margin: number;
  };
};

const DISC_R = 2.35;
// §2 ladder ceiling — read from world.origin_curve at the canonical observer_fraction,
// not hand-typed. L1 (network operator) is the hero; L0 (exact host) the honest secondary
// read. ⚠️ These curves are MODELED placeholders in world.json (see its _provenance) and
// deliberately sit above the landing's host-level recoverable_ceiling bar.
const OF = fixtures.world.observer_fraction;
const interpCurve = (curve: { fraction: number; top1: number }[], f: number): number => {
  for (let i = 0; i < curve.length - 1; i++) {
    const a = curve[i], b = curve[i + 1];
    if (f >= a.fraction && f <= b.fraction)
      return a.top1 + ((f - a.fraction) / (b.fraction - a.fraction)) * (b.top1 - a.top1);
  }
  return f <= curve[0].fraction ? curve[0].top1 : curve[curve.length - 1].top1;
};
const OP_CEIL = interpCurve(fixtures.world.origin_curve.l1_asn, OF) * 100; // ~58.8 (operator)
const HOST_CEIL = interpCurve(fixtures.world.origin_curve.l0_host, OF) * 100; // ~39.1 (host)

// Rings are grouped by network operator (ASN): the leader stays coral, the earliest
// announcer stays butter, and the remaining operators cycle this small curated palette.
const OP_PALETTE = [C.risoBlue, C.teal, C.fluoroPink];

/** Backend display format (DATA-CONTRACTS §9): keep first two octets, mask the rest —
 *  matches the fixtures' own peer_ip_display + runner_up_peer_ip. Never a full IP. */
const maskIp = (ip: string) =>
  ip.includes(":") ? ip.split(":").slice(0, 2).join(":") + ":…" : ip.split(".").slice(0, 2).join(".") + ".x.x";

type Placed = { lane: Lane; radius: number; x: number; z: number; i: number };

function place(lanes: Lane[]): Placed[] {
  const ps = lanes.map((l) => l.p_origin);
  const pTop = Math.max(...ps);
  const pMin = Math.min(...ps);
  const span = pTop - pMin || 1;
  return lanes.map((lane, i) => {
    const rNorm = (pTop - lane.p_origin) / span; // 0 = most likely (centre), 1 = least
    const radius = 0.4 + rNorm * (DISC_R - 0.4);
    const ang = i * 2.399963; // golden angle — deterministic, even spread
    return { lane, radius, x: Math.cos(ang) * radius, z: Math.sin(ang) * radius, i };
  });
}

function Rings({ placed, abstain, topIdx, earliestIdx, leaderR, asnHue, reduced }: {
  placed: Placed[]; abstain: boolean; topIdx: number; earliestIdx: number; leaderR: number; asnHue: Map<number, string>; reduced: boolean;
}) {
  const grp = useRef<THREE.Group>(null);
  const dot = useMemo(() => new THREE.SphereGeometry(1, 20, 20), []);
  useFrame((_, dt) => {
    if (grp.current && !reduced) grp.current.rotation.y += dt * 0.06;
  });
  const guides = [0.8, 1.5, 2.2];
  return (
    <group ref={grp} rotation={[-0.98, 0, 0]}>
      {/* concentric ring guides on the maze floor */}
      {guides.map((r) => (
        <mesh key={r} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[r - 0.006, r + 0.006, 96]} />
          <meshBasicMaterial color={C.line} transparent opacity={abstain ? 0.25 : 0.5} side={THREE.DoubleSide} />
        </mesh>
      ))}

      {/* confidence shell — hugs the one clear leader (only when we have a name) */}
      {!abstain && (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0, leaderR + 0.28, 64]} />
          <meshBasicMaterial color={C.risoBlue} transparent opacity={0.14} side={THREE.DoubleSide} />
        </mesh>
      )}

      {/* the pink first-seen fan — one lane per radial line, timed by announcement order */}
      {placed.map((p) => {
        const geo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0.01, 0),
          new THREE.Vector3(p.x, 0.01, p.z),
        ]);
        const mark = p.i === earliestIdx || p.i === topIdx;
        return (
          <primitive
            key={"fan" + p.i}
            object={new THREE.Line(geo, new THREE.LineBasicMaterial({
              color: abstain ? C.inkSoft : C.fluoroPink,
              transparent: true,
              opacity: abstain ? 0.2 : mark ? 0.85 : 0.32,
            }))}
          />
        );
      })}

      {/* the tx ◆ at the centre of the maze */}
      <mesh rotation={[0, Math.PI / 4, 0]} position={[0, 0.02, 0]}>
        <octahedronGeometry args={[0.16, 0]} />
        <meshStandardMaterial color={C.ink} emissive={C.ink} emissiveIntensity={0.2} roughness={0.7} />
      </mesh>

      {/* candidate IPs */}
      {placed.map((p) => {
        const leader = !abstain && p.i === topIdx;
        const col = abstain ? C.inkSoft : leader ? C.coral : p.i === earliestIdx ? C.butter : (asnHue.get(p.lane.asn) ?? C.risoBlue);
        return (
          <mesh key={"dot" + p.i} geometry={dot} position={[p.x, 0.06, p.z]} scale={leader ? 0.12 : 0.075}>
            <meshStandardMaterial color={col} emissive={col} emissiveIntensity={leader ? 0.5 : 0.18} roughness={0.6} />
          </mesh>
        );
      })}

      {/* abstain: a calm grey fog-dome over the centre — "No answer available" */}
      {abstain && (
        <mesh position={[0, 0, 0]}>
          <sphereGeometry args={[1.6, 32, 32]} />
          <meshBasicMaterial color={C.inkSoft} transparent opacity={0.16} />
        </mesh>
      )}
    </group>
  );
}

function Fallback({ placed }: { placed: Placed[] }) {
  return (
    <ul className={styles.fallback}>
      {placed.map((p) => (
        <li key={p.i}>{maskIp(p.lane.peer_ip)} · AS{p.lane.asn} · {(p.lane.p_origin * 100).toFixed(2)}%</li>
      ))}
    </ul>
  );
}

export function OriginScreen() {
  const reduced = usePrefersReducedMotion();
  const [showAbstain, setShowAbstain] = useState(false);
  const data: Origin = showAbstain ? (fixtures.originAbstain as Origin) : fixtures.origin;
  const abstain = data.abstain;

  const placed = useMemo(() => place(data.shortlist), [data]);
  const topIdx = useMemo(
    () => data.shortlist.reduce((b, l, i, a) => (l.p_origin > a[b].p_origin ? i : b), 0),
    [data],
  );
  const earliestIdx = useMemo(
    () => data.shortlist.reduce((b, l, i, a) => ((l.announcements_ms[0] ?? 0) < (a[b].announcements_ms[0] ?? 0) ? i : b), 0),
    [data],
  );
  // deterministic operator → hue map (leader/earliest are re-coloured in Rings)
  const asnHue = useMemo(() => {
    const m = new Map<number, string>();
    for (const l of data.shortlist) if (!m.has(l.asn)) m.set(l.asn, OP_PALETTE[m.size % OP_PALETTE.length]);
    return m;
  }, [data]);
  const leaderR = placed[topIdx]?.radius ?? 0.4;
  const trapCoincides = topIdx === earliestIdx;

  // rows ordered by likelihood for the DOM table (a11y + honesty)
  const rows = useMemo(() => [...placed].sort((a, b) => b.lane.p_origin - a.lane.p_origin), [placed]);

  return (
    <section className={styles.screen}>
      <div className={styles.canvasWrap}>
        <Canvas
          frameloop={reduced ? "demand" : "always"}
          dpr={[1, 2]}
          gl={{ alpha: true, antialias: true }}
          camera={{ position: [0, 1.7, 4.3], fov: 45 }}
          fallback={<Fallback placed={placed} />}
          onCreated={({ camera }) => camera.lookAt(0, 0, 0)}
        >
          <Suspense fallback={null}>
            <ambientLight intensity={0.85} />
            <directionalLight position={[2, 4, 3]} intensity={1} />
            <Rings
              placed={placed}
              abstain={abstain}
              topIdx={topIdx}
              earliestIdx={earliestIdx}
              leaderR={leaderR}
              asnHue={asnHue}
              reduced={reduced}
            />
            <AdaptiveDpr pixelated />
          </Suspense>
        </Canvas>

        <div className={styles.legend}>
          <span className={styles.key}><span className={styles.sw} style={{ background: C.coral }} /> most likely origin</span>
          <span className={styles.key}><span className={styles.sw} style={{ background: C.butter }} /> first to announce</span>
          <span className={styles.key}><span className={styles.sw} style={{ background: C.risoBlue }} /> other candidate</span>
          <p className={styles.legNote}>radius = inverse likelihood — nearest the centre is most likely.</p>
          <p className={styles.legNote}>rings grouped by network operator (ASN).</p>
        </div>
      </div>

      <div className={styles.panel}>
        <header className={styles.header}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>Origin</h1>
            <span className={styles.tag}>SHASTRA · शस्त्र</span>
          </div>
          <p className={styles.gloss}>
            One transaction at the centre of the maze; every IP that announced it on a ring.
            The closer to the centre, the more likely it started there.
          </p>
        </header>

        <button
          type="button"
          className={styles.toggle}
          onClick={() => setShowAbstain((v) => !v)}
          aria-pressed={showAbstain}
        >
          {showAbstain ? "← show the confident case" : "show a “no answer” case →"}
        </button>

        {abstain ? (
          <div className={`${styles.verdict} ${styles.vAbstain}`}>
            <span className={styles.vLabel}>No answer available</span>
            <p className={styles.vBody}>
              The shortlist was too close to call — the margin fell below the floor we're willing to
              act on. We say so plainly rather than name a peer we don't trust.
            </p>
          </div>
        ) : (
          <div className={`${styles.verdict} ${styles.vName}`}>
            <span className={styles.vLabel}>One clear operator</span>
            <p className={styles.vBody}>
              <span className={styles.vIp}>AS{data.attribution.asn} · {data.attribution.geo_country}</span> leads with
              operator-origin likelihood <strong>{(data.attribution.p_asn * 100).toFixed(2)}%</strong>, a margin of{" "}
              <strong>{(data.attribution.margin * 100).toFixed(2)}%</strong> over the runner-up — above the floor,
              so we're willing to name the operator. The exact host stays in the candidate table below.
            </p>
          </div>
        )}

        <div className={styles.trap}>
          <span className={styles.trapLabel}>the first-seen trap</span>
          <p>
            The earliest IP to announce a transaction is usually a <strong>relay</strong> passing it on,
            not the sender.{" "}
            {trapCoincides
              ? "Here the earliest announcer and the model's top candidate are the same peer — we show that honestly rather than manufacture a split."
              : "Here they differ: the first to speak is not the one we name."}
          </p>
        </div>

        {/* §2 ladder ceiling — operator (L1) hero + host (L0) honest secondary */}
        <div className={styles.gauge}>
          <div className={styles.gaugeHead}>
            <span className={styles.gaugeLabel}>operator visibility ceiling</span>
            <span className={styles.gaugeVal}>{OP_CEIL.toFixed(1)}%</span>
          </div>
          <div className={styles.gaugeTrack}><div className={styles.gaugeFill} style={{ width: `${OP_CEIL}%` }} /></div>
          <p className={styles.gaugeNote}>
            At {(OF * 100).toFixed(0)}% of the network observed, we can name the <strong>operator</strong> for
            ~{OP_CEIL.toFixed(1)}% of transactions, the exact <strong>host</strong> for ~{HOST_CEIL.toFixed(1)}%
            {abstain ? " — and this one, even within reach, was too close to call." : " — this one is within reach."}
          </p>
          <p className={styles.gaugeNote}>modeled projection — see world.json provenance.</p>
        </div>

        {/* confidence dial (display of the tunable numbers) */}
        <dl className={styles.dial}>
          <div className={styles.dialRow}><dt>origin likelihood</dt><dd>{(data.p_origin * 100).toFixed(2)}%</dd></div>
          <div className={styles.dialRow}><dt>runner-up</dt><dd>{(data.runner_up_p * 100).toFixed(2)}%</dd></div>
          <div className={styles.dialRow}><dt>margin</dt><dd>{(data.margin * 100).toFixed(2)}%</dd></div>
        </dl>

        {/* every candidate reachable in the DOM (§5.5), ordered by likelihood */}
        <table className={styles.table}>
          <thead>
            <tr><th>the IP that told us</th><th>operator (ASN)</th><th>geo</th><th>likelihood</th><th>first heard</th></tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.i} className={!abstain && p.i === topIdx ? styles.leadRow : ""}>
                <td className={styles.mono}>
                  {maskIp(p.lane.peer_ip)}
                  {!abstain && p.i === topIdx && <span className={styles.pill} style={{ color: C.coral }}>lead</span>}
                  {p.i === earliestIdx && <span className={styles.pill} style={{ color: C.butter }}>first</span>}
                </td>
                <td className={styles.mono}>AS{p.lane.asn}</td>
                <td className={styles.mono}>{p.lane.geo_country}</td>
                <td className={styles.mono}>{(p.lane.p_origin * 100).toFixed(2)}%</td>
                <td className={styles.dim}>{usToIST(data.first_seen_us + (p.lane.announcements_ms[0] ?? 0) * 1000)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
