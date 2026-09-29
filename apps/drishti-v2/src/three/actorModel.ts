// ACTOR — the map read at OWNER level (§10, the B3 `detail=actor` reading). Where the tx
// graph asks "where did the money go", this asks "which of these addresses are one person".
// Same discipline as graphModel: fixed math, never a force sim, so the same fixture lands on
// the same pixels every load.
//
//   X = time        earliest first_us on the left → latest on the right
//   Y = group size  how many addresses we can tie to this one owner
//   Z = de-overlap  deterministic lanes inside a time column — NOT a force sim
//
// THE CLAIM IS SPATIAL, NOT DRAWN. A same-owner claim used to be an arc across the frame,
// which at 95 arcs smeared into horizontal bands and read as noise. So addresses we claim are
// one owner are pulled to a shared point and ringed — a rosette — while every other address
// stays on the time field. You see the groups by their SHAPE, and nothing has to be read
// through a web of lines. (A rosette is a claim, never a proof: the ring's opacity is the
// claim's own confidence, and the drawer says so in words.)
//
// Two facts ride ON the mark: a CoinJoin'd address is greyed (a mix severs the link, so it is
// not evidence) and an address on a peel chain is coral (the money-trail shape). CoinJoin wins
// when an address is both — the disproof has to beat the clue.

import type { RawNode, RawEdge, Vec3 } from "./jaalLayout";
import type { GraphTick } from "./graphModel";

const XW = 5.0; // half-width of the time axis (matches the tx graph, so the two read alike)
const Y_BASE = 0.06;
const Y_TOP = 2.2;
const HALF_D = 1.5;
const COLUMNS = 26;
// A rosette: how far a claimed member sits from its group's centre, and the ring's radius.
// Tight on purpose — a ring that swallows eight other addresses overstates the claim, and
// at 84 claims the rings are the loudest ink on the floor. Just wide enough to hold the
// two or three marks it actually claims.
const ROSETTE_R = 0.16;
const RING_R = 0.25;

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const num = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) ? v : 0);

export type ActorNode = {
  id: string;
  label: string; // backend-truncated display form — the ONLY id we ever render
  groupLabel: string; // "owner group 4 · 29 addrs" — never the backend's word "cluster"
  groupSize: number;
  txs: number; // transactions this address appears in
  hops: number; // peel hops on a money trail (0 = not on one)
  chains: number; // distinct peel chains it sits on
  coinjoin: number; // >0 = passed through a mix → greyed
  claim: string | null; // the same-owner rosette it belongs to, if any
  firstUs: number | null;
  pos: Vec3;
  r: number;
};

/** One same-owner claim, drawn as a ring around the addresses we pulled together for it. */
export type Rosette = {
  id: string;
  members: string[];
  center: Vec3;
  radius: number;
  confidence: number; // the claim's own strength — the ring is drawn exactly this strong
  evidence: string[];
};

/** How much of the run this fixture actually holds — a sample is stated, never implied. */
export type ActorSample = {
  addresses: number;
  groups: number; // owner groups the sampled addresses resolve to
  totalAddresses: number;
  totalGroups: number;
};

export type Actor = {
  nodes: ActorNode[];
  rosettes: Rosette[];
  ticks: GraphTick[];
  count: number;
  peeled: number; // addresses on at least one peel chain
  mixed: number; // CoinJoin'd addresses
  both: number; // on a chain AND mixed — the case that must not be over-read
  claimed: number; // addresses inside a same-owner rosette
  tiers: number[]; // the distinct owner-group widths this run holds, ascending — the Y axis
  groupLo: number; // narrowest owner group sampled (the height axis' own floor)
  groupHi: number; // widest — a run with different groups moves the axis with it
  xw: number;
  yMax: number;
  sample: ActorSample;
};

type RawA = RawNode & { scores?: Record<string, unknown> };
type RawActorFixture = {
  nodes: RawA[];
  edges: RawEdge[];
  aggregated?: Record<string, unknown>;
};

/** "cluster:4 (29 addrs)" is backend vocabulary; on screen this is an owner group (§3). */
export function groupLabelOf(clusterId: string, size: number): string {
  const n = clusterId.replace(/^cluster:/, "");
  return `owner group ${n} · ${size} ${size === 1 ? "addr" : "addrs"}`;
}

export function buildActor(raw: RawActorFixture): Actor {
  const addr = raw.nodes.filter((n) => n.kind === "address");
  const clusterNode = new Map(
    raw.nodes.filter((n) => n.kind === "cluster").map((n) => [n.node_id, n]),
  );

  // MEMBER_OF: address → its owner group. The group's true width is the cluster NODE's own
  // degree — the sampled edge list only carries the sampled members, so counting member
  // edges here would report every group as smaller than it is.
  const groupOf = new Map<string, string>();
  for (const e of raw.edges) if (e.kind === "MEMBER_OF" && e.dst.startsWith("cluster:")) groupOf.set(e.src, e.dst);
  const sizeOf = (cid: string | undefined): number => {
    if (!cid) return 1;
    const c = clusterNode.get(cid);
    return c ? Math.max(1, num(c.scores?.degree)) : 1;
  };

  // The height axis is ORDINAL over the distinct group widths THIS run actually holds.
  // A log scale was tried and crushed the picture: widths run 10…187 but most sit in
  // 10…40, so on a log axis two thirds of the marks landed on the floor in one band.
  // Ranking the distinct widths instead gives every width its own row, and the axis then
  // says exactly what the run contains. Heights are labelled with the real widths below.
  const sizes = addr.map((n) => sizeOf(groupOf.get(n.node_id)));
  const tiers = [...new Set(sizes)].sort((a, b) => a - b);
  const gLo = tiers.length ? tiers[0] : 1;
  const gHi = tiers.length ? tiers[tiers.length - 1] : 1;
  const tierAt = new Map(tiers.map((s, i) => [s, i]));
  const yOf = (size: number) =>
    Y_BASE + (Y_TOP - Y_BASE) * (tiers.length > 1 ? (tierAt.get(size) ?? 0) / (tiers.length - 1) : 0);

  // SAME_OWNER components — a claim is a set of addresses we say are one owner. Members are
  // pulled to the component's shared point; everything else keeps its own time.
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
  const claimOf = new Map<string, string>(); // node id → component root
  const claims = new Map<string, RawEdge[]>();
  const known = new Set(addr.map((n) => n.node_id));
  const sameEdges = raw.edges.filter((e) => e.kind === "SAME_OWNER" && known.has(e.src) && known.has(e.dst));
  for (const e of sameEdges) {
    if (!parent.has(e.src)) parent.set(e.src, e.src);
    if (!parent.has(e.dst)) parent.set(e.dst, e.dst);
    parent.set(find(e.src), find(e.dst));
  }
  for (const id of parent.keys()) claimOf.set(id, find(id));
  for (const e of sameEdges) {
    const root = find(e.src);
    (claims.get(root) ?? claims.set(root, []).get(root)!).push(e);
  }

  // X = time, then a shared X/Y for the claimed
  const times = addr.map((n) => n.first_us).filter((t): t is number => t != null);
  const tMin = times.length ? Math.min(...times) : 0;
  const tMax = times.length ? Math.max(...times) : 1;
  const span = Math.max(1, tMax - tMin);
  const xOf = (t: number | null) => (t == null ? 0 : ((t - tMin) / span) * 2 * XW - XW);
  const colOf = (x: number) => Math.round(((x + XW) / (2 * XW)) * (COLUMNS - 1));

  type Placed = { n: RawA; x: number; y: number; z: number; root: string | null; i: number };
  const placed: Placed[] = [];
  const claimedRows = new Map<string, Placed[]>();

  for (const n of addr) {
    const size = sizeOf(groupOf.get(n.node_id));
    const root = claimOf.get(n.node_id) ?? null;
    // the rosette's centre is the mean of its members' own times and group widths — the
    // group is pulled to where it actually was, not to an arbitrary anchor
    const row: Placed = { n, x: xOf(n.first_us), y: yOf(size), z: 0, root, i: 0 };
    if (root) (claimedRows.get(root) ?? claimedRows.set(root, []).get(root)!).push(row);
    placed.push(row);
  }
  const rosettes: Rosette[] = [];
  for (const [root, rows] of claimedRows) {
    // keep the whole rosette inside the time frame — a group seen at the edge of the
    // window shifts inward by its own radius rather than spilling off the field
    const cx = Math.min(XW - ROSETTE_R, Math.max(-XW + ROSETTE_R, rows.reduce((s, r) => s + r.x, 0) / rows.length));
    const cy = rows.reduce((s, r) => s + r.y, 0) / rows.length;
    const radius = RING_R + rows.length * 0.02;
    rows.forEach((r, i) => {
      const a = (i / rows.length) * Math.PI * 2 + 0.7; // a fixed offset so pairs read level
      r.x = cx + Math.cos(a) * ROSETTE_R;
      r.z = Math.sin(a) * ROSETTE_R;
      r.y = cy;
      r.i = i;
    });
    const ev = claims.get(root) ?? [];
    rosettes.push({
      id: root,
      members: rows.map((r) => r.n.node_id),
      // the ring sits in the members' OWN plane (xz at their height) — a ring on the floor
      // under a group floating above it reads as two unrelated things
      center: [cx, cy, 0],
      radius,
      confidence: ev.length ? ev.reduce((s, e) => s + e.confidence, 0) / ev.length : 0,
      evidence: [...new Set(ev.map((e) => e.evidence))],
    });
  }

  // Z = de-overlap lanes inside each (time column, height) cell — deterministic order, and
  // only for addresses that are NOT already placed by a rosette
  const buckets = new Map<string, Placed[]>();
  for (const r of placed) {
    if (!r.root) {
      const key = `${colOf(r.x)}:${r.y.toFixed(3)}`;
      (buckets.get(key) ?? buckets.set(key, []).get(key)!).push(r);
    }
  }
  for (const group of buckets.values()) {
    group.sort((a, b) => (a.n.node_id < b.n.node_id ? -1 : a.n.node_id > b.n.node_id ? 1 : 0));
    group.forEach((r, i) => {
      r.z = group.length === 1 ? 0 : (i / (group.length - 1) - 0.5) * 2 * HALF_D;
    });
  }

  const nodes: ActorNode[] = placed.map((r) => {
    const cid = groupOf.get(r.n.node_id);
    const size = sizeOf(cid);
    const txs = num(r.n.scores?.n_transactions);
    const chains = Array.isArray(r.n.scores?.peel_chains) ? r.n.scores.peel_chains.length : 0;
    return {
      id: r.n.node_id,
      label: r.n.label,
      groupLabel: groupLabelOf(cid ?? "cluster:?", size),
      groupSize: size,
      txs,
      hops: num(r.n.scores?.n_peel_hops),
      chains,
      coinjoin: num(r.n.scores?.n_coinjoin),
      claim: r.root,
      firstUs: r.n.first_us ?? null,
      pos: [r.x, r.y, r.z],
      // busy addresses read heavier; the log keeps one 98-tx hub from dwarfing the field.
      // Kept small: 1,000 marks on one floor turn to mush if each one is a boulder.
      r: 0.04 + 0.075 * clamp01(Math.log10(1 + txs) / 2),
    };
  });

  const ticks: GraphTick[] = times.length
    ? [0, 1, 2, 3].map((k) => {
      const us = tMin + (span * k) / 3;
      return { x: xOf(us), us };
    })
    : [];

  const agg = raw.aggregated ?? {};
  return {
    nodes,
    rosettes,
    ticks,
    count: nodes.length,
    peeled: nodes.filter((n) => n.chains > 0).length,
    mixed: nodes.filter((n) => n.coinjoin > 0).length,
    both: nodes.filter((n) => n.chains > 0 && n.coinjoin > 0).length,
    claimed: nodes.filter((n) => n.claim != null).length,
    tiers,
    groupLo: gLo,
    groupHi: gHi,
    xw: XW,
    yMax: Y_TOP,
    sample: {
      addresses: nodes.length,
      groups: new Set(groupOf.values()).size,
      totalAddresses: num(agg.total_addresses),
      totalGroups: num(agg.total_clusters),
    },
  };
}

/** Four evenly-spaced rungs on the ordinal group-width axis, labelled with the run's own
 *  widths — so "higher = a wider owner group" is readable off the screen, not assumed. */
export function groupRungs(a: Actor): { y: number; label: string }[] {
  const n = a.tiers.length;
  const seen = new Set<number>();
  const out: { y: number; label: string }[] = [];
  for (let k = 0; k < 4; k++) {
    const i = n > 1 ? Math.round(((n - 1) * k) / 3) : 0;
    if (seen.has(i)) continue;
    seen.add(i);
    out.push({ y: Y_BASE + (Y_TOP - Y_BASE) * (n > 1 ? i / (n - 1) : 0), label: `${a.tiers[i] ?? 1}` });
  }
  return out;
}

/** The runnable check (ponytail): if the layout loses its grammar, fail loudly in dev rather
 *  than ship a field of marks that reads as noise. */
export function assertActorInvariants(a: Actor): void {
  for (const n of a.nodes) {
    const [x, y, z] = n.pos;
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z))
      throw new Error(`ACTOR: non-finite position for ${n.id}`);
    if (Math.abs(x) > XW + 1e-6) throw new Error(`ACTOR: ${n.id} x out of bounds`);
    if (Math.abs(z) > HALF_D + 1e-6) throw new Error(`ACTOR: ${n.id} z out of bounds`);
    if (y < Y_BASE - 1e-6 || y > Y_TOP + 1e-6) throw new Error(`ACTOR: ${n.id} y out of bounds`);
  }
  // a rosette must hold every one of its members, and hold them together — that IS the claim
  const byId = new Map(a.nodes.map((n) => [n.id, n]));
  const seen = new Set<string>();
  for (const r of a.rosettes) {
    if (r.members.length < 2) throw new Error(`ACTOR: rosette ${r.id} claims a single address`);
    for (const m of r.members) {
      const n = byId.get(m);
      if (!n) throw new Error(`ACTOR: rosette ${r.id} holds unknown ${m}`);
      if (seen.has(m)) throw new Error(`ACTOR: ${m} is in two claims`);
      seen.add(m);
      const d = Math.hypot(n.pos[0] - r.center[0], n.pos[2] - r.center[2]);
      if (d > r.radius) throw new Error(`ACTOR: ${m} sits outside rosette ${r.id} (${d} > ${r.radius})`);
    }
  }
  if (seen.size !== a.claimed) throw new Error("ACTOR: claimed count does not match the rosettes");
}
