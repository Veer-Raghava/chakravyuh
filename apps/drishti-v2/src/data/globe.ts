import { fixtures } from "./loader";
import { locate } from "../three/globeGeo";

/**
 * The app-home globe's data (§9), derived ONLY from committed fixtures — never
 * invented. Points are the located announcing peers of two real transactions:
 *  - the confident case (origin.json) → has a clear leading candidate
 *  - the abstain case (origin-abstain.json) → "No answer available", by design no
 *    point is allowed to look like a strong lead.
 *
 * Positions are COUNTRY-LEVEL ONLY (centroid + per-IP jitter, see globeGeo.locate).
 * Peers with no mappable country (CGNAT / TEST-NET / Tor) get no location and are
 * shown in the neutral off-globe "no fixed place" cluster, never faked onto land.
 *
 * UNITS stay raw here (sats int64, _us int64); formatting to BTC / IST happens only
 * at the display layer. Identifiers keep their backend `*_display` form for render.
 */

export type Tier = "high" | "med" | "low" | "unknown";

export type GlobePoint = {
  ipSeed: string; // full peer_ip — used ONLY as a positioning/identity seed, never rendered
  ipDisplay: string; // e.g. "198.18.x.x" — the backend-truncated form we render
  port: number;
  asn: number;
  country: string | null;
  pOrigin: number;
  rank: number;
  lat: number;
  lon: number;
  located: boolean;
  tier: Tier;
  isLeader: boolean; // the tx's top candidate (confident case only)
};

export type GlobeTx = {
  txid: string;
  txidDisplay: string;
  abstain: boolean;
  abstainReason: string;
  firstSeenUs: number;
  feeSats: number | null; // joined from transactions.json when the txid is present
  nAnnouncements: number;
  pOrigin: number; // leading candidate's origin likelihood
  marginBelowFloor: boolean;
  originDisplay: string; // leading candidate ip_display (or "" when abstain)
  runnerUpDisplay: string;
  points: GlobePoint[];
};

type Lane = {
  as_org: string;
  asn: number;
  geo_country: string;
  net_class: string;
  p_origin: number;
  peer_ip: string;
  peer_ip_display: string;
  peer_port: number;
  rank: number;
};

type OriginFixture = {
  abstain: boolean;
  abstain_reason: string;
  first_seen_us: number;
  shortlist: Lane[];
  p_origin: number;
  txid: string;
  txid_display: string;
};

const txMeta = new Map(
  fixtures.transactions.transactions.map((t) => [t.txid, t] as const),
);

function tierFor(abstain: boolean, lane: Lane, located: boolean): Tier {
  if (!located) return "unknown";
  if (abstain) return "low"; // honest: nothing may read as a strong lead
  if (lane.rank === 1) return "high"; // the leading candidate — the "look here"
  if (lane.p_origin >= 0.03) return "med";
  return "low";
}

function build(o: OriginFixture): GlobeTx {
  const points: GlobePoint[] = o.shortlist.map((lane) => {
    const pos = locate(lane.geo_country || null, lane.peer_ip);
    const located = pos != null;
    return {
      ipSeed: lane.peer_ip,
      ipDisplay: lane.peer_ip_display,
      port: lane.peer_port,
      asn: lane.asn,
      country: lane.geo_country || null,
      pOrigin: lane.p_origin,
      rank: lane.rank,
      lat: pos?.lat ?? 0,
      lon: pos?.lon ?? 0,
      located,
      tier: tierFor(o.abstain, lane, located),
      isLeader: !o.abstain && lane.rank === 1,
    };
  });
  const meta = txMeta.get(o.txid);
  return {
    txid: o.txid,
    txidDisplay: o.txid_display,
    abstain: o.abstain,
    abstainReason: o.abstain_reason,
    firstSeenUs: o.first_seen_us,
    feeSats: meta ? meta.fee_sats : null,
    nAnnouncements: meta ? meta.n_announcements : o.shortlist.length,
    pOrigin: o.p_origin,
    marginBelowFloor: o.abstain,
    originDisplay: o.abstain ? "" : (o.shortlist.find((l) => l.rank === 1)?.peer_ip_display ?? ""),
    runnerUpDisplay: o.shortlist.find((l) => l.rank === 2)?.peer_ip_display ?? "",
    points,
  };
}

export const globeTxs: GlobeTx[] = [
  build(fixtures.origin as OriginFixture),
  build(fixtures.originAbstain as OriginFixture),
];

/** Every located point across all txs — the globe's ambient point layer. */
export const locatedPoints: { tx: GlobeTx; point: GlobePoint }[] = globeTxs.flatMap((tx) =>
  tx.points.filter((p) => p.located).map((point) => ({ tx, point })),
);

/**
 * The ambient "signal field": every other announcing peer the run actually heard
 * (graph.json, 174 real peers) placed at its country. graph peers carry no country,
 * so we learn ASN→country from the fixtures that DO carry both (alerts + origin
 * lanes) and route each peer through its HOSTED_IN ASN. Still country-level only,
 * still 100% real fixture data — never invented. Peers whose ASN has no known
 * country (or Tor/CGNAT) get no place and fall into the neutral unlocated count.
 * These dots are faint + non-interactive; the located candidates above stay the
 * bright, clickable ones.
 */
type GNode = { kind: string; node_id: string; label: string };
type GEdge = { kind: string; src: string; dst: string };
const graph = fixtures.graph as { nodes: GNode[]; edges: GEdge[] };
const alertList = (fixtures.alerts as { alerts: { origin_asn: number | null; origin_country: string | null }[] })
  .alerts;

const asnCountry = new Map<number, string>();
for (const a of alertList)
  if (a.origin_asn != null && a.origin_country && !asnCountry.has(a.origin_asn))
    asnCountry.set(a.origin_asn, a.origin_country);
for (const o of [fixtures.origin, fixtures.originAbstain] as OriginFixture[])
  for (const ln of o.shortlist)
    if (ln.asn != null && ln.geo_country && !asnCountry.has(ln.asn))
      asnCountry.set(ln.asn, ln.geo_country);

const peerAsn = new Map<string, number>();
for (const e of graph.edges)
  if (e.kind === "HOSTED_IN") {
    const peer = e.src.startsWith("peer:") ? e.src : e.dst;
    const asn = e.dst.startsWith("asn:") ? e.dst : e.src;
    if (peer.startsWith("peer:") && asn.startsWith("asn:")) {
      const n = Number(asn.slice(4));
      if (!Number.isNaN(n)) peerAsn.set(peer, n);
    }
  }

const candidateIps = new Set(globeTxs.flatMap((tx) => tx.points.map((p) => p.ipSeed)));

const ambient: { lat: number; lon: number }[] = [];
let ambientUnlocated = 0;
for (const node of graph.nodes) {
  if (node.kind !== "peer") continue;
  const ip = node.node_id.slice("peer:".length);
  if (candidateIps.has(ip)) continue; // already a bright candidate dot
  const asn = peerAsn.get(node.node_id);
  const country = asn != null ? asnCountry.get(asn) ?? null : null;
  const pos = locate(country, ip);
  if (pos) ambient.push(pos);
  else ambientUnlocated += 1;
}

/** Faint non-interactive echoes — the other real IPs we heard (positions country-level). */
export const ambientPoints: { lat: number; lon: number }[] = ambient;

/** Peers with no mappable place (candidates + ambient) — counted, shown in the note, never faked. */
export const unlocatedCount: number =
  globeTxs.reduce((n, tx) => n + tx.points.filter((p) => !p.located).length, 0) + ambientUnlocated;

