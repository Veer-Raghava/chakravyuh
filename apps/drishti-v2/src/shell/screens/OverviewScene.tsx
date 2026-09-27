import { useState } from "react";
import { Html, ContactShadows } from "@react-three/drei";
import { C } from "../../styles/palette";
import { satsToBTC } from "../../data/jaal";
import type { Overview, OverviewNode } from "../../three/overviewModel";
import styles from "./LeadView.module.css";

/**
 * OVERVIEW — the calm global field (§10). Every tellable transaction is one coral mark
 * in a fixed spiral: most-suspicious near the centre, size = money through it, and in
 * 3D its height = how many IPs saw it on the wire. No edges, no hairball. Idle the marks
 * are bare so the field reads at a glance; hover reveals the txid, and a click drills
 * straight into that transaction's LEAD diorama.
 */

function Mark({
  node,
  flat,
  active,
  onPick,
  onHover,
}: {
  node: OverviewNode;
  flat: boolean; // 2D mode — sit flat on the plane, no height
  active: boolean;
  onPick: () => void;
  onHover: (on: boolean) => void;
}) {
  const [hot, setHot] = useState(false);
  const open = hot || active;
  const y = flat ? 0.02 : node.lift;
  // rank 0 (most suspicious) burns brightest; the field cools outward.
  const glow = 0.5 - Math.min(0.34, node.rank * 0.03);
  const enter = () => {
    setHot(true);
    onHover(true);
  };
  const leave = () => {
    setHot(false);
    onHover(false);
  };
  return (
    <group position={[node.pos[0], y, node.pos[2]]}>
      <mesh
        scale={open ? 1.28 : 1}
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
        {flat ? (
          <cylinderGeometry args={[node.r, node.r, 0.04, 30]} />
        ) : (
          <sphereGeometry args={[node.r, 26, 26]} />
        )}
        <meshStandardMaterial
          color={C.coral}
          emissive={C.coral}
          emissiveIntensity={open ? 0.7 : glow}
          roughness={0.42}
          metalness={0.05}
        />
      </mesh>
      {/* a thin stalk in 3D so a floating mark reads as "lifted off the floor" */}
      {!flat && node.lift > 0.2 && (
        <mesh position={[0, -node.lift / 2, 0]}>
          <cylinderGeometry args={[0.008, 0.008, node.lift, 6]} />
          <meshStandardMaterial color={C.inkSoft} transparent opacity={0.35} />
        </mesh>
      )}
      {open && (
        <Html position={[0, node.r + 0.16, 0]} center className={styles.coinTag} pointerEvents="none" zIndexRange={[60, 0]}>
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

export function OverviewScene({
  data,
  flat,
  activeId,
  onPick,
  onHover,
}: {
  data: Overview;
  flat: boolean;
  activeId: string | null;
  onPick: (txId: string) => void;
  onHover: (on: boolean) => void;
}) {
  return (
    <group>
      <ContactShadows position={[0, -0.02, 0]} scale={8} blur={2.4} opacity={0.22} far={4} />
      {data.nodes.map((n) => (
        <Mark
          key={n.txId}
          node={n}
          flat={flat}
          active={activeId === n.txId}
          onPick={() => onPick(n.txId)}
          onHover={onHover}
        />
      ))}
    </group>
  );
}
