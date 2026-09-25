import type { Screen } from "../screens";
import { Appearance } from "./Appearance";
import styles from "./Rail.module.css";

interface Props {
  screens: Screen[];
  activeKey: string;
  onSelect: (key: string) => void;
}

export function Rail({ screens, activeKey, onSelect }: Props) {
  const active = screens.find((s) => s.key === activeKey) ?? screens[0];

  return (
    <nav className={styles.rail} aria-label="screens">
      <div className={styles.brand}>
        <span className={styles.brandName}>DRISHTI</span>
        <span className={styles.brandSub}>chakravyuh console</span>
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
        <div className={styles.keyRow}>
          <span className={`${styles.keyCap} mono`}>?</span>
          <span className={styles.keyDoes}>all keys</span>
        </div>
      </div>

      <Appearance />
    </nav>
  );
}
