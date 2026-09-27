import { useMemo, useRef, useState, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";
import { panel, prose, kicker, datum } from "./panelStyle";

/**
 * ST.3 JAAL ★ THE CENTREPIECE (§7). The two streams from SETU weave into ONE
 * two-floor graph: peers ▲ on an UPPER floor (network), money (tx ◆ / clusters
 * ●) on a LOWER floor, left→right = time. The ANNOUNCE edges (peer↔tx) draw
 * LAST, in fluoro pink — the rarest colour on the whole site, saved for the one
 * line that is the entire project: "this IP told us about this money," and the
 * only edges that cross between the two floors.
 *
 * The layout is a CURATED subgraph of the real fused graph (a few transactions +
 * their announcing peers, ~2 dozen nodes) — not the 2,000-node hairball; the
 * live force-graph is the app's Map screen (§10). Deterministic placement + two
 * faint floor rules make the structure legible: no random hairball, no spin.
 * Assembly is a cheap position lerp on ~26 instances, so it holds 60fps.
 */
const SLICE = STATIONS[3].slice;
const UP = 1.2; // network floor height
const LO = -0.55; // money floor height
const SPAN = 3.4; // left→right time width

type GNode = { node_id: string; kind: string; first_us: number | null };
type GEdge = { src: string; dst: string; kind: string; ts_us: number | null };
type Placed = { pos: THREE.Vector3; shape: "peer" | "tx" | "cluster" };

function buildSubgraph() {
  const edges = (fixtures.graph.edges as unknown as GEdge[]).filter((e) => e.kind === "ANNOUNCED_BY");
  const txOrder: string[] = [];
  const peerSet = new Set<string>();
  const used: GEdge[] = [];
  for (const e of edges) {
    if (txOrder.length >= 4 && !txOrder.includes(e.src)) continue;
    if (!txOrder.includes(e.src)) txOrder.push(e.src);
    const perTx = used.filter((u) => u.src === e.src).length;
    if (perTx >= 5) continue;
    if (peerSet.size >= 16 && !peerSet.has(e.dst)) continue;
    peerSet.add(e.dst);
    used.push(e);
  }
  const clusters = (fixtures.graph.nodes as unknown as GNode[])
    .filter((n) => n.kind === "cluster")
    .slice(0, 4)
    .map((n) => n.node_id);

  // time axis: normalise announce timestamps → x (left→right = time)
  const times = used.map((e) => e.ts_us ?? 0);
  const tmin = Math.min(...times);
  const tmax = Math.max(...times);
  const xOf = (ts: number | null) =>
    tmax > tmin ? (((ts ?? tmin) - tmin) / (tmax - tmin) - 0.5) * SPAN : 0;

  const nodes = new Map<string, Placed>();
  // transactions on the lower floor, ordered along time
  txOrder.forEach((tx) => {
    const ts = Math.min(...used.filter((e) => e.src === tx).map((e) => e.ts_us ?? 0));
    nodes.set(tx, { pos: new THREE.Vector3(xOf(ts), LO, 0), shape: "tx" });
  });
  // peers on the upper floor, at their announce time, with a tidy depth stagger
  const peers = [...peerSet];
  peers.forEach((pr, i) => {
    const e = used.find((u) => u.dst === pr)!;
    const lane = (i % 3) - 1; // -1,0,1 depth lanes — deterministic, no jitter
    nodes.set(pr, {
      pos: new THREE.Vector3(xOf(e.ts_us), UP + lane * 0.14, lane * 0.35),
      shape: "peer",
    });
  });
  // clusters grouped at lower-left — the "likely same owner" halo
  clusters.forEach((cl, i) => {
    nodes.set(cl, { pos: new THREE.Vector3(-SPAN / 2 + i * 0.34, LO - 0.8, 0.1), shape: "cluster" });
  });

  const byShape = (s: Placed["shape"]) =>
    [...nodes.values()].filter((n) => n.shape === s).map((n) => n.pos);
  const announce = used.map((e) => ({ tx: nodes.get(e.src)!.pos, peer: nodes.get(e.dst)!.pos }));
  return { peers: byShape("peer"), txs: byShape("tx"), clusters: byShape("cluster"), announce };
}

export function Jaal({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const peerRef = useRef<THREE.InstancedMesh>(null);
  const txRef = useRef<THREE.InstancedMesh>(null);
  const clusterRef = useRef<THREE.InstancedMesh>(null);
  const lineRef = useRef<THREE.LineSegments>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const sg = useMemo(buildSubgraph, []);

  const linePos = useMemo(() => new Float32Array(sg.announce.length * 2 * 3), [sg.announce.length]);
  const mats = useMemo(
    () => ({
      peer: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.55, transparent: true }),
      tx: new THREE.MeshStandardMaterial({ color: C.ink, roughness: 0.7, transparent: true }),
      cluster: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.6, transparent: true }),
      floor: new THREE.MeshBasicMaterial({ color: C.line, transparent: true }),
      announce: new THREE.LineBasicMaterial({ color: C.fluoroPink, transparent: true, depthWrite: false }),
    }),
    [],
  );

  const place = (ref: RefObject<THREE.InstancedMesh | null>, list: THREE.Vector3[], a: number, scale: number, spin = 0) => {
    const m = ref.current;
    if (!m) return;
    for (let i = 0; i < list.length; i++) {
      // assemble: lerp from a collapsed centre out to the layout position
      dummy.position.copy(list[i]).multiplyScalar(a);
      dummy.rotation.set(0, spin, 0);
      dummy.scale.setScalar(scale * a);
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  };

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
    const time = reduced ? 2 : state.clock.elapsedTime;

    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.55); // assembly 0→1
    const bob = reduced ? 0 : Math.sin(time * 0.6) * 0.04; // calm idle, not a spin
    place(peerRef, sg.peers, a, 0.14, reduced ? 0 : time * 0.4);
    place(txRef, sg.txs, a, 0.17);
    place(clusterRef, sg.clusters, a, 0.13);

    // announce edges follow the assembling nodes, then LIGHT last
    for (let i = 0; i < sg.announce.length; i++) {
      const { tx, peer } = sg.announce[i];
      const o = i * 6;
      linePos[o] = tx.x * a;
      linePos[o + 1] = tx.y * a;
      linePos[o + 2] = tx.z * a;
      linePos[o + 3] = peer.x * a;
      linePos[o + 4] = peer.y * a;
      linePos[o + 5] = peer.z * a;
    }
    if (lineRef.current) {
      const attr = lineRef.current.geometry.getAttribute("position") as THREE.BufferAttribute;
      attr.array = linePos;
      attr.needsUpdate = true;
    }

    mats.peer.opacity = vis;
    mats.tx.opacity = vis;
    mats.cluster.opacity = vis;
    mats.floor.opacity = vis * 0.4 * a;
    // the announce reveal — the payoff, ramps in over the back half of the station
    const light = reduced ? 1 : THREE.MathUtils.clamp((t - 0.55) / 0.3, 0, 1);
    mats.announce.opacity = light * vis;

    // faked camera settle + a gentle whole-graph breath (no continuous yaw)
    const s = 1.12 - 0.12 * THREE.MathUtils.smoothstep(t, 0.5, 1);
    g.scale.setScalar(s);
    g.position.y = 0.45 + bob;
    g.rotation.y = reduced ? 0 : Math.sin(time * 0.25) * 0.12; // slow ±7° sway
  });

  return (
    <group ref={group} visible={false} position={[0.3, 0.45, 0]}>
      {/* two faint floor rules — make the upper (network) / lower (money) split legible */}
      <mesh position={[0, UP, -0.05]} material={mats.floor}>
        <boxGeometry args={[SPAN + 0.6, 0.012, 0.012]} />
      </mesh>
      <mesh position={[0, LO, -0.05]} material={mats.floor}>
        <boxGeometry args={[SPAN + 0.6, 0.012, 0.012]} />
      </mesh>

      {/* peers ▲ — upper floor (network) */}
      <instancedMesh ref={peerRef} args={[undefined, undefined, sg.peers.length]} material={mats.peer}>
        <coneGeometry args={[0.6, 1.1, 4]} />
      </instancedMesh>
      {/* transactions ◆ — lower floor (money) */}
      <instancedMesh ref={txRef} args={[undefined, undefined, sg.txs.length]} material={mats.tx}>
        <octahedronGeometry args={[0.7]} />
      </instancedMesh>
      {/* clusters ● — likely same owner */}
      <instancedMesh ref={clusterRef} args={[undefined, undefined, sg.clusters.length]} material={mats.cluster}>
        <sphereGeometry args={[0.6, 16, 16]} />
      </instancedMesh>
      {/* ★ ANNOUNCE edges — the only fluoro-pink on the site, drawn last */}
      <lineSegments ref={lineRef} material={mats.announce}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePos, 3]} />
        </bufferGeometry>
      </lineSegments>

      {active && (
        <>
          {/* floor tags */}
          <Html position={[-SPAN / 2 - 0.35, UP, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, color: "var(--riso-blue)", letterSpacing: "0.14em", whiteSpace: "nowrap" }}>▲ network</div>
          </Html>
          <Html position={[-SPAN / 2 - 0.35, LO, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, color: "var(--ink-soft)", letterSpacing: "0.14em", whiteSpace: "nowrap" }}>◆ money</div>
          </Html>
          {/* the one edge that is the whole project — a dial, not a grade (§6) */}
          <Html position={[0.15, 0.15, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...panel, width: 196 }}>
              <div style={kicker}>the announce edge</div>
              <div style={{ ...prose, color: "var(--fluoro-pink)", fontWeight: 600 }}>
                this IP told us about this money
              </div>
              <div style={{ ...datum, color: "var(--ink-soft)", marginTop: 6 }}>
                the only public link between wire and chain
              </div>
              <div style={{ ...datum, color: "var(--coral)", marginTop: 4 }}>
                likely same owner · confidence 0.36
              </div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
