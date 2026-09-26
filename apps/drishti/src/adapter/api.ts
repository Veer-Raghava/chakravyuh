/**
 * Live API adapter. Translates the loopback FastAPI JSON (chakravyuh.api.serialize) into
 * the typed adapter surface every screen reads through. Track A's serializers and Track B's
 * types were authored from the same contract but independently, so the shapes differ in
 * naming and nesting; this file is the one place that reconciles them. When VITE_SOURCE=api,
 * the console reads a real run over 127.0.0.1:8000 instead of the committed fixtures.
 *
 * The eight pipeline reads are served by the API. The six run-control and lineage calls are
 * the frontend-owned seam (see types.ts): they are simulated in the browser with no network
 * and no real execution, so they delegate to the fixtures adapter unchanged.
 */
import type {
  Adapter,
  AlertDetail,
  AlertRow,
  CollapseStats,
  GraphData,
  GraphParams,
  Manifest,
  OriginEstimate,
  Packet,
  TransactionRow,
} from "./types";
import { fixturesAdapter } from "./fixtures";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API ${path} -> ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

/** Announcement offsets and window come off the wire in microseconds; the fan reads ms. */
const usToMs = (us: number): number => Math.round(us / 1000);

// ----- raw API response shapes (only the fields this file reads) -----

interface RawTx {
  txid: string;
  first_seen_us: number;
  n_announcements: number;
  n_distinct_peers: number;
  announce_spread_us: number;
  total_out_sats: number;
  is_coinbase: boolean;
  has_equal_outputs: boolean;
  abstained: boolean;
}

interface RawLane {
  peer_ip: string;
  peer_port: number;
  asn: number | null;
  as_org: string | null;
  geo_country: string | null;
  net_class: string;
  first_seen_us: number;
  announcements_ms: number[];
  p_origin: number;
  rank: number;
}

export const apiAdapter: Adapter = {
  getManifest: () => get<Manifest>("/manifest"),

  async getCollapseStats(): Promise<CollapseStats> {
    const raw = await get<{
      announcements: number;
      transactions: number;
      echo: number;
      mean_announcements_per_tx: number;
      histogram: { n: number; count: number }[];
    }>("/collapse");
    return {
      n_announcements: raw.announcements,
      n_transactions: raw.transactions,
      n_echo: raw.echo,
      mean_announcements: raw.mean_announcements_per_tx,
      announcements_per_tx: raw.histogram.map((h) => ({ bucket: h.n, count: h.count })),
    };
  },

  async listTransactions(): Promise<TransactionRow[]> {
    const raw = await get<{ transactions: RawTx[] }>("/transactions?limit=2000");
    return raw.transactions.map((t) => ({
      txid: t.txid,
      first_seen_us: t.first_seen_us,
      n_announcements: t.n_announcements,
      n_distinct_peers: t.n_distinct_peers,
      announce_spread_us: t.announce_spread_us,
      total_out_sats: t.total_out_sats,
      is_coinbase: t.is_coinbase,
      has_equal_outputs: t.has_equal_outputs,
      abstained: t.abstained,
    }));
  },

  async getOriginEstimate(txid: string): Promise<OriginEstimate> {
    const raw = await get<{
      txid: string;
      estimator: string;
      abstain: boolean;
      abstain_reason: string | null;
      window_ms: number;
      margin: number;
      features: { label: string; value: string; gloss: string }[];
      lanes: RawLane[];
    }>(`/origin/${encodeURIComponent(txid)}`);
    return {
      txid: raw.txid,
      estimator: raw.estimator,
      abstain: raw.abstain,
      abstain_reason: raw.abstain_reason,
      window_ms: usToMs(raw.window_ms),
      margin: raw.abstain ? null : raw.margin,
      p_interval: null,
      features: raw.features,
      lanes: raw.lanes.map((l) => ({
        peer_ip: l.peer_ip,
        peer_port: l.peer_port,
        asn: l.asn,
        as_org: l.as_org,
        geo_country: l.geo_country,
        net_class: l.net_class,
        first_seen_us: l.first_seen_us,
        announce_times_ms: l.announcements_ms.map(usToMs),
        p_origin: l.p_origin,
        rank: l.rank,
      })),
    };
  },

  async getGraph(params: GraphParams): Promise<GraphData> {
    const query = params.txid
      ? `?detail=address&focus=${encodeURIComponent(params.txid)}`
      : "?detail=cluster";
    const raw = await get<{
      aggregated: { addresses: number; clusters: number } | null;
      nodes: { node_id: string; kind: GraphData["nodes"][number]["kind"]; label: string }[];
      edges: {
        src: string;
        dst: string;
        kind: GraphData["edges"][number]["kind"];
        confidence: number;
        evidence: string;
      }[];
    }>(`/graph${query}`);
    return {
      nodes: raw.nodes.map((n) => ({
        node_id: n.node_id,
        kind: n.kind,
        label: n.label,
        on_origin_path: false,
      })),
      edges: raw.edges.map((e) => ({
        src: e.src,
        dst: e.dst,
        kind: e.kind,
        confidence: e.confidence,
        evidence: e.evidence,
        on_origin_path: false,
      })),
      aggregated: raw.aggregated
        ? { addresses: raw.aggregated.addresses, clusters: raw.aggregated.clusters }
        : null,
    };
  },

  async listAlerts(): Promise<AlertRow[]> {
    const raw = await get<{
      alerts: {
        alert_id: string;
        rank: number;
        severity: AlertRow["severity"];
        conf_low: number;
        conf_high: number;
        headline: string;
        cluster_size: number;
        typologies: string[];
        origin_asn: number | null;
        origin_country: string;
      }[];
    }>("/alerts?limit=2000");
    return raw.alerts.map((a) => ({
      alert_id: a.alert_id,
      rank: a.rank,
      case_id: a.alert_id,
      severity: a.severity,
      conf_low: a.conf_low,
      conf_high: a.conf_high,
      typologies: a.typologies,
      cluster_size: a.cluster_size,
      origin_asn: a.origin_asn,
      origin_country: a.origin_country || null,
      dwell_us: 0,
      status: "OPEN",
      headline: a.headline,
    }));
  },

  async getAlert(caseId: string): Promise<AlertDetail> {
    const raw = await get<{
      alert_id: string;
      severity: AlertDetail["severity"];
      headline: string;
      base_rate: number | null;
      confidence: AlertDetail["confidence"];
      features: { statement: string; weight: number }[];
      evidence: { kind: string; statement: string; source_ref: string }[];
      counters: { kind: string; statement: string; strength: number; would_clear: boolean }[];
    }>(`/alerts/${encodeURIComponent(caseId)}`);
    return {
      alert_id: raw.alert_id,
      case_id: raw.alert_id,
      severity: raw.severity,
      headline: raw.headline,
      status: "OPEN",
      why: {
        base_rate: raw.base_rate,
        contributions: raw.features.map((f) => ({ feature: f.statement, value: f.weight })),
      },
      evidence: raw.evidence.map((e) => ({
        kind: e.kind,
        statement: e.statement,
        weight: 0,
        source_ref: e.source_ref,
      })),
      counter: raw.counters.map((c) => ({
        kind: c.kind,
        statement: c.statement,
        strength: c.strength,
        would_clear: c.would_clear,
      })),
      confidence: raw.confidence,
    };
  },

  async getPacket(caseId: string): Promise<Packet> {
    const raw = await get<
      Omit<Packet, "subject"> & {
        subject: { subject_id: string; addresses_redacted: string[]; cluster_id: string };
      }
    >(`/packets/${encodeURIComponent(caseId)}`);
    const { subject, ...rest } = raw;
    return {
      ...rest,
      subject: {
        subject_id: subject.subject_id,
        addresses: subject.addresses_redacted,
        cluster_id: subject.cluster_id,
      },
    };
  },

  // The frontend-owned seam: simulated in the browser, no network. Delegated unchanged.
  listLineageRecords: fixturesAdapter.listLineageRecords,
  getLineage: fixturesAdapter.getLineage,
  listRuns: fixturesAdapter.listRuns,
  setActiveRun: fixturesAdapter.setActiveRun,
  launchRun: fixturesAdapter.launchRun,
  getRows: fixturesAdapter.getRows,
};

export { BASE as API_BASE };
