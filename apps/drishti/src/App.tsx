import { useEffect, useState } from "react";
import { adapter, type Manifest } from "./adapter";
import { SCREENS } from "./screens";
import { StatusBar } from "./components/StatusBar";
import { Rail } from "./components/Rail";
import { CommandLine, type LastCall } from "./components/CommandLine";
import { Panel } from "./components/Panel";
import { Lineage } from "./routes/Lineage";
import { Origin } from "./routes/Origin";
import { Graph } from "./routes/Graph";
import styles from "./App.module.css";

export function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [activeKey, setActiveKey] = useState("1");
  const [last, setLast] = useState<LastCall | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(true);

  // On load the StatusBar's values come from one real adapter call, timed so the
  // CommandLine can show an honest latency rather than a decorative spinner.
  useEffect(() => {
    const t0 = performance.now();
    adapter.getManifest().then((m) => {
      setManifest(m);
      setLast({ label: "getManifest", ms: Math.round(performance.now() - t0) });
    });
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
      // LINEAGE owns the keyboard (1–8 stages, arrows, enter/space); Rail click navigates away.
      if (activeKey === "7") return;
      if (e.key >= "1" && e.key <= "7") {
        setActiveKey(e.key);
        setInspectorOpen(true);
      } else if (e.key === "Escape") {
        setInspectorOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeKey]);

  const active = SCREENS.find((s) => s.key === activeKey) ?? SCREENS[0];

  // Screen 7 is a complete page that owns its own StatusBar + CommandLine, so the shell
  // renders only the Rail beside it — no doubled chrome. Screens 1–6 are still the
  // placeholder frame until their Track B surfaces land.
  // Screen 3 (ORIGIN) is a full page like LINEAGE: the fan needs the room to be the hero
  // and owns its own keyboard (j/k move, Space reveals). It carries its own StatusBar +
  // CommandLine, so the shell renders only the Rail beside it.
  if (active.id === "ORIGIN") {
    return (
      <div className={styles.lineageFrame}>
        <div className={styles.rail}>
          <Rail screens={SCREENS} activeKey={activeKey} onSelect={setActiveKey} />
        </div>
        <div className={styles.lineageStage}>
          <Origin />
        </div>
      </div>
    );
  }

  if (active.id === "GRAPH") {
    return (
      <div className={styles.lineageFrame}>
        <div className={styles.rail}>
          <Rail screens={SCREENS} activeKey={activeKey} onSelect={setActiveKey} />
        </div>
        <div className={styles.lineageStage}>
          <Graph />
        </div>
      </div>
    );
  }

  if (active.id === "LINEAGE") {    return (
      <div className={styles.lineageFrame}>
        <div className={styles.rail}>
          <Rail screens={SCREENS} activeKey={activeKey} onSelect={setActiveKey} />
        </div>
        <div className={styles.lineageStage}>
          <Lineage />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.frame}>
      <div className={styles.status}>
        <StatusBar manifest={manifest} />
      </div>

      <div className={styles.rail}>
        <Rail screens={SCREENS} activeKey={activeKey} onSelect={setActiveKey} />
      </div>

      <div className={styles.stage}>
        <Panel title={active.id} right={<span className={`${styles.screenKey} mono`}>{active.key}</span>}>
          <p className={styles.verdict}>{active.verdict}</p>
          <p className={styles.note}>Working surface renders in a later Track B session.</p>
        </Panel>
      </div>

      <div className={styles.inspector} data-open={inspectorOpen}>
        <Panel title="inspector">
          {inspectorOpen ? (
            <p className={styles.empty}>Select an object to see its evidence and counter-evidence.</p>
          ) : (
            <p className={styles.empty}>Closed. Press a screen key to reopen.</p>
          )}
        </Panel>
      </div>

      <div className={styles.command}>
        <CommandLine last={last} />
      </div>
    </div>
  );
}
