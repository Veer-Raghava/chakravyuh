import { dec } from "../format";
import type { ShapContribution } from "../adapter";
import styles from "./ShapBars.module.css";

interface Props {
  /** Signed contributions, already ordered by absolute value (largest first). */
  contributions: ShapContribution[];
  /** Model base rate the contributions push away from. Marked, not hidden. Null when the
   *  eval side is stripped (air-gapped serve): shown as "—", never faked to 0. */
  baseRate: number | null;
}

/** WHY, as a diverging bar chart. Each feature pushes the score right (raises risk,
 *  --signal) or left (lowers it, --cool) from a centre axis, so a non-specialist reads
 *  "what argued for, what argued against" in one glance without a single number.
 *  Widths are relative to the largest contribution; the axis is the model's base rate. */
export function ShapBars({ contributions, baseRate }: Props) {
  const maxAbs = Math.max(1e-6, ...contributions.map((c) => Math.abs(c.value)));

  return (
    <div className={styles.chart}>
      <div className={styles.axisLabels}>
        <span className={styles.axisCool}>lowers risk</span>
        <span className={styles.axisSignal}>raises risk</span>
      </div>

      <div className={styles.rows}>
        <div className={styles.centre} aria-hidden="true" />
        {contributions.map((c) => {
          const pos = c.value >= 0;
          const width = `${(Math.abs(c.value) / maxAbs) * 50}%`;
          return (
            <div key={c.feature} className={styles.row}>
              <span className={styles.feature}>{c.feature}</span>
              <div className={styles.track} role="img" aria-label={`${c.feature}: ${dec(c.value)}`}>
                <span
                  className={styles.bar}
                  data-pos={pos || undefined}
                  style={pos ? { left: "50%", width } : { right: "50%", width }}
                />
              </div>
              <span className={`${styles.value} mono`} data-pos={pos || undefined}>
                {pos ? "+" : "−"}
                {dec(Math.abs(c.value))}
              </span>
            </div>
          );
        })}
      </div>

      <div className={styles.base}>
        <span className={styles.baseLabel}>BASE RATE</span>
        <span className={`${styles.baseValue} mono`}>{baseRate === null ? "—" : dec(baseRate)}</span>
        <span className={styles.baseGloss}>the model's prior before any of this evidence</span>
      </div>
    </div>
  );
}
