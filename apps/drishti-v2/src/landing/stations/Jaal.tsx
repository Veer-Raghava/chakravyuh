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
 * ST.3 JAAL ★ THE CENTREPIECE (§7). Not two flat floors — an ORBIT. The money
 * (transactions ◆ + likely-same-owner clusters ●) settles into a compact core;
 * the network peers ▲ ride a slow, tilted orbital ring wrapped around it in
 * depth. The ANNOUNCE links arc DOWN from each peer to the transaction it
 * announced — smooth fluoro-pink curves, the rarest colour on the whole site,
 * saved for the one line that is the entire project: "this IP told us about this
 * money," and the only threads that cross from the ring into the core.
 *
 * A CURATED subgraph of the real fused graph (~4 txs + their peers, ~2 dozen
 * nodes) — not the 2,000-node hairball (that's the app's Map screen, §10).
 * Deterministic placement + a calm orbit make the structure legible: no random
 * hairball. Assembly + arcs are a cheap lerp on ~26 instances → holds 60fps.
 */
const SLICE = STATIONS[3].slice;
const RX = 2.15; // orbit ellipse — wide
const RY = 1.15; // orbit ellipse — short
const TILT = 1.05; // ring tipped toward the camera (radians)
const SEG = 12; // samples per announce arc

type GNode = { node_id: string; kind: string; first_us: number | null };
type GEdge = { src: string; dst: string; kind: string; ts_us: number | null };

function buildGraph() {
  const edges = (fixtures.graph.edges as unknown as GEdge[]).filter((e) => e.kind === "ANNOUNCED_BY");
  const txOrder: string[] = [];
  const peerIdx = new Map<string, number>();
  const used: { ti: number; pi: number }[] = [];
  for (const e of edges) {
    if (txOrder.length >= 4 && !txOrder.includes(e.src)) continue;
    if (!txOrder.includes(e.src)) txOrder.push(e.src);
    const ti = txOrder.indexOf(e.src);
    if (used.filter((u) => u.ti === ti).length >= 5) continue;
    if (peerIdx.size >= 16 && !peerIdx.has(e.dst)) continue;
    if (!peerIdx.has(e.dst)) peerIdx.set(e.dst, peerIdx.size);
    used.push({ ti, pi: peerIdx.get(e.dst)! });
  }
  const nTx = txOrder.length;
  const nPeer = peerIdx.size;

  // money core: transactions on a small inner ring; clusters tucked just below
  const txBase = txOrder.map((_, i) => {
    const th = -Math.PI / 2 + (i / nTx) * Math.PI * 2;
    return new THREE.Vector3(Math.cos(th) * 0.55, Math.sin(th) * 0.4 - 0.05, Math.sin(th * 1.3) * 0.25);
  });
  const clusters = (fixtures.graph.nodes as unknown as GNode[])
    .filter((n) => n.kind === "cluster")
    .slice(0, 4)
    .map((_, i) => new THREE.Vector3((i - 1.5) * 0.28, -0.75, 0.15));

  // peers: base angle + a small deterministic radius wobble → organic ring
  const peerBase = Array.from({ length: nPeer }, (_, i) => ({
    ang: (i / nPeer) * Math.PI * 2,
    rw: 0.88 + ((i * 0.61803) % 1) * 0.24, // golden-ratio spread, no jitter
  }));
  return { nTx, nPeer, txBase, clusters, peerBase, used };
}

// peer world position from its orbit angle (tilted ellipse)
function peerPos(ang: number, rw: number, out: THREE.Vector3) {
  const x = Math.cos(ang) * RX * rw;
  const yy = Math.sin(ang) * RY * rw;
  return out.set(x, yy * Math.cos(TILT) + 0.35, yy * Math.sin(TILT));
}

export function Jaal({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const peerRef = useRef<THREE.InstancedMesh>(null);
  const txRef = useRef<THREE.InstancedMesh>(null);
  const clusterRef = useRef<THREE.InstancedMesh>(null);
  const lineRef = useRef<THREE.LineSegments>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const gr = useMemo(buildGraph, []);
  const scratch = useMemo(() => ({ p: new THREE.Vector3(), t: new THREE.Vector3(), mid: new THREE.Vector3(), a: new THREE.Vector3(), b: new THREE.Vector3() }), []);

  const linePos = useMemo(() => new Float32Array(gr.used.length * SEG * 2 * 3), [gr.used.length]);
  const mats = useMemo(
    () => ({
      peer: new THREE.MeshStandardMaterial({ color: C.risoBlue, roughness: 0.55, transparent: true }),
      tx: new THREE.MeshStandardMaterial({ color: C.ink, roughness: 0.7, transparent: true }),
      cluster: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.6, transparent: true }),
      ring: new THREE.MeshBasicMaterial({ color: C.line, transparent: true, side: THREE.DoubleSide }),
      announce: new THREE.LineBasicMaterial({ color: C.fluoroPink, transparent: true, depthWrite: false }),
    }),
    [],
  );

  const place = (ref: RefObject<THREE.InstancedMesh | null>, list: THREE.Vector3[], a: number, scale: number, spin = 0) => {
    const m = ref.current;
    if (!m) return;
    for (let i = 0; i < list.length; i++) {
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
    const orbit = reduced ? 0 : time * 0.12; // calm orbital drift, not a spin

    // core: money settles in; clusters below
    place(txRef, gr.txBase, a, 0.19);
    place(clusterRef, gr.clusters, a, 0.14);

    // peers ride the tilted ring
    if (peerRef.current) {
      for (let i = 0; i < gr.nPeer; i++) {
        const { ang, rw } = gr.peerBase[i];
        peerPos(ang + orbit, rw, scratch.p).multiplyScalar(a);
        dummy.position.copy(scratch.p);
        dummy.rotation.set(0, orbit, Math.PI); // ▲ points inward-ish
        dummy.scale.setScalar(0.13 * a);
        dummy.updateMatrix();
        peerRef.current.setMatrixAt(i, dummy.matrix);
      }
      peerRef.current.instanceMatrix.needsUpdate = true;
    }

    // ★ announce arcs — smooth curves from each peer down to its tx
    for (let e = 0; e < gr.used.length; e++) {
      const { ti, pi } = gr.used[e];
      const { ang, rw } = gr.peerBase[pi];
      peerPos(ang + orbit, rw, scratch.p).multiplyScalar(a); // peer
      scratch.t.copy(gr.txBase[ti]).multiplyScalar(a); // tx
      // lift the control point toward the viewer for an arched thread
      scratch.mid.addVectors(scratch.p, scratch.t).multiplyScalar(0.5);
      scratch.mid.z += 0.7;
      scratch.mid.y += 0.25;
      const o0 = e * SEG * 2 * 3;
      for (let j = 0; j < SEG; j++) {
        const u0 = j / SEG;
        const u1 = (j + 1) / SEG;
        bezier(scratch.p, scratch.mid, scratch.t, u0, scratch.a);
        bezier(scratch.p, scratch.mid, scratch.t, u1, scratch.b);
        const o = o0 + j * 6;
        linePos[o] = scratch.a.x; linePos[o + 1] = scratch.a.y; linePos[o + 2] = scratch.a.z;
        linePos[o + 3] = scratch.b.x; linePos[o + 4] = scratch.b.y; linePos[o + 5] = scratch.b.z;
      }
    }
    if (lineRef.current) {
      const attr = lineRef.current.geometry.getAttribute("position") as THREE.BufferAttribute;
      attr.needsUpdate = true;
    }

    if (ringRef.current) {
      ringRef.current.rotation.z = orbit;
      ringRef.current.scale.setScalar(a);
    }

    mats.peer.opacity = vis;
    mats.tx.opacity = vis;
    mats.cluster.opacity = vis;
    mats.ring.opacity = vis * 0.28 * a;
    const light = reduced ? 1 : THREE.MathUtils.clamp((t - 0.5) / 0.32, 0, 1);
    mats.announce.opacity = light * vis;

    // gentle whole-graph breath + settle — no continuous yaw
    const s = 1.05 - 0.05 * THREE.MathUtils.smoothstep(t, 0.5, 1);
    g.scale.setScalar(s);
    g.rotation.y = reduced ? 0 : Math.sin(time * 0.2) * 0.1;
  });

  return (
    <group ref={group} visible={false} position={[0.55, 0.75, 0]}>
      {/* faint orbit guide — a tilted ring that makes the structure legible */}
      <mesh ref={ringRef} rotation={[TILT, 0, 0]} position={[0, 0.35, 0]} material={mats.ring}>
        <torusGeometry args={[1, 0.006, 8, 96]} />
      </mesh>

      {/* peers ▲ — the orbital ring (network) */}
      <instancedMesh ref={peerRef} args={[undefined, undefined, gr.nPeer]} material={mats.peer}>
        <coneGeometry args={[0.6, 1.1, 4]} />
      </instancedMesh>
      {/* transactions ◆ — the money core */}
      <instancedMesh ref={txRef} args={[undefined, undefined, gr.nTx]} material={mats.tx}>
        <octahedronGeometry args={[0.7]} />
      </instancedMesh>
      {/* clusters ● — likely same owner */}
      <instancedMesh ref={clusterRef} args={[undefined, undefined, gr.clusters.length]} material={mats.cluster}>
        <sphereGeometry args={[0.6, 16, 16]} />
      </instancedMesh>
      {/* ★ ANNOUNCE arcs — the only fluoro-pink on the site, drawn last */}
      <lineSegments ref={lineRef} material={mats.announce}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePos, 3]} />
        </bufferGeometry>
      </lineSegments>

      {active && (
        <>
          <Html position={[0, -1.15, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, color: "var(--ink-soft)", letterSpacing: "0.14em", whiteSpace: "nowrap" }}>◆ the money</div>
          </Html>
          <Html position={[0, 1.7, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...datum, color: "var(--riso-blue)", letterSpacing: "0.14em", whiteSpace: "nowrap" }}>▲ the network</div>
          </Html>
          {/* the one link that is the whole point — you set how sure, not us (§6) */}
          <Html position={[2.15, -0.25, 0]} center distanceFactor={6} pointerEvents="none">
            <div style={{ ...panel, width: 196 }}>
              <div style={kicker}>the key link</div>
              <div style={{ ...prose, color: "var(--fluoro-pink)", fontWeight: 600 }}>
                which computer told us about which payment
              </div>
              <div style={{ ...datum, color: "var(--ink-soft)", marginTop: 6 }}>
                the one link between the network and the money
              </div>
              <div style={{ ...datum, color: "var(--coral)", marginTop: 4 }}>
                likely the same owner · you set how sure
              </div>
            </div>
          </Html>
        </>
      )}
    </group>
  );
}

// quadratic bezier into `out`
function bezier(p0: THREE.Vector3, p1: THREE.Vector3, p2: THREE.Vector3, u: number, out: THREE.Vector3) {
  const iu = 1 - u;
  out.set(
    iu * iu * p0.x + 2 * iu * u * p1.x + u * u * p2.x,
    iu * iu * p0.y + 2 * iu * u * p1.y + u * u * p2.y,
    iu * iu * p0.z + 2 * iu * u * p1.z + u * u * p2.z,
  );
  return out;
}
