/**
 * Deterministic aggregation for the multi-transaction view. The default GRAPH shows the
 * *shape* of an investigation — transactions, wallet clusters, peers and ASNs — with the
 * individual addresses folded into the cluster that owns them, so density never becomes a
 * hairball. Expanding one cluster reveals the sample of member wallets it aggregates; every
 * edge that touched a folded address is redirected to its cluster, so the picture stays
 * connected and honest at either zoom. Pure and seedless: same input, same output.
 */
import type { GraphData, GraphEdge, GraphNode } from "../adapter";

export interface Folded {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** address id -> the cluster it is a member of (from MEMBER_OF edges). */
  memberOf: Map<string, string>;
  /** cluster id -> its member address ids, sorted for a stable fan order. */
  members: Map<string, string[]>;
  /** how many addresses are currently hidden inside a collapsed cluster. */
  foldedAddresses: number;
}

/** Fold every address whose cluster is not in `expanded` into that cluster. `expanded` is
 *  normally a single cluster (accordion focus), but the fold is correct for any set. */
export function fold(data: GraphData, expanded: Set<string>): Folded {
  const kind = new Map(data.nodes.map((n) => [n.node_id, n.kind]));
  const memberOf = new Map<string, string>();
  const members = new Map<string, string[]>();
  for (const e of data.edges) {
    if (e.kind === "MEMBER_OF" && kind.get(e.src) === "address") {
      memberOf.set(e.src, e.dst);
      (members.get(e.dst) ?? members.set(e.dst, []).get(e.dst)!).push(e.src);
    }
  }
  for (const m of members.values()) m.sort();

  // An address with no cluster is always shown; one with a cluster shows only when expanded.
  const shown = (addr: string) => {
    const c = memberOf.get(addr);
    return c === undefined || expanded.has(c);
  };
  const hiddenAddr = (id: string) => kind.get(id) === "address" && !shown(id);
  const remap = (id: string) => (hiddenAddr(id) ? memberOf.get(id)! : id);

  const nodes = data.nodes.filter((n) => !(n.kind === "address" && !shown(n.node_id)));

  // Redirect edges off folded addresses onto their cluster; drop self-loops (an address's
  // own MEMBER_OF, or two members of one cluster); dedupe, keeping the strongest evidence.
  const byKey = new Map<string, GraphEdge>();
  for (const e of data.edges) {
    const src = remap(e.src);
    const dst = remap(e.dst);
    if (src === dst) continue;
    const key = `${src}|${dst}|${e.kind}`;
    const prev = byKey.get(key);
    if (!prev) {
      byKey.set(key, { ...e, src, dst });
    } else {
      prev.confidence = Math.max(prev.confidence, e.confidence);
      prev.on_origin_path = prev.on_origin_path || e.on_origin_path;
    }
  }

  const foldedAddresses = data.nodes.filter((n) => n.kind === "address" && !shown(n.node_id)).length;
  return { nodes, edges: [...byKey.values()], memberOf, members, foldedAddresses };
}
