import { THREAD_STAGES, WORLD_STAGE, STAGES, indexOf } from "../nav/stages";
import { useShell } from "./ShellContext";
import styles from "./Sutra.module.css";

/**
 * The Sutra (§11.0) — the thread out of the maze. A slim top sightline, always
 * visible, workflow-ordered. The current stage is enlarged + lit; past stages
 * carry a wax-seal tick (done); stages ahead stay quiet ink-soft (reachable, not
 * yet run). World (MAYAJAAL) is pinned far right, outside the funnel order. The
 * funnel bead rides the thread, carrying the run's signal-count → 1 counter.
 * Reduced-motion: the bead jumps instead of sliding (handled by the global
 * reduced-motion rule zeroing transitions).
 */
const fmt = new Intl.NumberFormat("en-US");

export function Sutra() {
  const { stage, goTo } = useShell();
  const currentIndex = indexOf(stage);
  const current = STAGES[currentIndex];

  // bead rides to the centre of the current thread stop (World sits off the funnel)
  const threadIndex = THREAD_STAGES.findIndex((s) => s.id === stage);
  const beadLeft =
    threadIndex >= 0 ? ((threadIndex + 0.5) / THREAD_STAGES.length) * 100 : 50;

  const renderStop = (id: string, name: string, tag: string) => {
    const idx = indexOf(id as never);
    const state = idx < currentIndex ? "done" : idx === currentIndex ? "current" : "ahead";
    return (
      <button
        key={id}
        type="button"
        className={`${styles.stop} ${styles[state]}`}
        aria-current={state === "current" ? "step" : undefined}
        onClick={() => goTo(id as never)}
      >
        <span className={styles.name}>
          {name}
          {state === "done" && <span className={styles.seal} aria-label="done" />}
        </span>
        {tag && <span className={styles.tag}>{tag}</span>}
      </button>
    );
  };

  return (
    <nav className={styles.sutra} aria-label="The thread — case workflow">
      <div className={styles.thread}>
        <div className={styles.line} aria-hidden="true" />
        {threadIndex >= 0 && (
          <div className={styles.bead} style={{ left: `${beadLeft}%` }} aria-hidden="true">
            <span className={styles.beadCount}>{current.count != null ? fmt.format(current.count) : ""}</span>
          </div>
        )}
        <div className={styles.stops}>
          {THREAD_STAGES.map((s) => renderStop(s.id, s.name, s.tag))}
        </div>
      </div>

      <div className={styles.world}>{renderStop(WORLD_STAGE.id, WORLD_STAGE.name, WORLD_STAGE.tag)}</div>
    </nav>
  );
}
