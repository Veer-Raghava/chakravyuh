import { useState } from "react";
import { Html, Line, ContactShadows } from "@react-three/drei";
import { C } from "../../styles/palette";
import { satsToBTC } from "../../data/jaal";
import { Bead, Arrow } from "./LeadView";
import type { Graph, GraphNode } from "../../three/graphModel";
import styles from "./LeadView.module.css";

/**
 * GRAPH — the whole run as one readable field (§10, signature moment #2). Every ◆ is a
 * transaction, placed left→right by time and lifted by how many IPs saw it. The blue
 * threads are the only edges: value that flowed from one transaction into the next. Most
 * marks stand alone; the linked ones (bright coral) are the chains worth following. Hover
 * reveals the txid; click drills straight into that transaction's LEAD flow.
 */

function Node({
  node,
  active,
  onPick,
  onHover,
}: {
  node: GraphNode;
  active: boolean;
  onPick: () => void;
  onHover: (on: boolean) => void;
}) {
  const [hot, setHot] = useState(false);
  const open = hot || active;
  // linked txs (part of a money chain) burn coral; islands sit dim so the eye follows flow
  const glow = node.connected ? 0.5 : 0.14;
  const enter = () => {
    setHot(true);
    onHover(true);
  };
  const leave = () => {
    setHot(false);
    onHover(false);
  };
  return (
    <group position={node.pos}>
      <mesh
        scale={open ? 1.4 : 1}
        rotation={[0, Math.PI / 4, 0]}
        castShadow
        onClick={(e) => {
          e.stopPropagation();
          onPick();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          enter();
        }}
        onPointerOut={leave}
      >
        <octahedronGeometry args={[node.r]} />
        <meshStandardMaterial
          color={C.coral}
          emissive={C.coral}
          emissiveIntensity={open ? 0.75 : glow}
          roughness={0.44}
          metalness={0.05}
        />
      </mesh>
      {/* a thin stalk to the floor so a lifted mark reads as "loud on the wire" */}
      {node.pos[1] > 0.3 && (
        <mesh position={[0, -node.pos[1] / 2, 0]}>
          <cylinderGeometry args={[0.006, 0.006, node.pos[1], 6]} />
          <meshStandardMaterial color={C.inkSoft} transparent opacity={0.25} />
        </mesh>
      )}
      {open && (
        <Html position={[0, node.r + 0.18, 0]} center className={styles.coinTag} pointerEvents="none" zIndexRange={[60, 0]}>
          <span className={styles.addr}>{node.label.replace(/^tx:/, "")}</span>
          <span className={styles.amt}>{satsToBTC(node.inSats)}</span>
          <span className={styles.role} style={{ color: C.fluoroPink }}>
            {node.announcers} {node.announcers === 1 ? "IP saw it" : "IPs saw it"}
          </span>
        </Html>
      )}
    </group>
  );
}

/** A value bridge: quiet blue base line + a packet moving in the direction the money
 *  went (tx → later tx). Reduced motion swaps the bead for a static arrowhead. */
function Link({ from, to, reduced, phase }: { from: [number, number, number]; to: [number, number, number]; reduced: boolean; phase: number }) {
  return (
    <>
      <Line points={[from, to]} color={C.risoBlue} lineWidth={1.5} transparent opacity={0.5} />
      {reduced ? <Arrow from={from} to={to} color={C.risoBlue} /> : <Bead from={from} to={to} color={C.risoBlue} phase={phase} speed={0.28} size={0.055} />}
    </>
  );
}

export function GraphScene({
  data,
  reduced,
  activeId,
  onPick,
  onHover,
}: {
  data: Graph;
  reduced: boolean;
  activeId: string | null;
  onPick: (txId: string) => void;
  onHover: (on: boolean) => void;
}) {
  return (
    <group>
      <ContactShadows position={[0, -0.02, 0]} scale={12} blur={2.6} opacity={0.2} far={5} />
      {data.links.map((l, i) => (
        <Link key={i} from={l.from} to={l.to} reduced={reduced} phase={i * 0.11} />
      ))}
      {data.nodes.map((n) => (
        <Node key={n.id} node={n} active={activeId === n.id} onPick={() => onPick(n.id)} onHover={onHover} />
      ))}
    </group>
  );
}
