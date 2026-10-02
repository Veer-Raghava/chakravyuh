import { useMemo, useState } from "react";
import type { Lead } from "../../three/leadModel";
import type { RawNode, RawEdge } from "../../three/jaalLayout";
import { satsToBTC, usToIST } from "../../data/jaal";
import { useRun } from "../../data/RunContext";
import { useShell } from "../ShellContext";
import styles from "./FlowAtlas.module.css";

export function FlowAtlas({
  lead,
  ids,
  raw,
  onPick,
  onSpatial,
  onTrace,
}: {
  lead: Lead;
  ids: string[];
  raw: { nodes: RawNode[]; edges: RawEdge[] };
  onPick: (id: string) => void;
  onSpatial: () => void;
  onTrace: () => void;
}) {
  const { selectedTx, selectTx, run } = useRun();
  const { goTo } = useShell();
  const [address, setAddress] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const options = useMemo(
    () =>
      ids
        .filter((id) => id.toLowerCase().includes(query.toLowerCase()))
        .slice(0, 60),
    [ids, query],
  );
  const next = address
    ? [
        ...new Set(
          raw.edges
            .filter(
              (e) =>
                e.kind === "SPENDS" && e.src === address && e.dst !== lead.txId &&
                e.ts_us != null && lead.firstUs != null && e.ts_us > lead.firstUs,
            )
            .map((e) => e.dst),
        ),
      ]
    : [];
  const incoming = lead.senders.slice(0, 6),
    outgoing = lead.receivers.slice(0, 6),
    peers = lead.announcers.slice(0, 8);
  const missing =
    selectedTx &&
    !raw.nodes.some(
      (n) =>
        n.node_id ===
        (selectedTx.startsWith("tx:") ? selectedTx : `tx:${selectedTx}`),
    );
  return (
    <section className={styles.atlas}>
      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>JAAL · जाल / FLOW ATLAS</span>
          <h1>
            See the flow.
            <br />
            <em>Follow the evidence.</em>
          </h1>
          <p>
            Value moves through addresses. Network peers report what they saw.
            Read both without confusing them.
          </p>
        </div>
        <div className={styles.modes}>
          <button type="button" aria-pressed="true">
            Flow atlas
          </button>
          <button type="button" onClick={onSpatial}>
            Spatial graph ↗
          </button>
          <button type="button" onClick={onTrace}>
            3D trace ↗
          </button>
        </div>
      </header>
      {missing && (
        <div role="status" className={styles.notice}>
          The selected transaction is outside this bounded graph export. The
          atlas below shows an available transaction.{" "}
          <button type="button" onClick={() => selectTx(null)}>
            Clear selection
          </button>
        </div>
      )}
      <div className={styles.workspace}>
        <aside className={styles.index}>
          <span className={styles.eyebrow}>TRANSACTION INDEX</span>
          <label>
            Find a TXID
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search transaction hash"
            />
          </label>
          <p>{ids.length} traceable transactions · bounded export</p>
          <div className={styles.transactionList}>
            {options.map((id, i) => (
              <button
                key={id}
                type="button"
                aria-pressed={lead.txId === id}
                onClick={() => {
                  setAddress(null);
                  onPick(id);
                }}
              >
                <span>{String(ids.indexOf(id) + 1).padStart(2, "0")}</span>
                <strong>
                  {raw.nodes
                    .find((n) => n.node_id === id)
                    ?.label.replace(/^tx:/, "") ?? `Transaction ${i + 1}`}
                </strong>
                <small>Open input → output flow</small>
              </button>
            ))}
          </div>
          {options.length === 0 && (
            <p>No matching transaction in this export.</p>
          )}
        </aside>
        <div className={styles.main}>
          <div className={styles.flowHead}>
            <div>
              <span className={styles.eyebrow}>OBSERVED TRANSACTION</span>
              <h2>{lead.txLabel.replace(/^tx:/, "")}</h2>
            </div>
            <span className={styles.time}>
              {lead.firstUs == null
                ? "Time not exported"
                : usToIST(lead.firstUs)}
            </span>
          </div>
          <div className={styles.metrics}>
            <div>
              <strong>{satsToBTC(lead.totalInSats)}</strong>
              <span>input value</span>
            </div>
            <div>
              <strong>
                {lead.senders.length} → {lead.receivers.length}
              </strong>
              <span>input / output addresses</span>
            </div>
            <div>
              <strong>{lead.announcers.length}</strong>
              <span>captured announcing peers</span>
            </div>
          </div>
          <div className={styles.diagram}>
            <svg
              viewBox="0 0 960 600"
              role="img"
              aria-label="Input addresses fund a transaction, output addresses receive funds, and peers announce the transaction"
            >
              <defs>
                <marker
                  id="flow-arrow"
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M0 0L10 5L0 10z" fill="var(--riso-blue)" />
                </marker>
              </defs>
              <text x="30" y="34" className={styles.column}>
                NETWORK / OBSERVED ANNOUNCEMENTS
              </text>
              {peers.map((p, i) => {
                const x = 60 + i * 112;
                return (
                  <g key={p.id}>
                    <path
                      d={`M480 340 C480 220 ${x} 240 ${x} 112`}
                      className={styles.announcement}
                    />
                    <circle cx={x} cy="93" r="7" fill="var(--fluoro-pink)" />
                    <text
                      x={x}
                      y="48"
                      textAnchor="middle"
                      className={styles.micro}
                    >
                      P{i + 1}
                    </text>
                    <text x={x} y="64" textAnchor="middle">
                      {p.label.replace(/^peer:/, "")}
                    </text>
                    <text
                      x={x}
                      y="125"
                      textAnchor="middle"
                      className={styles.micro}
                    >
                      {p.asn?.replace(/^asn:/, "AS") ?? "ASN unavailable"}
                    </text>
                  </g>
                );
              })}
              <line
                x1="25"
                x2="935"
                y1="182"
                y2="182"
                className={styles.seam}
              />
              <text x="30" y="215" className={styles.column}>
                BLOCKCHAIN / VALUE TRANSFER
              </text>
              <text x="35" y="260" className={styles.column}>
                INPUT ADDRESSES
              </text>
              <text x="700" y="260" className={styles.column}>
                OUTPUT ADDRESSES
              </text>
              {incoming.map((n, i) => {
                const y = 305 + i * 43;
                return (
                  <g key={n.id}>
                    <path
                      d={`M235 ${y} C335 ${y} 355 340 420 340`}
                      className={styles.money}
                      markerEnd="url(#flow-arrow)"
                    />
                    <circle cx="35" cy={y} r="5" fill="var(--riso-blue)" />
                    <text x="50" y={y - 3}>
                      {n.label.replace(/^addr:/, "")}
                    </text>
                    <text x="50" y={y + 13} className={styles.micro}>
                      {satsToBTC(n.sats)}
                    </text>
                  </g>
                );
              })}
              {outgoing.map((n, i) => {
                const y = 305 + i * 43;
                return (
                  <g key={n.id}>
                    <path
                      d={`M540 340 C600 340 625 ${y} 695 ${y}`}
                      className={styles.money}
                      markerEnd="url(#flow-arrow)"
                    />
                    <g
                      role="button"
                      tabIndex={0}
                      aria-label={`Follow output ${n.label}`}
                      onClick={() => setAddress(n.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setAddress(n.id);
                        }
                      }}
                      className={styles.output}
                    >
                      <rect
                        x="700"
                        y={y - 20}
                        width="224"
                        height="39"
                        rx="5"
                        className={
                          address === n.id
                            ? styles.selectedOutput
                            : styles.outputRect
                        }
                      />
                      <text x="712" y={y - 3}>
                        {n.label.replace(/^addr:/, "")}
                      </text>
                      <text x="712" y={y + 13} className={styles.micro}>
                        {satsToBTC(n.sats)}
                        {n.role === "change" ? " · possible change" : ""}
                      </text>
                    </g>
                  </g>
                );
              })}
              <g
                role="button"
                tabIndex={0}
                aria-label="Open transaction in 3D trace"
                onClick={onTrace}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onTrace();
                  }
                }}
                className={styles.output}
              >
                <rect
                  x="420"
                  y="307"
                  width="120"
                  height="66"
                  rx="12"
                  fill="var(--coral)"
                />
                <text x="480" y="333" textAnchor="middle" className={styles.tx}>
                  TRANSACTION
                </text>
                <text x="480" y="352" textAnchor="middle" className={styles.tx}>
                  Open trace ↗
                </text>
              </g>
            </svg>
          </div>
          <div className={styles.legend}>
            <span>
              <i /> exact value direction
            </span>
            <span>
              <i className={styles.dashed} /> captured announcement
            </span>
            <span>
              Showing {incoming.length}/{lead.senders.length} inputs,{" "}
              {outgoing.length}/{lead.receivers.length} outputs and{" "}
              {peers.length}/{lead.announcers.length} peers.
            </span>
          </div>
          <div className={styles.finding}>
            <span className={styles.eyebrow}>WHAT TO INSPECT</span>
            <p>{lead.why}</p>
            {address && (
              <div>
                <strong>Later observed spends from this address</strong><p>Address reuse connects these observations; it does not establish which output was spent.</p>
                {next.length ? (
                  next.slice(0, 5).map((id) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => {
                        setAddress(null);
                        onPick(id);
                      }}
                    >
                      {raw.nodes
                        .find((n) => n.node_id === id)
                        ?.label.replace(/^tx:/, "") ?? "Next transaction"}{" "}
                      →
                    </button>
                  ))
                ) : (
                  <p>No subsequent spend appears in this bounded export.</p>
                )}
              </div>
            )}
            <button
              type="button"
              onClick={() => {
                selectTx(lead.txId);
                goTo("origin");
              }}
            >
              Inspect this transaction’s origin →
            </button>
          </div>
          <details className={styles.exact}>
            <summary>All input and output amounts · exact satoshis</summary>
            <table>
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Address</th>
                  <th>Amount (sats)</th>
                </tr>
              </thead>
              <tbody>
                {[...lead.senders, ...lead.receivers].map((n) => (
                  <tr key={n.role + n.id}>
                    <td>{n.role === "change" ? "possible change" : n.role}</td>
                    <td>{n.label.replace(/^addr:/, "")}</td>
                    <td>{n.sats.toLocaleString("en-US")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
          <p className={styles.footer}>
            {run.id} · Displayed relationships come from the selected run.
            Ownership ties remain hypotheses.
          </p>
        </div>
      </div>
    </section>
  );
}
