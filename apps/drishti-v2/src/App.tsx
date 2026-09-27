import { useEffect, useRef, useState } from "react";
import { Stage } from "./stage/Stage";
import { LandingScenes } from "./landing/LandingScenes";
import { FunnelCounter } from "./landing/FunnelCounter";
import { StationCopy } from "./landing/StationCopy";
import { HeroText } from "./landing/Hero/HeroText";
import { DiyaHint } from "./landing/Diya/DiyaHint";
import { Login } from "./auth/Login";
import { ShellProvider } from "./shell/ShellContext";
import { Shell } from "./shell/Shell";
import { useScroll } from "./scroll/ScrollContext";
import { usePrefersReducedMotion } from "./scroll/usePrefersReducedMotion";
import styles from "./App.module.css";

type Phase = "landing" | "login" | "app";

/** No-WebGL 2D fallback (§5.5) — the hero message survives without a canvas. */
function HeroFallback() {
  return (
    <div style={{ display: "grid", placeItems: "center", height: "100vh", padding: "2rem" }}>
      <div style={{ maxWidth: "40rem" }}>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "clamp(2.5rem,9vw,6rem)", margin: 0 }}>
          See through the noise.
        </h1>
        <p style={{ color: "var(--ink-soft)", fontSize: "1.25rem" }}>
          DRISHTI reads the wire behind every Bitcoin transaction — and names the
          IP that sent it. Or tells you, honestly, when no one can.
        </p>
      </div>
    </div>
  );
}

function Landing({ onEnter }: { onEnter: () => void }) {
  const { scrolled, nearTop, progress } = useScroll();
  const reduced = usePrefersReducedMotion();
  const [diyaOn, setDiyaOn] = useState(true);
  // the outro affordance rises once the story has run its course (§7.OUTRO → login)
  const [atOutro, setAtOutro] = useState(false);
  const atOutroRef = useRef(false);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const p = progress.current ?? 0;
      const on = p > 0.95;
      if (on !== atOutroRef.current) {
        atOutroRef.current = on;
        setAtOutro(on);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [progress]);

  return (
    <Stage
      scene={<LandingScenes reduced={reduced} diyaOn={diyaOn} />}
      fallback={<HeroFallback />}
      overlay={
        <>
          <FunnelCounter />
          <HeroText dimmed={!nearTop} />
          <StationCopy />
          {diyaOn ? <DiyaHint silent={scrolled} onDismiss={() => setDiyaOn(false)} /> : null}
          <button
            className={`${styles.enter} ${atOutro ? styles.enterOn : ""}`}
            type="button"
            onClick={onEnter}
            tabIndex={atOutro ? 0 : -1}
            aria-hidden={!atOutro}
          >
            Enter the workstation →
          </button>
        </>
      }
    />
  );
}

export default function App() {
  const [phase, setPhase] = useState<Phase>("landing");

  if (phase === "login") return <Login onSuccess={() => setPhase("app")} />;
  if (phase === "app")
    return (
      <ShellProvider>
        <Shell />
      </ShellProvider>
    );
  return <Landing onEnter={() => setPhase("login")} />;
}
