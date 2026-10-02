import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import {
  Html,
  Line,
  ContactShadows,
  QuadraticBezierLine,
} from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { satsToBTC, usToIST } from "../../data/jaal";
import {
  MONEY_Y,
  WIRE_Y,
  type Lead,
  type MoneyNode,
  type Announcer,
  type Role,
} from "../../three/leadModel";
import styles from "./LeadView.module.css";

/**
 * LEAD — one suspect transaction as a lit paper diorama (§10, readability-first).
 * WHO (sender coins, left) → SENT WHAT (animated flow) → TO WHOM (receiver / change
 * coins, right) → WHICH IPs saw it (pink beacons on the wire above, threads down).
 * Every mark is a forensic object with an obvious role — you shouldn't need the legend.
 */

// colour = MEANING, so roles read without a key: blue = money's source, butter = where
// it landed (look here), muted grey = change looping back to self.
const ROLE_COLOR: Record<Role, string> = {
  sender: C.risoBlue,
  receiver: C.butter,
  change: C.inkSoft,
};
const ROLE_WORD: Record<Role, string> = {
  sender: "sender",
  receiver: "receiver",
  change: "possible change",
};
const v = (p: [number, number, number]) => new THREE.Vector3(...p);

/** A wallet — a coin resting on the money floor. Emissive lift when it's the payee.
 *  Idle it wears only a compact amount chip; the full address/role reveal on hover or
 *  when picked, so the diorama stays readable and the 3D objects stay visible. */
export function Coin({
  node,
  selected,
  onSelect,
  onHover,
}: {
  node: MoneyNode;
  selected: boolean;
  onSelect: () => void;
  onHover: (on: boolean) => void;
}) {
  const [hot, setHot] = useState(false);
  const color = ROLE_COLOR[node.role];
  const lift = node.role === "receiver" ? 0.18 : 0.06; // the payee glows a touch
  const open = hot || selected;
  const s = selected ? 1.35 : 1;
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
        scale={s}
        castShadow
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          enter();
        }}
        onPointerOut={leave}
      >
        <cylinderGeometry args={[0.24, 0.24, 0.1, 30]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={selected ? 0.5 : lift}
          roughness={0.5}
          metalness={0.05}
        />
      </mesh>
      {open ? (
        <Html
          position={[0, 0.34, 0]}
          center
          className={styles.coinTag}
          pointerEvents="none"
          zIndexRange={[60, 0]}
        >
          <span className={styles.addr}>
            {node.label.replace(/^addr:/, "")}
          </span>
          <span className={styles.amt}>{satsToBTC(node.sats)}</span>
          <span className={styles.role} style={{ color }}>
            {ROLE_WORD[node.role]}
            {node.count > 1
              ? ` · ${node.count} ${node.role === "sender" ? "inputs" : "outputs"}`
              : ""}
          </span>
        </Html>
      ) : (
        <Html
          position={[0, 0.28, 0]}
          center
          className={styles.miniTag}
          pointerEvents="none"
        >
          <span className={styles.miniAmt} style={{ color }}>
            {satsToBTC(node.sats)}
          </span>
        </Html>
      )}
    </group>
  );
}

/** The transaction — a coral block (the "block" in blockchain) at the centre where
 *  every flow meets. Gently turns so the eye lands on it first. */
function TxBlock({
  lead,
  reduced,
  selected,
  onSelect,
  onHover,
}: {
  lead: Lead;
  reduced: boolean;
  selected: boolean;
  onSelect: () => void;
  onHover: (on: boolean) => void;
}) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (!reduced && ref.current) ref.current.rotation.y += dt * 0.4;
  });
  return (
    <group position={lead.txPos}>
      <mesh
        ref={ref}
        scale={selected ? 1.25 : 1}
        castShadow
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          onHover(true);
        }}
        onPointerOut={() => onHover(false)}
      >
        <boxGeometry args={[0.44, 0.44, 0.44]} />
        <meshStandardMaterial
          color={C.coral}
          emissive={C.coral}
          emissiveIntensity={0.28}
          roughness={0.45}
        />
      </mesh>
      <Html
        position={[0, -0.5, 0]}
        center
        className={styles.txTag}
        pointerEvents="none"
      >
        <span className={styles.txWord}>the transaction</span>
        <span className={styles.addr}>{lead.txLabel.replace(/^tx:/, "")}</span>
      </Html>
    </group>
  );
}

/** An announcing IP — a beacon pin on the wire above, tip pointing down at the tx it
 *  told us about. Pink, to tie it to its thread. The IP string is hidden until hover /
 *  select — nine of these would otherwise smother the frame. */
function Pin({
  a,
  selected,
  onSelect,
  onHover,
}: {
  a: Announcer;
  selected: boolean;
  onSelect: () => void;
  onHover: (on: boolean) => void;
}) {
  const [hot, setHot] = useState(false);
  const open = hot || selected;
  const enter = () => {
    setHot(true);
    onHover(true);
  };
  const leave = () => {
    setHot(false);
    onHover(false);
  };
  return (
    <group position={a.pos}>
      <mesh
        scale={selected ? 1.4 : 1}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          enter();
        }}
        onPointerOut={leave}
      >
        <sphereGeometry args={[0.13, 20, 20]} />
        <meshStandardMaterial
          color={C.fluoroPink}
          emissive={C.fluoroPink}
          emissiveIntensity={0.4}
          roughness={0.4}
        />
      </mesh>
      <mesh position={[0, -0.17, 0]}>
        <coneGeometry args={[0.09, 0.22, 18]} />
        <meshStandardMaterial
          color={C.fluoroPink}
          emissive={C.fluoroPink}
          emissiveIntensity={0.25}
          roughness={0.5}
        />
      </mesh>
      {open && (
        <Html
          position={[0, 0.28, 0]}
          center
          className={styles.pinTag}
          pointerEvents="none"
          zIndexRange={[70, 0]}
        >
          <span className={styles.addr}>{a.label.replace(/^peer:/, "")}</span>
        </Html>
      )}
    </group>
  );
}

/** A packet of value travelling along an edge in the direction money (or an
 *  announcement) actually moved — the whole point of the animated flow. */
export function Bead({
  from,
  to,
  color,
  phase = 0,
  speed = 0.35,
  size = 0.07,
}: {
  from: [number, number, number];
  to: [number, number, number];
  color: string;
  phase?: number;
  speed?: number;
  size?: number;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const a = useMemo(() => v(from), [from]);
  const b = useMemo(() => v(to), [to]);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = (clock.elapsedTime * speed + phase) % 1;
    ref.current.position.lerpVectors(a, b, t);
  });
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[size, 12, 12]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.9}
        roughness={0.3}
      />
    </mesh>
  );
}

/** Reduced-motion stand-in for the bead: a static arrowhead near the destination. */
export function Arrow({
  from,
  to,
  color,
}: {
  from: [number, number, number];
  to: [number, number, number];
  color: string;
}) {
  const { pos, quat } = useMemo(() => {
    const a = v(from);
    const b = v(to);
    const p = a.clone().lerp(b, 0.78);
    const q = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      b.clone().sub(a).normalize(),
    );
    return { pos: p, quat: q };
  }, [from, to]);
  return (
    <mesh position={pos} quaternion={quat}>
      <coneGeometry args={[0.08, 0.2, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.35}
        roughness={0.5}
      />
    </mesh>
  );
}

/** Money edge: quiet base line + a moving packet. Change loops read dashed and muted. */
function FlowEdge({
  flow,
  reduced,
  phase,
}: {
  flow: Lead["flows"][number];
  reduced: boolean;
  phase: number;
}) {
  const color = ROLE_COLOR[flow.role];
  const change = flow.role === "change";
  return (
    <>
      <Line
        points={[flow.from, flow.to]}
        color={color}
        lineWidth={change ? 1.2 : 2}
        transparent
        opacity={change ? 0.4 : 0.7}
        dashed={change}
        dashScale={change ? 9 : 1}
      />
      {reduced ? (
        <Arrow from={flow.from} to={flow.to} color={color} />
      ) : (
        <Bead from={flow.from} to={flow.to} color={color} phase={phase} />
      )}
    </>
  );
}

/** The fusion, made physical: the pink announce thread from an IP down to the tx.
 *  Loudest edge in the frame — it IS the product thesis. */
function Thread({
  thread,
  reduced,
  phase,
}: {
  thread: Lead["threads"][number];
  reduced: boolean;
  phase: number;
}) {
  return (
    <>
      <Line
        points={[thread.from, thread.to]}
        color={C.fluoroPink}
        lineWidth={1.6}
        transparent
        opacity={0.85}
      />
      {!reduced && (
        <Bead
          from={thread.from}
          to={thread.to}
          color={C.fluoroPink}
          phase={phase}
          speed={0.5}
          size={0.05}
        />
      )}
    </>
  );
}

/** "Likely same owner" — a teal thread dipping below the floor from a change output
 *  back to the sender that funded it. The change-loop, shown honestly as a soft claim. */
function OwnerLink({
  from,
  to,
}: {
  from: [number, number, number];
  to: [number, number, number];
}) {
  const mid = useMemo(
    () =>
      [(from[0] + to[0]) / 2, MONEY_Y - 0.7, (from[2] + to[2]) / 2] as [
        number,
        number,
        number,
      ],
    [from, to],
  );
  return (
    <QuadraticBezierLine
      start={from}
      mid={mid}
      end={to}
      color={C.teal}
      lineWidth={1.1}
      dashed
      dashScale={12}
      transparent
      opacity={0.6}
    />
  );
}

// What the user picked in the scene — drives the reused Properties drawer.
export type LeadSelection =
  | { type: "tx" }
  | { type: "money"; node: MoneyNode }
  | { type: "ip"; ann: Announcer };

const selId = (lead: Lead, sel: LeadSelection | null): string | null =>
  sel == null
    ? null
    : sel.type === "tx"
      ? lead.txId
      : sel.type === "money"
        ? sel.node.id
        : sel.ann.id;

/** The whole lit diorama for one lead. Assembles floors, flows, threads, owner links,
 *  and every forensic object so a newcomer reads WHO → SENT WHAT → TO WHOM → WHICH IPs. */
export function LeadScene({
  lead,
  reduced,
  selection,
  onSelect,
  onHover,
}: {
  lead: Lead;
  reduced: boolean;
  selection: LeadSelection | null;
  onSelect: (sel: LeadSelection) => void;
  onHover: (on: boolean) => void;
}) {
  const selected = selId(lead, selection);

  // Ownership hypotheses remain in the evidence panel; avoid inventing pairwise ties.
  const ownerPairs: {
    from: [number, number, number];
    to: [number, number, number];
  }[] = [];

  return (
    <group>
      <ContactShadows
        position={[0, MONEY_Y - 0.11, 0]}
        scale={9}
        blur={2.4}
        opacity={0.26}
        far={4}
      />

      <Html
        position={[-3.5, WIRE_Y + 0.42, 0]}
        className={styles.floorTag}
        pointerEvents="none"
      >
        <span>THE WIRE · the IPs that saw it</span>
      </Html>


      {lead.flows.map((f, i) => (
        <FlowEdge key={`f${i}`} flow={f} reduced={reduced} phase={i * 0.2} />
      ))}
      {lead.threads.map((t, i) => (
        <Thread key={`t${i}`} thread={t} reduced={reduced} phase={i * 0.13} />
      ))}
      {ownerPairs.map((p, i) => (
        <OwnerLink key={`o${i}`} from={p.from} to={p.to} />
      ))}
      {ownerPairs.length > 0 && (
        <Html
          position={[0, MONEY_Y - 0.85, 0]}
          center
          className={styles.ownerTag}
          pointerEvents="none"
        >
          <span>likely same owner</span>
        </Html>
      )}

      <TxBlock
        lead={lead}
        reduced={reduced}
        selected={selected === lead.txId}
        onSelect={() => onSelect({ type: "tx" })}
        onHover={onHover}
      />
      {lead.senders.map((s) => (
        <Coin
          key={s.id}
          node={s}
          selected={selected === s.id}
          onSelect={() => onSelect({ type: "money", node: s })}
          onHover={onHover}
        />
      ))}
      {lead.receivers.map((r) => (
        <Coin
          key={r.id}
          node={r}
          selected={selected === r.id}
          onSelect={() => onSelect({ type: "money", node: r })}
          onHover={onHover}
        />
      ))}
      {lead.announcers.map((a) => (
        <Pin
          key={a.id}
          a={a}
          selected={selected === a.id}
          onSelect={() => onSelect({ type: "ip", ann: a })}
          onHover={onHover}
        />
      ))}
    </group>
  );
}

/** Properties-drawer body for whatever is selected in the LEAD scene (§10.3). Node-only
 *  selection; each panel says plainly what the object is and its one honest caveat. */
export function LeadDetail({ lead, sel }: { lead: Lead; sel: LeadSelection }) {
  if (sel.type === "tx") {
    return (
      <div className={styles.detail}>
        <span className={styles.dLabel}>the transaction ◆</span>
        <dl className={styles.rows}>
          <div className={styles.row}>
            <dt>txid</dt>
            <dd className={styles.mono}>{lead.txLabel.replace(/^tx:/, "")}</dd>
          </div>
          <div className={styles.row}>
            <dt>first seen</dt>
            <dd className={styles.mono}>
              {lead.firstUs != null ? usToIST(lead.firstUs) : "—"}
            </dd>
          </div>
          <div className={styles.row}>
            <dt>money in · out</dt>
            <dd className={styles.mono}>
              {satsToBTC(lead.totalInSats)} · {satsToBTC(lead.totalOutSats)}
            </dd>
          </div>
          <div className={styles.row}>
            <dt>senders · receivers</dt>
            <dd className={styles.mono}>
              {lead.senders.length} · {lead.receivers.length}
            </dd>
          </div>
          <div className={styles.row}>
            <dt>announced by</dt>
            <dd className={styles.mono}>{lead.announcers.length} IPs</dd>
          </div>
        </dl>
        <p className={styles.honest}>{lead.why}</p>
      </div>
    );
  }

  if (sel.type === "money") {
    const n = sel.node;
    return (
      <div className={styles.detail}>
        <span className={styles.dLabel} style={{ color: ROLE_COLOR[n.role] }}>
          {ROLE_WORD[n.role]} ●
        </span>
        <dl className={styles.rows}>
          <div className={styles.row}>
            <dt>address</dt>
            <dd className={styles.mono}>{n.label.replace(/^addr:/, "")}</dd>
          </div>
          <div className={styles.row}>
            <dt>value on this tx</dt>
            <dd className={styles.mono}>{satsToBTC(n.sats)}</dd>
          </div>
          <div className={styles.row}>
            <dt>{n.role === "sender" ? "inputs" : "outputs"} here</dt>
            <dd className={styles.mono}>{n.count}</dd>
          </div>
        </dl>
        <p className={styles.honest}>
          {n.role === "change"
            ? "Flagged change: a likely-same-owner link ties this back to a sender. This is an ownership hypothesis, not proof of the same controller."
            : n.role === "sender"
              ? "A wallet that funded this transaction."
              : "A wallet paid by this transaction."}
        </p>
      </div>
    );
  }

  const a = sel.ann;
  return (
    <div className={styles.detail}>
      <span className={styles.dLabel} style={{ color: C.fluoroPink }}>
        the IP that told us ▲
      </span>
      <dl className={styles.rows}>
        <div className={styles.row}>
          <dt>announcing IP</dt>
          <dd className={styles.mono}>{a.label.replace(/^peer:/, "")}</dd>
        </div>
        <div className={styles.row}>
          <dt>network operator (ASN)</dt>
          <dd className={styles.mono}>{a.asn ?? "—"}</dd>
        </div>
        <div className={styles.row}>
          <dt>heard at</dt>
          <dd className={styles.mono}>
            {a.tsUs != null ? usToIST(a.tsUs) : "—"}
          </dd>
        </div>
      </dl>
      <p className={styles.warn}>
        An IP that told us, usually a relay, not the sender.
      </p>
    </div>
  );
}
