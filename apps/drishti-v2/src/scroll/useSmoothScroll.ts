import { useEffect, type MutableRefObject } from "react";
import Lenis from "lenis";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * The §5.2 wiring, done once. Lenis and GSAP share ONE clock so scroll and
 * animation never desync; we drive the loop (autoRaf:false). ScrollTrigger is
 * married in now so later stations (M2+) get pinning for free.
 *
 * We do NOT use drei <ScrollControls> — it fights Lenis + ScrollTrigger.
 *
 * The single shared scrollProgress (0→1 over the whole page) is written to the
 * passed ref on every scroll tick. Scenes read `ref.current` inside useFrame —
 * no React re-render per frame. onFirstScroll fires once, the frame the user
 * first moves (drives the lens tip / diya silence).
 */
export function useSmoothScroll(
  progress: MutableRefObject<number>,
  onFirstScroll?: () => void,
  onProgress?: (p: number) => void,
): void {
  useEffect(() => {
    const lenis = new Lenis({ autoRaf: false });
    (window as unknown as { __lenis?: Lenis }).__lenis = lenis; // debug: drive from console
    let fired = false;

    const onScroll = ({ scroll, limit }: { scroll: number; limit: number }) => {
      progress.current = limit > 0 ? Math.min(Math.max(scroll / limit, 0), 1) : 0;
      ScrollTrigger.update();
      onProgress?.(progress.current);
      if (!fired && progress.current > 0.002) {
        fired = true;
        onFirstScroll?.();
      }
    };
    lenis.on("scroll", onScroll);

    const raf = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(raf);
    gsap.ticker.lagSmoothing(0);

    return () => {
      lenis.off("scroll", onScroll);
      gsap.ticker.remove(raf);
      lenis.destroy();
    };
    // progress/onFirstScroll are stable refs/callbacks from the provider.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
