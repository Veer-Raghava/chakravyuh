import styles from "./Sparkline.module.css";

interface Props {
  points: number[];
  /** Uppercase micro label above the line. */
  label: string;
  /** Mono unit shown with the latest value. */
  unit: string;
  width?: number;
  height?: number;
}

/** A hairline sparkline: no axes, no dots except the latest point, one mono readout of
 *  the current value. A small multiple, three to a row on the SETU collapse detail. */
export function Sparkline({ points, label, unit, width = 220, height = 40 }: Props) {
  const max = Math.max(...points);
  const min = Math.min(...points);
  const span = max - min || 1;
  const stepX = width / Math.max(1, points.length - 1);
  const y = (v: number) => height - ((v - min) / span) * height;
  const d = points.map((v, i) => `${i === 0 ? "M" : "L"}${(i * stepX).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const last = points[points.length - 1] ?? 0;

  return (
    <div className={styles.spark}>
      <div className={styles.head}>
        <span className={styles.label}>{label}</span>
        <span className={`${styles.value} mono`}>
          {last.toLocaleString("en-US")} {unit}
        </span>
      </div>
      <svg className={styles.svg} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label={label}>
        <path className={styles.line} d={d} />
        <circle className={styles.dot} cx={(points.length - 1) * stepX} cy={y(last)} r={1.5} />
      </svg>
    </div>
  );
}
