// GRAPH — the product's core (§10, signature moment #2): the whole run as ONE readable
// graph of transactions and the money that moved BETWEEN them, never a hairball. PURE:
// reads the backend graph, lays it out with fixed math (no force sim), and returns nodes
// + relation edges for the scene to render.
//
//   X = time (first_us, left→right = the run unfolding)
//   Z = de-overlap lane within a time-column        Y = height ∝ IPs that saw it (echo)
//   edge tx_a → tx_b = an OUTPUT address of tx_a was later SPENT as an input of tx_b —
//     i.e. value flowing from one transaction into the next (the peel/relay chains).
//
// Most transactions stand alone; the few that CHAIN are the forensic story, so linked
// nodes read bright/coral and islands sit dim. Clicking any node drills into its LEAD.

import type { RawNode, RawEdge, Vec3 } from "./jaalLayout";

const XW = 4.7; // half-width of the time axis
const COLS = 34; // time buckets for lane de-overlap
const LANE = 0.46; // Z spacing between co-timed transactions
const HGT = 1.7; // max Y lift (loudest tx)

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
  from: Vec3;
  to: Vec3;
  sats: number;
};
export type Graph = {
  nodes: GraphNode[];
  links: GraphLink[];
  count: number;
  bridged: number; // how many transactions are linked to at least one other
};

export function buildGraph(raw: { nodes: RawNode[]; edges: RawEdge[] }): Graph {
  const txs = raw.nodes.filter((n) => n.kind === "transaction");

  // money in per tx (SPENDS: addr → tx) and distinct IPs that announced it
  const inSats = new Map<string, number>();
  const ann = new Map<string, Set<string>>();
  // outputs (RECEIVES: tx → addr) and spenders (SPENDS: addr → tx) for the bridge join
  const outAddrs = new Map<string, { addr: string; sats: number }[]>();
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

  // time → X, then lane-pack co-timed txs across Z so nothing overlaps
  const times = txs.map((t) => t.first_us).filter((x): x is number => x != null);
  const tMin = times.length ? Math.min(...times) : 0;
  const tMax = times.length ? Math.max(...times) : 1;
  const span = Math.max(1, tMax - tMin);
  const xOf = (t: number | null) => (t == null ? 0 : ((t - tMin) / span) * 2 * XW - XW);

  const sorted = [...txs].sort((a, b) => (a.first_us ?? 0) - (b.first_us ?? 0));
  const colCount = new Map<number, number>(); // running lane index per column
  const maxIn = Math.max(1, ...txs.map((t) => inSats.get(t.node_id) ?? 0));
  const loudest = Math.max(1, ...txs.map((t) => ann.get(t.node_id)?.size ?? 0));

  const nodes: GraphNode[] = sorted.map((t) => {
    const x = xOf(t.first_us);
    const col = Math.round(((x + XW) / (2 * XW)) * (COLS - 1));
    const lane = colCount.get(col) ?? 0;
    colCount.set(col, lane + 1);
    const z = (lane - 1.5) * LANE + (col % 2) * (LANE / 2); // stagger odd columns
    const a = ann.get(t.node_id)?.size ?? 0;
    const share = (inSats.get(t.node_id) ?? 0) / maxIn;
    return {
      id: t.node_id,
      label: t.label,
      inSats: inSats.get(t.node_id) ?? 0,
      announcers: a,
      firstUs: t.first_us ?? null,
      pos: [x, 0.12 + (a / loudest) * HGT, z],
      r: 0.085 + Math.sqrt(share) * 0.19,
      connected: connected.has(t.node_id),
    };
  });

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const links: GraphLink[] = [];
  for (const [k, sats] of linkSats) {
    const [a, b] = k.split(">");
    const na = byId.get(a);
    const nb = byId.get(b);
    if (na && nb) links.push({ from: na.pos, to: nb.pos, sats });
  }

  return { nodes, links, count: nodes.length, bridged: connected.size };
}
