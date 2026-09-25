import { useEffect, useState } from "react";
import { adapter, type CollapseStats } from "../adapter";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { Histogram } from "../components/Histogram";
import { dec, num } from "../format";
import styles from "./Collapse.module.css";

const reduceMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function Collapse() {
  const [stats, setStats] = useState<CollapseStats | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [count, setCount] = useState(0);
  const [last, setLast] = useState<LastCall | null>(null);

  useEffect(() => {
    const t0 = performance.now();
    adapter.getCollapseStats().then((s) => {
      setStats(s);
      setCount(s.n_announcements);
      setLast({ label: "getCollapseStats", ms: Math.round(performance.now() - t0) });
    });
  }, []);

  // Space collapses announcements down to transactions, once, easing the focal count. The
  // announcements that carried no new transaction are the echo, revealed by the same press.
  useEffect(() => {
    if (!stats) return;
    if (!collapsed) return setCount(stats.n_announcements);
    if (reduceMotion()) return setCount(stats.n_transactions);
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / 420);
      const eased = 1 - Math.pow(1 - p, 3);
      setCount(Math.round(stats.n_announcements + (stats.n_transactions - stats.n_announcements) * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [collapsed, stats]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
      if (e.key === " ") {
        e.preventDefault();
        setCollapsed((c) => !c);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!stats) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>loading collapse stats…</div>
        <CommandLine last={last} />
      </div>
    );
  }

  const txPct = (stats.n_transactions / stats.n_announcements) * 100;
  const echoPct = (stats.n_echo / stats.n_announcements) * 100;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <span className={styles.crumb}>DRISHTI · /_collapse · <span className="mono">announcements → transactions</span></span>
        <span className={styles.verdict}>one million rows is not one million events</span>
      </div>

      <div className={styles.body}>
        <section className={styles.focalWrap}>
          <div className={styles.focal}>
            <span className={`${styles.count} mono`}>{num(count)}</span>
            <span className={styles.unit}>{collapsed ? "transactions" : "announcements"}</span>
          </div>

          <div className={styles.bar} role="img" aria-label={`${num(stats.n_transactions)} transactions, ${num(stats.n_echo)} echo announcements`}>
            <div className={styles.barTx} style={{ width: collapsed ? `${txPct}%` : "100%" }} />
            <div className={styles.barEcho} data-shown={collapsed || undefined} style={{ width: `${echoPct}%` }} />
          </div>

          <div className={styles.meta}>
            <span className="mono">{num(stats.n_announcements)} ann</span>
            <span className="mono">{num(stats.n_transactions)} tx</span>
            <span className="mono">{num(stats.n_echo)} echo</span>
            <span className={styles.mean}>mean {dec(stats.mean_announcements)} ann / tx</span>
          </div>

          <button className={styles.toggle} onClick={() => setCollapsed((c) => !c)}>
            Space · {collapsed ? "echo shown — press to expand" : "collapse the echo"}
          </button>

          <p className={styles.say}>
            The same transaction is announced by many peers; collapsing the echo turns the raw
            capture into the events the pipeline actually reasons over.
          </p>
        </section>

        <aside className={styles.histWrap}>
          <span className={styles.blockTitle}>announcements per transaction</span>
          <Histogram
            bars={stats.announcements_per_tx.map((b) => ({ label: b.bucket, value: b.count }))}
            mean={stats.mean_announcements}
            meanLabel={`mean ${dec(stats.mean_announcements)}`}
          />
        </aside>
      </div>

      <CommandLine last={last} />
    </div>
  );
}
