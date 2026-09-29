// The data seam for the JAAL graph (§10) — mirrors data/globe.ts. Reads ONLY the
// committed address-detail fixture (graph-address.json); the layout math lives in
// three/jaalLayout.ts. We render the three shapes the plan allows (● address,
// ◆ transaction, ▲ peer); cluster/asn nodes are not shapes — ASN rides in the peer
// panel, clusters are the live hulls. Identifiers render via the backend `label`
// (already truncated per DATA-CONTRACTS §9); node_id (full IP) is a seed, never shown.
import { fixtures } from "./loader";
import {
  layoutJaal,
  assertJaalInvariants,
  type RawNode,
  type RawEdge,
} from "../three/jaalLayout";
import { buildLead, rankLeads } from "../three/leadModel";
import { buildOverview } from "../three/overviewModel";
import { buildGraph } from "../three/graphModel";
import { buildActor, assertActorInvariants } from "../three/actorModel";

const raw = fixtures.graphAddress as { nodes: RawNode[]; edges: RawEdge[] };

export const jaal = layoutJaal(raw.nodes, raw.edges);
if (import.meta.env.DEV) assertJaalInvariants(jaal); // the two-floor grammar, guarded

// The focused-lead seam (the readable default view): a ranked list of transactions
// that tell a whole money-in → money-out story, and a builder for any one of them.
export const leadIds = rankLeads(raw);
export const buildLeadFor = (txId: string) => buildLead(raw, txId);

// The calm global: every tellable tx laid out as one clean spiral (no clustering).
export const buildOverviewAll = () => buildOverview(raw);

// THE main view: the whole run as one graph — every tx over time, linked by the money
// that moved between them. Click a node → its LEAD flow.
export const buildGraphAll = () => buildGraph(raw);

// The OWNER-level reading of the same run (`detail=actor`): addresses on one floor, height
// = how wide their owner group is, coral arcs = the same-owner claims. Built once, like the
// others — the fixture is static, so there is nothing to recompute per render.
const actorRaw = fixtures.graphActor as unknown as {
  nodes: RawNode[];
  edges: RawEdge[];
  aggregated?: Record<string, unknown>;
};
export const actor = buildActor(actorRaw);
if (import.meta.env.DEV) assertActorInvariants(actor); // the actor floor's grammar, guarded

export const counts = {
  address: jaal.nodes.filter((n) => n.kind === "address").length,
  transaction: jaal.nodes.filter((n) => n.kind === "transaction").length,
  peer: jaal.nodes.filter((n) => n.kind === "peer").length,
  announce: jaal.edges.filter((e) => e.kind === "announce").length,
  input: jaal.edges.filter((e) => e.kind === "input").length,
  output: jaal.edges.filter((e) => e.kind === "output").length,
};

// Per-peer rollups for the Properties panel: how many txs it announced + the earliest
// time we heard it. This is what makes the "usually a relay, not the sender" warning land.
export type PeerStat = { announced: number; earliestUs: number | null; asn: string | null };
export const peerStats = new Map<string, PeerStat>();
for (const e of jaal.edges) {
  if (e.kind !== "announce") continue;
  const s = peerStats.get(e.dst) ?? { announced: 0, earliestUs: null, asn: jaal.asnOf.get(e.dst) ?? null };
  s.announced += 1;
  if (e.tsUs != null && (s.earliestUs == null || e.tsUs < s.earliestUs)) s.earliestUs = e.tsUs;
  peerStats.set(e.dst, s);
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
export const scrubOwnerWords = (s: string): string => s.replace(/\bcluster\b/gi, "owner group");
