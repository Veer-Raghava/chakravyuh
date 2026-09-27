import { useMemo, useRef, useState, type RefObject } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.3 JAAL ★ THE CENTREPIECE (§7). The two streams from SETU weave into ONE
 * two-floor graph: peers ▲ on an upper floor, money (tx ◆ / clusters ●) on a
 * lower floor, left→right = time. The ANNOUNCE edges (peer↔tx) draw LAST, in
 * fluoro pink — the rarest colour on the whole site, saved for the one line
 * that is the entire project: "this IP told us about this money."
 *
 * The layout is a CURATED subgraph of the real fused graph (a few transactions
 * + their announcing peers, ~2 dozen nodes) — not the 2,000-node hairball; the
 * live force-graph is the app's Map screen, not the landing (§10). Assembly is
 * a cheap position lerp on ~26 instances, so it holds 60fps.
 *
 * // ponytail: no bloom dep installed — the announce edges read because they're
 * // the ONLY fluoro-pink on screen; add EffectComposer bloom only if it needs pop.
 */
const SLICE = STATIONS[3].slice;

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
    if (perTx >= 6) continue;
    if (peerSet.size >= 18 && !peerSet.has(e.dst)) continue;
    peerSet.add(e.dst);
    used.push(e);
  }
  // clusters (●) for the "likely same owner" halo — first few from the graph
  const clusters = (fixtures.graph.nodes as unknown as GNode[])
    .filter((n) => n.kind === "cluster")
    .slice(0, 4)
    .map((n) => n.node_id);

  // time axis: normalise the announce timestamps → x (left→right = time)
  const times = used.map((e) => e.ts_us ?? 0);
  const tmin = Math.min(...times);
  const tmax = Math.max(...times);
  const xOf = (ts: number | null) =>
    tmax > tmin ? ((ts ?? tmin) - tmin) / (tmax - tmin) - 0.5 : 0;

  const nodes = new Map<string, Placed>();
  txOrder.forEach((tx, i) => {
    const ts = Math.min(...used.filter((e) => e.src === tx).map((e) => e.ts_us ?? 0));
    nodes.set(tx, {
      pos: new THREE.Vector3(xOf(ts) * 3.4, -0.6, (i - 1.5) * 0.3),
      shape: "tx",
    });
  });
  const peers = [...peerSet];
  peers.forEach((pr, i) => {
    const e = used.find((u) => u.dst === pr)!;
    nodes.set(pr, {
      pos: new THREE.Vector3(
        xOf(e.ts_us) * 3.4 + Math.sin(i) * 0.22,
        1.15 + Math.cos(i * 1.7) * 0.16,
        (i % 5) * 0.24 - 0.5,
      ),
      shape: "peer",
    });
  });
  clusters.forEach((cl, i) => {
    nodes.set(cl, {
      pos: new THREE.Vector3(-0.5 + i * 0.32, -1.35, i * 0.18 - 0.25),
      shape: "cluster",
    });
  });

  const byShape = (s: Placed["shape"]) =>
    [...nodes.values()].filter((n) => n.shape === s).map((n) => n.pos);
  const announce = used.map((e) => ({
    tx: nodes.get(e.src)!.pos,
    peer: nodes.get(e.dst)!.pos,
  }));
  return {
    peers: byShape("peer"),
    txs: byShape("tx"),
    clusters: byShape("cluster"),
    announce,
  };
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

  const linePos = useMemo(
    () => new Float32Array(sg.announce.length * 2 * 3),
    [sg.announce.length],
  );
  const mats = useMemo(
    () => ({
      peer: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.6, transparent: true }),
      tx: new THREE.MeshStandardMaterial({ color: C.ink, roughness: 0.7, transparent: true }),
      cluster: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.6, transparent: true }),
      announce: new THREE.LineBasicMaterial({ color: C.fluoroPink, transparent: true, depthWrite: false }),
    }),
    [],
  );

  const place = (
    ref: RefObject<THREE.InstancedMesh | null>,
    list: THREE.Vector3[],
    a: number,
    scale: number,
  ) => {
    const m = ref.current;
    if (!m) return;
    for (let i = 0; i < list.length; i++) {
      // assemble: lerp from a collapsed centre out to the layout position
      dummy.position.copy(list[i]).multiplyScalar(a);
      dummy.scale.setScalar(scale * a);
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  };

  useFrame((_, delta) => {
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

    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.55); // assembly 0→1
    place(peerRef, sg.peers, a, 0.13);
    place(txRef, sg.txs, a, 0.16);
    place(clusterRef, sg.clusters, a, 0.12);

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

    const nodeVis = vis;
    mats.peer.opacity = nodeVis;
    mats.tx.opacity = nodeVis;
    mats.cluster.opacity = nodeVis;
    // the announce reveal — the payoff, ramps in over the back half of the station
    const light = reduced ? 1 : THREE.MathUtils.clamp((t - 0.6) / 0.3, 0, 1);
    mats.announce.opacity = light * vis;

    // camera pull-back, faked: settle scale 1.12→1.0, slow drift
    const s = 1.12 - 0.12 * THREE.MathUtils.smoothstep(t, 0.5, 1);
    g.scale.setScalar(s);
    if (!reduced) g.rotation.y += delta * 0.03;
  });

  return (
    <group ref={group} visible={false} position={[0.5, 0.45, 0]}>
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

      {/* the cluster halo tag — a dial, not a grade (§6) */}
      {active && (
        <Html position={[-0.4, -1.75, 0]} center distanceFactor={6} pointerEvents="none">
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              whiteSpace: "nowrap",
              color: "var(--coral)",
              letterSpacing: "0.04em",
            }}
          >
            likely same owner · confidence 0.36
          </div>
        </Html>
      )}
    </group>
  );
}
