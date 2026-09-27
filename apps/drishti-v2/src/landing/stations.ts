// The landing funnel, as data (§7). One source of truth for slices, the
// descending counter, and per-station copy — the director, counter, and copy
// blocks all read from here so M2b just extends STATIONS + regrows the spacer.
//
// Slices are the §7 fractions (hero+st.0–3 span 0.00–0.52 of the full 8-station
// page) rescaled by /0.52 so JAAL fills to the current page bottom with no dead
// scroll. // ponytail: drop the /0.52 rescale when st.4–7 land.

export type Slice = [start: number, end: number];

export type Station = {
  id: string;
  /** Layer name shown once, then the plain gloss is used (§3). */
  layer: string;
  gloss: string;
  /** Funnel counter value while this station holds. Canonical (§ "Canonical numbers"). */
  count: number;
  slice: Slice;
  /** DOM copy block — all §3 vocabulary, no kill-list words. */
  title: string;
  body: string;
  /** The diya's one calm line for this station (§2). */
  diya: string;
};

/** Raw §7 boundaries before rescale — kept for readability. */
const FULL_END = 0.52;
const s = (a: number, b: number): Slice => [a / FULL_END, b / FULL_END];

export const STATIONS: Station[] = [
  {
    id: "mayajaal",
    layer: "MAYAJAAL",
    gloss: "the world we built",
    count: 1_000_000,
    slice: s(0.0, 0.12),
    title: "A world we built to test this.",
    body:
      "Every signal here has a true origin we secretly know, so we can grade " +
      "ourselves honestly. No real dataset on earth has that answer key. " +
      "~4,000 nodes · realistic P2P gossip · Bitcoin Core's real relay timing. " +
      "One transaction, seen ~14 times — 93% of what you capture is echo.",
    diya: "This whole world is synthetic — and that's the point. Watch what we do with it.",
  },
  {
    id: "kavach",
    layer: "KAVACH",
    gloss: "the sealed intake",
    count: 999_847,
    slice: s(0.12, 0.24),
    title: "We seal the bytes before we read them.",
    body:
      "We hash the raw bytes BEFORE anything touches them, so a court can prove " +
      "this is exactly the file we received. Bad rows are set aside with a reason, " +
      "never quietly dropped.",
    diya: "Notice the hash is shown in full. That's the one identifier we never hide — the law requires it.",
  },
  {
    id: "setu",
    layer: "SETU",
    gloss: "network, untangled from money",
    count: 111_043,
    slice: s(0.24, 0.36),
    title: "We renamed one column. It defuses the whole trap.",
    body:
      "src_ip became “the IP that told us.” Now nobody downstream can " +
      "mistake a relay for a sender. One transaction ≈ 14 announcements — the " +
      "first IP you see is almost always an echo, not the source.",
    diya: "This rename is the whole trap, defused. Remember it — it comes back at the graph.",
  },
  {
    id: "jaal",
    layer: "JAAL",
    gloss: "the connection map",
    count: 24_626,
    slice: s(0.36, 0.52),
    title: "This edge is the entire project.",
    body:
      "IPs, wallets and transactions in one web. The pink lines are the only " +
      "place a public Bitcoin tool connects the IP that told us to the money it " +
      "moved. Addresses that likely share an owner glow together — but “likely” " +
      "is a number you can tune, never a claim we force.",
    diya: "Pink lines = “this IP told us about this money.” That link is why DRISHTI exists.",
  },
];

/** Origin of the funnel — the counter starts here before st.0 settles it. */
export const FUNNEL_START = 1_000_000;

const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const smoothstep = (x: number) => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};

/**
 * A station's local state at global scroll `p`.
 *  - `t`   linear 0→1 across the slice (drives choreo that runs the whole station)
 *  - `vis` 0→1→0 bell (opacity/scale): rises over the first `edge`, holds, dissolves
 *          over the last `edge` — "rises into focus, resolves, dissolves" (§7.0).
 */
export function local(p: number, [a, b]: Slice, edge = 0.22) {
  const span = b - a;
  const t = clamp01((p - a) / span);
  const vis = smoothstep(t / edge) * smoothstep((1 - t) / edge);
  return { t, vis };
}

/**
 * The funnel counter value at `p`: each station's number settles in as the
 * station arrives (odometer over the slice's first quarter), then holds.
 */
export function funnelValue(p: number): number {
  let prev = FUNNEL_START;
  for (const st of STATIONS) {
    const [a, b] = st.slice;
    const settleEnd = a + (b - a) * 0.25;
    if (p < a) return prev; // before this station: hold the previous number
    if (p < settleEnd) {
      const k = smoothstep((p - a) / (settleEnd - a));
      return Math.round(prev + (st.count - prev) * k);
    }
    if (p < b) return st.count; // holding inside the station
    prev = st.count;
  }
  return prev; // past the last station
}
