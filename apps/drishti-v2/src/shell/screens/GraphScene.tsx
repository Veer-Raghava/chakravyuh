import { useMemo, useState } from "react";
import { Html, Line, ContactShadows } from "@react-three/drei";
import { C } from "../../styles/palette";
import { satsToBTC, usToIST, peerStats } from "../../data/jaal";
import { Bead, Arrow } from "./LeadView";
import { FLOOR_Y, type Jaal, type LaidNode, type Vec3 } from "../../three/jaalLayout";
import styles from "./LeadView.module.css";

/**
 * GRAPH · JAAL — the whole run as ONE two-floor diorama (§10, signature moment #2), in the
 * exact visual language of the LEAD trace so the two feel like one world:
 *   • THE WIRE (upper floor)  — every announcing peer ▲, a calm sky of relays.
 *   • THE BLOCKCHAIN (lower floor) — every transaction ◆, resting on the money floor.
 *   • the fusion is REVEALED, never dumped: hover / focus a tx and its pink announce
 *     threads rain UP to the peers that saw it, its coins fan out, its money flows light.
 *   • focus a peer and its pink threads drop DOWN onto every tx it announced.
 *   • focus an address and its money flows light up on the floor.
 * Nothing crosses the floor gap except the pink threads — the thesis, made physical.
 */

const WIRE_Y = FLOOR_Y;
const MONEY_Y = -FLOOR_Y;
const EXT_X = 3.85; // a hair beyond the layout's half-width, for the floor frames
const EXT_Z = 1.9;

type AddrRef = { id: string; pos: Vec3; label: string; sats: number };
type Reveal = { inputs: AddrRef[]; outputs: AddrRef[]; peers: { id: string; pos: Vec3; label: string }[] };

const istDate = (us: number) =>
  new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short" }).format(new Date(us / 1000));

/** A transaction ◆ resting on the money floor — the same coral block as the trace view.
 *  Calm at rest; lifts and labels when hovered/focused; recedes when another node owns
 *  the frame. Click opens its full flow in TRACE. */
function Tx({
  node,
  active,
  dim,
  onPick,
  onOver,
  onOut,
}: {
  node: LaidNode;
  active: boolean;
  dim: boolean;
  onPick: () => void;
  onOver: () => void;
  onOut: () => void;
}) {
  const [hot, setHot] = useState(false);
  const open = hot || active;
  const emissive = open ? 0.5 : 0.16;
  const opacity = open ? 1 : dim ? 0.16 : 0.9;
  const scale = open ? 1.4 : 1;
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
        <boxGeometry args={[0.17, 0.17, 0.17]} />
        <meshStandardMaterial
          color={C.coral}
          emissive={C.coral}
          emissiveIntensity={emissive}
          transparent
          opacity={opacity}
          roughness={0.45}
          metalness={0.05}
        />
      </mesh>
      {open && (
        <Html position={[0, 0.24, 0]} center className={styles.coinTag} pointerEvents="none" zIndexRange={[60, 0]}>
          <span className={styles.addr}>{node.label.replace(/^tx:/, "")}</span>
          {node.firstUs != null && <span className={styles.amt}>{istDate(node.firstUs)}</span>}
          <span className={styles.role} style={{ color: C.risoBlue }}>click to trace</span>
        </Html>
      )}
    </group>
  );
}

/** An announcing peer ▲ on the wire floor — a quiet pink pin (beacon + down-tip), the same
 *  object as the trace view's IP pin. A calm sky of relays at rest; brightens when it or a
 *  tx it announced is in focus. Click pins it and drops its threads onto every tx it saw. */
function Peer({
  node,
  active,
  dim,
  onPick,
  onOver,
  onOut,
}: {
  node: LaidNode;
  active: boolean;
  dim: boolean;
  onPick: () => void;
  onOver: () => void;
  onOut: () => void;
}) {
  const [hot, setHot] = useState(false);
  const open = hot || active;
  const emissive = open ? 0.6 : 0.18;
  const opacity = open ? 1 : dim ? 0.12 : 0.5;
  const scale = open ? 1.4 : 0.82;
  return (
    <group position={node.pos}>
      <group
        scale={scale}
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
        <mesh>
          <sphereGeometry args={[0.085, 16, 16]} />
          <meshStandardMaterial color={C.fluoroPink} emissive={C.fluoroPink} emissiveIntensity={emissive} transparent opacity={opacity} roughness={0.4} />
        </mesh>
        <mesh position={[0, -0.12, 0]}>
          <coneGeometry args={[0.06, 0.16, 14]} />
          <meshStandardMaterial color={C.fluoroPink} emissive={C.fluoroPink} emissiveIntensity={emissive * 0.6} transparent opacity={opacity} roughness={0.5} />
        </mesh>
      </group>
      {open && (
        <Html position={[0, 0.22, 0]} center className={styles.pinTag} pointerEvents="none" zIndexRange={[70, 0]}>
          <span className={styles.addr}>{node.label.replace(/^peer:/, "")}</span>
        </Html>
      )}
    </group>
  );
}

/** A revealed wallet ● — small coin fanned out around a focused tx. Blue = funded it,
 *  butter = paid by it, teal = the likely-same-owner tie. Click opens its properties. */
function Coin({ a, color, onPick }: { a: AddrRef; color: string; onPick: () => void }) {
  const [hot, setHot] = useState(false);
  return (
    <group position={a.pos}>
      <mesh
        scale={hot ? 1.3 : 1}
        castShadow
        onClick={(e) => {
          e.stopPropagation();
          onPick();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHot(true);
        }}
        onPointerOut={() => setHot(false)}
      >
        <cylinderGeometry args={[0.11, 0.11, 0.06, 24]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={hot ? 0.5 : 0.14} roughness={0.5} metalness={0.05} />
      </mesh>
      {hot && (
        <Html position={[0, 0.2, 0]} center className={styles.coinTag} pointerEvents="none" zIndexRange={[60, 0]}>
          <span className={styles.addr}>{a.label.replace(/^addr:/, "")}</span>
          {a.sats > 0 && <span className={styles.amt}>{satsToBTC(a.sats)}</span>}
        </Html>
      )}
    </group>
  );
}

/** A money flow addr↔tx: a quiet line with a packet riding the way value moved. */
function Flow({ from, to, color, reduced, phase }: { from: Vec3; to: Vec3; color: string; reduced: boolean; phase: number }) {
  return (
    <>
      <Line points={[from, to]} color={color} lineWidth={1.8} transparent opacity={0.7} />
      {reduced ? <Arrow from={from} to={to} color={color} /> : <Bead from={from} to={to} color={color} phase={phase} />}
    </>
  );
}

/** The fusion, made physical: a pink announce thread from a tx up to a peer, packet rising. */
function Thread({ from, to, reduced, phase }: { from: Vec3; to: Vec3; reduced: boolean; phase: number }) {
  return (
    <>
      <Line points={[from, to]} color={C.fluoroPink} lineWidth={1.5} transparent opacity={0.85} />
      {!reduced && <Bead from={from} to={to} color={C.fluoroPink} phase={phase} speed={0.5} size={0.045} />}
    </>
  );
}

/** A hairline floor frame + soft breathing so the two shelves read as real surfaces. */
function FloorFrame({ y }: { y: number }) {
  return (
    <Line
      points={[
        [-EXT_X, y, -EXT_Z],
        [EXT_X, y, -EXT_Z],
        [EXT_X, y, EXT_Z],
        [-EXT_X, y, EXT_Z],
        [-EXT_X, y, -EXT_Z],
      ]}
      color={C.line}
      lineWidth={1}
      transparent
      opacity={0.4}
    />
  );
}
export function GraphScene({
  jaal,
  reduced,
  focusId,
  onFocus,
  onPickTx,
  onHover,
}: {
  jaal: Jaal;
  reduced: boolean;
  focusId: string | null;
  onFocus: (node: LaidNode | null) => void;
  onPickTx: (txId: string) => void;
  onHover: (on: boolean) => void;
}) {
  const [hoverId, setHoverId] = useState<string | null>(null);

  const { txs, peers } = useMemo(
    () => ({
      txs: jaal.nodes.filter((n) => n.kind === "transaction"),
      peers: jaal.nodes.filter((n) => n.kind === "peer"),
    }),
    [jaal],
  );

  // reveal index — for a tx: its funding/paid addresses + the peers that announced it;
  // and the reverse maps so a focused peer or address can light everything it touches.
  const index = useMemo(() => {
    const byTx = new Map<string, Reveal>();
    const peerTxs = new Map<string, string[]>();
    const addrTxs = new Map<string, string[]>();
    const get = (id: string) => byTx.get(id) ?? byTx.set(id, { inputs: [], outputs: [], peers: [] }).get(id)!;
    const push = (m: Map<string, string[]>, k: string, v: string) => (m.get(k) ?? m.set(k, []).get(k)!).push(v);
    for (const e of jaal.edges) {
      if (e.kind === "input") {
        const addr = jaal.byId.get(e.src);
        if (addr) get(e.dst).inputs.push({ id: addr.id, pos: addr.pos, label: addr.label, sats: e.sats ?? 0 });
        push(addrTxs, e.src, e.dst);
      } else if (e.kind === "output") {
        const addr = jaal.byId.get(e.dst);
        if (addr) get(e.src).outputs.push({ id: addr.id, pos: addr.pos, label: addr.label, sats: e.sats ?? 0 });
        push(addrTxs, e.dst, e.src);
      } else if (e.kind === "announce") {
        const peer = jaal.byId.get(e.dst);
        if (peer) get(e.src).peers.push({ id: peer.id, pos: peer.pos, label: peer.label });
        push(peerTxs, e.dst, e.src);
      }
    }
    return { byTx, peerTxs, addrTxs };
  }, [jaal]);

  // likely-same-owner partners at the current dial. In this run every claim is 0.36, so
  // the dial is a single honest bar: at/under 0.36 the ties show, above it none survive.
  const activeId = hoverId ?? focusId;
  const activeNode = activeId ? jaal.byId.get(activeId) ?? null : null;

  // which nodes stay lit while something owns the frame — everything else recedes
  const lit = useMemo(() => {
    if (!activeNode) return null;
    const s = new Set<string>([activeNode.id]);
    if (activeNode.kind === "transaction") {
      const r = index.byTx.get(activeNode.id);
      r?.peers.forEach((p) => s.add(p.id));
      r?.inputs.forEach((a) => s.add(a.id));
      r?.outputs.forEach((a) => s.add(a.id));
    } else if (activeNode.kind === "peer") {
      (index.peerTxs.get(activeNode.id) ?? []).forEach((t) => s.add(t));
    } else {
      (index.addrTxs.get(activeNode.id) ?? []).forEach((t) => s.add(t));
    }
    return s;
  }, [activeNode, index]);

  const over = (id: string) => {
    setHoverId(id);
    onHover(true);
  };
  const out = () => {
    setHoverId(null);
    onHover(false);
  };

  const txReveal = () => {
    if (activeNode?.kind !== "transaction") return null;
    const r = index.byTx.get(activeNode.id);
    if (!r) return null;
    const txPos = activeNode.pos;
    return (
      <group>
        {r.inputs.map((a, i) => (
          <Flow key={`fi${a.id}`} from={a.pos} to={txPos} color={C.risoBlue} reduced={reduced} phase={i * 0.13} />
        ))}
        {r.outputs.map((a, i) => (
          <Flow key={`fo${a.id}`} from={txPos} to={a.pos} color={C.butter} reduced={reduced} phase={i * 0.17} />
        ))}
        {r.peers.map((p, i) => (
          <Thread key={`th${p.id}`} from={txPos} to={p.pos} reduced={reduced} phase={i * 0.11} />
        ))}
        {r.inputs.map((a) => (
          <Coin key={`ci${a.id}`} a={a} color={C.risoBlue} onPick={() => onFocus(jaal.byId.get(a.id) ?? null)} />
        ))}
        {r.outputs.map((a) => (
          <Coin key={`co${a.id}`} a={a} color={C.butter} onPick={() => onFocus(jaal.byId.get(a.id) ?? null)} />
        ))}
      </group>
    );
  };

  const peerReveal = () => {
    if (activeNode?.kind !== "peer") return null;
    return (
      <group>
        {(index.peerTxs.get(activeNode.id) ?? []).map((tid, i) => {
          const t = jaal.byId.get(tid);
          return t ? <Thread key={tid} from={t.pos} to={activeNode.pos} reduced={reduced} phase={i * 0.09} /> : null;
        })}
      </group>
    );
  };

  const addrReveal = () => {
    if (activeNode?.kind !== "address") return null;
    return (
      <group>
        {(index.addrTxs.get(activeNode.id) ?? []).map((tid, i) => {
          const t = jaal.byId.get(tid);
          return t ? <Flow key={tid} from={activeNode.pos} to={t.pos} color={C.risoBlue} reduced={reduced} phase={i * 0.13} /> : null;
        })}
        <Coin a={{ id: activeNode.id, pos: activeNode.pos, label: activeNode.label, sats: 0 }} color={C.risoBlue} onPick={() => onFocus(activeNode)} />
      </group>
    );
  };

  return (
    <group>
      <ContactShadows position={[0, MONEY_Y - 0.12, 0]} scale={11} blur={2.6} opacity={0.18} far={5} />

      <FloorFrame y={WIRE_Y} />
      <FloorFrame y={MONEY_Y} />

      <Html position={[-EXT_X, WIRE_Y + 0.4, 0]} className={styles.floorTag} pointerEvents="none">
        <span>the wire</span>
      </Html>
      <Html position={[-EXT_X, MONEY_Y - 0.5, 0]} className={styles.floorTag} pointerEvents="none">
        <span>the money</span>
      </Html>
      <Html position={[EXT_X, MONEY_Y - 0.5, 0]} center className={styles.axisTime} pointerEvents="none">
        <span>time →</span>
      </Html>

      {peers.map((n) => (
        <Peer
          key={n.id}
          node={n}
          active={activeId === n.id}
          dim={lit != null && !lit.has(n.id)}
          onPick={() => onFocus(n)}
          onOver={() => over(n.id)}
          onOut={out}
        />
      ))}
      {txs.map((n) => (
        <Tx
          key={n.id}
          node={n}
          active={activeId === n.id}
          dim={lit != null && !lit.has(n.id)}
          onPick={() => onPickTx(n.id)}
          onOver={() => over(n.id)}
          onOut={out}
        />
      ))}

      {txReveal()}
      {peerReveal()}
      {addrReveal()}
    </group>
  );
}

/** Properties-drawer body for a node focused on the GRAPH (a peer ▲ or an address ●).
 *  Trace handles transactions; this covers the two nodes that have no flow of their own:
 *  a peer (the relay warning) and an address (the transactions it appears in). */
export function GraphDetail({
  node,
  jaal,
}: {
  node: LaidNode;
  jaal: Jaal;
}) {
  if (node.kind === "peer") {
    const s = peerStats.get(node.id);
    return (
      <div className={styles.detail}>
        <span className={styles.dLabel} style={{ color: C.fluoroPink }}>the IP that told us ▲</span>
        <dl className={styles.rows}>
          <div className={styles.row}>
            <dt>announcing IP</dt>
            <dd className={styles.mono}>{node.label.replace(/^peer:/, "")}</dd>
          </div>
          <div className={styles.row}>
            <dt>network operator (ASN)</dt>
            <dd className={styles.mono}>{s?.asn ?? "—"}</dd>
          </div>
          <div className={styles.row}>
            <dt>transactions announced</dt>
            <dd className={styles.mono}>{s?.announced ?? 0}</dd>
          </div>
          <div className={styles.row}>
            <dt>earliest heard</dt>
            <dd className={styles.mono}>{s?.earliestUs != null ? usToIST(s.earliestUs) : "—"}</dd>
          </div>
        </dl>
        <p className={styles.warn}>An IP that told us, usually a relay, not the sender.</p>
      </div>
    );
  }

  // address ● — the transactions it appears in
  const txCount = new Set(
    jaal.edges.filter((e) => (e.kind === "input" && e.src === node.id) || (e.kind === "output" && e.dst === node.id)).map((e) => (e.kind === "input" ? e.dst : e.src)),
  ).size;
  return (
    <div className={styles.detail}>
      <span className={styles.dLabel} style={{ color: C.risoBlue }}>an address ●</span>
      <dl className={styles.rows}>
        <div className={styles.row}>
          <dt>address</dt>
          <dd className={styles.mono}>{node.label.replace(/^addr:/, "")}</dd>
        </div>
        <div className={styles.row}>
          <dt>appears in</dt>
          <dd className={styles.mono}>{txCount} transaction{txCount === 1 ? "" : "s"}</dd>
        </div>
      </dl>
      <p className={styles.honest}>A wallet address in the run. Focus it to light the transactions it touches.</p>
    </div>
  );
}
