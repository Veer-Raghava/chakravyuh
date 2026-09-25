import { dec } from "../format";
import styles from "./RangeBar.module.css";

interface Props {
  /** Interval endpoints and the point estimate, all on [domainMin, domainMax]. */
  low: number;
  high: number;
  point?: number;
  domainMin?: number;
  domainMax?: number;
  /** Show the numeric endpoints in mono beside the bar. */
  showBounds?: boolean;
}

/** A conformal interval drawn as a hairline track with a --cool span and a point marker.
 *  A wide interval visibly reads as low confidence; that honesty is the whole point. */
export function RangeBar({
  low,
  high,
  point,
  domainMin = 0,
  domainMax = 1,
  showBounds = true,
}: Props) {
  const span = domainMax - domainMin || 1;
  const pct = (v: number) => `${((v - domainMin) / span) * 100}%`;

  return (
    <div className={styles.wrap}>
      {showBounds && <span className={`${styles.bound} mono`}>{dec(low)}</span>}
      <div className={styles.track} role="img" aria-label={`interval ${dec(low)} to ${dec(high)}`}>
        <div className={styles.fill} style={{ left: pct(low), right: `calc(100% - ${pct(high)})` }} />
        {point !== undefined && <div className={styles.point} style={{ left: pct(point) }} />}
      </div>
      {showBounds && <span className={`${styles.bound} mono`}>{dec(high)}</span>}
    </div>
  );
}
