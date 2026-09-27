// OVERVIEW — the calm global (§10, replaces the wallet/trail views). PURE: reads the
// backend graph and lays EVERY tellable transaction out as one clean constellation, no
// edges, no hairball. It answers "what's in this run and which ones are loud?" at a
// glance; clicking one drills into its LEAD diorama. No clustering, no confidence dial —
// we don't lean on the weak same-owner model here, we just show the transactions.
//
//   XZ = a deterministic phyllotaxis spiral, most-suspicious (rank 0) at the centre
//   size = money through the tx           height (3D) = how many IPs saw it on the wire
// The spiral is fixed math (never a force sim) so the field is identical every load.

import type { RawNode, RawEdge, Vec3 } from "./jaalLayout";
import { rankLeads } from "./leadModel";

const GOLDEN = 2.399963229728653; // golden angle — even, non-clumping spiral
const SPACING = 0.62;

export type OverviewNode = {
  txId: string;
  label: string;
  rank: number; // 0 = most suspicious (centre, brightest)
  inSats: number;
  announcers: number; // distinct IPs that announced it
  firstUs: number | null;
  pos: Vec3; // on the XZ plane (y set by the view's 2D/3D mode at render)
  r: number; // mark radius, ∝ √(share of the run's money)
  lift: number; // 3D height, ∝ announcer count
};
export type Overview = {
  nodes: OverviewNode[];
  count: number;
  loudest: number; // max announcer count in the run (for the honest headline)
};

export function buildOverview(raw: { nodes: RawNode[]; edges: RawEdge[] }): Overview {
  const nodes = new Map(raw.nodes.map((n) => [n.node_id, n]));
  const ranked = rankLeads(raw);

  const inSats = new Map<string, number>();
  const ann = new Map<string, Set<string>>();
  for (const e of raw.edges) {
    if (e.kind === "SPENDS") inSats.set(e.dst, (inSats.get(e.dst) ?? 0) + (e.sats ?? 0));
    else if (e.kind === "ANNOUNCED_BY")
      (ann.get(e.src) ?? ann.set(e.src, new Set()).get(e.src)!).add(e.dst);
  }

  const maxIn = Math.max(1, ...ranked.map((t) => inSats.get(t) ?? 0));
  const loudest = Math.max(0, ...ranked.map((t) => ann.get(t)?.size ?? 0));

  const overviewNodes: OverviewNode[] = ranked.map((txId, i) => {
    const a = ann.get(txId)?.size ?? 0;
    const rad = SPACING * Math.sqrt(i + 0.5);
    const theta = i * GOLDEN;
    const share = (inSats.get(txId) ?? 0) / maxIn;
    return {
      txId,
      label: nodes.get(txId)?.label ?? txId,
      rank: i,
      inSats: inSats.get(txId) ?? 0,
      announcers: a,
      firstUs: nodes.get(txId)?.first_us ?? null,
      pos: [Math.cos(theta) * rad, 0, Math.sin(theta) * rad],
      r: 0.16 + Math.sqrt(share) * 0.24,
      lift: 0.16 + (loudest > 0 ? a / loudest : 0) * 0.9,
    };
  });

  return { nodes: overviewNodes, count: overviewNodes.length, loudest };
}
