import type { Screen } from "../screens";
import type { StageLamp, RunSummary } from "../adapter";
import type { LampState } from "./Lamp";
import { Appearance } from "./Appearance";
import styles from "./Rail.module.css";

export type { LampState };

interface Props {
  screens: Screen[];
  activeKey: string;
  onSelect: (key: string) => void;
  runs: RunSummary[];
  activeRunId: string;
  airGapped: boolean;
  /** L0–L6, from the manifest, drawn as the pipeline lamp strip. */
  lampStages: StageLamp[];
  /** Per-lamp state, from the manifest's completed flags. */
  lampStates: Record<string, LampState>;
  onSwitchRun: (runId: string) => void;
}

export function Rail({
  screens, activeKey, onSelect, runs, activeRunId, airGapped,
  lampStages, lampStates, onSwitchRun,
}: Props) {
  const active = screens.find((s) => s.key === activeKey) ?? screens[0];

  return (
    <nav className={styles.rail} aria-label="screens">
      <div className={styles.brand}>
        <span className={styles.brandName}>DRISHTI</span>
        <span className={styles.brandSub}>chakravyuh console</span>
      </div>

      {/* run context: which capture we analyse, its lamps, and a simulated re-run */}
      <div className={styles.run} aria-label="run">
        <div className={styles.runHead}>
          <label className={styles.runLabel} htmlFor="run-switch">run</label>
          {airGapped && <span className={styles.airGap}>AIR-GAPPED</span>}
        </div>
        <select
          id="run-switch"
          className={`${styles.runSelect} mono`}
          value={activeRunId}
          onChange={(e) => onSwitchRun(e.target.value)}
        >
          {runs.map((r) => (
            <option key={r.run_id} value={r.run_id}>{r.run_id} · {r.label}</option>
          ))}
        </select>

        <div className={styles.lamps} aria-label="pipeline stages">
          {lampStages.map((s) => (
            <span key={s.id} className={styles.lampCol} title={`${s.id} · ${s.stage}`}>
              <span className={styles.lamp} data-state={lampStates[s.id] ?? "pending"} aria-hidden />
              <span className={`${styles.lampId} mono`}>{s.id}</span>
            </span>
          ))}
        </div>
      </div>

      <ul className={styles.list}>
        {screens.map((s) => {
          const on = s.key === activeKey;
          return (
            <li key={s.key}>
              <button
                className={styles.item}
                data-active={on}
                aria-current={on ? "page" : undefined}
                onClick={() => onSelect(s.key)}
              >
                <span className={`${styles.key} mono`}>{s.key}</span>
                <span className={styles.name}>{s.id}</span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className={styles.spacer} />

      <div className={styles.keys} aria-label={`${active.id} shortcuts`}>
        <div className={styles.keysHead}>{active.id} keys</div>
        {active.shortcuts.map((sc) => (
          <div key={sc.keys} className={styles.keyRow}>
            <span className={`${styles.keyCap} mono`}>{sc.keys}</span>
            <span className={styles.keyDoes}>{sc.does}</span>
          </div>
        ))}
      </div>

      <Appearance />
    </nav>
  );
}
