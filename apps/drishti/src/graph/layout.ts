/**
 * Deterministic, seedless layered layout. The two structures — chain (transactions,
 * addresses, clusters) on the left of a centre seam, network (peers, ASNs) on the right —
 * get fixed columnar positions so the picture is calm and identical on every render (no
 * force sim, no jitter). One base layout is computed once; `place(base, id, mode)` derives
 * a node's position and visibility for CHAIN / NETWORK / BOTH by translating a whole layer
 * as one block. That is what lets the mode change animate as two blocks sliding, never a
 * reflow — the snap the screen is built around.
 */
import type { GraphNode } from "../adapter";
import { COLUMN, LAYER, type Layer } from "./semantics";

export type Mode = "chain" | "network" | "both";

export const W = 1200;
export const H = 720;
const SEAM = W / 2;
const COL_GAP = 200;
const ROW_GAP = 104;
const PAD = 72; // vertical breathing room a column keeps from the top and bottom edges

// Expanded-cluster fan: member wallets stack just outside their cluster (further from the
// seam), so a cluster "opens" into the addresses it aggregates without disturbing the grid.
const FAN_DX = 132;
const FAN_ROW = 46;

interface BasePos {
  x: number;
  y: number;
  layer: Layer;
}

export interface Base {
  pos: Record<string, BasePos>;
  chainDx: number; // shift that centres the chain block on the seam when it is alone
  networkDx: number;
}

/** Column x measured out from the seam: chain to the left, network to the right. */
function columnX(layer: Layer, col: number): number {
  const out = COL_GAP * (col + 1);
  return layer === "chain" ? SEAM - out : SEAM + out;
}

export function computeBase(nodes: GraphNode[]): Base {
  const pos: Record<string, BasePos> = {};

  // Addresses never sit in the grid — they bloom in a fan beside their cluster on expand.
  // The aggregate nodes (transactions, clusters, peers, ASNs) are the stable columnar frame,
  // so a cluster expanding/collapsing never reflows anything else.
  const grid = nodes.filter((n) => n.kind !== "address");

  // Group by (layer, column); order within a column deterministically, origin-path first so
  // the lit path sits high and stable, then by id so a reorder never moves anything.
  const columns = new Map<string, GraphNode[]>();
  for (const n of grid) {
    const key = `${LAYER[n.kind]}:${COLUMN[n.kind]}`;
    (columns.get(key) ?? columns.set(key, []).get(key)!).push(n);
  }

  for (const [key, group] of columns) {
    const [layer, colStr] = key.split(":");
    const col = Number(colStr);
    group.sort((a, b) =>
      a.on_origin_path === b.on_origin_path
        ? a.node_id.localeCompare(b.node_id)
        : a.on_origin_path
          ? -1
          : 1,
    );
    const x = columnX(layer as Layer, col);
    // Distribute the column across the vertical band, tightening the gap as a column grows so
    // a dozen transactions fit without overflow — the picture stays calm at any node count.
    const gap = group.length > 1 ? Math.min(ROW_GAP, (H - 2 * PAD) / (group.length - 1)) : 0;
    const span = (group.length - 1) * gap;
    group.forEach((n, i) => {
      pos[n.node_id] = { x, y: H / 2 - span / 2 + i * gap, layer: layer as Layer };
    });
  }

  return { pos, chainDx: centringDx(pos, "chain"), networkDx: centringDx(pos, "network") };
}

function centringDx(pos: Record<string, BasePos>, layer: Layer): number {
  const xs = Object.values(pos).filter((p) => p.layer === layer).map((p) => p.x);
  if (xs.length === 0) return 0;
  const centre = (Math.min(...xs) + Math.max(...xs)) / 2;
  return SEAM - centre;
}

export interface Placed {
  x: number;
  y: number;
  visible: boolean;
}

/** A node's position and whether it is shown in a given mode. In a solo mode the visible
 *  layer is translated to centre on the seam; the other layer keeps its seam-side position
 *  (so it slides in from the correct side) but is not shown. */
export function place(base: Base, id: string, mode: Mode): Placed {
  const p = base.pos[id];
  if (!p) return { x: SEAM, y: H / 2, visible: false };
  if (mode === "both") return { x: p.x, y: p.y, visible: true };
  if (mode === "chain") {
    return p.layer === "chain" ? { x: p.x + base.chainDx, y: p.y, visible: true } : { x: p.x, y: p.y, visible: false };
  }
  return p.layer === "network" ? { x: p.x + base.networkDx, y: p.y, visible: true } : { x: p.x, y: p.y, visible: false };
}

/** An expanded cluster's i-th member wallet (of n), fanned just outside the cluster. It
 *  inherits the cluster's mode placement — sliding with the chain block and hiding in the
 *  network solo view — so the bloom always tracks the cluster it belongs to. */
export function placeAddress(base: Base, clusterId: string, i: number, n: number, mode: Mode): Placed {
  const c = place(base, clusterId, mode);
  if (!c.visible) return { x: c.x, y: c.y, visible: false };
  const span = (n - 1) * FAN_ROW;
  return { x: c.x - FAN_DX, y: c.y - span / 2 + i * FAN_ROW, visible: true };
}
