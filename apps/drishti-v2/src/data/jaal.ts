// The data seam for the JAAL graph (§10) — mirrors data/globe.ts. Reads ONLY the
// committed address-detail fixture (graph-address.json); the layout math lives in
// three/jaalLayout.ts. We render the three shapes the plan allows (● address,
// ◆ transaction, ▲ peer); cluster/asn nodes are not shapes — ASN rides in the peer
// panel, clusters are the live hulls. Identifiers render via the backend `label`
// (already truncated per DATA-CONTRACTS §9); node_id (full IP) is a seed, never shown.
import {
  layoutJaal,
  assertJaalInvariants,
  type RawNode,
  type RawEdge,
} from "../three/jaalLayout";
import { buildLead, rankLeads } from "../three/leadModel";
import { buildOverview } from "../three/overviewModel";

export function buildJaalData(
  fixtures: Pick<import("./loader").Fixtures, "graphAddress">,
  focuses: Record<string, import("./loader").Fixtures["graphAddress"]> = {},
) {
  const raw = fixtures.graphAddress as { nodes: RawNode[]; edges: RawEdge[] };
  const jaal = layoutJaal(raw.nodes, raw.edges);
  if (import.meta.env.DEV) assertJaalInvariants(jaal);
  const nodes = new Map(raw.nodes.map((n) => [n.node_id, n]));
  const edges = new Map(raw.edges.map((e) => [JSON.stringify(e), e]));
  for (const g of Object.values(focuses)) {
    for (const n of g.nodes) nodes.set(n.node_id, n);
    for (const e of g.edges) edges.set(JSON.stringify(e), e);
  }
  const atlasRaw = { nodes: [...nodes.values()], edges: [...edges.values()] };
  const leadIds = rankLeads(atlasRaw);
  const buildLeadFor = (id: string) => buildLead(focuses[id] ?? atlasRaw, id);
  const buildOverviewAll = () => buildOverview(raw);
  const counts = {
    address: jaal.nodes.filter((n) => n.kind === "address").length,
    transaction: jaal.nodes.filter((n) => n.kind === "transaction").length,
    peer: jaal.nodes.filter((n) => n.kind === "peer").length,
  };
  return { atlasRaw, jaal, leadIds, buildLeadFor, buildOverviewAll, counts };
}

// UNITS convert to human form ONLY here (display layer), never in the data.
export function satsToBTC(sats: number): string {
  return `${(sats / 100_000_000).toFixed(8)} BTC`;
}
export function usToIST(us: number): string {
  return (
    new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(us / 1000)) + " IST"
  );
}

/**
 * Display-layer rename (§3 kill-list): the bare word "cluster" never reaches the screen.
 * The backend's own id `cluster:616` is a likely-same-owner group, so it renders as
 * "owner group 616". One helper, because the same id turns up on the leads queue, the
 * proof and the landing card — three copies of this rule is three places to drift.
 */
export const ownerGroupLabel = (s: string): string =>
  s.startsWith("cluster:") ? `owner group ${s.slice(8)}` : s;

/** The same rename applied inside backend-authored prose. Display-only, guarded by \b so
 *  "clustering" is not mangled into nonsense. */
export const scrubOwnerWords = (s: string): string =>
  s.replace(/\bcluster\b/gi, "owner group");
