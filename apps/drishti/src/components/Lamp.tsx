import styles from "./Lamp.module.css";

interface Props {
  /** Uppercase label, e.g. "HASH VERIFIED". */
  label: string;
  /** True lights the lamp --ok; false leaves it --ink-mute ("not yet run"). */
  on: boolean;
  /** The actual command that was run, printed under the lamp in micro mono. */
  detail?: string;
}

/** A boolean verification state. State is carried by the filled/hollow square AND the
 *  colour AND the label, never by colour alone, so it survives a colour-blind viewer. */
export function Lamp({ label, on, detail }: Props) {
  return (
    <div className={styles.lamp} data-on={on}>
      <div className={styles.row}>
        <span className={styles.square} aria-hidden />
        <span className={styles.label}>{label}</span>
      </div>
      {detail && <code className={`${styles.detail} mono`}>{detail}</code>}
    </div>
  );
}
