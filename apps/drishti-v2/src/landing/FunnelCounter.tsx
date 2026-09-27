import { useEffect, useRef } from "react";
import { useScroll } from "../scroll/ScrollContext";
import { STATIONS, funnelValue } from "./stations";
import styles from "./FunnelCounter.module.css";

/**
 * The funnel — the descending counter that is the spine of the whole landing
 * (§7: craft-move #2, 3D that IS the data, expressed as the page). Starts at
 * 1,000,000 raw signals and counts down as each station settles.
 *
 * It polls the shared scroll ref in its own rAF loop and writes the DOM node
 * directly — the number changes every frame, so routing it through React state
 * would re-render the tree ~60x/s. The value stays in the DOM (screen-reachable,
 * §5.5); we skip aria-live so it doesn't spam a screen reader each tick.
 */
const UNIT: Record<string, string> = {
  mayajaal: "signals",
  kavach: "sealed",
  setu: "untangled",
  jaal: "real transactions",
  shastra: "attributable",
  buddhi: "flagged",
  vaani: "leads",
  pramaan: "proof",
};

const fmt = new Intl.NumberFormat("en-US");

export function FunnelCounter() {
  const { progress } = useScroll();
  const numRef = useRef<HTMLSpanElement>(null);
  const unitRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    let raf = 0;
    let lastN = -1;
    let lastUnit = "";
    const tick = () => {
      const p = progress.current ?? 0;
      const n = funnelValue(p);
      if (n !== lastN && numRef.current) {
        numRef.current.textContent = fmt.format(n);
        lastN = n;
      }
      // current station = the last one whose slice has started
      let cur = STATIONS[0];
      for (const st of STATIONS) if (p >= st.slice[0]) cur = st;
      const u = UNIT[cur.id];
      if (u !== lastUnit && unitRef.current) {
        unitRef.current.textContent = u;
        lastUnit = u;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [progress]);

  return (
    <div className={styles.funnel} aria-label="Signal funnel — signals narrowing toward one proof">
      <span className={styles.label}>THE FUNNEL</span>
      <span ref={numRef} className={styles.value}>
        {fmt.format(STATIONS[0].count)}
      </span>
      <span ref={unitRef} className={styles.unit}>
        {UNIT.mayajaal}
      </span>
    </div>
  );
}
