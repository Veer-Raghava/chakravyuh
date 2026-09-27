import { useEffect } from "react";
import { useShell } from "./ShellContext";
import styles from "./PropertiesDrawer.module.css";

/**
 * The reusable Properties / detail drawer (§11.0) — slides in from the right,
 * NEVER a modal. The same pattern on every screen, so the user learns it once;
 * it's the app's spine of interaction. Context-driven: any screen calls
 * openDrawer(title, content). Closes on esc or the close control.
 */
export function PropertiesDrawer() {
  const { drawer, closeDrawer } = useShell();

  useEffect(() => {
    if (!drawer.open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDrawer();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer.open, closeDrawer]);

  return (
    <aside
      className={`${styles.drawer} ${drawer.open ? styles.open : ""}`}
      aria-hidden={!drawer.open}
      aria-label="Properties"
    >
      <header className={styles.head}>
        <span className={styles.title}>{drawer.title}</span>
        <button className={styles.close} type="button" onClick={closeDrawer} aria-label="Close properties">
          ✕
        </button>
      </header>
      <div className={styles.body}>{drawer.content}</div>
    </aside>
  );
}
