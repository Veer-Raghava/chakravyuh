import { useEffect, useRef, useState } from "react";
import { useRun, type RunId } from "../data/RunContext";
import styles from "./RunSwitcher.module.css";

/**
 * The run switcher (top strip). A small dropdown proving the console is not
 * hardcoded to one run: pick a coverage regime, every screen re-reads from
 * RunContext. Active run = Riso Blue; the others quiet ink-soft. Closes on
 * select, outside click, or Escape. The subtle badge beside it reads the ACTIVE
 * fixtures' real world.json — never invented numbers.
 */
export function RunSwitcher() {
  const { runId, run, runs, setRun, fixtures } = useRun();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const pick = (id: RunId) => {
    setRun(id);
    setOpen(false);
  };

  const w = fixtures.world;
  const coveragePct = Math.round((w.observer_fraction ?? 0) * 100);

  return (
    <div className={styles.wrap} ref={rootRef}>
      <button
        type="button"
        className={styles.trigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={styles.label}>{run.label}</span>
        <span className={styles.cov}>{run.coverageLabel}</span>
        <span className={styles.caret} aria-hidden="true" />
      </button>

      {open && (
        <ul className={styles.menu} role="listbox" aria-label="Run — observer coverage regime">
          {runs.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                role="option"
                aria-selected={r.id === runId}
                className={`${styles.option} ${r.id === runId ? styles.active : ""}`}
                onClick={() => pick(r.id)}
              >
                <span className={styles.optDot} aria-hidden="true" />
                <span className={styles.optLabel}>{r.label}</span>
                <span className={styles.optCov}>{r.coverageLabel}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* honest badge — reads the active fixtures' real world.json */}
      <span className={styles.badge}>
        <span className={styles.badgeLabel}>run</span> {w.run_id} · {coveragePct}% coverage ·{" "}
        {w.observer_regime}
      </span>
    </div>
  );
}
