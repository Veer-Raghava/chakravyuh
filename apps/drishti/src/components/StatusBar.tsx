import type { Manifest } from "../adapter";
import styles from "./StatusBar.module.css";

/** first four and last four hex, the compact form the chrome shows. The full Merkle
 *  root is printed exactly once, on PACKET, never here. */
const head4 = (hex: string): string => `${hex.slice(0, 4)}…${hex.slice(-4)}`;
const group = (n: number): string => n.toLocaleString("en-US");

interface Props {
  manifest: Manifest | null;
}

export function StatusBar({ manifest }: Props) {
  if (!manifest) {
    return (
      <div className={styles.bar} role="banner">
        <span className={styles.label}>run</span>
        <span className={`${styles.value} mono`}>loading…</span>
      </div>
    );
  }

  return (
    <div className={styles.bar} role="banner">
      <Field label="run" value={manifest.run_id} />
      <Div />
      <Field label="sha" value={head4(manifest.input_sha256)} title={manifest.input_sha256} />
      <Div />
      <Field label="rows" value={group(manifest.rows_sealed)} />
      <Field label="tx" value={group(manifest.n_transactions)} />
      <Div />
      <div className={styles.lamps} aria-label="stage completion">
        {manifest.stages.map((s) => (
          <span
            key={s.id}
            className={`${styles.lamp} mono`}
            data-complete={s.complete}
            title={`${s.stage} ${s.complete ? "complete" : "pending"}`}
          >
            {s.id}
          </span>
        ))}
      </div>
      <Div />
      <Field label="merkle" value={head4(manifest.merkle_head)} title={manifest.merkle_head} />

      <div className={styles.spacer} />

      {manifest.air_gapped && (
        <span className={styles.airgap}>
          <span className={styles.square} aria-hidden="true" />
          air-gapped
        </span>
      )}
    </div>
  );
}

function Field({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <span className={styles.field} title={title}>
      <span className={styles.label}>{label}</span>
      <span className={`${styles.value} mono`}>{value}</span>
    </span>
  );
}

const Div = () => <span className={styles.divider} aria-hidden="true" />;
