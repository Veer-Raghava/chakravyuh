// GRAPH — the product's core (§10, signature moment #2): the whole run as ONE readable
// field of transactions and the money that moved BETWEEN them. Layout follows the
// canonical bitcoin-forensics encoding (money-over-time) so an officer reads it at a
// glance, never a hairball, always fixed math (no force sim):
//
//   X = time (first_us, left→right = the run unfolding)
//   Y = value  (log₁₀ BTC in — big money floats up; zero-input txs rest on the baseline)
//   Z = signal vs noise: transactions that CHAIN to another sit forward & bright; lone
//       transactions recede to the back & fade — the eye lands on the money trails.
//   size = how many IPs saw it on the wire (corroboration)
//
//   edge tx_a → tx_b = an OUTPUT address of tx_a was later SPENT as an input of tx_b —
//     value flowing from one transaction into the next (the peel/relay chains).

import type { RawNode, RawEdge, Vec3 } from "./jaalLayout";

const XW = 5.0; // half-width of the time axis (frame-fitted)
const Y_BASE = 0.08; // baseline: a zero-input transaction sits here
const Y_TOP = 2.5; // the richest transaction floats to here
const LOG_LO = -3.2; // log₁₀(BTC) floor (~0.0006 BTC) → maps to Y_BASE
const LOG_HI = 0.6; // log₁₀(BTC) ceil (~4 BTC)   → maps to Y_TOP

// deterministic 0..1 jitter from an index — keeps the field identical every load
const jit = (i: number) => ((i * 2654435761) % 10000) / 10000;

export type GraphNode = {
  id: string;
  label: string;
  inSats: number;
  announcers: number;
  firstUs: number | null;
  pos: Vec3;
  r: number;
  connected: boolean; // part of at least one tx→tx money bridge
};
export type GraphLink = {
  fromId: string;
  toId: string;
  from: Vec3;
  to: Vec3;
  sats: number;
};
export type GraphTick = { x: number; us: number }; // a time gridline (label formatted at render)
export type Graph = {
  nodes: GraphNode[];
  links: GraphLink[];
  ticks: GraphTick[];
  count: number;
  bridged: number; // transactions linked to at least one other
  xw: number; // half-width, for the scene's baseline/axis
};

export function buildGraph(raw: { nodes: RawNode[]; edges: RawEdge[] }): Graph {
  const txs = raw.nodes.filter((n) => n.kind === "transaction");

  // money in per tx (SPENDS: addr → tx), distinct announcing IPs, and the join tables
  const inSats = new Map<string, number>();
  const ann = new Map<string, Set<string>>();
  const outAddrs = new Map<string, { addr: string; sats: number }[]>(); // tx → its outputs
  const spentBy = new Map<string, string[]>(); // addr → txs that spent it as input
  for (const e of raw.edges) {
    if (e.kind === "SPENDS") {
      inSats.set(e.dst, (inSats.get(e.dst) ?? 0) + (e.sats ?? 0));
      (spentBy.get(e.src) ?? spentBy.set(e.src, []).get(e.src)!).push(e.dst);
    } else if (e.kind === "RECEIVES") {
      (outAddrs.get(e.src) ?? outAddrs.set(e.src, []).get(e.src)!).push({ addr: e.dst, sats: e.sats ?? 0 });
    } else if (e.kind === "ANNOUNCED_BY") {
      (ann.get(e.src) ?? ann.set(e.src, new Set()).get(e.src)!).add(e.dst);
    }
  }

  // tx_a → tx_b when an output of a is later spent into b (dedup, keep bridged sats)
  const linkSats = new Map<string, number>(); // "a>b" → sats
  const connected = new Set<string>();
  for (const [txA, outs] of outAddrs) {
    for (const o of outs) {
      for (const txB of spentBy.get(o.addr) ?? []) {
        if (txB === txA) continue;
        const k = `${txA}>${txB}`;
        linkSats.set(k, (linkSats.get(k) ?? 0) + o.sats);
        connected.add(txA);
        connected.add(txB);
      }
    }
  }

  // time → X (fitted to ±XW)
  const times = txs.map((t) => t.first_us).filter((x): x is number => x != null);
  const tMin = times.length ? Math.min(...times) : 0;
  const tMax = times.length ? Math.max(...times) : 1;
  const span = Math.max(1, tMax - tMin);
  const xOf = (t: number | null) => (t == null ? 0 : ((t - tMin) / span) * 2 * XW - XW);
  // value (sats) → Y (log scale; zero-input txs rest on the baseline)
  const yOf = (sats: number) => {
    if (sats <= 0) return Y_BASE;
    const l = Math.log10(sats / 1e8);
    const f = Math.min(1, Math.max(0, (l - LOG_LO) / (LOG_HI - LOG_LO)));
    return Y_BASE + f * (Y_TOP - Y_BASE);
  };

  const loudest = Math.max(1, ...txs.map((t) => ann.get(t.node_id)?.size ?? 0));

  const nodes: GraphNode[] = txs.map((t, i) => {
    const isLinked = connected.has(t.node_id);
    const a = ann.get(t.node_id)?.size ?? 0;
    // chains sit forward (z≥0), islands recede (z<0); jitter de-overlaps co-located marks
    const z = isLinked ? 0.15 + jit(i) * 0.7 : -0.55 - jit(i) * 1.05;
    return {
      id: t.node_id,
      label: t.label,
      inSats: inSats.get(t.node_id) ?? 0,
      announcers: a,
      firstUs: t.first_us ?? null,
      pos: [xOf(t.first_us), yOf(inSats.get(t.node_id) ?? 0), z],
      r: 0.075 + (a / loudest) * 0.16,
      connected: isLinked,
    };
  });

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const links: GraphLink[] = [];
  for (const [k, sats] of linkSats) {
    const [a, b] = k.split(">");
    const na = byId.get(a);
    const nb = byId.get(b);
    if (na && nb) links.push({ fromId: a, toId: b, from: na.pos, to: nb.pos, sats });
  }

  // 4 evenly spaced time gridlines across the run
  const ticks: GraphTick[] = times.length
    ? [0, 1, 2, 3].map((k) => {
      const us = tMin + (span * k) / 3;
      return { x: xOf(us), us };
    })
    : [];

  return { nodes, links, ticks, count: nodes.length, bridged: connected.size, xw: XW };
}
