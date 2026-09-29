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
      <span className={styles.arrow} role="img" aria-label="Scroll down to begin">
        <svg width="22" height="30" viewBox="0 0 22 30" fill="none" aria-hidden="true">
          <path
            d="M11 2 L11 24 M3 16 L11 24 L19 16"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
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
