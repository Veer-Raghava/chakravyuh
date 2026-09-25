import styles from "./MetricReadout.module.css";

interface Props {
  /** Uppercase micro label. */
  label: string;
  /** Pre-formatted mono value. Numbers must arrive already run through format.num/dec. */
  value: string;
  /** One-line plain-english gloss under the value. Optional. */
  gloss?: string;
  /** Tint the value with the signal accent (origin/selected) or cool (counter/abstain). */
  tone?: "signal" | "cool" | "ok" | "alert";
}

/** A micro label, a mono value, and an optional one-line gloss. The atom the readout rows
 *  on ORIGIN and the confidence blocks are built from. */
export function MetricReadout({ label, value, gloss, tone }: Props) {
  return (
    <div className={styles.readout}>
      <span className={styles.label}>{label}</span>
      <span className={`${styles.value} mono`} data-tone={tone}>
        {value}
      </span>
      {gloss && <span className={styles.gloss}>{gloss}</span>}
    </div>
  );
}
