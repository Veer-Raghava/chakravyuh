import { useEffect, useState } from "react";
import { adapter, type Manifest } from "../adapter";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { HashBlock } from "../components/HashBlock";
import { MetricReadout } from "../components/MetricReadout";
import { balances, num } from "../format";
import styles from "./Intake.module.css";

export function Intake() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [last, setLast] = useState<LastCall | null>(null);

  useEffect(() => {
    const t0 = performance.now();
    adapter.getManifest().then((m) => {
      setManifest(m);
      setLast({ label: "getManifest", ms: Math.round(performance.now() - t0) });
    });
  }, []);

  if (!manifest) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>loading intake manifest…</div>
        <CommandLine last={last} />
      </div>
    );
  }

  // The intake identity: every row read is either sealed or rejected — nothing vanishes.
  const counts = { in: manifest.rows_read, out: manifest.rows_sealed, dropped: manifest.rows_rejected };
  const ok = balances(counts);
  const rejects = Object.entries(manifest.reject_reasons).sort((a, b) => b[1] - a[1]);
  const maxReject = Math.max(1, ...rejects.map(([, n]) => n));

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <span className={styles.crumb}>DRISHTI · /_intake · <span className="mono">seal + custody</span></span>
        <span className={styles.verdict}>it never breaks on their file</span>
      </div>

      <div className={styles.body}>
        <section className={styles.left}>
          <div className={styles.block}>
            <span className={styles.blockTitle}>sealed input · sha-256 in full</span>
            <HashBlock value={manifest.input_sha256} label="input sha-256" />
            <span className={styles.foot}>
              taken on the raw bytes before any coercion, so the seal is over exactly what they handed us.
            </span>
          </div>

          <div className={styles.counts}>
            <MetricReadout label="rows read" value={num(manifest.rows_read)} gloss="lines in the capture, as delivered" />
            <MetricReadout label="rows sealed" value={num(manifest.rows_sealed)} gloss="passed the seal and entered the pipeline" tone="ok" />
            <MetricReadout label="rows rejected" value={num(manifest.rows_rejected)} gloss="refused at intake, each with a reason" tone="alert" />
            <MetricReadout label="transactions" value={num(manifest.n_transactions)} gloss="after collapsing announcements to events" />
          </div>

          <div className={styles.balance} data-fail={!ok || undefined}>
            <span className="mono">read {num(counts.in)}</span>
            <span className={styles.eq}>{ok ? "==" : "≠"}</span>
            <span className="mono">sealed {num(counts.out)} + {num(counts.dropped)} rejected</span>
            <span className={styles.ok}>{ok ? "✓" : "✕"}</span>
            <span className={styles.cap}>{ok ? "nothing lost silently" : "does not balance"}</span>
          </div>
        </section>

        <aside className={styles.right}>
          <div className={styles.block}>
            <span className={styles.blockTitle}>why rows were rejected</span>
            <div className={styles.reasons}>
              {rejects.map(([reason, n]) => (
                <div key={reason} className={styles.reason}>
                  <div className={styles.reasonHead}>
                    <span className={styles.reasonName}>{reason.replace(/_/g, " ")}</span>
                    <span className={`${styles.reasonN} mono`}>{num(n)}</span>
                  </div>
                  <div className={styles.reasonBar}>
                    <div className={styles.reasonFill} style={{ width: `${(n / maxReject) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.block}>
            <span className={styles.blockTitle}>optional columns not in their file</span>
            <div className={styles.chips}>
              {manifest.columns_missing_optional.map((c) => (
                <span key={c} className={`${styles.chip} mono`}>{c}</span>
              ))}
            </div>
            <span className={styles.foot}>
              absent, not invented: the pipeline runs on what it was given and flags what it never saw.
            </span>
          </div>

          <div className={styles.meta}>
            <span className="mono">code {manifest.code_version}</span>
            <span className="mono">tool {manifest.tool_version}</span>
          </div>
        </aside>
      </div>

      <CommandLine last={last} />
    </div>
  );
}
