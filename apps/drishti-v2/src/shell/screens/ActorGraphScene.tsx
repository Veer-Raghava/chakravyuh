// ACTOR GRAPH SCENE — §3 "detail=actor" surface rendered as a R3F scene.
// Visual grammar mirrors GraphScene (money-over-time field) but uses distinct shapes:
//   cluster node  → teal cube (a group of addresses, owner-linked)
//   address node  → risoBlue sphere (standalone — not in any owner group)
// Edges remain blue arcs with flowing packets.
// Same hover/pick contract as GraphScene (onPick(actorId), onHover(bool)).

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line, QuadraticBezierLine, ContactShadows } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { satsToBTC } from "../../data/jaal";
import type { ActorGraph, ActorNode, ActorLink } from "../../three/actorGraphModel";
import styles from "./LeadView.module.css";

// same value rungs as GraphScene for visual continuity
const RUNGS: { y: number; label: string }[] = [
  { y: 0.08, label: "0" },
  { y: 1.29, label: "~0.05 ₿" },
  { y: 2.5, label: "~4 ₿" },
];

const istDate = (us: number) =>
  new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short" }).format(new Date(us / 1000));

// quadratic bezier point (copy of GraphScene's qbez for the packet animation)
const qbez = (a: THREE.Vector3, m: THREE.Vector3, b: THREE.Vector3, t: number, out: THREE.Vector3) => {
  const u = 1 - t;
  return out.set(
    u * u * a.x + 2 * u * t * m.x + t * t * b.x,
    u * u * a.y + 2 * u * t * m.y + t * t * b.y,
    u * u * a.z + 2 * u * t * m.z + t * t * b.z,
  );
};

function ActorNodeMesh({
  node,
  active,
  dim,
  onPick,
  onOver,
  onOut,
}: {
  node: ActorNode;
  active: boolean;
  dim: boolean;
  onPick: () => void;
  onOver: () => void;
  onOut: () => void;
}) {
  const [hot, setHot] = useState(false);
  const open = hot || active;
  // cluster = teal cube; address = risoBlue sphere
  const isCluster = node.kind === "cluster";
  const color = isCluster ? C.teal : C.risoBlue;
  const emissive = open ? 0.85 : node.connected ? 0.45 : 0.12;
  const opacity = open ? 1 : node.connected ? 0.9 : dim ? 0.14 : 0.42;
  const scale = (open ? 1.45 : node.connected ? 1 : 0.82) as number;

  return (
    <group position={node.pos}>
      <mesh
        scale={scale}
        castShadow
        onClick={(e) => { e.stopPropagation(); onPick(); }}
        onPointerOver={(e) => { e.stopPropagation(); setHot(true); onOver(); }}
        onPointerOut={() => { setHot(false); onOut(); }}
      >
        {isCluster ? (
          <boxGeometry args={[node.r * 1.6, node.r * 1.6, node.r * 1.6]} />
        ) : (
          <sphereGeometry args={[node.r, 16, 16]} />
        )}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={emissive}
          transparent
          opacity={opacity}
          roughness={0.44}
          metalness={0.05}
        />
      </mesh>
      {open && (
        <Html position={[0, node.r + 0.22, 0]} center className={styles.coinTag} pointerEvents="none" zIndexRange={[60, 0]}>
          <span className={styles.addr}>{node.label.replace(/^(cluster|addr):/, "")}</span>
          <span className={styles.amt}>{node.totalSats > 0 ? satsToBTC(node.totalSats) : "no tracked value"}</span>
          <span className={styles.role} style={{ color }}>
            {isCluster
              ? `owner group · ${node.memberCount} addresses`
              : "standalone address"}
          </span>
        </Html>
      )}
    </group>
  );
}

function ActorBridge({ link, active, reduced, phase }: { link: ActorLink; active: boolean; reduced: boolean; phase: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const a = useMemo(() => new THREE.Vector3(...link.from), [link.from]);
  const b = useMemo(() => new THREE.Vector3(...link.to), [link.to]);
  const mid = useMemo(() => {
    const m = a.clone().lerp(b, 0.5);
    m.y += 0.35 + a.distanceTo(b) * 0.12;
    m.z += 0.25;
    return m;
  }, [a, b]);
  const scratch = useMemo(() => new THREE.Vector3(), []);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = (clock.elapsedTime * 0.26 + phase) % 1;
    qbez(a, mid, b, t, scratch);
    ref.current.position.copy(scratch);
  });
  return (
    <>
      <QuadraticBezierLine
        start={link.from}
        mid={[mid.x, mid.y, mid.z]}
        end={link.to}
        color={C.teal}
        lineWidth={active ? 2.6 : 1.4}
        transparent
        opacity={active ? 0.95 : 0.4}
      />
      {!reduced && (
        <mesh ref={ref}>
          <sphereGeometry args={[active ? 0.07 : 0.05, 12, 12]} />
          <meshStandardMaterial color={C.teal} emissive={C.teal} emissiveIntensity={0.9} roughness={0.3} />
        </mesh>
      )}
    </>
  );
}

export function ActorGraphScene({
  data,
  reduced,
  onPick,
  onHover,
}: {
  data: ActorGraph;
  reduced: boolean;
  onPick: (actorId: string) => void;
  onHover: (on: boolean) => void;
}) {
  const [hoverId, setHoverId] = useState<string | null>(null);

  const litSet = useMemo(() => {
    if (!hoverId) return null;
    const s = new Set<string>([hoverId]);
    for (const l of data.links) {
      if (l.fromId === hoverId) s.add(l.toId);
      if (l.toId === hoverId) s.add(l.fromId);
    }
    return s;
  }, [hoverId, data.links]);

  // xw = same as graphModel's XW constant (5.0) for identical axis framing
  const xw = 5.0;

  const over = (id: string) => { setHoverId(id); onHover(true); };
  const out = () => { setHoverId(null); onHover(false); };

  return (
    <group>
      <ContactShadows position={[0, -0.02, 0]} scale={13} blur={2.8} opacity={0.16} far={5} />

      {/* value rungs */}
      {RUNGS.map((r) => (
        <group key={r.label}>
          <Line
            points={[[-xw, r.y, 0], [xw, r.y, 0]]}
            color={C.line}
            lineWidth={1}
            transparent
            opacity={0.28}
            dashed
            dashScale={10}
          />
          <Html position={[-xw - 0.15, r.y, 0]} className={styles.axisTag} pointerEvents="none">
            <span>{r.label}</span>
          </Html>
        </group>
      ))}
      <Html position={[-xw - 0.15, 2.5 + 0.34, 0]} className={styles.axisCap} pointerEvents="none">
        <span>value ↑</span>
      </Html>

      {data.links.map((l, i) => (
        <ActorBridge
          key={i}
          link={l}
          active={hoverId === l.fromId || hoverId === l.toId}
          reduced={reduced}
          phase={i * 0.11}
        />
      ))}
      {data.nodes.map((n) => (
        <ActorNodeMesh
          key={n.id}
          node={n}
          active={hoverId === n.id}
          dim={litSet != null && !litSet.has(n.id)}
          onPick={() => onPick(n.id)}
          onOver={() => over(n.id)}
          onOut={out}
        />
      ))}
    </group>
  );
}
