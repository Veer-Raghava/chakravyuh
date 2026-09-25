import { useState } from "react";
import styles from "./HashBlock.module.css";

interface Props {
  /** The full value. Copy always copies this in full, whatever is displayed. */
  value: string;
  /** Uppercase micro label, e.g. "MERKLE HEAD" or "SHA-256". */
  label?: string;
  /** Show first8…last4 instead of the full string. A hash prints in full; ids truncate. */
  truncate?: boolean;
}

const short = (v: string) => (v.length <= 16 ? v : `${v.slice(0, 8)}…${v.slice(-4)}`);

/** A mono hash with a copy affordance. The one string that is allowed in full — its whole
 *  purpose is to be checkable — so copy yields the complete value even when displayed short. */
export function HashBlock({ value, label, truncate = false }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      // Clipboard denied (no https / no permission). The value is still selectable.
    }
  };

  return (
    <div className={styles.block}>
      {label && <span className={styles.label}>{label}</span>}
      <code className={`${styles.value} mono`}>{truncate ? short(value) : value}</code>
      <button className={styles.copy} onClick={copy} aria-label="copy full value" title="copy full value">
        {copied ? "COPIED" : "COPY"}
      </button>
    </div>
  );
}
