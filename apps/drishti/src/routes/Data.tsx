import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { adapter, type SealedRow } from "../adapter";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { DataTable, type Column } from "../components/DataTable";
import { ms, num } from "../format";
import styles from "./Data.module.css";

const columns: Column<SealedRow>[] = [
  { key: "row_id", header: "row", numeric: true, width: "72px", render: (r) => num(r.row_id), sortValue: (r) => r.row_id },
  { key: "txid", header: "txid", width: "2fr", render: (r) => <span className="mono">{r.txid}</span>, sortValue: (r) => r.txid },
  {
    key: "peer", header: "peer", width: "1.3fr",
    render: (r) => <span className="mono">{r.peer_ip}:{r.peer_port}</span>,
    sortValue: (r) => r.peer_ip,
  },
  { key: "seen", header: "first seen", numeric: true, width: "96px", render: (r) => ms(r.first_seen_us), sortValue: (r) => r.first_seen_us },
  { key: "out", header: "out sats", numeric: true, width: "120px", render: (r) => num(r.out_sats), sortValue: (r) => r.out_sats },
  {
    key: "status", header: "custody", width: "1.4fr", sortValue: (r) => (r.sealed ? "0" : `1${r.reject_reason ?? ""}`),
    render: (r) =>
      r.sealed ? (
        <span className={styles.sealed}>sealed</span>
      ) : (
        <span className={styles.rejected}>
          rejected<span className={styles.reason}>{r.reject_reason ?? "unspecified"}</span>
        </span>
      ),
  },
];

export function Data() {
  const [rows, setRows] = useState<SealedRow[]>([]);
  const [last, setLast] = useState<LastCall | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [tableH, setTableH] = useState(520);

  useEffect(() => {
    const t0 = performance.now();
    adapter.getRows().then((r) => {
      setRows(r);
      setLast({ label: "getRows", ms: Math.round(performance.now() - t0) });
    });
  }, []);

  useLayoutEffect(() => {
    const el = bodyRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => setTableH(el.clientHeight));
    ro.observe(el);
    setTableH(el.clientHeight);
    return () => ro.disconnect();
  }, []);

  const sealed = rows.filter((r) => r.sealed).length;
  const rejected = rows.length - sealed;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <span className={styles.crumb}>DRISHTI · /_data · <span className="mono">sealed rows</span></span>
        <span className={styles.counts}>
          <span className="mono">{num(rows.length)} read</span>
          <span className={`${styles.sealed} mono`}>{num(sealed)} sealed</span>
          <span className={`${styles.rejected} mono`}>{num(rejected)} rejected</span>
        </span>
      </div>

      <div className={styles.body}>
        <div className={styles.tableFill} ref={bodyRef}>
          <DataTable rows={rows} columns={columns} getKey={(r) => String(r.row_id)} rowHeight={28} height={tableH} />
        </div>
        <p className={styles.note}>
          the rows exactly as the pipeline read them, in full · click a header to sort · scroll to page
        </p>
      </div>

      <CommandLine last={last} />
    </div>
  );
}
