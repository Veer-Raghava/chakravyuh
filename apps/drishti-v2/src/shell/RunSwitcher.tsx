import { useEffect, useRef, useState } from "react";
import { useRun } from "../data/RunContext";
import styles from "./RunSwitcher.module.css";
export function RunSwitcher() {
  const { runId, run, runs, setRun, loading, loadError } = useRun();
  const [open, setOpen] = useState(false);
  const [all, setAll] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", outside);
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("mousedown", outside);
      window.removeEventListener("keydown", key);
    };
  }, [open]);
  const visible = runs.filter(
    (r) => !/^(s\d|run-)/.test(r.id) && (all || r.curated),
  );
  return (
    <div className={styles.wrap} ref={root}>
      <button
        type="button"
        className={styles.trigger}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span className={styles.label}>
          {loading ? "Loading capture…" : run.label}
        </span>
        <span className={styles.cov}>{run.coverageLabel}</span>
        <span className={styles.caret} />
      </button>
      {open && (
        <div
          className={styles.menu}
          role="dialog"
          aria-label="Choose an investigation run"
        >
          <div className={styles.menuHead}>
            <strong>Choose your investigation</strong>
            <span>Curated captures · real stage artifacts</span>
          </div>
          <div className={styles.tabs}>
            <button
              type="button"
              aria-pressed={!all}
              onClick={() => setAll(false)}
            >
              Demo selection
            </button>
            <button
              type="button"
              aria-pressed={all}
              onClick={() => setAll(true)}
            >
              All coverage runs
            </button>
          </div>
          {visible.map((r) => (
            <button
              key={r.id}
              type="button"
              aria-pressed={runId === r.id}
              className={`${styles.option} ${runId === r.id ? styles.active : ""}`}
              onClick={() => {
                setRun(r.id);
                setOpen(false);
              }}
            >
              <span className={styles.optDot} />
              <span className={styles.optLabel}>
                {r.label}
                <small>{r.description}</small>
              </span>
              <span className={styles.optCov}>{r.coverageLabel}</span>
            </button>
          ))}
          <p className={styles.menuNote}>
            Changing the run updates the map, observations, queue and available
            evidence. Development runs stay outside the demo catalog.
          </p>
        </div>
      )}
      {loadError && <span role="alert">{loadError}</span>}
      <span className={styles.badge}>
        {run.id} · <strong>{run.alert_count}</strong> leads
      </span>
    </div>
  );
}
