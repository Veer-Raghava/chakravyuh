import styles from "./Lamp.module.css";

export type LampState = "ok" | "pending" | "fail";

interface Props {
  /** Uppercase label, e.g. "HASH VERIFIED". */
  label: string;
  /** Back-compat boolean: true -> "ok", false -> "pending" ("not yet run"). */
  on?: boolean;
  /** Explicit tri-state; wins over `on`. "fail" is a red --alert lamp (e.g. replay mismatch). */
  state?: LampState;
  /** The actual command that was run, printed under the lamp in micro mono. */
  detail?: string;
}

/** A verification state. State is carried by the filled/hollow square AND the colour AND the
 *  label, never by colour alone, so it survives a colour-blind viewer. "fail" turns the lamp
 *  --alert: a verification that ran and did NOT hold is louder than one not yet run. */
export function Lamp({ label, on, state, detail }: Props) {
  const s: LampState = state ?? (on ? "ok" : "pending");
  return (
    <div className={styles.lamp} data-state={s}>
      <div className={styles.row}>
        <span className={styles.square} aria-hidden />
        <span className={styles.label}>{label}</span>
      </div>
      {detail && <code className={`${styles.detail} mono`}>{detail}</code>}
    </div>
  );
}
