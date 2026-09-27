import styles from "./DiyaHint.module.css";

/**
 * The diya's one calm line (§2). Spoken once on arrival, silent after first
 * scroll. Dismissible — turning it off removes the diya entirely for the
 * session. The off-state is in-memory React state only, NEVER localStorage
 * (§2, §5) — every session starts with the guide present.
 */
export function DiyaHint({
  silent,
  onDismiss,
}: {
  silent: boolean;
  onDismiss: () => void;
}) {
  return (
    <div className={`${styles.hint} ${silent ? styles.silent : ""}`}>
      <p className={styles.line}>Scroll. I&rsquo;ll show you the maze.</p>
      <button
        className={styles.dismiss}
        onClick={onDismiss}
        aria-label="Dismiss the guide for this session"
        title="Dismiss the guide"
      >
        ✕
      </button>
    </div>
  );
}
