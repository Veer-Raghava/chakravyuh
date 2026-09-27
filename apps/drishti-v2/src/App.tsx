import { useState } from "react";
import { Stage } from "./stage/Stage";
import { LandingScenes } from "./landing/LandingScenes";
import { FunnelCounter } from "./landing/FunnelCounter";
import { StationCopy } from "./landing/StationCopy";
import { HeroText } from "./landing/Hero/HeroText";
import { DiyaHint } from "./landing/Diya/DiyaHint";
import { useScroll } from "./scroll/ScrollContext";
import { usePrefersReducedMotion } from "./scroll/usePrefersReducedMotion";

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

export default function App() {
  const { scrolled, nearTop } = useScroll();
  const reduced = usePrefersReducedMotion();
  // Diya on/off — in-memory only, never persisted (§2). Fresh every session.
  const [diyaOn, setDiyaOn] = useState(true);

  return (
    <Stage
      scene={<LandingScenes reduced={reduced} diyaOn={diyaOn} />}
      fallback={<HeroFallback />}
      overlay={
        <>
          <FunnelCounter />
          <HeroText dimmed={!nearTop} />
          <StationCopy />
          {diyaOn ? (
            <DiyaHint silent={scrolled} onDismiss={() => setDiyaOn(false)} />
          ) : null}
        </>
      }
    />
  );
}
