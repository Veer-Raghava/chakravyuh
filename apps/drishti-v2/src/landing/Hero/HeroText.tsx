import styles from "./HeroText.module.css";

/**
 * Hero copy (§7.HERO) — lives in the DOM (screen-reader reachable, §5.5), pinned
 * over the fixed canvas. Lifts away on first scroll as the camera descends.
 */
export function HeroText({ dimmed }: { dimmed: boolean }) {
  return (
    <div className={`${styles.wrap} ${dimmed ? styles.dimmed : ""}`}>
      <p className={styles.brand}>CHAKRAVYUH</p>
      <p className={styles.tag}>BITCOIN TRANSACTION ANALYSIS</p>
      <h1 className={styles.headline}>See where the money came from.</h1>
      <p className={styles.sub}>
        Our solution visualises Bitcoin transaction traffic, shows how
        transactions move across the network, and estimates where they
        originated.
      </p>
    </div>
  );
}
