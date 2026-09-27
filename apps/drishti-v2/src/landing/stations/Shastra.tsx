import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.4 SHASTRA ★ THE HONESTY FLEX (§7). One transaction is pulled to the centre;
 * its candidate origin IPs arrange in a ring around it — the chakravyuha rings,
 * literal — each a spoke whose LENGTH is that candidate's origin likelihood. The
 * leading candidate glows coral; the rest recede in blue.
 *
 * The ★ moment is the ceiling bar: only 41.5% of transactions even contain a
 * recoverable answer, so a full-width bar splits 41.5% "possible" (coral) from
 * 58.5% "unknowable" (calm grey), with a dignified grey "no answer available"
 * card beside it — abstention is a correct output, not a failure (§6). The one
 * reframe the whole site is built to earn: no confident wrong names.
 */
const SLICE = STATIONS[4].slice;
const CEIL_POSSIBLE = 0.415;
const BAR_W = 3.4;

type Cand = { theta: number; len: number; top: boolean; ip: string; p: number; rank: number };

function buildRing() {
  const lanes = fixtures.origin.lanes;
  const pmax = Math.max(...lanes.map((l) => l.p_origin));
  const n = lanes.length;
  const cands: Cand[] = lanes.map((l, i) => ({
    theta: -Math.PI / 2 + (i / n) * Math.PI * 2,
    len: 0.45 + (l.p_origin / pmax) * 1.15,
    top: l.rank === 1,
    ip: l.peer_ip_display,
    p: l.p_origin,
    rank: l.rank,
  }));
  const top = cands.find((c) => c.top) ?? cands[0];
  const runnerUp = cands.find((c) => c.rank === 2) ?? cands[1];
  const rest = cands.filter((c) => !c.top);
  return { top, runnerUp, rest };
}

export function Shastra({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const txRef = useRef<THREE.Mesh>(null);
  const topBar = useRef<THREE.Mesh>(null);
  const topPeer = useRef<THREE.Mesh>(null);
  const restBars = useRef<THREE.InstancedMesh>(null);
  const restPeers = useRef<THREE.InstancedMesh>(null);
  const coralSeg = useRef<THREE.Mesh>(null);
  const greySeg = useRef<THREE.Mesh>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const { top, runnerUp, rest } = useMemo(buildRing, []);

  const mats = useMemo(
    () => ({
      spoke: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.6, transparent: true }),
      peer: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.6, transparent: true }),
      topSpoke: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.55, transparent: true }),
      topPeer: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.55, transparent: true }),
      tx: new THREE.MeshStandardMaterial({ color: C.ink, roughness: 0.7, transparent: true }),
      possible: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.6, transparent: true }),
      unknowable: new THREE.MeshStandardMaterial({ color: C.line, roughness: 0.9, transparent: true }),
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

    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.5);
    if (txRef.current) txRef.current.scale.setScalar(0.22 * a + 0.0001);

    // leading candidate — coral spoke from centre + marker at its end
    if (topBar.current) {
      topBar.current.position.set(Math.cos(top.theta) * top.len * 0.5 * a, Math.sin(top.theta) * top.len * 0.5 * a, 0);
      topBar.current.rotation.z = top.theta;
      topBar.current.scale.set(top.len * a + 0.0001, 0.06, 0.06);
    }
    if (topPeer.current) {
      const r = (top.len + 0.16) * a;
      topPeer.current.position.set(Math.cos(top.theta) * r, Math.sin(top.theta) * r, 0);
      topPeer.current.scale.setScalar(0.14 * a + 0.0001);
    }

    // the other candidates — blue spokes + markers
    if (restBars.current && restPeers.current) {
      for (let i = 0; i < rest.length; i++) {
        const c = rest[i];
        dummy.position.set(Math.cos(c.theta) * c.len * 0.5 * a, Math.sin(c.theta) * c.len * 0.5 * a, 0);
        dummy.rotation.set(0, 0, c.theta);
        dummy.scale.set(c.len * a + 0.0001, 0.045, 0.045);
        dummy.updateMatrix();
        restBars.current.setMatrixAt(i, dummy.matrix);
        const r = (c.len + 0.16) * a;
        dummy.position.set(Math.cos(c.theta) * r, Math.sin(c.theta) * r, 0);
        dummy.rotation.set(0, 0, 0);
        dummy.scale.setScalar(0.1 * a + 0.0001);
        dummy.updateMatrix();
        restPeers.current.setMatrixAt(i, dummy.matrix);
      }
      restBars.current.instanceMatrix.needsUpdate = true;
      restPeers.current.instanceMatrix.needsUpdate = true;
    }

    mats.tx.opacity = vis;
    mats.topSpoke.opacity = vis;
    mats.topPeer.opacity = vis;
    mats.spoke.opacity = vis * 0.85;
    mats.peer.opacity = vis * 0.85;

    // ★ the ceiling bar reveal — ramps in over the back half of the station
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
    <group ref={group} visible={false} position={[0, 0.4, 0]}>
      {/* the transaction under scrutiny — centre of the ring */}
      <mesh ref={txRef} material={mats.tx}>
        <octahedronGeometry args={[0.9]} />
      </mesh>
      {/* leading candidate — coral spoke + marker */}
      <mesh ref={topBar} material={mats.topSpoke}>
        <boxGeometry args={[1, 1, 1]} />
      </mesh>
      <mesh ref={topPeer} material={mats.topPeer}>
        <coneGeometry args={[0.6, 1.2, 5]} />
      </mesh>

      {/* the other candidates — blue spokes + markers */}
      <instancedMesh ref={restBars} args={[undefined, undefined, rest.length]} material={mats.spoke}>
        <boxGeometry args={[1, 1, 1]} />
      </instancedMesh>
      <instancedMesh ref={restPeers} args={[undefined, undefined, rest.length]} material={mats.peer}>
        <coneGeometry args={[0.6, 1.2, 5]} />
      </instancedMesh>

      {/* ★ the ceiling bar — 41.5% possible | 58.5% unknowable */}
      <mesh ref={coralSeg} position={[0, -1.95, 0]} material={mats.possible}>
        <boxGeometry args={[1, 1, 1]} />
      </mesh>
      <mesh ref={greySeg} position={[0, -1.95, 0]} material={mats.unknowable}>
        <boxGeometry args={[1, 1, 1]} />
      </mesh>
      {active && (
        <>
          {/* leading candidate readout */}
          <Html position={[0, 1.55, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "11px", whiteSpace: "nowrap", textAlign: "center", color: "var(--coral)", letterSpacing: "0.03em" }}>
              leading candidate · {top.ip} · p={top.p.toFixed(3)} · rank {top.rank}
            </div>
          </Html>
          {/* shortlist — a set you can act on, not one name */}
          <Html position={[2.15, 0.5, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", width: 156, textAlign: "left", color: "var(--riso-blue)", lineHeight: 1.5 }}>
              shortlist · 90% conf
              <br />
              sender ∈ {`{ ${runnerUp.ip} · ${top.ip} }`}
              <br />
              a set you can act on — not one name
            </div>
          </Html>
          {/* ceiling-bar labels */}
          <Html position={[-0.995, -2.4, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", whiteSpace: "nowrap", color: "var(--coral)", fontWeight: 600 }}>
              41.5% possible
            </div>
          </Html>
          <Html position={[0.705, -2.4, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", whiteSpace: "nowrap", color: "var(--ink-soft)" }}>
              58.5% unknowable
            </div>
          </Html>
          {/* the dignified grey "no answer" card — abstention as a correct output */}
          <Html position={[-2.2, -0.4, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", width: 150, textAlign: "left", color: "var(--ink-soft)", border: "1px solid var(--line)", borderRadius: 6, padding: "8px 10px", background: "rgba(236,227,208,0.55)", lineHeight: 1.5 }}>
              no answer available
              <br />
              reason · margin below floor
              <br />
              this is a correct output
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
