import { useMemo, useState } from "react";
import packet from "../../data/fixtures/research-leads.json";
import window7 from "../../data/fixtures/research-leads-window7.json";
import window9 from "../../data/fixtures/research-leads-window9.json";
import styles from "./ModelIntelligence.module.css";

type Node = {
  id: string;
  kind: string;
  label: string;
  focus?: boolean;
  asn?: number | null;
};
type Edge = {
  source: string;
  target: string;
  relation: string;
  amount_sats?: number;
};
type Lead = {
  id: string;
  rank: number;
  risk_score: number;
  address_count: number;
  addresses: string[];
  supporting_transaction_count: number;
  displayed_transaction_count: number;
  graph_truncated: boolean;
  facts: Record<string, number | string | null>;
  reasons: { feature: string; shap_margin: number }[];
  mitigating_contributions: { feature: string; shap_margin: number }[];
  evidence_graph: { nodes: Node[]; edges: Edge[] };
  next_actions: string[];
  network_observation_count: number;
};
type Queue = {
  schema_version: number;
  leads: Lead[];
  lead_count: number;
  partition_mode: string;
};
const initialQueue = packet as unknown as Queue;
function parseQueue(value: unknown): Queue {
  const q = value as Queue;
  if (
    !q ||
    q.schema_version !== 1 ||
    !Array.isArray(q.leads) ||
    q.leads.length < 1 ||
    q.leads.length > 200 ||
    q.lead_count !== q.leads.length
  )
    throw new Error(
      "Expected a generated investigation queue with 1–200 leads.",
    );
  for (const lead of q.leads) {
    if (
      !Number.isInteger(lead.rank) ||
      lead.rank < 1 ||
      !Number.isInteger(lead.address_count) ||
      lead.address_count < 1 ||
      !Number.isInteger(lead.supporting_transaction_count) ||
      lead.supporting_transaction_count < 0
    )
      throw new Error("Invalid lead counts.");
    if (
      !lead ||
      typeof lead.id !== "string" ||
      !Array.isArray(lead.addresses) ||
      !lead.addresses.every((a) => typeof a === "string") ||
      !lead.addresses.length ||
      !Number.isFinite(lead.risk_score) ||
      lead.risk_score < 0 ||
      lead.risk_score > 1 ||
      !lead.facts ||
      typeof lead.facts !== "object" ||
      Array.isArray(lead.facts) ||
      !Array.isArray(lead.reasons) ||
      !Array.isArray(lead.mitigating_contributions) ||
      !Array.isArray(lead.next_actions) ||
      !lead.next_actions.every((a) => typeof a === "string")
    )
      throw new Error("Lead fields are missing or invalid.");
    if (
      ![...lead.reasons, ...lead.mitigating_contributions].every(
        (r) => typeof r.feature === "string" && Number.isFinite(r.shap_margin),
      )
    )
      throw new Error("Invalid model contributions.");
    if (
      !Object.values(lead.facts).every(
        (v) =>
          v == null ||
          typeof v === "string" ||
          (typeof v === "number" && Number.isFinite(v)),
      )
    )
      throw new Error("Invalid observed facts.");
    const g = lead.evidence_graph;
    if (
      !g ||
      !Array.isArray(g.nodes) ||
      !Array.isArray(g.edges) ||
      g.nodes.length > 2000 ||
      g.edges.length > 5000 ||
      !g.nodes.every(
        (n) =>
          typeof n.id === "string" &&
          typeof n.label === "string" &&
          ["transaction", "address", "ip"].includes(n.kind) &&
          (n.asn == null || Number.isInteger(n.asn)) &&
          (n.focus == null || typeof n.focus === "boolean"),
      ) ||
      !g.edges.every(
        (e) =>
          typeof e.source === "string" &&
          typeof e.target === "string" &&
          typeof e.relation === "string",
      )
    )
      throw new Error("Evidence graph is missing or exceeds preview limits.");
    const ids = new Set(g.nodes.map((n) => n.id));
    if (
      ids.size !== g.nodes.length ||
      !g.edges.every(
        (e) =>
          ids.has(e.source) &&
          ids.has(e.target) &&
          (e.amount_sats == null ||
            (Number.isSafeInteger(e.amount_sats) && e.amount_sats >= 0)),
      )
    )
      throw new Error("Graph references or amounts are invalid.");
  }
  return q;
}
const localNames: Record<string, string> = {
  n_in: "input count",
  n_out: "output count",
  fee_sats: "transaction fee",
  total_out_sats: "total output value",
  fee_rate_sat_vb: "fee rate",
  has_equal_outputs: "equal-value outputs",
  n_addresses: "address count",
  mean_sent_sats: "average input amount spent",
  mean_received_sats: "average amount received",
  peel_leak_frac: "forwarding-chain amount fraction",
  fan_in_ratio: "fan-in ratio",
  fee_anomaly: "fee deviation",
  n_script_types: "script-type diversity",
  n_heuristics: "ownership evidence methods",
  min_edge_confidence: "ownership evidence weight",
  n_coinbase_received: "coinbase receipts",
  observations: "announcement count",
  transactions: "transaction count",
  observers: "observer count",
  class_0: "unclassified peer share",
  class_1: "hosting-peer share",
  class_2: "residential-peer share",
  class_3: "Tor-exit share",
  class_4: "unknown-class share",
  class_5: "VPN-suspected share",
  n_tx_sent: "Outgoing transaction activity",
  n_tx_received: "Incoming transaction activity",
  n_counterparties: "Number of counterparties",
  max_fan_out: "Output fan-out",
  burstiness: "Transaction timing concentration",
  median_dwell_us: "Time between receiving and spending",
  total_sent_sats: "Total input amount spent",
  total_received_sats: "Total amount received",
  structuring_frac: "Small-payment pattern",
  peel_chain_depth: "Sequential forwarding depth",
  mean_fee_rate: "Transaction fee rate",
  frac_equal_outputs: "Equal-output pattern",
  balance_sats: "Received amount minus spent input amount",
};
function featureName(name: string): string {
  if (localNames[name]) return localNames[name];
  const match = /^(received|spent)_(mean|std|min|max)_(.+)$/.exec(name);
  if (!match) return name.replace(/_/g, " ");
  const relation = match[1] === "received" ? "incoming" : "outgoing";
  const stat: Record<string, string> = {
    mean: "Average",
    std: "Variation in",
    min: "Minimum",
    max: "Maximum",
  };
  const raw = match[3];
  const prefix = raw.startsWith("announcer_mean_")
    ? "announcing-peer "
    : raw.startsWith("funder_mean_")
      ? "funding-address "
      : "";
  const field = raw.replace(/^announcer_mean_|^funder_mean_/, "");
  return `${stat[match[2]]} ${prefix}${localNames[field] ?? field.replace(/_/g, " ")} in ${relation} context`;
}
function download(queue: Queue) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(queue, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "chakravyuh-investigation-preview.json";
  link.click();
  URL.revokeObjectURL(url);
}
function EvidenceGraph({ lead }: { lead: Lead }) {
  const graph = useMemo(() => {
    const tx = new Set(
      lead.evidence_graph.nodes
        .filter((n) => n.kind === "transaction")
        .slice(-3)
        .map((n) => n.id),
    );
    const connected = lead.evidence_graph.edges.filter(
      (e) => tx.has(e.source) || tx.has(e.target),
    );
    const ids = new Set(connected.flatMap((e) => [e.source, e.target]));
    const nodes = lead.evidence_graph.nodes.filter((n) => ids.has(n.id));
    const address = nodes
      .filter((n) => n.kind === "address")
      .sort((a, b) => Number(b.focus) - Number(a.focus))
      .slice(0, 24);
    const transactions = nodes.filter((n) => tx.has(n.id));
    const ips = nodes.filter((n) => n.kind === "ip").slice(0, 12);
    const height = Math.max(180, address.length * 25 + 50);
    const positions = new Map<string, { x: number; y: number }>();
    [address, transactions, ips].forEach((column, i) =>
      column.forEach((n, j) => {
        positions.set(n.id, {
          x: [155, 440, 710][i],
          y: 40 + ((j + 0.5) * (height - 60)) / Math.max(column.length, 1),
        });
      }),
    );
    return {
      nodes: [...address, ...transactions, ...ips],
      edges: connected.filter(
        (e) => positions.has(e.source) && positions.has(e.target),
      ),
      positions,
      height,
    };
  }, [lead]);
  return (
    <div className={styles.graphWrap}>
      <svg
        viewBox={`0 0 880 ${graph.height}`}
        role="img"
        aria-label="Observed address, transaction and announcing-IP evidence"
      >
        <defs>
          <marker
            id={`arrow-${lead.id.replace(/[^a-zA-Z0-9_-]/g, "")}`}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--riso-blue)" />
          </marker>
        </defs>
        <text x="85" y="20">
          Addresses
        </text>
        <text x="395" y="20">
          Transactions
        </text>
        <text x="660" y="20">
          Observed peers
        </text>
        {graph.edges.map((e, i) => {
          const a = graph.positions.get(e.source)!,
            b = graph.positions.get(e.target)!;
          return (
            <path
              key={i}
              d={`M ${a.x} ${a.y} C ${(a.x + b.x) / 2} ${a.y}, ${(a.x + b.x) / 2} ${b.y}, ${b.x} ${b.y}`}
              className={
                e.relation === "announced"
                  ? styles.networkEdge
                  : styles.moneyEdge
              }
              markerEnd={`url(#arrow-${lead.id.replace(/[^a-zA-Z0-9_-]/g, "")})`}
            >
              <title>
                {e.relation}
                {e.amount_sats == null
                  ? ""
                  : `: ${e.amount_sats.toLocaleString()} satoshis`}
              </title>
            </path>
          );
        })}
        {graph.nodes.map((n) => {
          const p = graph.positions.get(n.id)!;
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`}>
              <circle
                r={n.focus ? 6 : 4}
                className={n.focus ? styles.focusNode : styles.contextNode}
              />
              <text x="9" y="4">
                {n.label}
              </text>
              {n.kind === "ip" && n.asn != null && (
                <text x="9" y="19">
                  AS{n.asn}
                </text>
              )}
              <title>
                {n.kind}: {n.label}
                {n.focus ? " · selected lead" : ""}
              </title>
            </g>
          );
        })}
      </svg>
      <p className={styles.cardLine}>
        Preview of up to three transactions. Solid: input/output amounts.
        Dashed: captured announcements. Full bounded evidence is included in the
        exported packet.
      </p>
    </div>
  );
}
export function InvestigationPreview() {
  const [selected, setSelected] = useState(0);
  const [queue, setQueue] = useState(initialQueue);
  const [source, setSource] = useState(
    "Fixed synthetic research snapshot · window 8",
  );
  const [loadError, setLoadError] = useState("");
  async function loadFile(file?: File) {
    if (!file) return;
    try {
      if (file.size > 10 * 1024 * 1024)
        throw new Error("Queue exceeds the 10 MB preview limit.");
      const next = parseQueue(JSON.parse(await file.text()));
      setQueue(next);
      setSelected(0);
      setSource(`Local evidence queue · ${file.name}`);
      setLoadError("");
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Could not open this queue.",
      );
    }
  }
  const lead = queue.leads[selected];
  if (!lead) return null;
  return (
    <section className={styles.research}>
      <div className={styles.researchHead}>
        <h3 className={styles.sectionTitle}>Open an investigative lead</h3>
        <span className={styles.chip}>Offline investigation preview</span>
      </div>
      <p className={styles.body}>
        A graph-context model selects addresses for review, then reduces
        repeated transaction evidence. These packets were generated by the
        offline CPU engine. Open a generated evidence queue to inspect it
        locally. This panel is independent of the selected application run.
      </p>
      <p className={styles.cardLine}>{source}</p>
      <div
        className={styles.snapshotTabs}
        role="group"
        aria-label="Research queue snapshots"
      >
        {[
          [7, window7],
          [8, packet],
          [9, window9],
        ].map(([window, data]) => (
          <button
            type="button"
            key={window as number}
            aria-pressed={
              source === `Fixed synthetic research snapshot · window ${window}`
            }
            onClick={() => {
              setQueue(data as Queue);
              setSelected(0);
              setSource(`Fixed synthetic research snapshot · window ${window}`);
              setLoadError("");
            }}
          >
            Window {window as number}
            <small>
              {window === 7
                ? "Early campaign"
                : window === 8
                  ? "Campaign activity"
                  : "Later review queue"}
            </small>
          </button>
        ))}
      </div>
      <label className={styles.exportButton}>
        Open evidence queue · JSON{" "}
        <input
          type="file"
          accept=".json,application/json"
          onChange={(e) => {
            void loadFile(e.target.files?.[0]);
          }}
        />
      </label>
      {loadError && (
        <p role="alert" className={styles.cardLine}>
          {loadError}
        </p>
      )}
      <div className={styles.leadLayout}>
        <nav className={styles.leadList} aria-label="Ranked research leads">
          {queue.leads.map((item, i) => (
            <button
              key={item.id}
              type="button"
              className={`${styles.leadButton} ${i === selected ? styles.selectedLead : ""}`}
              onClick={() => setSelected(i)}
              aria-pressed={i === selected}
            >
              <span>
                #{item.rank} · {item.addresses[0]}
              </span>
              <span>
                {item.supporting_transaction_count} supporting TXs · score{" "}
                {item.risk_score.toFixed(3)}
              </span>
            </button>
          ))}
        </nav>
        <article className={styles.leadDetail}>
          <h4 className={styles.cardName}>
            Lead #{lead.rank} · {lead.addresses[0]}
          </h4>
          <p className={styles.body}>
            {lead.facts.n_tx_sent ?? 0} outgoing transactions ·{" "}
            {lead.facts.n_tx_received ?? 0} incoming transactions ·{" "}
            {lead.facts.n_counterparties ?? 0} counterparties
          </p>
          <p className={styles.cardLine}>
            Ranking score {lead.risk_score.toFixed(3)} · {lead.address_count}{" "}
            observed address{lead.address_count === 1 ? "" : "es"}. Graph
            evidence remains available without asserting a common owner.
          </p>
          <h5 className={styles.reasonTitle}>What increased the model score</h5>
          <ul className={styles.reasonList}>
            {lead.reasons.map((r) => (
              <li key={r.feature}>
                <span>{featureName(r.feature)}</span>
                <strong>+{r.shap_margin.toFixed(3)}</strong>
              </li>
            ))}
          </ul>
          <details>
            <summary className={styles.cardLine}>
              View countervailing model contributions
            </summary>
            <ul className={styles.reasonList}>
              {lead.mitigating_contributions.map((r) => (
                <li key={r.feature}>
                  <span>{featureName(r.feature)}</span>
                  <strong>{r.shap_margin.toFixed(3)}</strong>
                </li>
              ))}
            </ul>
          </details>
          <p className={styles.cardLine}>
            Signed TreeSHAP effects in model log-odds. They explain the score;
            the score prioritizes investigation.
          </p>
          <EvidenceGraph lead={lead} />
          <details>
            <summary className={styles.cardLine}>
              Inspect exact amounts and observation times
            </summary>
            <ul className={styles.reasonList}>
              {lead.evidence_graph.edges
                .filter((e) => e.amount_sats != null)
                .slice(0, 8)
                .map((e, i) => (
                  <li key={i}>
                    {e.relation === "funds"
                      ? "Transaction input"
                      : "Transaction output"}
                    : {e.amount_sats!.toLocaleString()} satoshis
                  </li>
                ))}
            </ul>
            <p className={styles.cardLine}>
              {lead.network_observation_count} displayed peer/TX observations.
              Full event timestamps and captured ports are in the exported
              packet.
            </p>
          </details>
          <h5 className={styles.reasonTitle}>Next investigative steps</h5>
          <ol className={styles.body}>
            {lead.next_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ol>
          <button
            type="button"
            className={styles.exportButton}
            onClick={() => download(queue)}
          >
            Export evidence queue · JSON
          </button>
        </article>
      </div>
    </section>
  );
}
