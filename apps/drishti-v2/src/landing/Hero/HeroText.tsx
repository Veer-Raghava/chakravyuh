import styles from "./HeroText.module.css";

/**
 * Hero copy (§7.HERO) — lives in the DOM (screen-reader reachable, §5.5), pinned
 * over the fixed canvas. Lifts away on first scroll as the camera descends.
 */
export function HeroText({ dimmed }: { dimmed: boolean }) {
  return (
    <div className={`${styles.wrap} ${dimmed ? styles.dimmed : ""}`}>
      <p className={styles.brand}>CHAKRAVYUH</p>
      <p className={styles.tag}>two-layer attribution · offline</p>
      <h1 className={styles.headline}>See through the noise.</h1>
      <p className={styles.sub}>
        DRISHTI reads the wire behind every Bitcoin transaction — and names the
        IP that sent it. <b>Or tells you, honestly, when no one can.</b>
      </p>
    </div>
  );
}
