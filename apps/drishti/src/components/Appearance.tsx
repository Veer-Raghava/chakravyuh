import { useState } from "react";
import { THEMES, FONTS, applyTheme, applyFont, getTheme, getFont, type ThemeId, type FontId } from "../theme";
import styles from "./Appearance.module.css";

// Theme + UI-face switchers. Live in the rail footer. Presentational only — they set
// attributes on <html> via theme.ts and never call the adapter.
export function Appearance() {
  const [theme, setTheme] = useState<ThemeId>(getTheme);
  const [font, setFont] = useState<FontId>(getFont);

  return (
    <div className={styles.root} aria-label="appearance">
      <label className={styles.field}>
        <span className={styles.head}>theme</span>
        <select
          className={styles.select}
          value={theme}
          onChange={(e) => {
            const id = e.target.value as ThemeId;
            setTheme(id);
            applyTheme(id);
          }}
        >
          {THEMES.map((t) => (
            <option key={t.id} value={t.id}>{t.label}</option>
          ))}
        </select>
      </label>

      <label className={styles.field}>
        <span className={styles.head}>ui font</span>
        <select
          className={styles.select}
          value={font}
          onChange={(e) => {
            const id = e.target.value as FontId;
            setFont(id);
            applyFont(id);
          }}
        >
          {FONTS.map((f) => (
            <option key={f.id} value={f.id}>{f.label}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
