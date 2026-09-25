import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphData, GraphEdge, GraphNode } from "../adapter";
import { computeBase, place, placeAddress, W, H, type Mode } from "../graph/layout";
import { fold } from "../graph/fold";
import { NODE_GEOM, EDGE_STROKE, KIND_WORD, edgeBaseOpacity } from "../graph/semantics";
import styles from "./ForceGraph.module.css";

/** OVERVIEW keeps the whole case in view — a selection only highlights; EXPLORE narrows to
 *  the selected node's neighbourhood, ghosting the rest so global context is never lost. */
export type View = "overview" | "explore";

interface Props {
  data: GraphData;
  mode: Mode;
  view: View;
  hop: number;
  hidden: Set<GraphEdge["kind"]>;
  expanded: Set<string>;
  hovered: string | null;
  selected: string | null;
  onHover: (id: string | null) => void;
  onSelect: (id: string | null) => void;
  reduceMotion: boolean;
}

const DIM = 0.12; // opacity of everything not adjacent to the hovered node
const GHOST = 0.08; // EXPLORE: out-of-neighbourhood nodes fade to a ghost, never vanish
const STATE_MS = 120; // --t-state: a layer swap is a state change, not a reveal (those are reserved)

// The exact --t-state curve, cubic-bezier(0.2, 0, 0.3, 1), sampled in JS because the swap
// tweens cross-seam edges that no single CSS-transformed group can carry. Same curve as the
// token, not a hand-rolled approximation — motion obeys the two-curve law. The 420ms --t-reveal
// budget is spent elsewhere (COLLAPSE, ORIGIN, QUEUE); a layer toggle here rides the state curve.
function cubicBezier(p1x: number, p1y: number, p2x: number, p2y: number) {
  const cx = 3 * p1x, bx = 3 * (p2x - p1x) - cx, ax = 1 - cx - bx;
  const cy = 3 * p1y, by = 3 * (p2y - p1y) - cy, ay = 1 - cy - by;
  const fx = (t: number) => ((ax * t + bx) * t + cx) * t;
  const fy = (t: number) => ((ay * t + by) * t + cy) * t;
  const dfx = (t: number) => (3 * ax * t + 2 * bx) * t + cx;
  return (x: number) => {
    let t = x;
    for (let i = 0; i < 5; i++) {
      const err = fx(t) - x;
      if (Math.abs(err) < 1e-4) break;
      const d = dfx(t);
      if (Math.abs(d) < 1e-6) break;
      t -= err / d;
    }
    return fy(t);
  };
}
const easeState = cubicBezier(0.2, 0, 0.3, 1);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Animates mode changes: mp runs 0->1 while the two layers slide between the previous and
 *  current mode. Everything the eye tracks (nodes and every edge) is recomputed each frame
 *  from one scalar, so the two blocks move together and nothing unrelated reflows. */
function useModeTween(mode: Mode, reduceMotion: boolean) {
  const [mp, setMp] = useState(1);
  const from = useRef(mode);
  const to = useRef(mode);
  useEffect(() => {
    if (to.current === mode) return;
    from.current = to.current;
    to.current = mode;
    if (reduceMotion) return setMp(1);
    setMp(0);
    let raf = 0;
    const t0 = performance.now();
    const step = () => {
      const p = Math.min(1, (performance.now() - t0) / STATE_MS);
      setMp(p);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [mode, reduceMotion]);
  return { fromMode: from.current, toMode: to.current, mp };
}

function adjacency(edges: GraphEdge[]): Map<string, Set<string>> {
  const adj = new Map<string, Set<string>>();
  const link = (a: string, b: string) => (adj.get(a) ?? adj.set(a, new Set()).get(a)!).add(b);
  for (const e of edges) {
    link(e.src, e.dst);
    link(e.dst, e.src);
  }
  return adj;
}

/** Nodes within `hop` steps of the given roots, over the visible graph. On selection the
 *  root is the selected node, so clicking anything focuses its neighbourhood and everything
 *  outside that radius drops away — the investigation narrows to what you touched. */
function reachableFrom(roots: string[], adj: Map<string, Set<string>>, hop: number): Set<string> {
  const seen = new Set(roots);
  let frontier = roots;
  for (let d = 0; d < hop; d++) {
    const next: string[] = [];
    for (const id of frontier)
      for (const nb of adj.get(id) ?? [])
        if (!seen.has(nb)) (seen.add(nb), next.push(nb));
    frontier = next;
  }
  return seen;
}

interface Frame {
  x: number;
  y: number;
  op: number;
}

/** A rotated square, a plain square, or a circle at the origin — shape carries node type. */
function Glyph({ kind }: { kind: GraphNode["kind"] }) {
  const g = NODE_GEOM[kind];
  if (g.shape === "circle" || g.shape === "hollow-circle")
    return <circle r={g.size} className={styles.glyph} data-shape={g.shape} data-kind={kind} />;
  const s = g.size;
  return (
    <rect
      x={-s / 2}
      y={-s / 2}
      width={s}
      height={s}
      rx={2}
      className={styles.glyph}
      data-shape={g.shape}
      data-kind={kind}
      transform={g.shape === "diamond" ? "rotate(45)" : undefined}
    />
  );
}

export function ForceGraph({ data, mode, view, hop, hidden, expanded, hovered, selected, onHover, onSelect, reduceMotion }: Props) {
  // Fold addresses into their cluster unless it is expanded; the aggregate grid stays put,
  // so a cluster opening never reflows the rest of the picture.
  const folded = useMemo(() => fold(data, expanded), [data, expanded]);
  const base = useMemo(() => computeBase(data.nodes), [data]);
  const adj = useMemo(() => adjacency(folded.edges), [folded]);
  const { fromMode, toMode, mp } = useModeTween(mode, reduceMotion);
  const animating = mp < 1;
  const e = easeState(mp);

  // Which address belongs to which cluster, and its slot in the fan, so a member wallet is
  // placed relative to its (moving) cluster in every mode.
  const addrInfo = useMemo(() => {
    const info = new Map<string, { cluster: string; i: number; n: number }>();
    for (const [cluster, ids] of folded.members)
      ids.forEach((id, i) => info.set(id, { cluster, i, n: ids.length }));
    return info;
  }, [folded]);

  // Focus is an EXPLORE-only act: only there does selecting a node narrow the picture to its
  // hop-neighbourhood. In OVERVIEW the whole case stays fully in view and a selection merely
  // lights up (ring + labels + inspector), so global context is never traded away.
  const inFocus = useMemo(
    () => (view === "explore" && selected ? reachableFrom([selected], adj, hop) : null),
    [view, selected, adj, hop],
  );

  const positionOf = (id: string, m: Mode) => {
    const a = addrInfo.get(id);
    return a ? placeAddress(base, a.cluster, a.i, a.n, m) : place(base, id, m);
  };

  // One frame: fuse the from/to layouts by the eased progress, then apply focus and hover
  // dimming. hover keeps the hovered node and its neighbours lit and drops the rest.
  const near = hovered ? new Set([hovered, ...(adj.get(hovered) ?? [])]) : null;
  const frame: Record<string, Frame> = {};
  for (const n of folded.nodes) {
    const a = positionOf(n.node_id, fromMode);
    const b = positionOf(n.node_id, toMode);
    let op = lerp(a.visible ? 1 : 0, b.visible ? 1 : 0, e);
    if (inFocus && !inFocus.has(n.node_id)) op *= GHOST; // explore: fade, don't hide
    if (near && !near.has(n.node_id)) op *= DIM;
    frame[n.node_id] = { x: lerp(a.x, b.x, e), y: lerp(a.y, b.y, e), op };
  }

  const trans = animating ? "none" : undefined; // CSS eases hover/focus; rAF owns the layer swap

  return (
    <svg
      className={styles.svg}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Fused attribution graph: the wallet chain on the left, the peer-and-ASN network on the right, joined across the seam; the estimated-origin path is lit."
    >
      {/* Money-flow arrowheads. One shape, orient='auto-start-reverse' so it points correctly
          whether placed at the start (SPENDS: value into the tx) or end (RECEIVES: value out
          to the wallet). A neutral head and a signal head for the lit origin path. */}
      <defs>
        <marker id="fg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9" className={styles.arrow} />
        </marker>
        <marker id="fg-arrow-path" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,1 L9,5 L0,9" className={styles.arrowPath} />
        </marker>
      </defs>

      <g className={styles.edges}>
        {folded.edges.map((edge, i) => {
          if (hidden.has(edge.kind)) return null;
          const a = frame[edge.src];
          const b = frame[edge.dst];
          if (!a || !b) return null;
          const op = Math.min(a.op, b.op) * edgeBaseOpacity(edge);
          const cross = edge.kind === "ANNOUNCED_BY";
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2 - Math.abs(b.x - a.x) * 0.12; // gentle bow on the stitch
          const d = cross ? `M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}` : `M${a.x},${a.y} L${b.x},${b.y}`;
          // Money flows into the tx on a SPENDS and out to the wallet on a RECEIVES; the head
          // sits on the value-destination end so the direction reads without a caption.
          const arrow = edge.on_origin_path ? "url(#fg-arrow-path)" : "url(#fg-arrow)";
          const hi = edge.src === hovered || edge.dst === hovered || undefined;
          return (
            <path
              key={i}
              d={d}
              className={styles.edge}
              data-stroke={EDGE_STROKE[edge.kind]}
              data-path={edge.on_origin_path || undefined}
              data-hi={hi}
              markerStart={edge.kind === "SPENDS" ? arrow : undefined}
              markerEnd={edge.kind === "RECEIVES" ? arrow : undefined}
              style={{ opacity: op, transition: trans }}
            />
          );
        })}
      </g>

      <g className={styles.nodes}>
        {folded.nodes.map((n) => {
          const f = frame[n.node_id];
          const labelled = n.on_origin_path || n.node_id === hovered || n.node_id === selected;
          const g = NODE_GEOM[n.kind];
          return (
            <g
              key={n.node_id}
              transform={`translate(${f.x},${f.y})`}
              className={styles.node}
              data-path={n.on_origin_path || undefined}
              data-selected={n.node_id === selected || undefined}
              data-expanded={(n.kind === "cluster" && expanded.has(n.node_id)) || undefined}
              style={{ opacity: f.op, transition: trans, pointerEvents: f.op < 0.2 ? "none" : "auto" }}
              onMouseEnter={() => onHover(n.node_id)}
              onMouseLeave={() => onHover(null)}
              onClick={() => onSelect(n.node_id)}
            >
              {n.node_id === selected && <circle r={g.size + 8} className={styles.ring} />}
              <Glyph kind={n.kind} />
              {labelled && (
                <>
                  <text className={styles.kind} y={-(g.size + 9)}>
                    {KIND_WORD[n.kind]}
                  </text>
                  <text className={`${styles.label} mono`} y={g.size + 16}>
                    {n.label}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </g>
    </svg>
  );
}
