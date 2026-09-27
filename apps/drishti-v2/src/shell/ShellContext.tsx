import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { StageId } from "../nav/stages";

/**
 * The shell's one context (§11.0) — current stage, the Aperture quick-switcher,
 * and the reusable right-hand Properties drawer. Built once; every screen learns
 * this interaction once and reuses it everywhere. No url router (offline, §5.5) —
 * the current stage is plain in-memory state, fresh each session.
 */
type Drawer = { open: boolean; title: string; content: ReactNode };

type ShellState = {
  stage: StageId;
  goTo: (id: StageId) => void;
  apertureOpen: boolean;
  setApertureOpen: (v: boolean) => void;
  drawer: Drawer;
  openDrawer: (title: string, content: ReactNode) => void;
  closeDrawer: () => void;
};

const ShellCtx = createContext<ShellState | null>(null);

export function ShellProvider({ children }: { children: ReactNode }) {
  const [stage, setStage] = useState<StageId>("globe");
  const [apertureOpen, setApertureOpen] = useState(false);
  const [drawer, setDrawer] = useState<Drawer>({ open: false, title: "", content: null });

  const goTo = useCallback((id: StageId) => {
    setStage(id);
    setApertureOpen(false);
  }, []);
  const openDrawer = useCallback(
    (title: string, content: ReactNode) => setDrawer({ open: true, title, content }),
    [],
  );
  const closeDrawer = useCallback(() => setDrawer((d) => ({ ...d, open: false })), []);

  const value = useMemo(
    () => ({ stage, goTo, apertureOpen, setApertureOpen, drawer, openDrawer, closeDrawer }),
    [stage, goTo, apertureOpen, drawer, openDrawer, closeDrawer],
  );

  return <ShellCtx.Provider value={value}>{children}</ShellCtx.Provider>;
}

export function useShell(): ShellState {
  const ctx = useContext(ShellCtx);
  if (!ctx) throw new Error("useShell must be used inside <ShellProvider>");
  return ctx;
}
