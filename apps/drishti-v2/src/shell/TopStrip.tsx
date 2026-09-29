import { useShell } from "./ShellContext";
import { RunSwitcher } from "./RunSwitcher";
import styles from "./TopStrip.module.css";

/**
 * The thin top strip above the thread (§11.0) — case id (mono), the run switcher
 * + run badge (§12.1), the offline badge, and the diya glyph (clicking it opens
 * the Aperture, the same as pressing space). Deliberately quiet: no breadcrumbs,
 * no menus, no settings gear.
 */
export function TopStrip() {
  const { setApertureOpen } = useShell();

  return (
    <div className={styles.strip}>
      <div className={styles.ids}>
        <span className={styles.wordmark}>DRISHTI</span>
        <span className={styles.sep} />
        <span className={styles.id}>
          <span className={styles.idLabel}>case</span> SIH-26146
        </span>
        <RunSwitcher />
      </div>

      <div className={styles.right}>
        <span className={styles.offline}>
          <span className={styles.dot} /> OFFLINE · 127.0.0.1 · no external calls
        </span>
        <button
          className={styles.diya}
          type="button"
          aria-label="Open the Aperture (or press space)"
          onClick={() => setApertureOpen(true)}
        >
          <span className={styles.diyaFlame} />
        </button>
      </div>
    </div>
  );
}
