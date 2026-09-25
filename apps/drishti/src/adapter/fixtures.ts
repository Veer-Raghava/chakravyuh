/**
 * Hand-authored fixtures for the console, derived from docs/DATA-CONTRACTS.md 3-9.
 * Every payload is a separate exported constant keyed to one adapter call, so when
 * data/fixtures/ui/*.json lands after S04 each constant is replaced by a JSON import
 * and nothing else in the app changes.
 *
 * All identifiers here are already redacted (ip 103.x.x.x, address bc1q..first6..last4,
 * txid first8..last4). SHA-256 and Merkle roots are carried in full on purpose.
 *
 * Deliberately includes the awkward cases the contract demands: a coinbase tx, a
 * single-peer tx, a >15-peer tx, a Tor-broadcast tx that abstains, a CGNAT pair sharing
 * one IP on two ports, a mining pool that gets cleared, and a WOULD CLEAR counter.
 */
import type {
  Adapter,
  AlertDetail,
  AlertRow,
  CollapseStats,
  FieldStatus,
  GraphData,
  LineageField,
  LineageRecord,
  LineageTrace,
  Manifest,
  OriginEstimate,
  Packet,
  TransactionRow,
} from "./types";

/** Small real latency so the CommandLine shows an honest adapter timing. */
const reply = <T>(value: T, ms = 4): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms));

export const MANIFEST: Manifest = {
  run_id: "20260903-A",
  input_sha256: "4f2a9c3e5b1d7a08f6c42e19b83d5a7c0e91f2b4d6a8c30e5f71b92d4c8ac19d",
  rows_read: 1_000_000,
  rows_sealed: 999_847,
  rows_rejected: 153,
  n_transactions: 111_043,
  stages: [
    { id: "L0", stage: "kavach", complete: true },
    { id: "L1", stage: "setu", complete: true },
    { id: "L2", stage: "jaal", complete: true },
    { id: "L3", stage: "shastra", complete: true },
    { id: "L4", stage: "buddhi", complete: true },
    { id: "L5", stage: "vaani", complete: true },
    { id: "L6", stage: "pramaan", complete: true },
  ],
  merkle_head: "7b81a3f5c9d2e6b40817a92c5f3e8d1b6a04f7c2e590b83d6a1f4c7e02b95e02",
  air_gapped: true,
  reject_reasons: { amount_mismatch: 91, bad_txid: 38, chain_columns_differ: 24 },
  columns_missing_optional: ["vsize", "block_height"],
  code_version: "f70e451",
  tool_version: "0.1.0",
};

export const COLLAPSE_STATS: CollapseStats = {
  n_announcements: 999_847,
  n_transactions: 111_043,
  n_echo: 888_804,
  mean_announcements: 9,
  announcements_per_tx: [
    { bucket: 1, count: 4_812 },
    { bucket: 2, count: 6_140 },
    { bucket: 3, count: 8_903 },
    { bucket: 5, count: 14_552 },
    { bucket: 7, count: 19_881 },
    { bucket: 9, count: 24_106 },
    { bucket: 11, count: 15_774 },
    { bucket: 13, count: 9_402 },
    { bucket: 16, count: 4_988 },
    { bucket: 20, count: 1_485 },
  ],
};

// keyed by redacted txid; the two entries are the confident case and the Tor abstain case.
export const ORIGIN_ESTIMATES: Record<string, OriginEstimate> = {
  "4f2a9c3e…b19d": {
    txid: "4f2a9c3e…b19d",
    estimator: "ensemble",
    window_ms: 12_000,
    abstain: false,
    abstain_reason: null,
    margin: 0.81,
    p_interval: [0.79, 0.92],
    features: [
      {
        label: "FIRST-SEEN RANK",
        value: "1 of 5",
        gloss: "saw it before anyone else we listen to",
      },
      {
        label: "SPREAD",
        value: "412 ms",
        gloss: "its announcements cluster tightly, which relays do not do",
      },
      {
        label: "OBSERVER COVERAGE",
        value: "4 of 16",
        gloss: "twelve of our listeners never saw it, which is itself information",
      },
    ],
    lanes: [
      {
        peer_ip: "103.x.x.x", peer_port: 8333, asn: 9829, as_org: "BSNL", geo_country: "IN",
        net_class: "residential", first_seen_us: 0, announce_times_ms: [0, 118, 402],
        p_origin: 0.87, rank: 1,
      },
      {
        peer_ip: "185.x.x.x", peer_port: 8333, asn: 24940, as_org: "Hetzner", geo_country: "DE",
        net_class: "hosting", first_seen_us: 940_000, announce_times_ms: [940, 1_320],
        p_origin: 0.06, rank: 2,
      },
      // CGNAT pair: one public IP, two ports, ranked separately.
      {
        peer_ip: "198.51.x.x", peer_port: 51_820, asn: 55836, as_org: "Reliance Jio",
        geo_country: "IN", net_class: "mobile", first_seen_us: 2_110_000,
        announce_times_ms: [2_110, 3_004], p_origin: 0.03, rank: 3,
      },
      {
        peer_ip: "198.51.x.x", peer_port: 51_944, asn: 55836, as_org: "Reliance Jio",
        geo_country: "IN", net_class: "mobile", first_seen_us: 3_540_000,
        announce_times_ms: [3_540], p_origin: 0.02, rank: 4,
      },
      {
        peer_ip: "45.x.x.x", peer_port: 8333, asn: 14061, as_org: "DigitalOcean",
        geo_country: "US", net_class: "hosting", first_seen_us: 5_220_000,
        announce_times_ms: [5_220, 7_880], p_origin: 0.01, rank: 5,
      },
    ],
  },
  "e7c4a018…9f4d": {
    txid: "e7c4a018…9f4d",
    estimator: "ensemble",
    window_ms: 12_000,
    abstain: true,
    abstain_reason: "tor_present",
    margin: null,
    p_interval: null,
    features: [
      { label: "FIRST-SEEN RANK", value: "—", gloss: "observed peer is a Tor exit" },
      { label: "SPREAD", value: "980 ms", gloss: "order is uninformative through Tor" },
      { label: "OBSERVER COVERAGE", value: "3 of 16", gloss: "too little of the network saw it" },
    ],
    lanes: [
      {
        peer_ip: "104.x.x.x", peer_port: 8333, asn: 60729, as_org: "Tor Exit",
        geo_country: "NL", net_class: "tor_exit", first_seen_us: 0,
        announce_times_ms: [0, 470], p_origin: 0, rank: 0,
      },
      {
        peer_ip: "171.x.x.x", peer_port: 8333, asn: 9808, as_org: "China Mobile",
        geo_country: "CN", net_class: "unknown", first_seen_us: 510_000,
        announce_times_ms: [510], p_origin: 0, rank: 0,
      },
    ],
  },
  // A second confident case, nine lanes — the "typical" fan the spec describes. Lower
  // margin than 4f2a, so the bracket between first and second reads as a real, smaller gap.
  "c39f1d5a…4e88": {
    txid: "c39f1d5a…4e88",
    estimator: "ensemble",
    window_ms: 12_000,
    abstain: false,
    margin: 0.7,
    p_interval: [0.7, 0.87],
    abstain_reason: null,
    features: [
      { label: "FIRST-SEEN RANK", value: "1 of 9", gloss: "saw it before anyone else we listen to" },
      { label: "SPREAD", value: "628 ms", gloss: "its announcements cluster tightly, which relays do not do" },
      { label: "OBSERVER COVERAGE", value: "6 of 16", gloss: "ten of our listeners never saw it, which is itself information" },
    ],
    lanes: [
      { peer_ip: "49.x.x.x", peer_port: 8333, asn: 45609, as_org: "Bharti Airtel", geo_country: "IN", net_class: "residential", first_seen_us: 0, announce_times_ms: [0, 214, 628], p_origin: 0.79, rank: 1 },
      { peer_ip: "162.x.x.x", peer_port: 8333, asn: 63949, as_org: "Akamai Linode", geo_country: "US", net_class: "hosting", first_seen_us: 1_260_000, announce_times_ms: [1_260, 1_902], p_origin: 0.09, rank: 2 },
      { peer_ip: "88.x.x.x", peer_port: 8333, asn: 24940, as_org: "Hetzner", geo_country: "DE", net_class: "hosting", first_seen_us: 2_540_000, announce_times_ms: [2_540, 3_310], p_origin: 0.04, rank: 3 },
      { peer_ip: "116.x.x.x", peer_port: 8333, asn: 4713, as_org: "NTT", geo_country: "JP", net_class: "residential", first_seen_us: 3_980_000, announce_times_ms: [3_980], p_origin: 0.03, rank: 4 },
      { peer_ip: "51.x.x.x", peer_port: 8333, asn: 16276, as_org: "OVH", geo_country: "FR", net_class: "hosting", first_seen_us: 5_410_000, announce_times_ms: [5_410, 6_120], p_origin: 0.02, rank: 5 },
      { peer_ip: "203.x.x.x", peer_port: 8333, asn: 7545, as_org: "TPG", geo_country: "AU", net_class: "residential", first_seen_us: 6_870_000, announce_times_ms: [6_870], p_origin: 0.01, rank: 6 },
      { peer_ip: "77.x.x.x", peer_port: 8333, asn: 12389, as_org: "Rostelecom", geo_country: "RU", net_class: "residential", first_seen_us: 8_240_000, announce_times_ms: [8_240], p_origin: 0.01, rank: 7 },
      { peer_ip: "197.x.x.x", peer_port: 8333, asn: 36992, as_org: "Etisalat", geo_country: "EG", net_class: "mobile", first_seen_us: 9_710_000, announce_times_ms: [9_710], p_origin: 0.005, rank: 8 },
      { peer_ip: "190.x.x.x", peer_port: 8333, asn: 27699, as_org: "Telefonica", geo_country: "BR", net_class: "residential", first_seen_us: 11_020_000, announce_times_ms: [11_020], p_origin: 0.005, rank: 9 },
    ],
  },
};

export const GRAPHS: Record<string, GraphData> = {
  // The default is a whole investigation, not one transaction: ~10 transactions announced by
  // eight peers across six ASNs, spending and receiving across six wallet clusters. Individual
  // wallets are folded into their cluster by fold() until a cluster is clicked open, so the
  // default view shows the SHAPE (six clusters, the lit origin path) without a hairball. The
  // conceptual totals (171 wallets in 6 clusters) drive the AGGREGATED badge; the MEMBER_OF
  // edges below carry a representative sample of each cluster's wallets for the bloom.
  default: {
    aggregated: { addresses: 171, clusters: 6 },
    nodes: [
      // network layer — eight observed peers nearest the seam, six ASNs behind them
      { node_id: "peer:103.x.x.x", kind: "peer", label: "103.x.x.x", on_origin_path: true },
      { node_id: "peer:49.x.x.x", kind: "peer", label: "49.x.x.x", on_origin_path: false },
      { node_id: "peer:185.x.x.x", kind: "peer", label: "185.x.x.x", on_origin_path: false },
      { node_id: "peer:162.x.x.x", kind: "peer", label: "162.x.x.x", on_origin_path: false },
      { node_id: "peer:88.x.x.x", kind: "peer", label: "88.x.x.x", on_origin_path: false },
      { node_id: "peer:198.51.x.x", kind: "peer", label: "198.51.x.x", on_origin_path: false },
      { node_id: "peer:45.x.x.x", kind: "peer", label: "45.x.x.x", on_origin_path: false },
      { node_id: "peer:116.x.x.x", kind: "peer", label: "116.x.x.x", on_origin_path: false },
      { node_id: "asn:9829", kind: "asn", label: "AS9829 BSNL", on_origin_path: true },
      { node_id: "asn:24940", kind: "asn", label: "AS24940 Hetzner", on_origin_path: false },
      { node_id: "asn:45609", kind: "asn", label: "AS45609 Airtel", on_origin_path: false },
      { node_id: "asn:63949", kind: "asn", label: "AS63949 Linode", on_origin_path: false },
      { node_id: "asn:55836", kind: "asn", label: "AS55836 Jio", on_origin_path: false },
      { node_id: "asn:14061", kind: "asn", label: "AS14061 DigitalOcean", on_origin_path: false },
      // chain layer — ten transactions nearest the seam, six clusters behind them
      { node_id: "tx:4f2a9c3e", kind: "transaction", label: "4f2a9c3e…b19d", on_origin_path: true },
      { node_id: "tx:c39f1d5a", kind: "transaction", label: "c39f1d5a…4e88", on_origin_path: false },
      { node_id: "tx:9b02fa7c", kind: "transaction", label: "9b02fa7c…d341", on_origin_path: false },
      { node_id: "tx:0a17be44", kind: "transaction", label: "0a17be44…7c02", on_origin_path: false },
      { node_id: "tx:7d3e1a90", kind: "transaction", label: "7d3e1a90…af15", on_origin_path: false },
      { node_id: "tx:2c8b5f01", kind: "transaction", label: "2c8b5f01…6b7a", on_origin_path: false },
      { node_id: "tx:5a9d2e3f", kind: "transaction", label: "5a9d2e3f…10cc", on_origin_path: false },
      { node_id: "tx:b1c04d7e", kind: "transaction", label: "b1c04d7e…8e29", on_origin_path: false },
      { node_id: "tx:38f6a2b9", kind: "transaction", label: "38f6a2b9…5d4f", on_origin_path: false },
      { node_id: "tx:e7c4a018", kind: "transaction", label: "e7c4a018…9f4d", on_origin_path: false },
      { node_id: "cluster:12", kind: "cluster", label: "cluster 12 · 41 addr", on_origin_path: true },
      { node_id: "cluster:07", kind: "cluster", label: "cluster 07 · 88 addr", on_origin_path: false },
      { node_id: "cluster:19", kind: "cluster", label: "cluster 19 · 12 addr", on_origin_path: false },
      { node_id: "cluster:23", kind: "cluster", label: "cluster 23 · 9 addr", on_origin_path: false },
      { node_id: "cluster:31", kind: "cluster", label: "cluster 31 · 15 addr", on_origin_path: false },
      { node_id: "cluster:44", kind: "cluster", label: "cluster 44 · 6 addr", on_origin_path: false },
      // sample member wallets — hidden until their cluster is expanded (fold folds these in)
      { node_id: "addr:bc1q4f", kind: "address", label: "bc1q4f…9f4d", on_origin_path: true },
      { node_id: "addr:bc1q7a", kind: "address", label: "bc1q7a…22c8", on_origin_path: false },
      { node_id: "addr:bc1q9c", kind: "address", label: "bc1q9c…4d10", on_origin_path: false },
      { node_id: "addr:bc1qd2", kind: "address", label: "bc1qd2…7f31", on_origin_path: false },
      { node_id: "addr:bc1q1e", kind: "address", label: "bc1q1e…0a9b", on_origin_path: false },
      { node_id: "addr:bc1q88", kind: "address", label: "bc1q88…c3e7", on_origin_path: false },
      { node_id: "addr:bc1qa3", kind: "address", label: "bc1qa3…91f0", on_origin_path: false },
      { node_id: "addr:bc1qf0", kind: "address", label: "bc1qf0…5b22", on_origin_path: false },
      { node_id: "addr:bc1q55", kind: "address", label: "bc1q55…8e14", on_origin_path: false },
      { node_id: "addr:bc1q2b", kind: "address", label: "bc1q2b…d6a1", on_origin_path: false },
      { node_id: "addr:bc1q6d", kind: "address", label: "bc1q6d…2c88", on_origin_path: false },
      { node_id: "addr:bc1qc1", kind: "address", label: "bc1qc1…7a03", on_origin_path: false },
      { node_id: "addr:bc1q90", kind: "address", label: "bc1q90…e4d5", on_origin_path: false },
      { node_id: "addr:bc1q4a", kind: "address", label: "bc1q4a…13bf", on_origin_path: false },
      { node_id: "addr:bc1qe7", kind: "address", label: "bc1qe7…6021", on_origin_path: false },
      { node_id: "addr:bc1q33", kind: "address", label: "bc1q33…9c7e", on_origin_path: false },
      { node_id: "addr:bc1qb8", kind: "address", label: "bc1qb8…4f10", on_origin_path: false },
      { node_id: "addr:bc1q0f", kind: "address", label: "bc1q0f…a288", on_origin_path: false },
      { node_id: "addr:bc1q7e", kind: "address", label: "bc1q7e…30d4", on_origin_path: false },
    ],
    edges: [
      // announcements (dotted, cross the seam). The origin peer announced 4f2a first.
      { src: "peer:103.x.x.x", dst: "tx:4f2a9c3e", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed first, 402ms spread", on_origin_path: true },
      { src: "peer:185.x.x.x", dst: "tx:4f2a9c3e", kind: "ANNOUNCED_BY", confidence: 1, evidence: "relayed 940ms later", on_origin_path: false },
      { src: "peer:49.x.x.x", dst: "tx:c39f1d5a", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:185.x.x.x", dst: "tx:9b02fa7c", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:162.x.x.x", dst: "tx:0a17be44", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:88.x.x.x", dst: "tx:7d3e1a90", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:198.51.x.x", dst: "tx:2c8b5f01", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:45.x.x.x", dst: "tx:5a9d2e3f", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:116.x.x.x", dst: "tx:b1c04d7e", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:103.x.x.x", dst: "tx:38f6a2b9", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      { src: "peer:198.51.x.x", dst: "tx:e7c4a018", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: false },
      // peer → ASN scaffolding (hair)
      { src: "peer:103.x.x.x", dst: "asn:9829", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: true },
      { src: "peer:185.x.x.x", dst: "asn:24940", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: false },
      { src: "peer:88.x.x.x", dst: "asn:24940", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: false },
      { src: "peer:49.x.x.x", dst: "asn:45609", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: false },
      { src: "peer:162.x.x.x", dst: "asn:63949", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: false },
      { src: "peer:116.x.x.x", dst: "asn:63949", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: false },
      { src: "peer:198.51.x.x", dst: "asn:55836", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: false },
      { src: "peer:45.x.x.x", dst: "asn:14061", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: false },
      // transaction → wallet flows (solid); fold redirects each onto the wallet's cluster
      { src: "tx:4f2a9c3e", dst: "addr:bc1q4f", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: true },
      { src: "tx:4f2a9c3e", dst: "addr:bc1q1e", kind: "RECEIVES", confidence: 1, evidence: "output 0", on_origin_path: false },
      { src: "tx:c39f1d5a", dst: "addr:bc1q7a", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:c39f1d5a", dst: "addr:bc1qf0", kind: "RECEIVES", confidence: 1, evidence: "output 0", on_origin_path: false },
      { src: "tx:9b02fa7c", dst: "addr:bc1q88", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:9b02fa7c", dst: "addr:bc1q6d", kind: "RECEIVES", confidence: 1, evidence: "output 1", on_origin_path: false },
      { src: "tx:0a17be44", dst: "addr:bc1q55", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:0a17be44", dst: "addr:bc1q4a", kind: "RECEIVES", confidence: 1, evidence: "output 0", on_origin_path: false },
      { src: "tx:7d3e1a90", dst: "addr:bc1qc1", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:7d3e1a90", dst: "addr:bc1qb8", kind: "RECEIVES", confidence: 1, evidence: "output 2", on_origin_path: false },
      { src: "tx:2c8b5f01", dst: "addr:bc1qe7", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:2c8b5f01", dst: "addr:bc1q9c", kind: "RECEIVES", confidence: 1, evidence: "output 0", on_origin_path: false },
      { src: "tx:5a9d2e3f", dst: "addr:bc1q0f", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:5a9d2e3f", dst: "addr:bc1qa3", kind: "RECEIVES", confidence: 1, evidence: "output 1", on_origin_path: false },
      { src: "tx:b1c04d7e", dst: "addr:bc1q2b", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:b1c04d7e", dst: "addr:bc1qd2", kind: "RECEIVES", confidence: 1, evidence: "output 0", on_origin_path: false },
      { src: "tx:38f6a2b9", dst: "addr:bc1q33", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "tx:38f6a2b9", dst: "addr:bc1q90", kind: "RECEIVES", confidence: 1, evidence: "output 0", on_origin_path: false },
      { src: "tx:e7c4a018", dst: "addr:bc1q7e", kind: "RECEIVES", confidence: 1, evidence: "output 0", on_origin_path: false },
      // wallet → cluster membership (hair). bc1q4f is the lit member of the origin cluster.
      { src: "addr:bc1q4f", dst: "cluster:12", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: true },
      { src: "addr:bc1q7a", dst: "cluster:12", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q9c", dst: "cluster:12", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1qd2", dst: "cluster:12", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q1e", dst: "cluster:07", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q88", dst: "cluster:07", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1qa3", dst: "cluster:07", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1qf0", dst: "cluster:19", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q55", dst: "cluster:19", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q2b", dst: "cluster:19", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q6d", dst: "cluster:23", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1qc1", dst: "cluster:23", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q90", dst: "cluster:23", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q4a", dst: "cluster:31", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1qe7", dst: "cluster:31", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q33", dst: "cluster:31", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1qb8", dst: "cluster:44", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q0f", dst: "cluster:44", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q7e", dst: "cluster:44", kind: "MEMBER_OF", confidence: 1, evidence: "multi_input", on_origin_path: false },
      // SAME_OWNER heuristics (dashed, drawn at confidence — a weak link looks weak)
      { src: "cluster:12", dst: "cluster:19", kind: "SAME_OWNER", confidence: 0.36, evidence: "shared change address", on_origin_path: false },
      { src: "cluster:07", dst: "cluster:31", kind: "SAME_OWNER", confidence: 0.52, evidence: "co-spend heuristic", on_origin_path: false },
      { src: "cluster:23", dst: "cluster:44", kind: "SAME_OWNER", confidence: 0.41, evidence: "timing correlation", on_origin_path: false },
    ],
  },
  // The smallest possible case: one transaction, one peer, one cluster. Kept as the floor of
  // the visual model, reachable via getGraph({ txid: "single" }); the model scales from here.
  single: {
    aggregated: null,
    nodes: [
      { node_id: "peer:103.x.x.x", kind: "peer", label: "103.x.x.x", on_origin_path: true },
      { node_id: "tx:4f2a9c3e", kind: "transaction", label: "4f2a9c3e…b19d", on_origin_path: true },
      { node_id: "addr:bc1q4f", kind: "address", label: "bc1q4f…9f4d", on_origin_path: true },
      { node_id: "addr:bc1q7a", kind: "address", label: "bc1q7a…22c8", on_origin_path: false },
      { node_id: "cluster:12", kind: "cluster", label: "cluster 12", on_origin_path: false },
      { node_id: "asn:9829", kind: "asn", label: "AS9829 BSNL", on_origin_path: true },
    ],
    edges: [
      { src: "peer:103.x.x.x", dst: "tx:4f2a9c3e", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: true },
      { src: "tx:4f2a9c3e", dst: "addr:bc1q4f", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: true },
      { src: "tx:4f2a9c3e", dst: "addr:bc1q7a", kind: "RECEIVES", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q4f", dst: "cluster:12", kind: "MEMBER_OF", confidence: 0.36, evidence: "multi_input", on_origin_path: false },
      { src: "addr:bc1q7a", dst: "cluster:12", kind: "SAME_OWNER", confidence: 0.36, evidence: "multi_input", on_origin_path: false },
      { src: "peer:103.x.x.x", dst: "asn:9829", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: true },
    ],
  },
  // Above the node cap: getGraph collapses addresses into cluster nodes and sets
  // `aggregated` so the fallback renders the AGGREGATED badge instead of a silent subset.
  aggregated: {
    aggregated: { addresses: 4912, clusters: 318 },
    nodes: [
      { node_id: "peer:103.x.x.x", kind: "peer", label: "103.x.x.x", on_origin_path: true },
      { node_id: "tx:4f2a9c3e", kind: "transaction", label: "4f2a9c3e…b19d", on_origin_path: true },
      { node_id: "cluster:12", kind: "cluster", label: "cluster 12 · 41 addr", on_origin_path: true },
      { node_id: "cluster:07", kind: "cluster", label: "cluster 07 · 318 addr", on_origin_path: false },
      { node_id: "cluster:19", kind: "cluster", label: "cluster 19 · 12 addr", on_origin_path: false },
      { node_id: "asn:9829", kind: "asn", label: "AS9829 BSNL", on_origin_path: true },
    ],
    edges: [
      { src: "peer:103.x.x.x", dst: "tx:4f2a9c3e", kind: "ANNOUNCED_BY", confidence: 1, evidence: "observed", on_origin_path: true },
      { src: "tx:4f2a9c3e", dst: "cluster:12", kind: "SPENDS", confidence: 1, evidence: "multi_input", on_origin_path: true },
      { src: "tx:4f2a9c3e", dst: "cluster:07", kind: "RECEIVES", confidence: 1, evidence: "multi_input", on_origin_path: false },
      { src: "cluster:12", dst: "cluster:19", kind: "SAME_OWNER", confidence: 0.36, evidence: "multi_input", on_origin_path: false },
      { src: "peer:103.x.x.x", dst: "asn:9829", kind: "HOSTED_IN", confidence: 1, evidence: "geoip", on_origin_path: true },
    ],
  },
};

export const TRANSACTIONS: TransactionRow[] = [
  {
    txid: "4f2a9c3e…b19d",
    first_seen_us: 1_756_872_100_000_000,
    n_announcements: 10,
    n_distinct_peers: 5,
    announce_spread_us: 7_880_000,
    total_out_sats: 248_500_000,
    is_coinbase: false,
    has_equal_outputs: false,
    abstained: false,
  },
  {
    txid: "0a17be44…7c02",
    first_seen_us: 1_756_872_260_000_000,
    n_announcements: 1,
    n_distinct_peers: 1,
    announce_spread_us: 0,
    total_out_sats: 5_000_000_000,
    is_coinbase: true,
    has_equal_outputs: false,
    abstained: true,
  },
  {
    txid: "c39f1d5a…4e88",
    first_seen_us: 1_756_872_410_000_000,
    n_announcements: 14,
    n_distinct_peers: 9,
    announce_spread_us: 11_020_000,
    total_out_sats: 12_004_120,
    is_coinbase: false,
    has_equal_outputs: true,
    abstained: false,
  },
  {
    txid: "9b02fa7c…d341",
    first_seen_us: 1_756_872_540_000_000,
    n_announcements: 6,
    n_distinct_peers: 5,
    announce_spread_us: 4_120_000,
    total_out_sats: 88_190_000,
    is_coinbase: false,
    has_equal_outputs: false,
    abstained: false,
  },
  {
    txid: "e7c4a018…9f4d",
    first_seen_us: 1_756_872_690_000_000,
    n_announcements: 3,
    n_distinct_peers: 3,
    announce_spread_us: 980_000,
    total_out_sats: 4_500_000,
    is_coinbase: false,
    has_equal_outputs: false,
    abstained: true,
  },
];

export const ALERTS: AlertRow[] = [
  {
    alert_id: "AL-0001", rank: 1, case_id: "CASE-2026-0917", severity: "high",
    conf_low: 0.71, conf_high: 0.9, typologies: ["fan_out", "rapid_hop"], cluster_size: 318,
    origin_asn: 9829, origin_country: "IN", dwell_us: 42_000_000, status: "OPEN",
    headline: "Cluster fans out to 41 wallets within one block window.",
  },
  {
    // The mining pool that gets cleared in the demo.
    alert_id: "AL-0002", rank: 2, case_id: "CASE-2026-0918", severity: "high",
    conf_low: 0.63, conf_high: 0.85, typologies: ["fan_out"], cluster_size: 902,
    origin_asn: 24940, origin_country: "DE", dwell_us: 5_400_000, status: "OPEN",
    headline: "High out-degree payout pattern from a single funding source.",
  },
  {
    alert_id: "AL-0003", rank: 3, case_id: "CASE-2026-0919", severity: "medium",
    conf_low: 0.44, conf_high: 0.68, typologies: ["peel_chain"], cluster_size: 27,
    origin_asn: 55836, origin_country: "IN", dwell_us: 118_000_000, status: "OPEN",
    headline: "Three-hop peel chain sheds change across new addresses.",
  },
  {
    alert_id: "AL-0004", rank: 4, case_id: "CASE-2026-0920", severity: "low",
    conf_low: 0.2, conf_high: 0.52, typologies: ["structuring"], cluster_size: 12,
    origin_asn: null, origin_country: null, dwell_us: 9_000_000, status: "OPEN",
    headline: "Repeated sub-threshold transfers to one collector address.",
  },
];

export const ALERT_DETAILS: Record<string, AlertDetail> = {
  "CASE-2026-0918": {
    alert_id: "AL-0002",
    case_id: "CASE-2026-0918",
    severity: "high",
    headline: "High out-degree payout pattern from a single funding source.",
    status: "OPEN",
    why: {
      base_rate: 0.03,
      contributions: [
        { feature: "pays many addresses on a fixed cadence", value: 0.31 },
        { feature: "single large funding input", value: 0.18 },
        { feature: "consistent low fee rate", value: -0.12 },
        { feature: "no reuse of payout addresses", value: -0.22 },
        { feature: "long account age", value: -0.15 },
      ],
    },
    evidence: [
      { kind: "typology", statement: "902 outputs share one funding source in 40 minutes.", weight: 0.31, source_ref: "signals/typology_hits.parquet#h-2231" },
      { kind: "network_context", statement: "Funding peer sits in a hosting ASN, not residential.", weight: 0.12, source_ref: "normalised/peers.parquet#185.x.x.x" },
    ],
    counter: [
      { kind: "pool_payout_pattern", statement: "Cadence and fan-out match a mining pool payout, not laundering.", strength: 0.88, would_clear: true },
      { kind: "entity_type_conflict", statement: "Subject is flagged exempt_from_scoring as a mining_pool.", strength: 0.74, would_clear: true },
    ],
    confidence: {
      score: 0.74, low: 0.63, high: 0.85, coverage_target: 0.9,
      empirical_coverage: 0.91, label: "UNCLEAR",
    },
  },
};

export const PACKETS: Record<string, Packet> = {
  "CASE-2026-0917": {
    case_id: "CASE-2026-0917",
    generated_at_us: 1_756_890_000_000_000,
    tool_version: "0.1.0",
    code_version: "f70e451",
    subject: { subject_id: "cluster:12", addresses_redacted: ["bc1q4f…9f4d", "bc1q7a…22c8"], cluster_id: "cluster:12" },
    attribution: {
      peer_ip: "103.x.x.x", peer_port: 8333, observed_at_utc: "2026-09-03T04:15:00Z",
      p_origin: 0.87, margin: 0.81, asn: 9829, as_org: "BSNL", geo_country: "IN",
      net_class: "residential",
    },
    findings: [
      { statement: "Peer announced the transaction before any other observer saw it.", kind: "origin_estimate", source_ref: "signals/origin_estimates.parquet#4f2a" },
      { statement: "Cluster fans out to 41 destination wallets within one block.", kind: "typology", source_ref: "signals/typology_hits.parquet#h-1180" },
    ],
    counter_findings: [
      { statement: "Twelve of sixteen observers never saw this transaction.", kind: "insufficient_observation", would_clear: false },
    ],
    confidence: { low: 0.71, high: 0.9, coverage_target: 0.9, method: "class_conditional" },
    merkle_head: "7b81a3f5c9d2e6b40817a92c5f3e8d1b6a04f7c2e590b83d6a1f4c7e02b95e02",
    ed25519_signature: "s7Qm2fL9xK0pR4vN8cH3bW1eU6yT5aD2gJ7iZ0oX4mB9nQ5rF8kC1dP3wS6tY0uL2hG4jV7bN9xA1cM5eK8oR3q==",
    replay: {
      seed: 42,
      command: "make verify-replay CASE=CASE-2026-0917",
      expected_packet_sha256: "b3d9f1027a6c4e85d0b28f39c6a1e74f2058b9d3c7e04a16f8b25d9c30e7a1f4",
    },
    legal: { basis: "BNSS 2023 s.94", hash_disclosure: "BSA 2023 s.63(4), Schedule Part A" },
    verification: { hash_verified: true, signature_valid: true, replay_matched: true },
    notice: {
      statute: "BNSS 2023 s.94",
      exchange: "CoinExch Pvt Ltd",
      requested_records: [
        "KYC records for the account controlling bc1q4f…9f4d",
        "Login IP history for 2026-09-01 to 2026-09-03",
        "Withdrawal ledger referencing txid 4f2a9c3e…b19d",
      ],
    },
  },
};

// ---- lineage: the per-record trace through all eight stages ----
// Composed over contract sections 3, 4, 5, 8 and the origin/score/packet shapes above.
// S10 will replace LINEAGE_TRACES with a JSON import from a real endpoint; nothing else
// in the app changes. Run-level counts balance at every stage (in === out + dropped);
// the only drop is KAVACH's 153 rejects. The funnel narrows by grain (announcements ->
// transactions -> scored subjects -> top-20 leads -> one packet), never by silent loss.

const f = (
  name: string,
  value: string,
  status: FieldStatus = "passthrough",
  extra: Partial<LineageField> = {},
): LineageField => ({ name, value, status, ...extra });

// Shared across both traces: the KAVACH custody drill-in and the SETU collapse drill-in.
const KAVACH_DETAIL = {
  files: [
    { name: "capture_2026-09-03_00.csv", bytes: 4_182_559_744, sha256: "9d1f4a7c2e5b83160af92c4d7e1b6035a8c40f92e7b1d5063a9f24c8e10b7d3a" },
    { name: "capture_2026-09-03_12.csv", bytes: 3_904_112_128, sha256: "1b7e0c39a5d24f68b03e91c7d4a25086f39b1c7e05a2d8460b71f39c2e8a5d04" },
  ],
  // A sample of the 153 rejected lines; the table is shown with rows, never empty.
  rejects: [
    { row_id: 12_004, reason: "amount_mismatch" },
    { row_id: 48_991, reason: "chain_columns_differ" },
    { row_id: 51_230, reason: "bad_txid" },
    { row_id: 88_417, reason: "amount_mismatch" },
    { row_id: 90_882, reason: "chain_columns_differ" },
    { row_id: 204_556, reason: "bad_txid" },
    { row_id: 771_009, reason: "amount_mismatch" },
    { row_id: 903_744, reason: "chain_columns_differ" },
  ],
  schema: [
    { column: "txid", tag: "MAPPED" as const },
    { column: "src_ip", tag: "MAPPED" as const },
    { column: "output_amounts", tag: "MAPPED" as const },
    { column: "script_type", tag: "SYNTHESISED" as const },
    { column: "geo_country", tag: "MISSING" as const },
    { column: "asn", tag: "MISSING" as const },
    { column: "vsize", tag: "MISSING" as const },
    { column: "block_height", tag: "MISSING" as const },
  ],
};

const SETU_DETAIL = {
  collapse: COLLAPSE_STATS,
  sparklines: [
    { label: "announcements / sec", unit: "ann", points: [140, 162, 155, 190, 210, 198, 176, 165, 182, 205, 221, 214, 199, 188, 176, 169, 158, 172, 190, 201] },
    { label: "unique peers / min", unit: "peers", points: [42, 45, 47, 44, 49, 52, 55, 51, 48, 46, 50, 53, 57, 54, 52, 49, 47, 45, 48, 51] },
    { label: "transactions / block", unit: "tx", points: [1180, 1240, 1195, 1310, 1288, 1402, 1356, 1298, 1247, 1330, 1410, 1388, 1276, 1225, 1301, 1360] },
  ],
};

const first = <T>(rec: Record<string, T>): T => rec[Object.keys(rec)[0]];

const HERO_TRACE: LineageTrace = {
  record_id: "4f2a9c3e…b19d",
  merkle_head: MANIFEST.merkle_head,
  kavach: KAVACH_DETAIL,
  setu: SETU_DETAIL,
  stages: [
    {
      stage: "MAYAJAAL", complete: true, counts: { in: 1_000_000, out: 1_000_000, dropped: 0 },
      note: "Synthetic capture from a seeded generator. Every field below is the ground the pipeline reasons over.",
      before: [],
      after: [
        f("timestamp", "2026-09-03T04:15:00Z", "added"),
        f("src_ip", "103.x.x.x", "added"),
        f("src_port", "8333", "added"),
        f("dst_ip", "198.18.x.x", "added"),
        f("txid", "4f2a9c3e…b19d", "added"),
        f("output_addresses", "bc1q4f…9f4d | bc1q7a…22c8", "added"),
        f("output_amounts", "248,500,000 | 12,000,000", "added"),
      ],
    },
    {
      stage: "KAVACH", complete: true, counts: { in: 1_000_000, out: 999_847, dropped: 153 },
      note: "sha256 taken on the raw bytes before any coercion. 153 rows rejected run-wide — none of them this record's. Click to open the custody detail.",
      before: [f("timestamp", "2026-09-03T04:15:00Z"), f("src_ip", "103.x.x.x"), f("txid", "4f2a9c3e…b19d")],
      after: [
        f("ts_us", "1,756,872,900,000,000", "renamed", { from: "timestamp" }),
        f("ts_raw", "2026-09-03T04:15:00Z", "added"),
        f("row_id", "728,041", "added"),
        f("src_ip_version", "4", "added"),
        f("src_ip", "103.x.x.x"),
        f("txid", "4f2a9c3e…b19d"),
      ],
    },
    {
      stage: "SETU", complete: true, counts: { in: 999_847, out: 999_847, dropped: 0 },
      note: "The grain splits: announcements become transactions. This record is 9 announcements of 1 transaction. Click to open the collapse detail.",
      before: [f("src_ip", "103.x.x.x"), f("src_port", "8333"), f("dst_ip", "198.18.x.x")],
      after: [
        f("peer_ip", "103.x.x.x", "renamed", { from: "src_ip" }),
        f("peer_port", "8333", "renamed", { from: "src_port" }),
        f("observer_ip", "198.18.x.x", "renamed", { from: "dst_ip" }),
        f("geo_country", "IN", "added"),
        f("asn", "9829", "added"),
        f("as_org", "BSNL", "added"),
        f("net_class", "residential", "added"),
        f("rank_in_tx", "1", "added"),
      ],
    },
    // __LINEAGE_HERO_MORE__
    {
      stage: "JAAL", complete: true, counts: { in: 111_043, out: 111_043, dropped: 0 },
      note: "SAME_OWNER never merges nodes — the cluster link stays an edge at 0.36 confidence, so a weak heuristic reads weak.",
      before: [f("peer_ip", "103.x.x.x"), f("txid", "4f2a9c3e…b19d")],
      after: [
        f("node", "tx:4f2a9c3e", "added"),
        f("ANNOUNCED_BY", "peer 103.x.x.x → tx 4f2a9c3e · conf 1.00", "added"),
        f("SPENDS", "tx 4f2a9c3e → addr bc1q4f…9f4d · conf 1.00", "added"),
        f("MEMBER_OF", "addr bc1q4f…9f4d → cluster 12 · conf 0.36", "added"),
      ],
    },
    {
      stage: "SHASTRA", complete: true, counts: { in: 111_043, out: 111_043, dropped: 0 },
      note: "Order is noisy by design. The estimate uses order, spread, and who did not see it — not first-seen alone.",
      before: [f("node", "tx:4f2a9c3e")],
      after: [
        f("p_origin", "p = 0.87  [0.79, 0.92]", "added"),
        f("rank", "1 of 9", "added"),
        f("margin", "0.81", "added"),
      ],
    },
    {
      stage: "BUDDHI", complete: true, counts: { in: 4_912, out: 4_912, dropped: 0 },
      note: "Never a score without its interval. Coverage 0.91 against a 0.90 target.",
      before: [f("p_origin", "p = 0.87  [0.79, 0.92]")],
      after: [
        f("risk_score", "0.81  [0.71, 0.90]", "added"),
        f("label", "LIKELY_ILLICIT", "added"),
      ],
    },
    {
      stage: "VAANI", complete: true, counts: { in: 20, out: 20, dropped: 0 },
      note: "Every alert carries its counter-evidence; an empty counter section is a bug, not a clean alert.",
      before: [f("risk_score", "0.81  [0.71, 0.90]")],
      after: [
        f("headline", "Cluster fans out to 41 wallets within one block window.", "added"),
        f("counter", "Twelve of sixteen observers never saw this transaction.", "added"),
      ],
    },
    {
      stage: "PRAMAAN", complete: true, counts: { in: 1, out: 1, dropped: 0 },
      note: "The packet verifies: hash, signature and replay all matched. The Merkle head prints in full below.",
      before: [f("headline", "Cluster fans out to 41 wallets within one block window.")],
      after: [
        f("packet", "signed · hash-chained · replay: make verify-replay CASE=CASE-2026-0917", "added"),
        f("ed25519", "s7Qm2fL9…Q5r=", "added"),
      ],
    },
  ],
};

// The Tor-broadcast record: the honest refusal, end to end. Origin abstains, so no
// confidence is claimed downstream and the packet is withheld as not attribution-ready.
const ABSTAIN_TRACE: LineageTrace = {
  record_id: "e7c4a018…9f4d",
  merkle_head: MANIFEST.merkle_head,
  kavach: KAVACH_DETAIL,
  setu: SETU_DETAIL,
  stages: [
    {
      stage: "MAYAJAAL", complete: true, counts: { in: 1_000_000, out: 1_000_000, dropped: 0 },
      note: "Synthetic capture from a seeded generator.",
      before: [],
      after: [
        f("src_ip", "104.x.x.x", "added"),
        f("src_port", "8333", "added"),
        f("txid", "e7c4a018…9f4d", "added"),
        f("output_amounts", "4,500,000", "added"),
      ],
    },
    {
      stage: "KAVACH", complete: true, counts: { in: 1_000_000, out: 999_847, dropped: 153 },
      note: "sha256 taken on the raw bytes. Click to open the custody detail.",
      before: [f("timestamp", "2026-09-03T04:31:30Z"), f("src_ip", "104.x.x.x")],
      after: [
        f("ts_us", "1,756,872,690,000,000", "renamed", { from: "timestamp" }),
        f("row_id", "804,517", "added"),
        f("src_ip", "104.x.x.x"),
      ],
    },
    {
      stage: "SETU", complete: true, counts: { in: 999_847, out: 999_847, dropped: 0 },
      note: "The grain splits: announcements become transactions. This record is 3 announcements of 1 transaction.",
      before: [f("src_ip", "104.x.x.x"), f("src_port", "8333")],
      after: [
        f("peer_ip", "104.x.x.x", "renamed", { from: "src_ip" }),
        f("peer_port", "8333", "renamed", { from: "src_port" }),
        f("geo_country", "NL", "added"),
        f("asn", "60729", "added"),
        f("net_class", "tor_exit", "added"),
      ],
    },
    {
      stage: "JAAL", complete: true, counts: { in: 111_043, out: 111_043, dropped: 0 },
      note: "The record still projects to nodes and edges; the announcement edge is observed.",
      before: [f("peer_ip", "104.x.x.x"), f("txid", "e7c4a018…9f4d")],
      after: [
        f("node", "tx:e7c4a018", "added"),
        f("ANNOUNCED_BY", "peer 104.x.x.x → tx e7c4a018 · conf 1.00", "added"),
      ],
    },
    {
      stage: "SHASTRA", complete: true, counts: { in: 111_043, out: 111_043, dropped: 0 },
      note: "Observed peer is a Tor exit; origin not estimable. Abstention is a first-class outcome, not a low score in disguise.",
      before: [f("node", "tx:e7c4a018")],
      after: [f("origin", "ABSTAIN · tor_present", "added")],
    },
    {
      stage: "BUDDHI", complete: true, counts: { in: 4_912, out: 4_912, dropped: 0 },
      note: "Too little of the network saw it to score honestly.",
      before: [f("origin", "ABSTAIN · tor_present")],
      after: [f("risk_score", "ABSTAIN · insufficient evidence", "added")],
    },
    {
      stage: "VAANI", complete: true, counts: { in: 20, out: 20, dropped: 0 },
      note: "The counter-evidence is decisive here.",
      before: [f("risk_score", "ABSTAIN · insufficient evidence")],
      after: [
        f("headline", "Insufficient observation — three of sixteen listeners saw it.", "added"),
        f("counter", "WOULD CLEAR · observed only through a Tor exit.", "added"),
      ],
    },
    {
      stage: "PRAMAAN", complete: true, counts: { in: 1, out: 1, dropped: 0 },
      note: "Packet withheld: attribution is not ready without a peer IP, a source port and a precise time.",
      before: [f("headline", "Insufficient observation — three of sixteen listeners saw it.")],
      after: [f("packet", "withheld · attribution_ready = false", "dropped", { reason: "no origin peer; Tor exit only" })],
    },
  ],
};

export const LINEAGE_TRACES: Record<string, LineageTrace> = {
  "4f2a9c3e…b19d": HERO_TRACE,
  "e7c4a018…9f4d": ABSTAIN_TRACE,
};

// The selector list, keyed to LINEAGE_TRACES; notes live here, not in the view layer.
export const LINEAGE_RECORDS: LineageRecord[] = [
  { id: "4f2a9c3e…b19d", note: "confident originator" },
  { id: "e7c4a018…9f4d", note: "Tor · abstains" },
];

export const fixturesAdapter: Adapter = {
  getManifest: () => reply(MANIFEST),
  getCollapseStats: () => reply(COLLAPSE_STATS),
  listTransactions: () => reply(TRANSACTIONS),
  getOriginEstimate: (txid) => reply(ORIGIN_ESTIMATES[txid] ?? first(ORIGIN_ESTIMATES)),
  getGraph: (params) => reply(GRAPHS[params.txid ?? "default"] ?? GRAPHS.default),
  listAlerts: () => reply(ALERTS),
  getAlert: (caseId) => reply(ALERT_DETAILS[caseId] ?? first(ALERT_DETAILS)),
  getPacket: (caseId) => reply(PACKETS[caseId] ?? first(PACKETS)),
  listLineageRecords: () => reply(LINEAGE_RECORDS),
  getLineage: (recordId) => reply(LINEAGE_TRACES[recordId] ?? first(LINEAGE_TRACES)),
};
