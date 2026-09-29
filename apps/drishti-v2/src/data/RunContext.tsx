import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fixtures, type Fixtures } from "./loader";
// Stealth = the real `_sweep-0.10` run (observer_fraction 0.10), exported off the
// same serializer as agency. Only the layers the sweep run regenerates differ
// (world · origin · abstain); the per-lead artifacts (alerts/packet/manifest…)
// weren't produced for the sweep, so stealth reuses agency's for those — a
// documented fallback, never invented numbers.
import stealthWorld from "./fixtures/stealth/world.json";
import stealthOrigin from "./fixtures/stealth/origin.json";
import stealthOriginAbstain from "./fixtures/stealth/origin-abstain.json";

/**
 * The run switcher's one seam. DRISHTI holds more than one CHAKRAVYUH run
 * (an observer-coverage regime each) and swaps between them without touching a
 * screen. Screens read their data from `useRun().fixtures`, never the static
 * loader import — so a new run's fixtures slot in here and every screen follows.
 *
 * The badge reads the ACTIVE fixtures' real world.json
 * (run_id · observer_fraction · observer_regime), so it never claims coverage
 * the data doesn't have.
 */
export type RunId = "agency" | "stealth";

// Stealth's own world/origin numbers (real, from _sweep-0.10) over agency's rest.
// `as unknown as` because the sweep run legitimately has nulls where agency has
// numbers (campaign_recall, elliptic_* — the risk model wasn't scored at 10%
// coverage); the screens null-guard those, so the widened shape is correct.
const stealthFixtures: Fixtures = {
  ...fixtures,
  world: stealthWorld as unknown as Fixtures["world"],
  origin: stealthOrigin as unknown as Fixtures["origin"],
  originAbstain: stealthOriginAbstain as unknown as Fixtures["originAbstain"],
};

type RunDef = {
  id: RunId;
  label: string; // dropdown label, e.g. "Agency"
  coverageLabel: string; // intended coverage, e.g. "60% coverage"
  fixtures: Fixtures;
};

// ponytail: stealth regenerates only the origin/world layer; alerts/packet reuse
// agency (the sweep run has no per-lead stages). Swap in a full stealth pipeline
// when one is generated.
const RUNS: RunDef[] = [
  { id: "agency", label: "Agency", coverageLabel: "60% coverage", fixtures },
  { id: "stealth", label: "Stealth", coverageLabel: "10% coverage", fixtures: stealthFixtures },
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
