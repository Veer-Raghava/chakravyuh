import { useMemo, useState } from "react";
import { Html, Line, Billboard, ContactShadows } from "@react-three/drei";
import { C } from "../../styles/palette";
import { usToIST } from "../../data/jaal";
import { groupRungs } from "../../three/actorModel";
import type { Actor, ActorNode } from "../../three/actorModel";
import type { GraphTick } from "../../three/graphModel";
// the Properties drawer's shared vocabulary — LeadDetail and ActorDetail are the same
// drawer in the same voice, so they share one stylesheet rather than two that drift.
import styles from "./LeadView.module.css";

/**
 * ACTOR — the owner-level reading of the run (§10, `detail=actor`). One floor, one claim:
 * which of these addresses are the same person. Height is how wide the owner group is;
 * left→right is time. Addresses we claim share an owner are pulled to a shared point and
 * ringed — a rosette — so the claim reads as SHAPE. It is drawn only as strong as the
 * claim is: the ring's opacity IS its confidence. A CoinJoin'd address is greyed because
 * a mix severs the link, so it is not evidence; an address on a peel chain is coral, the
 * money-trail shape. When both are true the grey wins and the hover says why: the
 * disproof has to beat the clue (§6).
 *
 * Nothing here animates on its own — the floor is a still diagram, so reduced motion has
 * nothing to damp; the camera rig (in MapScreen) is what carries that branch.
 */

/** The three states a mark can be in — reusing the token semantics (§4): blue is data,
 *  coral is the trail, grey is doubt. CoinJoin outranks the peel clue.
 *  The plain blue bulk is deliberately quiet: on this floor the CLAIMS are the subject,
 *  and 800 full-strength marks buried the 84 rings that carry the argument. */
function stateOf(n: ActorNode): { color: string; emissive: number; opacity: number } {
  if (n.coinjoin > 0) return { color: C.inkSoft, emissive: 0.1, opacity: 0.42 };
  if (n.chains > 0) return { color: C.coral, emissive: 0.6, opacity: 0.97 };
  return { color: C.risoBlue, emissive: 0.16, opacity: 0.5 };
}

const istDate = (us: number) =>
  new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short" }).format(new Date(us / 1000));

function Mark({
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
  const s = stateOf(node);
  const scale = (open ? 1.6 : node.chains > 0 ? 1.05 : 0.9) as number;
  return (
    <group position={node.pos}>
      <mesh
        scale={scale}
        rotation={[0, Math.PI / 4, 0]}
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
          color={open ? C.butter : s.color}
          emissive={open ? C.butter : s.color}
          emissiveIntensity={open ? 0.9 : s.emissive}
          transparent
          opacity={open ? 1 : dim ? 0.13 : s.opacity}
          roughness={0.44}
          metalness={0.05}
        />
      </mesh>
      {open && (
        <Html position={[0, 0.18, 0]} center className={styles.coinTag} pointerEvents="none" zIndexRange={[60, 0]}>
          <span className={styles.addr}>{node.label.replace(/^addr:/, "")}</span>
          <span className={styles.role}>{node.groupLabel}</span>
          <span className={styles.amt}>
            {node.txs} {node.txs === 1 ? "transaction" : "transactions"}
          </span>
          {node.chains > 0 && (
            <span className={styles.role} style={{ color: node.coinjoin > 0 ? "var(--ink-soft)" : "var(--coral)" }}>
              on a peel chain · {node.hops} {node.hops === 1 ? "hop" : "hops"}
            </span>
          )}
          {node.coinjoin > 0 && (
            <span className={styles.role} style={{ color: "var(--ink-soft)" }}>
              {node.coinjoin} CoinJoin{node.coinjoin > 1 ? "s" : ""} · the link is not evidence
            </span>
          )}
        </Html>
      )}
    </group>
  );
}

/** The drawer for one address — the mark's facts, in the same voice as LeadDetail. */
export function ActorDetail({ node }: { node: ActorNode }) {
  const s = stateOf(node);
  return (
    <div className={styles.detail}>
      <span className={styles.dLabel} style={{ color: s.color }}>
        {node.coinjoin > 0 ? "address · CoinJoin'd" : node.chains > 0 ? "address · on a peel chain" : "address"} ●
      </span>
      <dl className={styles.rows}>
        <div className={styles.row}>
          <dt>address</dt>
          <dd className={styles.mono}>{node.label.replace(/^addr:/, "")}</dd>
        </div>
        <div className={styles.row}>
          <dt>owner group</dt>
          <dd className={styles.mono}>{node.groupLabel}</dd>
        </div>
        <div className={styles.row}>
          <dt>transactions</dt>
          <dd className={styles.mono}>{node.txs}</dd>
        </div>
        <div className={styles.row}>
          <dt>first seen</dt>
          <dd className={styles.mono}>{node.firstUs != null ? usToIST(node.firstUs) : "—"}</dd>
        </div>
        {node.chains > 0 && (
          <div className={styles.row}>
            <dt>peel chain</dt>
            <dd className={styles.mono}>
              {node.chains} {node.chains === 1 ? "chain" : "chains"} · {node.hops} hops
            </dd>
          </div>
        )}
        {node.coinjoin > 0 && (
          <div className={styles.row}>
            <dt>CoinJoin</dt>
            <dd className={styles.mono}>{node.coinjoin}</dd>
          </div>
        )}
      </dl>
      <p className={styles.honest}>
        {node.coinjoin > 0
          ? "This address passed through a CoinJoin mix. A mix severs the link between inputs and outputs, so we grey it rather than draw a trail through it."
          : node.chains > 0
            ? "On a peel chain: value stepping through a run of transactions. That is the shape of the trail, not yet a person."
            : "An ordinary address in this run. Its owner group is what ties it to others, if anything does."}
      </p>
    </div>
  );
}

export function ActorScene({
  data,
  onPick,
  onHover,
}: {
  data: Actor;
  onPick: (node: ActorNode) => void;
  onHover: (on: boolean) => void;
}) {
  const [hoverId, setHoverId] = useState<string | null>(null);
  const RUNGS = useMemo(() => groupRungs(data), [data]);

  // lit while hovering: the mark + everyone sharing its claim — the rosette is the claim,
  // so lighting the rosette is how you read who is tied to whom
  const litSet = useMemo(() => {
    if (!hoverId) return null;
    const r = data.rosettes.find((x) => x.members.includes(hoverId));
    return r ? new Set(r.members) : new Set([hoverId]);
  }, [hoverId, data.rosettes]);

  // each claim, drawn as a ring around the addresses we pulled together. Opacity IS the
  // confidence — a 0.25 claim must not look like a 0.36 one. The ring is a BILLBOARD: a
  // circle lying in the floor plane foreshortens to a flat smear from this camera, and 84
  // smears stack into a fence. Facing the camera, it reads the way a ring on paper does —
  // "these marks are one person".
  const rings = useMemo(
    () =>
      data.rosettes.map((r) => {
        const pts: [number, number, number][] = [];
        for (let i = 0; i <= 40; i++) {
          const a = (i / 40) * Math.PI * 2;
          pts.push([Math.cos(a) * r.radius, Math.sin(a) * r.radius, 0]);
        }
        return { id: r.id, pts, confidence: r.confidence, at: r.center };
      }),
    [data.rosettes],
  );

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

      {/* group-width rungs — height reads as "how many addresses we tied to one owner" */}
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
      <Html position={[-data.xw - 0.15, data.yMax + 0.34, 0]} className={styles.axisCap} pointerEvents="none">
        <span>owner group ↑</span>
      </Html>

      <Html position={[data.xw, -0.34, 0]} center className={styles.axisTime} pointerEvents="none">
        <span>time →</span>
      </Html>
      {data.ticks.map((t: GraphTick, i: number) => (
        <Html key={i} position={[t.x, -0.12, 0]} center className={styles.axisTime} pointerEvents="none">
          <span>{istDate(t.us)}</span>
        </Html>
      ))}

      {/* the same-owner claims — one ring per claim, drawn exactly as strong as it is */}
      {rings.map((r) => (
        <Billboard key={r.id} position={r.at}>
          <Line
            points={r.pts}
            color={C.coral}
            lineWidth={1.2}
            transparent
            opacity={0.16 + r.confidence * 0.9}
          />
        </Billboard>
      ))}

      {data.nodes.map((n) => (
        <Mark
          key={n.id}
          node={n}
          active={hoverId === n.id}
          dim={litSet != null && !litSet.has(n.id)}
          onPick={() => onPick(n)}
          onOver={() => over(n.id)}
          onOut={out}
        />
      ))}
    </group>
  );
}
