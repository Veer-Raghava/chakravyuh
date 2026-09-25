import type { ReactNode } from "react";
import styles from "./Panel.module.css";

interface Props {
  title: string;
  right?: ReactNode;
  children?: ReactNode;
}

/** A ruled surface with an uppercase micro title and an optional right slot. Every
 *  working surface on the console sits inside one of these. */
export function Panel({ title, right, children }: Props) {
  return (
    <section className={styles.panel}>
      <header className={styles.head}>
        <span className={styles.title}>{title}</span>
        {right && <div className={styles.right}>{right}</div>}
      </header>
      <div className={styles.body}>{children}</div>
    </section>
  );
}
