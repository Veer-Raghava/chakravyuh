import { useEffect, useState } from "react";
import gsap from "gsap";

/**
 * prefers-reduced-motion, via gsap.matchMedia (§4.4, CLAUDE.md a11y rule).
 * Returns true when the user asked for reduced motion — every animated scene
 * branches on this to a static/looped-off fallback.
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: reduce)", () => {
      setReduced(true);
      return () => setReduced(false);
    });
    return () => mm.revert();
  }, []);

  return reduced;
}
