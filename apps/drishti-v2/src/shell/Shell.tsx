import { useEffect } from "react";
import { useRun } from "../data/RunContext";
import { CaseRibbon } from "./CaseRibbon";
import { TopStrip } from "./TopStrip";
import { Sutra } from "./Sutra";
import { Aperture } from "./Aperture";
import { PropertiesDrawer } from "./PropertiesDrawer";
import { StageScreen } from "./screens/Screens";
import { useShell } from "./ShellContext";
import styles from "./Shell.module.css";

/**
 * The app shell (§11.0) — no vertical rail anywhere. The thin top strip, the Sutra thread, one
 * dominant screen, and the two reusables (Aperture + Properties drawer) mounted
 * once at the root. The space key is the signature gesture: it blooms the
 * Aperture (guarded so typing a space in a field never triggers it).
 */
function isTyping(el: EventTarget | null): boolean {
  const t = el as HTMLElement | null;
  if (!t) return false;
  const tag = t.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || t.isContentEditable;
}

export function Shell() {
  const { stage, apertureOpen, setApertureOpen, closeDrawer } = useShell();
  const { runId } = useRun();
  useEffect(() => { closeDrawer(); }, [runId, closeDrawer]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === " " && !apertureOpen && !isTyping(e.target)) {
        e.preventDefault(); // space would otherwise scroll the page
        setApertureOpen(true);
      } else if (e.key === "Escape" && apertureOpen) {
        setApertureOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [apertureOpen, setApertureOpen]);

  return (
    <div className={styles.shell}>
      <TopStrip />
      <Sutra />
      <CaseRibbon />
      <main className={styles.stage}>
        <StageScreen key={runId + stage} id={stage} />
      </main>
      <Aperture />
      <PropertiesDrawer />
    </div>
  );
}
