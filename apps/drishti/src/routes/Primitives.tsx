import { useEffect, useState } from "react";
import { adapter, type AlertDetail, type AlertRow, type Manifest, type Packet, type TransactionRow } from "../adapter";
import { Panel } from "../components/Panel";
import { DataTable, type Column } from "../components/DataTable";
import { MetricReadout } from "../components/MetricReadout";
import { RangeBar } from "../components/RangeBar";
import { HashBlock } from "../components/HashBlock";
import { Lamp } from "../components/Lamp";
import { drishtiTheme } from "../styles/echarts-theme";
import { dec, id, ms, num } from "../format";
import styles from "./Primitives.module.css";

const txColumns: Column<TransactionRow>[] = [
  { key: "txid", header: "txid", width: "1.4fr", render: (r) => id(r.txid, "txid") },
  { key: "ann", header: "ann", width: "72px", numeric: true, render: (r) => num(r.n_announcements), sortValue: (r) => r.n_announcements },
  { key: "peers", header: "peers", width: "72px", numeric: true, render: (r) => num(r.n_distinct_peers), sortValue: (r) => r.n_distinct_peers },
  { key: "spread", header: "spread", width: "1fr", numeric: true, render: (r) => ms(r.announce_spread_us), sortValue: (r) => r.announce_spread_us },
  { key: "sats", header: "out sats", width: "1.2fr", numeric: true, render: (r) => num(r.total_out_sats), sortValue: (r) => r.total_out_sats },
  { key: "flag", header: "flag", width: "80px", render: (r) => (r.abstained ? "ABSTAIN" : r.is_coinbase ? "COINBASE" : "") },
];

export function Primitives() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [txs, setTxs] = useState<TransactionRow[]>([]);
  const [alert, setAlert] = useState<AlertDetail | null>(null);
  const [packet, setPacket] = useState<Packet | null>(null);
  const [selected, setSelected] = useState<string>();

  useEffect(() => {
    adapter.getManifest().then(setManifest);
    adapter.listTransactions().then(setTxs);
    adapter.listAlerts().then((rows: AlertRow[]) => {
      const first = rows[0];
      if (!first) return;
      adapter.getAlert(first.case_id).then(setAlert);
      adapter.getPacket(first.case_id).then(setPacket);
    });
  }, []);

  const theme = drishtiTheme();
  const palette = (theme.color as string[]) ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <span className={styles.crumb}>DRISHTI · /_primitives</span>
        <span className={`${styles.crumb} mono`}>scratch route · fixture data · not a demo screen</span>
      </div>

      <div className={styles.grid}>
        <Panel title="DataTable · virtualised, sortable, mono numerics">
          <DataTable rows={txs} columns={txColumns} getKey={(r) => r.txid} height={300} selectedKey={selected} onSelect={(r) => setSelected(r.txid)} />
        </Panel>

        <Panel title="MetricReadout">
          <div className={styles.readouts}>
            <MetricReadout label="rows sealed" value={manifest ? num(manifest.rows_sealed) : "—"} gloss="passed the seal and entered the pipeline" />
            <MetricReadout label="rows rejected" value={manifest ? num(manifest.rows_rejected) : "—"} gloss="refused at intake, each with a reason" />
            <MetricReadout label="transactions" value={manifest ? num(manifest.n_transactions) : "—"} gloss="after collapsing announcements to events" />
            <MetricReadout label="observer coverage" value="4 of 16" gloss="twelve listeners never saw it — itself information" />
          </div>
        </Panel>

        <Panel title="RangeBar · conformal interval">
          <div className={styles.stack}>
            {alert ? (
              <>
                <div className={styles.intervalRow}>
                  <span className={styles.intervalLabel}>{alert.confidence.label}</span>
                  <RangeBar low={alert.confidence.low} high={alert.confidence.high} point={alert.confidence.score} />
                </div>
                <span className={styles.foot}>
                  coverage {alert.confidence.empirical_coverage === null ? "—" : dec(alert.confidence.empirical_coverage)} against a {dec(alert.confidence.coverage_target)} target
                </span>
              </>
            ) : (
              <span className={styles.foot}>loading…</span>
            )}
            <div className={styles.intervalRow}>
              <span className={styles.intervalLabel}>wide (low confidence)</span>
              <RangeBar low={0.18} high={0.74} point={0.41} />
            </div>
          </div>
        </Panel>

        <Panel title="HashBlock · full merkle head, truncated ids">
          <div className={styles.stack}>
            {manifest && <HashBlock label="merkle head" value={manifest.merkle_head} />}
            {manifest && <HashBlock label="input sha-256" value={manifest.input_sha256} />}
            {manifest && <HashBlock label="run" value={manifest.input_sha256} truncate />}
          </div>
        </Panel>

        <Panel title="Lamp · verification state">
          <div className={styles.lamps}>
            {packet ? (
              <>
                <Lamp label="hash verified" on={packet.verification.hash_verified} detail={packet.replay.command} />
                <Lamp label="signature valid" on={packet.verification.signature_valid} detail="ed25519 · vk in packet header" />
                <Lamp label="replay matched" on={packet.verification.replay_matched} detail="rendered packet sha256 compared to expected" />
              </>
            ) : (
              <>
                <Lamp label="hash verified" on={false} detail="not yet run" />
                <Lamp label="signature valid" on={false} detail="not yet run" />
                <Lamp label="replay matched" on={false} detail="not yet run" />
              </>
            )}
          </div>
        </Panel>

        <Panel title="echarts-theme · token-driven palette" right={<span className={`${styles.crumb} mono`}>drishti</span>}>
          <div className={styles.stack}>
            <div className={styles.swatches}>
              {palette.map((c, i) => (
                <div key={i} className={styles.swatch}>
                  <span className={styles.chip} style={{ background: c }} aria-hidden />
                  <span className={`${styles.foot} mono`}>{c}</span>
                </div>
              ))}
            </div>
            <span className={styles.foot}>
              theme registers with no title, no legend, no gridlines, mono micro ticks, a hairline
              tooltip and animation off. Live chart lands with the echarts dependency.
            </span>
          </div>
        </Panel>
      </div>
    </div>
  );
}
