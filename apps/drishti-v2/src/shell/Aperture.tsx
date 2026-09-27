import { useEffect, useMemo, useRef, useState } from "react";
import { STAGES } from "../nav/stages";
import { useShell } from "./ShellContext";
import styles from "./Aperture.module.css";

/**
 * The Aperture (§11.0) — the signature nav gesture. Press space (or click the
 * diya / lens glyph) and an iris blooms from the centre of the screen: the
 * chakravyuha rings made literal, every destination on a radial ring, with a
 * search field at the pupil. DRISHTI opening its eye. Closes on esc or selection.
 * Never required (the thread covers everyone) — the power move judges remember.
 */
export function Aperture() {
  const { apertureOpen, setApertureOpen, goTo } = useShell();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return STAGES;
    return STAGES.filter(
      (s) => s.name.toLowerCase().includes(q) || s.tag.toLowerCase().includes(q) || s.gloss.toLowerCase().includes(q),
    );
  }, [query]);

  useEffect(() => {
    if (apertureOpen) {
      setQuery("");
      // focus the pupil once the iris has begun to open
      const t = setTimeout(() => inputRef.current?.focus(), 60);
      return () => clearTimeout(t);
    }
  }, [apertureOpen]);

  if (!apertureOpen) return null;

  const n = STAGES.length;

  return (
    <div
      className={styles.scrim}
      role="dialog"
      aria-modal="true"
      aria-label="Aperture — jump to a destination"
      onClick={() => setApertureOpen(false)}
    >
      <div className={styles.iris} onClick={(e) => e.stopPropagation()}>
        {/* the rings — the chakravyuha, made literal */}
        <span className={styles.ring} style={{ width: "34rem", height: "34rem" }} aria-hidden="true" />
        <span className={styles.ring} style={{ width: "24rem", height: "24rem" }} aria-hidden="true" />
        <span className={styles.ring} style={{ width: "14rem", height: "14rem" }} aria-hidden="true" />

        {/* destinations arranged on the outer ring */}
        {STAGES.map((s, i) => {
          const angle = (i / n) * Math.PI * 2 - Math.PI / 2; // start at top
          const r = 15; // rem
          const x = Math.cos(angle) * r;
          const y = Math.sin(angle) * r;
          const dim = !matches.includes(s);
          return (
            <button
              key={s.id}
              type="button"
              className={`${styles.dest} ${dim ? styles.dim : ""}`}
              style={{ transform: `translate(calc(-50% + ${x}rem), calc(-50% + ${y}rem))` }}
              onClick={() => goTo(s.id)}
            >
              <span className={styles.destName}>{s.name}</span>
              {s.tag && <span className={styles.destTag}>{s.tag}</span>}
            </button>
          );
        })}

        {/* the pupil — search */}
        <form
          className={styles.pupil}
          onSubmit={(e) => {
            e.preventDefault();
            if (matches[0]) goTo(matches[0].id);
          }}
        >
          <input
            ref={inputRef}
            className={styles.search}
            type="text"
            value={query}
            placeholder="go to tx / address / IP…"
            aria-label="Search destinations"
            onChange={(e) => setQuery(e.target.value)}
          />
        </form>
      </div>
    </div>
  );
}
