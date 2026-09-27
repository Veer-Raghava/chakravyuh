// LEAD — the focused subgraph for ONE suspect transaction (§10, rebuilt for
// readability-first). PURE: reads the backend graph shape, returns a small, fully
// laid-out scene for a single tx — WHO sent, TO WHOM, what came back as CHANGE, and
// WHICH IPs announced it. No R3F, no fixture import.
//
// Fixed columns so every camera keeps the same hierarchy:
//   X = FLOW    senders (left) → tx (centre) → receivers (right)
//   Y = FLOOR   money below, the announcing IPs on the wire above
//   Z = LANE    de-overlap within a column only (never a force sim)
// The only edges we ever draw are the ones that answer an investigative question:
// money in, money out, change-back, and the pink announce threads. Nothing else.

import type { RawNode, RawEdge, Vec3 } from "./jaalLayout";

export const MONEY_Y = -1.05; // the blockchain floor
export const WIRE_Y = 1.75; //   the network floor (IPs sit up here)
const SENDER_X = -2.7;
const TX_X = 0;
const RECV_X = 2.7;

export type Role = "sender" | "receiver" | "change";
export type MoneyNode = {
  id: string;
  label: string;
  role: Role;
  sats: number; // aggregated across this address's edges on this tx
  count: number; // how many inputs/outputs collapsed into this coin
  pos: Vec3;
};
export type Announcer = {
  id: string;
  label: string;
  asn: string | null;
  tsUs: number | null;
  pos: Vec3;
};
export type FlowEdge = { from: Vec3; to: Vec3; sats: number; role: Role };
export type ThreadEdge = { from: Vec3; to: Vec3 };

export type Lead = {
  txId: string;
  txLabel: string;
  txPos: Vec3;
  firstUs: number | null;
  senders: MoneyNode[];
  receivers: MoneyNode[]; // includes change outputs — role marks which
  announcers: Announcer[];
  flows: FlowEdge[];
  threads: ThreadEdge[];
  ownerCluster: Set<string>; // ids likely the same owner (senders + their change)
  totalInSats: number;
  totalOutSats: number;
  why: string; // honest, data-derived reason this is worth a look
};

const laneZ = (i: number, n: number, gap = 1.15): number =>
  n <= 1 ? 0 : (i - (n - 1) / 2) * gap;

// aggregate a set of edges into one coin per unique address (2 inputs from the same
// wallet read as one wallet that spent twice, not two identical dots).
function collapse(
  edges: RawEdge[],
  addrOf: (e: RawEdge) => string,
  nodes: Map<string, RawNode>,
): { id: string; label: string; sats: number; count: number }[] {
  const by = new Map<string, { id: string; label: string; sats: number; count: number }>();
  for (const e of edges) {
    const id = addrOf(e);
    const cur = by.get(id) ?? { id, label: nodes.get(id)?.label ?? id, sats: 0, count: 0 };
    cur.sats += e.sats ?? 0;
    cur.count += 1;
    by.set(id, cur);
  }
  return [...by.values()].sort((a, b) => b.sats - a.sats);
}

export function buildLead(raw: { nodes: RawNode[]; edges: RawEdge[] }, txId: string): Lead {
  const nodes = new Map(raw.nodes.map((n) => [n.node_id, n]));
  const tx = nodes.get(txId);
  const txLabel = tx?.label ?? txId;

  const spends = raw.edges.filter((e) => e.kind === "SPENDS" && e.dst === txId); // addr → tx
  const receives = raw.edges.filter((e) => e.kind === "RECEIVES" && e.src === txId); // tx → addr
  const announced = raw.edges.filter((e) => e.kind === "ANNOUNCED_BY" && e.src === txId);
  const sameOwner = raw.edges.filter((e) => e.kind === "SAME_OWNER");
  const hostedIn = new Map(
    raw.edges.filter((e) => e.kind === "HOSTED_IN").map((e) => [e.src, e.dst]),
  );

  const inAgg = collapse(spends, (e) => e.src, nodes);
  const outAgg = collapse(receives, (e) => e.dst, nodes);
  const senderIds = new Set(inAgg.map((s) => s.id));

  // an output is CHANGE if the value loops back to the sender: either the exact same
  // address is reused (the strongest signal there is), or a SAME_OWNER edge ties it to
  // an input address. This is the one heuristic that matters for reading the story.
  const ownerLinked = (addr: string): boolean =>
    senderIds.has(addr) ||
    sameOwner.some(
      (e) =>
        (e.src === addr && senderIds.has(e.dst)) || (e.dst === addr && senderIds.has(e.src)),
    );

  const txPos: Vec3 = [TX_X, MONEY_Y, 0];
  const senders: MoneyNode[] = inAgg.map((s, i) => ({
    ...s,
    role: "sender" as const,
    pos: [SENDER_X, MONEY_Y, laneZ(i, inAgg.length)],
  }));
  const receivers: MoneyNode[] = outAgg.map((o, i) => ({
    ...o,
    role: ownerLinked(o.id) ? ("change" as const) : ("receiver" as const),
    pos: [RECV_X, MONEY_Y, laneZ(i, outAgg.length)],
  }));

  // announcers — dedupe by peer node_id, arc them across the wire above the tx.
  const seen = new Set<string>();
  const peerEdges = announced.filter((e) => (seen.has(e.dst) ? false : seen.add(e.dst)));
  const announcers: Announcer[] = peerEdges.map((e, i, arr) => {
    const n = arr.length;
    const t = n <= 1 ? 0.5 : i / (n - 1);
    const x = (t - 0.5) * 5.6;
    const arc = Math.sin(t * Math.PI) * 0.28; // gentle bow so the fan reads
    return {
      id: e.dst,
      label: nodes.get(e.dst)?.label ?? e.dst,
      asn: hostedIn.get(e.dst) ?? null,
      tsUs: e.ts_us,
      pos: [x, WIRE_Y + arc, laneZ(i, n, 0.3)],
    };
  });

  const flows: FlowEdge[] = [
    ...senders.map((s) => ({ from: s.pos, to: txPos, sats: s.sats, role: s.role })),
    ...receivers.map((r) => ({ from: txPos, to: r.pos, sats: r.sats, role: r.role })),
  ];
  const threads: ThreadEdge[] = announcers.map((a) => ({ from: a.pos, to: txPos }));

  const ownerCluster = new Set<string>([
    ...senderIds,
    ...receivers.filter((r) => r.role === "change").map((r) => r.id),
  ]);

  const totalInSats = senders.reduce((s, n) => s + n.sats, 0);
  const totalOutSats = receivers.reduce((s, n) => s + n.sats, 0);
  const changeSats = receivers
    .filter((r) => r.role === "change")
    .reduce((s, n) => s + n.sats, 0);
  const asnCount = new Set(announcers.map((a) => a.asn).filter(Boolean)).size;

  const why = buildWhy(announcers.length, asnCount, changeSats, totalOutSats);

  return {
    txId,
    txLabel,
    txPos,
    firstUs: tx?.first_us ?? null,
    senders,
    receivers,
    announcers,
    flows,
    threads,
    ownerCluster,
    totalInSats,
    totalOutSats,
    why,
  };
}

// Honest one-liner: only claims what the observed edges support — how many IPs saw
// it, across how many networks, and whether the value loops back to the sender.
function buildWhy(
  nIps: number,
  nNetworks: number,
  changeSats: number,
  totalOut: number,
): string {
  const parts: string[] = [];
  if (nIps > 0)
    parts.push(`seen by ${nIps} IP${nIps === 1 ? "" : "s"}${nNetworks > 1 ? ` across ${nNetworks} networks` : ""}`);
  if (totalOut > 0 && changeSats / totalOut > 0.5)
    parts.push("most of the value loops back to the sender's own wallet");
  return parts.length ? parts.join(" · ") : "a transaction with observed network echoes";
}

// Rank the tellable leads best-first: each needs money in AND out (a whole story),
// then the most announcing IPs. Drives both the default and prev/next stepping.
export function rankLeads(raw: { nodes: RawNode[]; edges: RawEdge[] }): string[] {
  const ins = new Map<string, number>();
  const outs = new Map<string, number>();
  const ann = new Map<string, number>();
  for (const e of raw.edges) {
    if (e.kind === "SPENDS") ins.set(e.dst, (ins.get(e.dst) ?? 0) + 1);
    else if (e.kind === "RECEIVES") outs.set(e.src, (outs.get(e.src) ?? 0) + 1);
    else if (e.kind === "ANNOUNCED_BY") ann.set(e.src, (ann.get(e.src) ?? 0) + 1);
  }
  return raw.nodes
    .filter((n) => n.kind === "transaction")
    .map((n) => n.node_id)
    .filter((t) => (ins.get(t) ?? 0) >= 1 && (outs.get(t) ?? 0) >= 1)
    .sort(
      (a, b) =>
        (ann.get(b) ?? 0) * 10 + (ins.get(b) ?? 0) + (outs.get(b) ?? 0) -
        ((ann.get(a) ?? 0) * 10 + (ins.get(a) ?? 0) + (outs.get(a) ?? 0)),
    );
}

export function pickDefaultLead(raw: { nodes: RawNode[]; edges: RawEdge[] }): string {
  const ranked = rankLeads(raw);
  return ranked[0] ?? raw.nodes.find((n) => n.kind === "transaction")!.node_id;
}
