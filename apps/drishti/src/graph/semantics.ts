/**
 * The single source of the GRAPH visual grammar: what shape a node is and which layer it
 * belongs to. Colour lives entirely in CSS (tokens) — nothing here names a colour. Shape
 * and stroke, never colour, carry node/edge type, per DRISHTI-SPEC section 4.
 *
 * Node px sizes are scaled up from the spec's dense-graph 6px baseline because the demo
 * graph is sparse; the ENCODING (square/diamond/circle/hollow, cluster largest + bordered)
 * is preserved exactly. Geometry numbers live here, not in tokens.css, because an SVG's
 * coordinates cannot be expressed as CSS design tokens.
 */
import type { GraphNode, GraphEdge } from "../adapter";

export type Layer = "chain" | "network";

export const LAYER: Record<GraphNode["kind"], Layer> = {
  transaction: "chain",
  address: "chain",
  cluster: "chain",
  peer: "network",
  asn: "network",
};

/** Distance from the centre seam, in columns. Transactions and peers sit nearest the seam
 *  so the ANNOUNCED_BY stitches that cross it are the shortest, most legible edges on screen.
 *  Clusters are the chain-side aggregate the default view shows; individual addresses do not
 *  take a column — they bloom in a fan beside their cluster only when it is expanded. */
export const COLUMN: Record<GraphNode["kind"], number> = {
  transaction: 0,
  address: 1, // unused by the grid; addresses are placed by placeAddress(), not computeBase
  cluster: 1,
  peer: 0,
  asn: 1,
};

export type Shape = "square" | "diamond" | "circle" | "hollow-circle" | "bordered-square";

interface NodeGeom {
  shape: Shape;
  /** Side for squares/diamonds, radius for circles. */
  size: number;
}

export const NODE_GEOM: Record<GraphNode["kind"], NodeGeom> = {
  address: { shape: "square", size: 18 },
  transaction: { shape: "diamond", size: 22 },
  cluster: { shape: "bordered-square", size: 30 }, // largest + a border, always
  peer: { shape: "circle", size: 10 },
  asn: { shape: "hollow-circle", size: 15 }, // larger, hollow
};

/** The plain word the eye reads for each node type, shown as a caption on the labelled
 *  nodes so a viewer learns the shape grammar without a manual: a diamond IS a TX. */
export const KIND_WORD: Record<GraphNode["kind"], string> = {
  address: "WALLET",
  transaction: "TX",
  cluster: "CLUSTER",
  peer: "PEER",
  asn: "ASN",
};

/**
 * Edges carry meaning by stroke, not colour. `solid` = an observed value transfer, `dotted`
 * = a network announcement, `dashed` = the SAME_OWNER heuristic (drawn faint by confidence
 * so a weak link looks weak — it never merges nodes), `hair` = structural scaffolding.
 */
export type Stroke = "solid" | "dotted" | "dashed" | "hair";

export const EDGE_STROKE: Record<GraphEdge["kind"], Stroke> = {
  SPENDS: "solid",
  RECEIVES: "solid",
  ANNOUNCED_BY: "dotted",
  SAME_OWNER: "dashed",
  HOSTED_IN: "hair",
  MEMBER_OF: "hair",
};

/** SAME_OWNER opacity is exactly its cluster confidence, per DATA-CONTRACTS §5, so a 0.36
 *  heuristic reads visibly fainter than a confirmed spend and never masquerades as one.
 *  Every other stroke is opaque; structural scaffolding sits at a fixed hair weight. */
export function edgeBaseOpacity(edge: GraphEdge): number {
  if (edge.kind === "SAME_OWNER") return edge.confidence;
  if (EDGE_STROKE[edge.kind] === "hair") return 0.55;
  return 1;
}
