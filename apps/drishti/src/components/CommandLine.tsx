import styles from "./CommandLine.module.css";

export interface LastCall {
  label: string;
  ms: number;
}

interface Props {
  last: LastCall | null;
}

export function CommandLine({ last }: Props) {
  return (
    <div className={styles.line} role="contentinfo">
      <span className={`${styles.prompt} mono`}>⌘K</span>
      <span className={styles.hint}>command</span>
      <span className={styles.divider} aria-hidden="true" />
      <span className={`${styles.cmd} mono`}>{last ? last.label : "ready"}</span>
      <div className={styles.spacer} />
      {last && (
        <span className={styles.timing}>
          <span className={styles.label}>adapter</span>
          <span className={`${styles.ms} mono`}>{last.ms} ms</span>
        </span>
      )}
    </div>
  );
}
