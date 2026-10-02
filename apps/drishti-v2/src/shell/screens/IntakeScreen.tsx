import { useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRun } from "../../data/RunContext";
import { useShell } from "../ShellContext";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import styles from "./IntakeScreen.module.css";

/**
 * Intake · KAVACH (§11.1) — "load & seal a dataset". A calm drop zone → a live
 * sealing readout (rows in / sealed / set aside, with reasons), the file's full
 * SHA-256 printed IN FULL (the one identifier the law never lets us hide), a
 * balance tick (rows_read == sealed + set_aside), and one primary action that
 * presses a wax seal and moves on. Everything else is a readout, not a control.
 * Offline: the "drop" is theatrical — it reveals what the backend already sealed.
 */
const nf = new Intl.NumberFormat("en-US");

type Phase = "idle" | "sealing" | "sealed";

/** A tabular figure that counts up to its target on seal (static under reduced motion). */
function Tally({ to, phase, reduced, delay = 0 }: { to: number; phase: Phase; reduced: boolean; delay?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  useGSAP(
    () => {
      if (phase !== "sealing" || reduced || !ref.current) return;
      const o = { v: 0 };
      gsap.to(o, {
        v: to,
        duration: 1.1,
        delay,
        ease: "power2.out",
        onUpdate: () => {
          if (ref.current) ref.current.textContent = nf.format(Math.round(o.v));
        },
      });
    },
    { dependencies: [phase, to, reduced, delay] },
  );
  // idle shows nothing yet; sealed (or reduced) shows the final figure immediately.
  return <span ref={ref}>{phase === "idle" ? "—" : phase === "sealed" || reduced ? nf.format(to) : "0"}</span>;
}

export function IntakeScreen() {
  const { goTo } = useShell();
  const reduced = usePrefersReducedMotion();
  const { fixtures } = useRun();
  const m = fixtures.manifest;
  const [phase, setPhase] = useState<Phase>("idle");

  const setAside = m.rows_rejected;
  const balanced = m.rows_read === m.rows_sealed + setAside && m.arithmetic_ok;
  const reasons = Object.entries(m.reject_reasons as Record<string, number>);
  const files = m.files as { name: string; sha256: string; bytes?: number }[];
  const file = files.find((f) => f.bytes != null) ?? files[0];

  const seal = () => {
    if (phase !== "idle") return;
    if (reduced) {
      setPhase("sealed");
      return;
    }
    setPhase("sealing");
    window.setTimeout(() => setPhase("sealed"), 1250);
  };

  return (
    <section className={styles.screen}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Intake</h1>
          <span className={styles.tag}>KAVACH · सील</span>
        </div>
        <p className={styles.gloss}>
          Inspect the selected run’s capture and its existing seal. We hash the raw bytes <em>before</em> we read them,
          so a court can prove nothing changed.
        </p>
      </header>

      {phase === "idle" ? (
        <button className={styles.dropzone} type="button" onClick={seal} aria-label="Inspect the capture seal">
          <span className={styles.dropRing} aria-hidden />
          <span className={styles.dropTitle}>Inspect the sealed capture</span>
          <span className={styles.dropMeta}>
            {file?.name} · {file?.bytes != null ? `${(file.bytes / 1e6).toFixed(1)} MB` : "—"}
          </span>
        </button>
      ) : (
        <div className={styles.readout}>
          <div className={styles.tallies}>
            <div className={styles.tally}>
              <span className={styles.tallyNum}>
                <Tally to={m.rows_read} phase={phase} reduced={reduced} />
              </span>
              <span className={styles.tallyLabel}>rows in</span>
            </div>
            <span className={styles.op}>=</span>
            <div className={styles.tally}>
              <span className={`${styles.tallyNum} ${styles.sealed}`}>
                <Tally to={m.rows_sealed} phase={phase} reduced={reduced} delay={0.15} />
              </span>
              <span className={styles.tallyLabel}>sealed</span>
            </div>
            <span className={styles.op}>+</span>
            <div className={styles.tally}>
              <span className={`${styles.tallyNum} ${setAside > 0 ? styles.aside : styles.zero}`}>
                <Tally to={setAside} phase={phase} reduced={reduced} delay={0.3} />
              </span>
              <span className={styles.tallyLabel}>set aside</span>
            </div>
          </div>

          {balanced && (
            <p className={styles.balance}>
              <span className={styles.tick} aria-hidden>✓</span>
              balanced: every row is accounted for, nothing dropped silently.
            </p>
          )}

          {setAside > 0 ? (
            <ul className={styles.reasons}>
              {reasons.map(([reason, n]) => (
                <li key={reason} className={styles.reason}>
                  <span className={styles.reasonN}>{nf.format(n)}</span>
                  <span className={styles.reasonWhy}>{reason}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.noAside}>No rows set aside in this capture. When some are, each reason is listed here, never hidden.</p>
          )}

          <div className={styles.hashBlock}>
            <span className={styles.hashLabel}>full-file SHA-256 · printed in full (BSA 2023 §63(4))</span>
            <code className={styles.hash}>{m.input_sha256}</code>
          </div>

          <dl className={styles.meta}>
            <div className={styles.metaRow}>
              <dt>amount unit</dt>
              <dd>{m.amount_unit_detected} (detected)</dd>
            </div>
            <div className={styles.metaRow}>
              <dt>time format</dt>
              <dd>{m.timestamp_format_detected}</dd>
            </div>
            <div className={styles.metaRow}>
              <dt>columns mapped</dt>
              <dd>{m.columns.filter((c) => c.status === "MAPPED").length} / {m.columns.length}</dd>
            </div>
            <div className={styles.metaRow}>
              <dt>provenance</dt>
              <dd>offline · code v{m.code_version} · seed {m.seed} · run {m.run_id}</dd>
            </div>
          </dl>

          <button
            className={styles.primary}
            type="button"
            disabled={phase !== "sealed"}
            onClick={() => goTo("untangle")}
          >
            <span className={styles.wax} aria-hidden />
            Seal &amp; continue
          </button>
        </div>
      )}
    </section>
  );
}
