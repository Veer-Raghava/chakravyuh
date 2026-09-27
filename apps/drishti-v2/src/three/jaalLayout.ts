// JAAL — the two-floor fusion layout (§10.0). PURE geometry, no fixture import, no
// R3F: it takes the backend's graph nodes/edges and returns fixed positions so the
// screen only renders. The spatial grammar (never a hairball) lives entirely here:
//   Y = LAYER   peers ▲ on the upper floor, money (● addr / ◆ tx) on the lower floor.
//   X = FLOW/TIME  earliest first_us on the left → latest on the right.
//   Z = de-overlap only  a deterministic per-column lane spread (NOT a force sim).
// The one edge that crosses floors is ANNOUNCED_BY (fluoro pink) — the fusion, made
// physical. assertJaalInvariants() is the runnable check that guards that grammar.

export type JaalKind = "address" | "transaction" | "peer";
export type EdgeKind = "input" | "output" | "announce";

export type RawNode = {
  node_id: string;
  kind: string;
  label: string;
  first_us: number | null;
  last_us: number | null;
};
export type RawEdge = {
  src: string;
  dst: string;
  kind: string;
  confidence: number;
  sats: number | null;
  ts_us: number | null;
  evidence: string;
};

export type Vec3 = [number, number, number];
export type LaidNode = {
  id: string;
  kind: JaalKind;
  label: string; // backend-truncated display form — the ONLY id we ever render
  pos: Vec3;
  firstUs: number | null;
};
export type LaidEdge = {
  kind: EdgeKind;
  a: Vec3;
  b: Vec3;
  src: string;
  dst: string;
  sats: number | null;
  tsUs: number | null;
};

export type Jaal = {
  nodes: LaidNode[];
  byId: Map<string, LaidNode>;
  edges: LaidEdge[];
  asnOf: Map<string, string>; // peer id → "asn:64496" (network operator, via HOSTED_IN)
};

// World extent of the diagram. Floors sit at ±FLOOR_Y so a side-on camera reads two
// clearly separated bands; the pink threads span the whole gap between them.
export const FLOOR_Y = 1.5;
const HALF_W = 3.6; // left(earliest) ↔ right(latest)
const HALF_D = 1.7; // depth of a floor (the z lane spread)
const COLUMNS = 26; // time is bucketed into columns; z de-overlaps within a column

const RENDER: Record<string, JaalKind> = {
  address: "address",
  transaction: "transaction",
  peer: "peer",
};
const EDGE: Record<string, EdgeKind> = {
  SPENDS: "input", // addr → tx  (money in)
  RECEIVES: "output", // tx → addr (money out)
  ANNOUNCED_BY: "announce", // tx → peer (THE cross-floor thread)
};

function floorY(kind: JaalKind): number {
  return kind === "peer" ? FLOOR_Y : -FLOOR_Y;
}

/** Deterministic tie-broken sort so a lane assignment is stable across reloads. */
function cmpId(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function layoutJaal(rawNodes: RawNode[], rawEdges: RawEdge[]): Jaal {
  const render = rawNodes.filter((n) => n.kind in RENDER);

  // X = flow. On the MONEY floor x = real time (value flows left→right). Peers get
  // an even rank-by-time spread instead: it keeps temporal order but fills the whole
  // upper floor, so the announce threads fan out into readable crossings rather than
  // collapsing into one corner (a peer's first_us clusters at session start).
  const times = render.map((n) => n.first_us).filter((t): t is number => t != null);
  const tMin = times.length ? Math.min(...times) : 0;
  const tMax = times.length ? Math.max(...times) : 1;
  const span = Math.max(1, tMax - tMin);
  const xOf = (t: number | null): number =>
    t == null ? 0 : ((t - tMin) / span) * (2 * HALF_W) - HALF_W;

  const peers = render
    .filter((n) => n.kind === "peer")
    .sort((a, b) => (a.first_us ?? 0) - (b.first_us ?? 0) || cmpId(a.node_id, b.node_id));
  const peerX = new Map<string, number>();
  peers.forEach((n, i) =>
    peerX.set(n.node_id, peers.length === 1 ? 0 : (i / (peers.length - 1)) * (2 * HALF_W) - HALF_W),
  );
  const xFor = (n: RawNode): number =>
    n.kind === "peer" ? peerX.get(n.node_id)! : xOf(n.first_us);

  // Bucket by (floor, time-column); within a bucket, spread across z to de-overlap.
  // Real x is preserved — only z is synthesised, and only to stop nodes stacking.
  // This is what keeps it a diagram, not a physics blob.
  type Pre = { n: RawNode; kind: JaalKind; x: number; col: number };
  const pre: Pre[] = render.map((n) => {
    const kind = RENDER[n.kind];
    const x = xFor(n);
    const col = Math.round(((x + HALF_W) / (2 * HALF_W)) * (COLUMNS - 1));
    return { n, kind, x, col };
  });

  const buckets = new Map<string, Pre[]>();
  for (const p of pre) {
    const key = `${p.kind === "peer" ? "U" : "L"}:${p.col}`;
    (buckets.get(key) ?? buckets.set(key, []).get(key)!).push(p);
  }

  const byId = new Map<string, LaidNode>();
  const nodes: LaidNode[] = [];
  for (const group of buckets.values()) {
    group.sort((a, b) => cmpId(a.n.node_id, b.n.node_id));
    const n = group.length;
    group.forEach((p, i) => {
      // centred, evenly spaced lanes; a lone node sits at z = 0
      const z = n === 1 ? 0 : (i / (n - 1) - 0.5) * 2 * HALF_D;
      const pos: Vec3 = [p.x, floorY(p.kind), z];
      const node: LaidNode = {
        id: p.n.node_id,
        kind: p.kind,
        label: p.n.label,
        pos,
        firstUs: p.n.first_us,
      };
      byId.set(node.id, node);
      nodes.push(node);
    });
  }

  const edges: LaidEdge[] = [];
  const asnOf = new Map<string, string>();
  for (const e of rawEdges) {
    if (e.kind === "HOSTED_IN") {
      asnOf.set(e.src, e.dst); // peer → asn (network operator)
      continue;
    }
    const kind = EDGE[e.kind];
    if (!kind) continue; // MEMBER_OF / SAME_OWNER drive hulls, not lines
    const a = byId.get(e.src);
    const b = byId.get(e.dst);
    if (!a || !b) continue;
    edges.push({ kind, a: a.pos, b: b.pos, src: e.src, dst: e.dst, sats: e.sats, tsUs: e.ts_us });
  }

  return { nodes, byId, edges, asnOf };
}

// ── Clusters — "likely same owner", recomputed live from the confidence dial (§10.4).
// Union-find over SAME_OWNER edges whose confidence ≥ threshold. Raise the dial and
// weak links drop out → clusters split; lower it → they merge. Never a hard claim.
export type Hull = {
  id: string;
  members: string[];
  center: Vec3; // on the lower (money) floor
  rx: number; // ellipse radii covering the members, padded
  rz: number;
  count: number;
};

export function clustersAtThreshold(
  jaal: Jaal,
  sameOwner: RawEdge[],
  threshold: number,
): Hull[] {
  const parent = new Map<string, string>();
  const find = (x: string): string => {
    let r = x;
    while (parent.get(r) !== r) r = parent.get(r)!;
    for (let c = x; c !== r; ) {
      const next = parent.get(c)!;
      parent.set(c, r);
      c = next;
    }
    return r;
  };
  const add = (x: string) => {
    if (!parent.has(x)) parent.set(x, x);
  };
  for (const e of sameOwner) {
    if (e.confidence < threshold) continue;
    if (!jaal.byId.has(e.src) || !jaal.byId.has(e.dst)) continue;
    add(e.src);
    add(e.dst);
    parent.set(find(e.src), find(e.dst));
  }

  const groups = new Map<string, string[]>();
  for (const id of parent.keys()) {
    const root = find(id);
    (groups.get(root) ?? groups.set(root, []).get(root)!).push(id);
  }

  const PAD = 0.55;
  const hulls: Hull[] = [];
  for (const [root, members] of groups) {
    if (members.length < 2) continue; // a group of one is not a cluster
    const pts = members.map((m) => jaal.byId.get(m)!.pos);
    const xs = pts.map((p) => p[0]);
    const zs = pts.map((p) => p[2]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const cz = (Math.min(...zs) + Math.max(...zs)) / 2;
    hulls.push({
      id: root,
      members,
      center: [cx, -FLOOR_Y + 0.01, cz],
      rx: (Math.max(...xs) - Math.min(...xs)) / 2 + PAD,
      rz: (Math.max(...zs) - Math.min(...zs)) / 2 + PAD,
      count: members.length,
    });
  }
  return hulls.sort((a, b) => b.count - a.count);
}

// ── The runnable check (ponytail): the invariants that make this a diagram. If any
// break, the layout is wrong — throw loudly in dev rather than ship a hairball.
export function assertJaalInvariants(jaal: Jaal): void {
  for (const n of jaal.nodes) {
    const [x, y, z] = n.pos;
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z))
      throw new Error(`JAAL: non-finite position for ${n.id}`);
    if (Math.abs(x) > HALF_W + 1e-6) throw new Error(`JAAL: ${n.id} x out of bounds`);
    if (Math.abs(z) > HALF_D + 1e-6) throw new Error(`JAAL: ${n.id} z out of bounds`);
    const upper = n.kind === "peer";
    if (upper && y <= 0) throw new Error(`JAAL: peer ${n.id} not on upper floor`);
    if (!upper && y >= 0) throw new Error(`JAAL: money node ${n.id} not on lower floor`);
  }
  for (const e of jaal.edges) {
    const crosses = e.a[1] * e.b[1] < 0; // endpoints on opposite floors
    if (e.kind === "announce" && !crosses)
      throw new Error("JAAL: an announce edge does not cross floors");
    if (e.kind !== "announce" && crosses)
      throw new Error(`JAAL: a ${e.kind} edge crosses floors (only announce may)`);
  }
}
