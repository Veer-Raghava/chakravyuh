import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { fixtures as baseline, type Fixtures } from "./loader";
import agency from "./fixtures/runs/agency-v2.json";
import graphAgency from "./fixtures/runs/agency-graph.json";
import catalog from "./fixtures/runs/catalog.json";

export type RunId = string;
type Payload = Partial<Fixtures> & {
  alertDetails?: Record<string, Fixtures["alert"]>;
  packets?: Record<string, Fixtures["packet"]>;
  focusedGraphs?: Record<string, Fixtures["graphAddress"]>;
  originDetails?: Record<string, Fixtures["origin"]>;
};
const modules = import.meta.glob(["./fixtures/runs/_sweep-*.json", "./fixtures/runs/agency-graph.json"], {
  import: "default",
});
const loaded = new Map<string, Payload>([
  ["agency-v2", agency as unknown as Payload],
  ["agency-graph", graphAgency as unknown as Payload],
]);
const names: Record<string, [string, string]> = {
  "agency-graph": ["Graph intelligence", "329-input CPU engine · diverse leads · newly signed cases"],
  "agency-v2": ["Agency", "Full investigation · capture to signed proof"],
  "_sweep-0.10": [
    "Stealth",
    "Sparse observation · inspect the candidate shortlist",
  ],
  "_sweep-0.02": [
    "Blind spots",
    "Minimal observation · explore what remains visible",
  ],
  "s12-canonical": [
    "Canonical case",
    "Complete pipeline · a second evidence dossier",
  ],
};
export type RunDef = {
  id: RunId;
  label: string;
  description: string;
  coverageLabel: string;
  curated: boolean;
  available: string[];
  stages: string[];
  payload: Payload;
  sha256: string;
  alert_count: number;
};
const RUNS: RunDef[] = catalog
  .filter((r) => r.id === "agency-v2" || r.id === "agency-graph" || r.id.startsWith("_sweep-"))
  .map((r) => {
    const payload = loaded.get(r.id) ?? {};
    const coverage = r.observer_fraction;
    return {
      ...r,
      payload,
      label: names[r.id]?.[0] ?? r.id.replace("_sweep-", "Coverage "),
      description:
        names[r.id]?.[1] ?? `${r.stages.length} generated stages · ${r.id}`,
      coverageLabel:
        coverage == null
          ? "Partial run"
          : `${Math.round(coverage * 100)}% coverage`,
    };
  })
  .sort(
    (a, b) =>
      Number(b.curated) - Number(a.curated) ||
      (a.id === "agency-graph"
        ? -1
        : b.id === "agency-graph"
          ? 1
          : a.id.localeCompare(b.id)),
  );

type RunState = {
  runId: RunId;
  run: RunDef;
  runs: RunDef[];
  setRun: (id: RunId) => void;
  loading: string | null;
  loadError: string;
  fixtures: Fixtures;
  has: (key: keyof Fixtures) => boolean;
  selectedTx: string | null;
  selectTx: (id: string | null) => void;
  selectedAlert: string | null;
  selectAlert: (id: string | null) => void;
};
const RunCtx = createContext<RunState | null>(null);
export function RunProvider({ children }: { children: ReactNode }) {
  const [runId, setRunId] = useState("agency-graph");
  const [selectedTx, setSelectedTx] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<string | null>(null);
  const selectTx = useCallback((id: string | null) => {
    setSelectedTx(id);
    setSelectedAlert(null);
  }, []);
  const selectAlert = useCallback(
    (id: string | null) => {
      setSelectedAlert(id);
      const payload = loaded.get(runId);
      const detail = id ? payload?.alertDetails?.[id] : null;
      setSelectedTx(detail?.origin?.txid ?? detail?.representative_txid ?? null);
    },
    [runId],
  );
  const [loading, setLoading] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");
  const request = useRef(0);
  const setRun = useCallback((id: RunId) => {
    const ticket = ++request.current;
    setLoading(id);
    setLoadError("");
    const load = loaded.has(id)
      ? Promise.resolve(loaded.get(id)!)
      : (modules[`./fixtures/runs/${id}.json`]?.() as
          | Promise<Payload>
          | undefined);
    if (!load) {
      setLoading(null);
      setLoadError("This run is not packaged in this workstation.");
      return;
    }
    void load
      .then((payload) => {
        loaded.set(id, payload);
        if (ticket !== request.current) return;
        setRunId(id);
        setSelectedTx(null);
        setSelectedAlert(null);
        setLoading(null);
      })
      .catch(() => {
        if (ticket === request.current) {
          setLoading(null);
          setLoadError(
            "Could not load the local run artifact. The current investigation is preserved.",
          );
        }
      });
  }, []);
  const value = useMemo<RunState>(() => {
    const definition = RUNS.find((r) => r.id === runId) ?? RUNS[0];
    const run = {
      ...definition,
      payload: loaded.get(definition.id) ?? definition.payload,
    };
    const p = run.payload;
    const alert = selectedAlert ? p.alertDetails?.[selectedAlert] : p.alert;
    const matchingCase = selectedTx
      ? Object.entries(p.alertDetails ?? {}).find(
          ([, a]) => (a.origin?.txid ?? a.representative_txid) === selectedTx.replace(/^tx:/, ""),
        )?.[0]
      : null;
    const packet = selectedAlert
      ? p.packets?.[selectedAlert]
      : selectedTx
        ? matchingCase
          ? p.packets?.[matchingCase]
          : undefined
        : p.packet;
    const origin = selectedTx
      ? p.originDetails?.[selectedTx.replace(/^tx:/, "")]
      : p.origin;
    // Baseline values only complete the compile-time contract. has() gates every
    // stage before rendering; missing artifacts are never presented as this run.
    const fixtures = {
      ...baseline,
      ...p,
      ...(alert ? { alert } : {}),
      ...(packet ? { packet } : {}),
      ...(origin ? { origin } : {}),
    } as Fixtures;
    const has = (key: keyof Fixtures) =>
      key === "packet"
        ? Boolean(packet)
        : key === "alert"
          ? Boolean(alert)
          : key === "origin"
            ? Boolean(origin)
            : p[key] != null;
    return {
      runId: run.id,
      run,
      runs: RUNS,
      setRun,
      loading,
      loadError,
      fixtures,
      has,
      selectedTx,
      selectTx,
      selectedAlert,
      selectAlert,
    };
  }, [
    runId,
    setRun,
    selectedTx,
    selectedAlert,
    loading,
    loadError,
    selectTx,
    selectAlert,
  ]);
  return <RunCtx.Provider value={value}>{children}</RunCtx.Provider>;
}
export function useRun(): RunState {
  const ctx = useContext(RunCtx);
  if (!ctx) throw new Error("useRun must be used inside <RunProvider>");
  return ctx;
}
