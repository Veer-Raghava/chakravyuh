import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fixtures, type Fixtures } from "./loader";

/**
 * The run switcher's one seam. DRISHTI can hold more than one CHAKRAVYUH run
 * (an observer-coverage regime each) and swap between them without touching a
 * screen. Screens read their data from `useRun().fixtures`, never the static
 * loader import — so when a new run's fixtures land, they slot in here and every
 * screen follows.
 *
 * Today only `agency-v2` is generated; "Stealth" points at the same fixtures as
 * a preview. The badge reads the ACTIVE fixtures' real world.json
 * (run_id · observer_fraction · observer_regime), so it never claims coverage
 * the data doesn't have — pick Stealth before its fixtures exist and the badge
 * honestly still reads agency-v2.
 */
export type RunId = "agency" | "stealth";

type RunDef = {
  id: RunId;
  label: string; // dropdown label, e.g. "Agency"
  coverageLabel: string; // intended coverage, e.g. "60% coverage"
  fixtures: Fixtures;
};

// ponytail: both entries share agency-v2 fixtures until stealth is generated;
// swap `fixtures` on the stealth row for its own set when it exists.
const RUNS: RunDef[] = [
  { id: "agency", label: "Agency", coverageLabel: "60% coverage", fixtures },
  { id: "stealth", label: "Stealth", coverageLabel: "10% coverage", fixtures },
];

type RunState = {
  runId: RunId;
  run: RunDef;
  runs: RunDef[];
  setRun: (id: RunId) => void;
  fixtures: Fixtures; // the active run's data — the one source every screen reads
};

const RunCtx = createContext<RunState | null>(null);

export function RunProvider({ children }: { children: ReactNode }) {
  const [runId, setRunId] = useState<RunId>("agency");
  const setRun = useCallback((id: RunId) => setRunId(id), []);

  const value = useMemo<RunState>(() => {
    const run = RUNS.find((r) => r.id === runId) ?? RUNS[0];
    return { runId: run.id, run, runs: RUNS, setRun, fixtures: run.fixtures };
  }, [runId, setRun]);

  return <RunCtx.Provider value={value}>{children}</RunCtx.Provider>;
}

export function useRun(): RunState {
  const ctx = useContext(RunCtx);
  if (!ctx) throw new Error("useRun must be used inside <RunProvider>");
  return ctx;
}
