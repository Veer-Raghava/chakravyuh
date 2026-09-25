import { useEffect, useMemo, useState } from "react";
import { adapter, type GraphData, type GraphEdge, type Manifest } from "../adapter";
import { StatusBar } from "../components/StatusBar";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { ForceGraph, type View } from "../components/ForceGraph";
import { Legend } from "../components/Legend";
import { num } from "../format";
import { KIND_WORD } from "../graph/semantics";
import type { Mode } from "../graph/layout";
import styles from "./Graph.module.css";

const reduceMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const MODES: { id: Mode; label: string }[] = [
  { id: "chain", label: "CHAIN" },
  { id: "network", label: "NETWORK" },
  { id: "both", label: "BOTH" },
];

const VIEWS: { id: View; label: string }[] = [
  { id: "overview", label: "OVERVIEW" },
  { id: "explore", label: "EXPLORE" },
];

// Edge kinds in the order they read, with the human word for the inspector and toggles.
const EDGE_WORD: Record<GraphEdge["kind"], string> = {
  SPENDS: "spends",
  RECEIVES: "receives",
  ANNOUNCED_BY: "announced by",
  SAME_OWNER: "same owner?",
  HOSTED_IN: "hosted in",
  MEMBER_OF: "member of",
};

export function Graph() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [data, setData] = useState<GraphData | null>(null);
  const [last, setLast] = useState<LastCall | null>(null);
  const [mode, setMode] = useState<Mode>("both");
  const [view, setView] = useState<View>("overview");
  const [hop, setHop] = useState(3);
  const [hidden, setHidden] = useState<Set<GraphEdge["kind"]>>(new Set());
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  // Accordion: at most one cluster open at a time, so member wallets bloom without
  // colliding and the picture never fills with fans.
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    adapter.getManifest().then(setManifest);
    const t0 = performance.now();
    adapter.getGraph({}).then((g) => {
      setData(g);
      setLast({ label: "getGraph", ms: Math.round(performance.now() - t0) });
    });
  }, []);

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const el = ev.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
      // Hop depth is a click control only — the number keys stay global screen-jumps so
      // 1–7 mean the same thing on every screen. Escape drops the current selection.
      if (ev.key === "Escape") resetView();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // RESET VIEW puts the case back the way it opened: whole graph, both layers, nothing
  // selected, no cluster bloomed — the "show me the original as-is" escape hatch.
  const resetView = () => {
    setSelected(null);
    setExpanded(new Set());
    setView("overview");
    setMode("both");
  };
  const isDefaultView =
    selected === null && expanded.size === 0 && view === "overview" && mode === "both";

  // Clicking a node selects it (narrowing the view to its neighbourhood). Clicking a cluster
  // also toggles it open — one at a time — so the aggregate blooms into its member wallets.
  const onSelect = (id: string | null) => {
    setSelected(id);
    if (id === null) return;
    const node = data?.nodes.find((n) => n.node_id === id);
    if (node?.kind === "cluster") {
      setExpanded((cur) => (cur.has(id) ? new Set() : new Set([id])));
    }
  };

  const kinds = useMemo(
    () => (data ? [...new Set(data.edges.map((e) => e.kind))] : []),
    [data],
  );

  const selectedNode = data?.nodes.find((n) => n.node_id === selected) ?? null;
  const selectedEdges = data && selected ? data.edges.filter((e) => e.src === selected || e.dst === selected) : [];

  const toggleKind = (k: GraphEdge["kind"]) =>
    setHidden((h) => {
      const next = new Set(h);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });

  if (!data) {
    return (
      <div className={styles.page}>
        <StatusBar manifest={manifest} />
        <div className={styles.loading}>loading fused graph…</div>
        <CommandLine last={last} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <StatusBar manifest={manifest} />

      {/* quiet hairline control strip — never competes with the graph */}
      <div className={styles.strip}>
        <div className={styles.stripGroup}>
          <div className={styles.seg} role="group" aria-label="layers">
            {MODES.map((m) => (
              <button
                key={m.id}
                className={styles.segBtn}
                data-active={mode === m.id || undefined}
                onClick={() => setMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>

          <div className={styles.seg} role="group" aria-label="view">
            {VIEWS.map((v) => (
              <button
                key={v.id}
                className={styles.segBtn}
                data-active={view === v.id || undefined}
                onClick={() => setView(v.id)}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.controls}>
          <span className={styles.ctlLabel}>hop</span>
          <div className={styles.seg} role="group" aria-label="hop depth">
            {[1, 2, 3].map((h) => (
              <button key={h} className={`${styles.segBtn} mono`} data-active={hop === h || undefined} onClick={() => setHop(h)}>
                {h}
              </button>
            ))}
          </div>

          <span className={styles.ctlLabel}>edges</span>
          <div className={styles.toggles}>
            {kinds.map((k) => (
              <button
                key={k}
                className={styles.toggle}
                data-off={hidden.has(k) || undefined}
                data-stroke-swatch={k}
                onClick={() => toggleKind(k)}
              >
                {EDGE_WORD[k]}
              </button>
            ))}
          </div>

          <button className={styles.reset} onClick={resetView} disabled={isDefaultView}>
            RESET VIEW
          </button>
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.stage}>
          {/* the two territories, named where the eye needs it — no more */}
          <div className={styles.seam} data-mode={mode} aria-hidden="true">
            <span className={styles.seamLabel} data-side="chain">CHAIN · wallets + transactions</span>
            <span className={styles.seamLabel} data-side="network">NETWORK · peers + ASNs</span>
          </div>

          <Legend />

          {data.aggregated && (
            <div className={styles.aggregated} role="status">
              AGGREGATED · {num(data.aggregated.addresses)} addresses in {num(data.aggregated.clusters)} clusters
            </div>
          )}

          <ForceGraph
            data={data}
            mode={mode}
            view={view}
            hop={hop}
            hidden={hidden}
            expanded={expanded}
            hovered={hovered}
            selected={selected}
            onHover={setHovered}
            onSelect={onSelect}
            reduceMotion={reduceMotion()}
          />
        </div>

        <aside className={styles.aside}>
          {selectedNode ? (
            <div className={styles.detail}>
              <span className={styles.detailKind} data-path={selectedNode.on_origin_path || undefined}>
                {KIND_WORD[selectedNode.kind]}
              </span>
              <span className={`${styles.detailLabel} mono`}>{selectedNode.label}</span>
              {selectedNode.on_origin_path && <span className={styles.pathTag}>on estimated-origin path</span>}

              {selectedEdges.length > 0 && (
                <ul className={styles.edgeList}>
                  {selectedEdges.map((e, i) => (
                    <li key={i} className={styles.edgeItem}>
                      <span className={styles.edgeKind}>{EDGE_WORD[e.kind]}</span>
                      <span className={`${styles.edgeMeta} mono`}>
                        {e.confidence < 1 ? "heuristic · " : ""}
                        {e.evidence}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <p className={styles.prompt}>
              One case, many transactions. The wallet chain sits left of the seam, the peers and
              ASNs that carried it sit right; the lit path runs to the peer we estimate <b>sent</b>{" "}
              it, not merely relayed it. In <b>OVERVIEW</b> the whole case stays in view — click a
              node to read it, click a cluster to bloom its wallets in place. Switch to{" "}
              <b>EXPLORE</b> to focus a node's neighbourhood; <b>RESET VIEW</b> returns the original.
            </p>
          )}
        </aside>
      </div>

      <CommandLine last={last} />
    </div>
  );
}
