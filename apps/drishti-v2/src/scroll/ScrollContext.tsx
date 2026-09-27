import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { useSmoothScroll } from "./useSmoothScroll";

type ScrollState = {
  /** 0→1 over the whole page. Read inside useFrame — never triggers re-render. */
  progress: RefObject<number>;
  /** Flips true (once) the first frame the user scrolls. Drives DOM reactions. */
  scrolled: boolean;
  /** True while near the very top. Reversible — flips back on scroll-up so the
   *  hero copy returns. Only setState on threshold crossing, not per frame. */
  nearTop: boolean;
};

const ScrollCtx = createContext<ScrollState | null>(null);

export function ScrollProvider({ children }: { children: ReactNode }) {
  const progress = useRef(0);
  const [scrolled, setScrolled] = useState(false);
  const [nearTop, setNearTop] = useState(true);
  const nearTopRef = useRef(true);
  const onFirstScroll = useCallback(() => setScrolled(true), []);
  const onProgress = useCallback((p: number) => {
    const nt = p < 0.02;
    if (nt !== nearTopRef.current) {
      nearTopRef.current = nt;
      setNearTop(nt);
    }
  }, []);

  useSmoothScroll(progress, onFirstScroll, onProgress);

  return (
    <ScrollCtx.Provider value={{ progress, scrolled, nearTop }}>
      {children}
    </ScrollCtx.Provider>
  );
}

export function useScroll(): ScrollState {
  const ctx = useContext(ScrollCtx);
  if (!ctx) throw new Error("useScroll must be used inside <ScrollProvider>");
  return ctx;
}
