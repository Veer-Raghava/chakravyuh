import styles from "./Histogram.module.css";

interface Props {
  /** One bar per bucket. `label` is the x value (e.g. announcements-per-tx). */
  bars: { label: number; value: number }[];
  /** Draw a vertical marker at this x value, e.g. the computed mean. */
  mean?: number;
  /** Caption printed at the mean marker, already mono-formatted. */
  meanLabel?: string;
  height?: number;
}

/** A hairline bar histogram: no gridlines, no chart title, mono micro tick labels, a
 *  single --signal marker for the mean. Hand-rolled SVG — the console carries no chart
 *  dependency yet, and this is one of the primitives the spec's inventory names. */
export function Histogram({ bars, mean, meanLabel, height = 160 }: Props) {
  const max = Math.max(1, ...bars.map((b) => b.value));
  const minX = Math.min(...bars.map((b) => b.label));
  const maxX = Math.max(...bars.map((b) => b.label));
  const spanX = maxX - minX || 1;
  const meanPct = mean !== undefined ? ((mean - minX) / spanX) * 100 : null;

  return (
    <div className={styles.wrap} style={{ height }}>
      <div className={styles.plot}>
        {bars.map((b) => (
          <div key={b.label} className={styles.col} title={`${b.label}: ${b.value.toLocaleString("en-US")}`}>
            <div className={styles.bar} style={{ height: `${(b.value / max) * 100}%` }} aria-hidden />
            <span className={`${styles.tick} mono`}>{b.label}</span>
          </div>
        ))}
        {meanPct !== null && (
          <div className={styles.mean} style={{ left: `${meanPct}%` }} aria-hidden>
            {meanLabel && <span className={`${styles.meanLabel} mono`}>{meanLabel}</span>}
          </div>
        )}
      </div>
    </div>
  );
}
