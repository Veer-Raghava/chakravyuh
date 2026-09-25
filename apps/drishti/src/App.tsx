import { useEffect, useState } from "react";
import { adapter, type Manifest, type RunSummary } from "./adapter";
import { SCREENS } from "./screens";
import { Rail, type LampState } from "./components/Rail";
import { Lineage } from "./routes/Lineage";
import { Origin } from "./routes/Origin";
import { Graph } from "./routes/Graph";
import { Queue } from "./routes/Queue";
import { Packet } from "./routes/Packet";
import { Intake } from "./routes/Intake";
import { Collapse } from "./routes/Collapse";
import { Data } from "./routes/Data";
import styles from "./App.module.css";

export function App() {
  const [activeKey, setActiveKey] = useState("1");
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [activeRunId, setActiveRunId] = useState("");

  useEffect(() => {
    adapter.getManifest().then((m) => {
      setManifest(m);
      setActiveRunId((cur) => cur || m.run_id);
    });
    adapter.listRuns().then((rs) => {
      setRuns(rs);
      setActiveRunId((cur) => cur || rs.find((r) => r.active)?.run_id || rs[0]?.run_id || "");
    });
  }, []);

  const switchRun = (runId: string) => {
    setActiveRunId(runId);
    adapter.setActiveRun(runId).then(setManifest);
  };

  // Lamp states for the rail's L0–L6 strip, straight from the manifest's completed flags.
  const lampStates: Record<string, LampState> = {};
  for (const s of manifest?.stages ?? []) lampStates[s.id] = s.complete ? "ok" : "pending";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT")) return;
      // LINEAGE owns the keyboard (1–8 stages, arrows, enter/space); a Rail click navigates away.
      if (activeKey === "7") return;
      if (e.key >= "1" && e.key <= "8") setActiveKey(e.key);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeKey]);

  const active = SCREENS.find((s) => s.key === activeKey) ?? SCREENS[0];

  return (
    <div className={styles.appFrame}>
      <div className={styles.rail}>
        <Rail
          screens={SCREENS}
          activeKey={activeKey}
          onSelect={setActiveKey}
          runs={runs}
          activeRunId={activeRunId}
          airGapped={manifest?.air_gapped ?? true}
          lampStages={manifest?.stages ?? []}
          lampStates={lampStates}
          onSwitchRun={switchRun}
        />
      </div>
      <div className={styles.stage}>
        {active.id === "INTAKE" && <Intake />}
        {active.id === "COLLAPSE" && <Collapse />}
        {active.id === "ORIGIN" && <Origin />}
        {active.id === "GRAPH" && <Graph />}
        {active.id === "QUEUE" && <Queue onNavigate={setActiveKey} />}
        {active.id === "PACKET" && <Packet />}
        {active.id === "LINEAGE" && <Lineage />}
        {active.id === "DATA" && <Data />}
      </div>
    </div>
  );
}
