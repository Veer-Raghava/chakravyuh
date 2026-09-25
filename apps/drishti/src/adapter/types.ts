/**
 * The one typed surface every screen reads through. No component fetches anything
 * itself; it calls one of these. Shapes are derived by hand from
 * docs/DATA-CONTRACTS.md sections 3-9 and hand-checked. When the live pipeline lands,
 * only the fixtures constants get swapped for JSON in data/fixtures/ui/ — these types
 * and this call surface do not change.
 *
 * Identifier redaction is a value invariant, not a formatting step: every ip/address/
 * txid string that reaches this layer is ALREADY truncated. SHA-256 and Merkle roots
 * are the deliberate exception and are carried in full.
 */

// ----- status / intake (contract section 3) -----

/** L0..L6 map to kavach, setu, jaal, shastra, buddhi, vaani, pramaan. */
export interface StageLamp {
  id: string; // "L0".."L6"
  stage: string; // "kavach".."pramaan"
  complete: boolean;
}

export interface Manifest {
  run_id: string;
  /** SHA-256 of the sealed input, in full. The StatusBar truncates for display. */
  input_sha256: string;
  rows_read: number;
  rows_sealed: number;
  rows_rejected: number;
  /** Denormalised onto the manifest so the StatusBar is a single adapter call. */
  n_transactions: number;
  stages: StageLamp[];
  /** Head of the append-only Merkle log for this run, in full. */
  merkle_head: string;
  air_gapped: boolean;
  reject_reasons: Record<string, number>;
  columns_missing_optional: string[];
  code_version: string;
  tool_version: string;
}

// ----- collapse (announcements -> transactions) -----

export interface CollapseStats {
  n_announcements: number;
  n_transactions: number;
  n_echo: number; // n_announcements - n_transactions
  /** announcements-per-transaction histogram; index is the bucket count value. */
  announcements_per_tx: { bucket: number; count: number }[];
  mean_announcements: number;
}

// ----- transactions list (contract section 4) -----

export interface TransactionRow {
  txid: string; // redacted: first 8 + last 4
  first_seen_us: number;
  n_announcements: number;
  n_distinct_peers: number;
  announce_spread_us: number;
  total_out_sats: number;
  is_coinbase: boolean;
  has_equal_outputs: boolean;
  /** Set when this txid's origin estimate abstains, so the list can badge it. */
  abstained: boolean;
}

// ----- origin estimate (contract section 6) -----

export interface OriginLane {
  peer_ip: string; // redacted: 103.x.x.x
  peer_port: number;
  asn: number | null;
  as_org: string | null;
  geo_country: string | null;
  net_class: string;
  first_seen_us: number;
  /** announcement times relative to first announcement of this txid, ms. */
  announce_times_ms: number[];
  p_origin: number;
  rank: number;
}

export interface OriginFeature {
  label: string; // plain english
  value: string; // mono value, pre-formatted
  gloss: string; // one-line plain-english gloss
}

export interface OriginEstimate {
  txid: string; // redacted
  estimator: string;
  lanes: OriginLane[];
  /** ms extent of the fan x-axis, e.g. 12000. */
  window_ms: number;
  features: OriginFeature[];
  abstain: boolean;
  abstain_reason: string | null;
  /** p_origin(rank 1) - p_origin(rank 2). Null when abstaining. */
  margin: number | null;
  /** conformal-style interval on the rank-1 probability. Null when abstaining. */
  p_interval: [number, number] | null;
}

// ----- fused graph (contract section 5) -----

/**
 * Rendering threshold, not a contract column. cosmos.gl (GPU) draws up to this
 * many nodes; above it getGraph returns cluster-aggregated nodes with `aggregated`
 * set. No `run_config` source exists yet on the frontend, so this is the named
 * source of truth. Documented in docs/DRISHTI-SPEC.md section 4.
 */
export const GRAPH_NODE_CAP = 2000;

export interface GraphParams {
  txid?: string;
  hop_depth?: number;
  value_floor_sats?: number;
  /** Time-window brush, inclusive. Server-side filter; structural edges (null ts) are exempt. */
  time_from_us?: number;
  time_to_us?: number;
}

export interface GraphNode {
  node_id: string;
  kind: "address" | "transaction" | "peer" | "cluster" | "asn";
  label: string; // already truncated
  on_origin_path: boolean;
}

export interface GraphEdge {
  src: string;
  dst: string;
  kind: "SPENDS" | "RECEIVES" | "ANNOUNCED_BY" | "SAME_OWNER" | "HOSTED_IN" | "MEMBER_OF";
  confidence: number;
  evidence: string;
  /** True for edges on the estimated-origin path, so the render lights the whole path, not just its endpoints. */
  on_origin_path: boolean;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** Set when the view aggregated to clusters above the node cap. */
  aggregated: { addresses: number; clusters: number } | null;
}

// ----- alerts queue + inspector (contract sections 7, 8) -----

export interface AlertRow {
  alert_id: string;
  rank: number;
  case_id: string;
  severity: "high" | "medium" | "low";
  conf_low: number;
  conf_high: number;
  typologies: string[];
  cluster_size: number;
  origin_asn: number | null;
  origin_country: string | null;
  dwell_us: number;
  status: "OPEN" | "CLEARED";
  headline: string;
}

export interface ShapContribution {
  feature: string; // plain language, not a column name
  value: number; // signed SHAP contribution
}

export interface EvidenceItem {
  kind: string;
  statement: string;
  weight: number;
  source_ref: string;
}

export interface CounterItem {
  kind: string;
  statement: string;
  strength: number;
  would_clear: boolean;
}

export interface AlertDetail {
  alert_id: string;
  case_id: string;
  severity: "high" | "medium" | "low";
  headline: string;
  status: "OPEN" | "CLEARED";
  why: { base_rate: number; contributions: ShapContribution[] };
  evidence: EvidenceItem[];
  counter: CounterItem[]; // mandatory, never empty
  confidence: {
    score: number;
    low: number;
    high: number;
    coverage_target: number;
    empirical_coverage: number;
    label: string; // "LIKELY_ILLICIT" | ... | "ABSTAIN · insufficient evidence"
  };
}

// ----- evidence packet (contract section 9) -----

export interface Packet {
  case_id: string;
  generated_at_us: number;
  tool_version: string;
  code_version: string;
  subject: { subject_id: string; addresses_redacted: string[]; cluster_id: string };
  attribution: {
    peer_ip: string; // redacted
    peer_port: number;
    observed_at_utc: string;
    p_origin: number;
    margin: number;
    asn: number | null;
    as_org: string | null;
    geo_country: string | null;
    net_class: string;
  };
  findings: { statement: string; kind: string; source_ref: string }[];
  counter_findings: { statement: string; kind: string; would_clear: boolean }[];
  confidence: { low: number; high: number; coverage_target: number; method: string };
  /** printed in full on PACKET; the one string that must not be truncated. */
  merkle_head: string;
  ed25519_signature: string;
  replay: { seed: number; command: string; expected_packet_sha256: string };
  legal: { basis: string; hash_disclosure: string };
  verification: { hash_verified: boolean; signature_valid: boolean; replay_matched: boolean };
  notice: {
    statute: string;
    exchange: string;
    requested_records: string[];
  };
}

// ----- lineage: a per-record trace through all eight stages -----
// A view composed over contract sections 3, 4, 5 and 8 (plus the origin/score/packet
// shapes already typed above). S10 will back getLineage with a real API endpoint; this
// shape is the seam and is authored now against fixtures, exactly like the other calls.

export type FieldStatus = "passthrough" | "added" | "renamed" | "dropped";

export interface LineageField {
  /** Column/field name at this stage. */
  name: string;
  /** Pre-formatted, already redacted. Numeric values arrive mono-ready. */
  value: string;
  status: FieldStatus;
  /** renamed only: the previous name, rendered as `from -> name`. */
  from?: string;
  /** dropped/quarantined only: why it was refused. */
  reason?: string;
}

/** Run-level throughput at a stage. The identity `in === out + dropped` always holds;
 *  when a fixture breaks it, the diff renders a visible failure rather than three numbers
 *  that quietly do not add up. */
export interface StageCounts {
  in: number;
  out: number;
  dropped: number;
}

/** The eight pipeline stages, in fixed order. MAYAJAAL is the generator/source; the
 *  remaining seven are L0..L6 (kavach..pramaan). */
export type LineageStageName =
  | "MAYAJAAL"
  | "KAVACH"
  | "SETU"
  | "JAAL"
  | "SHASTRA"
  | "BUDDHI"
  | "VAANI"
  | "PRAMAAN";

export interface LineageStage {
  stage: LineageStageName;
  /** Drives the Lamp on the spine node. */
  complete: boolean;
  counts: StageCounts;
  /** The record as it entered this stage. */
  before: LineageField[];
  /** The record as it left this stage. */
  after: LineageField[];
  /** One plain-english line of stage-specific truth, shown under the diff. */
  note?: string;
}

/** KAVACH drill-in: the custody evidence. */
export interface KavachDetail {
  /** One entry per input file; sha256 carried in full. */
  files: { name: string; bytes: number; sha256: string }[];
  /** One row per rejected input line, with its reason. Never empty in a real run. */
  rejects: { row_id: number; reason: string }[];
  /** Schema mapping tags for the record's columns. */
  schema: { column: string; tag: "MAPPED" | "SYNTHESISED" | "MISSING" }[];
}

/** SETU drill-in: the grain split. The mean announcements-per-transaction is COMPUTED in
 *  the component from `collapse` (n_announcements / n_transactions), never stored, so a
 *  future run that lands at seven shows seven. */
export interface SetuDetail {
  collapse: CollapseStats;
  sparklines: { label: string; unit: string; points: number[] }[];
}

export interface LineageTrace {
  /** The redacted txid the whole screen follows. */
  record_id: string;
  /** Printed in full on the PRAMAAN stage via HashBlock; the one string not truncated. */
  merkle_head: string;
  /** Exactly eight stages, in the fixed order above. */
  stages: LineageStage[];
  kavach: KavachDetail;
  setu: SetuDetail;
}

/** One entry in the hero-record selector. The note is a short human label; it comes from
 *  the adapter, not the component, so nothing on screen is invented in the view layer. */
export interface LineageRecord {
  id: string; // redacted txid
  note: string;
}

// ----- the fixed adapter surface -----

export interface Adapter {
  getManifest(): Promise<Manifest>;
  getCollapseStats(): Promise<CollapseStats>;
  listTransactions(): Promise<TransactionRow[]>;
  getOriginEstimate(txid: string): Promise<OriginEstimate>;
  getGraph(params: GraphParams): Promise<GraphData>;
  listAlerts(): Promise<AlertRow[]>;
  getAlert(caseId: string): Promise<AlertDetail>;
  getPacket(caseId: string): Promise<Packet>;
  /** The records that carry a full lineage trace, for the hero-record selector. */
  listLineageRecords(): Promise<LineageRecord[]>;
  /** A per-record trace through all eight stages. S10 backs this with a real endpoint. */
  getLineage(recordId: string): Promise<LineageTrace>;
}
