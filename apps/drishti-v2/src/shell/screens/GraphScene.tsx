import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line, QuadraticBezierLine, ContactShadows } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { satsToBTC } from "../../data/jaal";
import type { Graph, GraphNode, GraphLink } from "../../three/graphModel";
import styles from "./LeadView.module.css";

/**
 * GRAPH — the whole run as one readable field (§10, signature moment #2), laid out the way
 * forensic analysts already read bitcoin: money over time. Left→right is time; a mark's
 * HEIGHT is how much value went through it; SIZE is how many IPs saw it. The transactions
 * that chain together (an output of one spent into the next) sit forward and bright — the
 * money trails — while lone transactions recede and fade. The only edges are those value
 * bridges, drawn as soft blue arcs with a packet flowing the way the money went. Hover a
 * mark to light up what it connects to; click to trace that transaction in full.
 */

// value height guides — three faint rungs so "higher = more money" reads without a manual
const RUNGS: { y: number; label: string }[] = [
  { y: 0.08, label: "0" },
  { y: 1.29, label: "~0.05 ₿" },
  { y: 2.5, label: "~4 ₿" },
];

const istDate = (us: number) =>
  new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short" }).format(new Date(us / 1000));

function Node({
  node,
  active,
  dim,
  onPick,
  onOver,
  onOut,
}: {
  node: GraphNode;
  active: boolean;
  dim: boolean; // another node is hovered and this one isn't in its chain — recede
  onPick: () => void;
  onOver: () => void;
  onOut: () => void;
}) {
  const [hot, setHot] = useState(false);
  const open = hot || active;
  const linked = node.connected;
  // linked txs (money trails) read solid & lit; lone txs sit faint so the trails lead the eye
  const emissive = open ? 0.85 : linked ? 0.5 : 0.12;
  const opacity = open ? 1 : linked ? 0.96 : dim ? 0.14 : 0.42;
  const scale = (open ? 1.45 : linked ? 1 : 0.82) as number;
  return (
    <group position={node.pos}>
      <mesh
        scale={scale}
        rotation={[0, Math.PI / 4, 0]}
        castShadow
        onClick={(e) => {
          e.stopPropagation();
          onPick();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHot(true);
          onOver();
        }}
        onPointerOut={() => {
          setHot(false);
          onOut();
        }}
      >
        <octahedronGeometry args={[node.r]} />
        <meshStandardMaterial
          color={C.coral}
          emissive={C.coral}
          emissiveIntensity={emissive}
          transparent
          opacity={opacity}
          roughness={0.44}
          metalness={0.05}
        />
      </mesh>
      {open && (
        <Html position={[0, node.r + 0.2, 0]} center className={styles.coinTag} pointerEvents="none" zIndexRange={[60, 0]}>
          <span className={styles.addr}>{node.label.replace(/^tx:/, "")}</span>
          <span className={styles.amt}>{node.inSats > 0 ? satsToBTC(node.inSats) : "no tracked value in"}</span>
          <span className={styles.role} style={{ color: C.fluoroPink }}>
            {node.announcers} {node.announcers === 1 ? "IP saw it" : "IPs saw it"}
          </span>
        </Html>
      )}
    </group>
  );
}

// a point along a quadratic bezier (for a packet that rides the arc, not a straight chord)
const qbez = (a: THREE.Vector3, m: THREE.Vector3, b: THREE.Vector3, t: number, out: THREE.Vector3) => {
  const u = 1 - t;
  return out.set(
    u * u * a.x + 2 * u * t * m.x + t * t * b.x,
    u * u * a.y + 2 * u * t * m.y + t * t * b.y,
    u * u * a.z + 2 * u * t * m.z + t * t * b.z,
  );
};

/** A value bridge: a soft blue arc bowing up between two transactions, with a packet
 *  riding it in the direction the money moved. Lights up when either end is hovered. */
function Bridge({ link, active, reduced, phase }: { link: GraphLink; active: boolean; reduced: boolean; phase: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const a = useMemo(() => new THREE.Vector3(...link.from), [link.from]);
  const b = useMemo(() => new THREE.Vector3(...link.to), [link.to]);
  const mid = useMemo(() => {
    const m = a.clone().lerp(b, 0.5);
    m.y += 0.35 + a.distanceTo(b) * 0.12; // bow up, more for longer reaches
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
        color={C.risoBlue}
        lineWidth={active ? 2.6 : 1.4}
        transparent
        opacity={active ? 0.95 : 0.4}
      />
      {!reduced && (
        <mesh ref={ref}>
          <sphereGeometry args={[active ? 0.07 : 0.05, 12, 12]} />
          <meshStandardMaterial color={C.risoBlue} emissive={C.risoBlue} emissiveIntensity={0.9} roughness={0.3} />
        </mesh>
      )}
    </>
  );
}

export function GraphScene({
  data,
  reduced,
  onPick,
  onHover,
}: {
  data: Graph;
  reduced: boolean;
  onPick: (txId: string) => void;
  onHover: (on: boolean) => void;
}) {
  const [hoverId, setHoverId] = useState<string | null>(null);

  // which nodes are lit while hovering: the hovered one + everything it bridges to
  const litSet = useMemo(() => {
    if (!hoverId) return null;
    const s = new Set<string>([hoverId]);
    for (const l of data.links) {
      if (l.fromId === hoverId) s.add(l.toId);
      if (l.toId === hoverId) s.add(l.fromId);
    }
    return s;
  }, [hoverId, data.links]);

  const over = (id: string) => {
    setHoverId(id);
    onHover(true);
  };
  const out = () => {
    setHoverId(null);
    onHover(false);
  };

  return (
    <group>
      <ContactShadows position={[0, -0.02, 0]} scale={13} blur={2.8} opacity={0.16} far={5} />

      {/* value rungs — faint horizontal guides so height reads as money */}
      {RUNGS.map((r) => (
        <group key={r.label}>
          <Line
            points={[
              [-data.xw, r.y, 0],
              [data.xw, r.y, 0],
            ]}
            color={C.line}
            lineWidth={1}
            transparent
            opacity={0.28}
            dashed
            dashScale={10}
          />
          <Html position={[-data.xw - 0.15, r.y, 0]} className={styles.axisTag} pointerEvents="none">
            <span>{r.label}</span>
          </Html>
        </group>
      ))}
      <Html position={[-data.xw - 0.15, 2.5 + 0.34, 0]} className={styles.axisCap} pointerEvents="none">
        <span>value ↑</span>
      </Html>

      {/* time ticks along the baseline */}
      {data.ticks.map((t, i) => (
        <Html key={i} position={[t.x, -0.12, 0]} center className={styles.axisTime} pointerEvents="none">
          <span>{istDate(t.us)}</span>
        </Html>
      ))}
      <Html position={[data.xw, -0.34, 0]} center className={styles.axisTime} pointerEvents="none">
        <span>time →</span>
      </Html>

      {data.links.map((l, i) => (
        <Bridge key={i} link={l} active={hoverId === l.fromId || hoverId === l.toId} reduced={reduced} phase={i * 0.11} />
      ))}
      {data.nodes.map((n) => (
        <Node
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
