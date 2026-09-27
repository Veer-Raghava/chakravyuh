import { useEffect, useRef } from "react";
import { useScroll } from "../scroll/ScrollContext";
import { STATIONS, local } from "./stations";
import styles from "./StationCopy.module.css";

/**
 * The per-station DOM copy (§7). Every station's block is rendered once and
 * stacked in the same lower-left slot; a single rAF loop sets each block's
 * opacity to its slice's rise/hold/dissolve bell, so they physically cross-fade
 * as you scroll — no text-swap bookkeeping. All copy is in the DOM (§5.5,
 * screen-reachable) and uses §3 vocabulary only.
 *
 * Opacity here is a function of scroll POSITION, not time, so the
 * reduced-motion path needs no branch — it cross-fades exactly the same.
 */
export function StationCopy() {
  const { progress } = useScroll();
  const refs = useRef<(HTMLElement | null)[]>([]);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const p = progress.current ?? 0;
      STATIONS.forEach((st, i) => {
        const el = refs.current[i];
        if (!el) return;
        const { vis } = local(p, st.slice);
        el.style.opacity = String(vis);
        // lift a touch as it resolves — a small settle, not a slide
        el.style.transform = `translateY(${(1 - vis) * 12}px)`;
        el.style.visibility = vis < 0.01 ? "hidden" : "visible";
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [progress]);

  return (
    <div className={styles.slot}>
      {STATIONS.map((st, i) => (
        <article
          key={st.id}
          ref={(el) => {
            refs.current[i] = el;
          }}
          className={styles.block}
          style={{ opacity: i === 0 ? 1 : 0 }}
        >
          <p className={styles.layer}>
            <span className={styles.layerName}>{st.layer}</span>
            <span className={styles.gloss}> — {st.gloss}</span>
          </p>
          <h2 className={styles.title}>{st.title}</h2>
          <p className={styles.body}>{st.body}</p>
          <p className={styles.diya}>{st.diya}</p>
        </article>
      ))}
    </div>
  );
}
