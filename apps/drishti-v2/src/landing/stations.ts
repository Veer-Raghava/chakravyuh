// The landing funnel, as data (§7). One source of truth for slices, the
// descending counter, and per-station copy — the director, counter, and copy
// blocks all read from here.
//
// Slices are the raw §7 fractions: all eight stations now span the full page
// (0.00–1.00), so each owns its literal scroll range with no rescale.
//
// Funnel counts + the SHASTRA ceiling are read from the world.json fixture
// (FRONTEND-HANDOFF-V2 §1), the same source WorldScreen + nav/stages.ts use —
// no number is hand-typed. Copy and slices stay here.

import { fixtures } from "../data/loader";

/** Canonical funnel count for a layer, from world.json. */
const layerCount = (layer: string): number =>
  fixtures.world.funnel.find((s) => s.layer === layer)?.count ?? 0;

/** Recoverable ceilings, per grain, straight from world.json (FRONTEND-HANDOFF-V2 §1). */
const L1_CEIL = fixtures.world.ceilings?.l1_asn ?? null;
/** What the run actually scored at operator level — the hero number. */
const L1_TOP1 = fixtures.world.headline.l1_top1;
/** Our accuracy as a share of the most any estimator could score at the same grain. */
const CAPTURED_PCT =
  L1_CEIL && L1_CEIL > 0 ? ((L1_TOP1 / L1_CEIL) * 100).toFixed(0) : null;
const L1_TOP1_PCT = (L1_TOP1 * 100).toFixed(1);

// Slices are laid out in ONE contiguous chain: slice i ends exactly where slice
// i+1 begins, and that single shared instant is the only place two stations meet.
// Each scene has fully cleared before the next one starts to arrive, so exactly
// one is ever on screen. Nothing on this page runs two scenes at once.

export type Slice = [start: number, end: number];

/**
 * Hand-over width, in page fraction: the beat of scroll over which a station
 * arrives (from its slice start) or leaves (into its slice end).
 *
 * The slices themselves do NOT overlap, and that is the point. Two 3D scenes
 * drawn into one canvas at the same time do not cross-fade, they INTERPENETRATE:
 * MAYAJAAL's globe and KAVACH's blocks occupy the same screen space, so at half
 * opacity you see one ghost standing inside the other — two half-scenes on one
 * screen read as a smear, and worse, as two scenes fighting for the eye. The
 * outgoing scene has to be *gone* before the incoming one begins.
 *
 * So the chain is serial: station i is at zero exactly when station i+1 leaves
 * zero. What the eye gets at each boundary is a clean cut — a beat of bare paper
 * — rather than a dissolve, which is also what §7.0 asks for ("rises into focus,
 * resolves, dissolves" — they are three separate states, never two at once).
 *
 * The ramps are deliberately short relative to the slices, so the beat where
 * nothing is on stage is about one wheel notch. Long enough to read as intended,
 * short enough that it never reads as the page stalling.
 */
export const RAMP = 0.022;

/**
 * The p at which the hero has completely dissolved (the hero's own P_FADE_B),
 * and the start of station 0. The maze is gone before the world begins to rise,
 * on the same serial rule as every other boundary on the page.
 */
export const HERO_END = 0.142;

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

export const STATIONS: Station[] = [
  {
    id: "mayajaal",
    layer: "MAYAJAAL",
    gloss: "the world we built",
    count: layerCount("MAYAJAAL"),
    // Station zero is the CHAKRAVYUH hero (Hero/Chakravyuh.tsx). It owns the
    // opening beat: the walk, the gate, and the escape all finish, and the walls
    // fully dissolve, before this slice starts — so the world rises into a stage
    // the signal has already left. The counter holds the run's first count across
    // the whole hero, then counts down.
    slice: [0.142, 0.247],
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
    count: layerCount("KAVACH"),
    slice: [0.247, 0.352],
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
    count: layerCount("SETU"),
    slice: [0.352, 0.457],
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
    count: layerCount("JAAL"),
    slice: [0.457, 0.5805],
    title: "This edge is the entire project.",
    body:
      "IPs, wallets and transactions in one web. The pink lines are the only " +
      "place a public Bitcoin tool connects the IP that told us to the money it " +
      "moved. Addresses that likely share an owner glow together — but “likely” " +
      "is a number you can tune, never a claim we force.",
    diya: "Pink lines = “this IP told us about this money.” That link is why DRISHTI exists.",
  },
  {
    id: "shastra",
    layer: "SHASTRA",
    gloss: "who sent it — or honestly, we don't know",
    count: layerCount("SHASTRA"),
    slice: [0.5805, 0.698],
    title: `We name the sender's network for ${L1_TOP1_PCT}% of these.`,
    body:
      "That is " +
      (CAPTURED_PCT ? `${CAPTURED_PCT}% of what physics allows. ` : "") +
      "For each transaction we estimate how likely every candidate IP is to be " +
      "the true origin — and abstain when the evidence can't carry any answer. " +
      "You get a name when the math earns one, a shortlist when it's unsure, and " +
      "an honest “no answer” when the sender never showed up in the capture. A " +
      "confident wrong name destroys an investigation; we refuse to give you one.",
    diya: "The grey cards aren't failures. Knowing when to stay silent is the whole skill.",
  },
  {
    id: "buddhi",
    layer: "BUDDHI",
    gloss: "how risky is this",
    count: layerCount("BUDDHI"),
    slice: [0.698, 0.7924],
    title: "Every flag arrives with the reasons it might be wrong.",
    body:
      "We weigh each wallet for risk and show the handful of factors that raised " +
      "the score — in plain words, not a model report. Beside every “why flagged” " +
      "sits a muted “why it might be innocent,” shown at the same moment. The same " +
      "pattern that looks like laundering also fits a merchant settling daily.",
    diya: "An honest tool shows the exculpatory evidence at the same moment as the damning — not in cross-examination.",
  },
  {
    id: "vaani",
    layer: "VAANI",
    gloss: "the plain-English lead",
    count: layerCount("VAANI"),
    slice: [0.7924, 0.8847],
    title: "A score means nothing to an officer. A sentence does.",
    body:
      "The risk number unfolds into a ranked, plain-English lead that carries its " +
      "own evidence and its own doubts — what happened, the network detail, why " +
      "it's flagged, and where the origin abstained. Twenty leads, ranked. Not a " +
      "thousand maybes.",
    diya: "Twenty leads, ranked. Not a thousand maybes. Triage is a race against hours.",
  },
  {
    id: "pramaan",
    layer: "PRAMAAN",
    gloss: "the court-ready proof",
    count: layerCount("PRAMAAN"),
    slice: [0.8847, 1.0],
    title: "Not a guess. A document.",
    body:
      "One lead pressed into a signed file whose every pipeline stage is " +
      "hash-chained and re-runs to byte-identical output. We don't hand you a " +
      "wallet address — we hand you an IP, a source port and an exact timestamp: " +
      "the three values an ISP needs to name one subscriber, under BNSS 2023 §94.",
    diya: "This is the finish line: not a guess, a document. Ready when you are.",
  },
];

/** Origin of the funnel — the counter starts here before st.0 settles it. */
export const FUNNEL_START = fixtures.world.funnel[0].count;

const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const smoothstep = (x: number) => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};

/**
 * A station's local state at global scroll `p`.
 *  - `t`   linear 0→1 across the slice (drives choreo that runs the whole station)
 *  - `vis` 0→1→0: rises over `RAMP` from the slice start, holds, falls over `RAMP`
 *          into the slice end — "rises into focus, resolves, dissolves" (§7.0).
 *
 * The ramps are measured in absolute scroll (`RAMP`), NOT as a fraction of the
 * slice, so every station on the page arrives and leaves at the same rate no
 * matter how wide its slice is. A fraction would make the short slices snap and
 * the long ones crawl, and the page's tempo would change under the hand.
 */
export function local(p: number, [a, b]: Slice) {
  const t = clamp01((p - a) / (b - a));
  // The final station hands off to nothing, so it holds to the bottom of the
  // page. Letting it dissolve on the ordinary schedule emptied the stage exactly
  // at the scroll limit — the page ended on bare paper, which reads as stuck.
  const fall = b >= 1 ? 1 : smoothstep((b - p) / RAMP);
  const vis = Math.min(smoothstep((p - a) / RAMP), fall);
  return { t, vis };
}

/** The p at which a station owns the screen: its slice start — the single instant
 *  the outgoing station has gone and this one begins to arrive. The scenes, the
 *  copy and the funnel counter all switch on this one number. */
export const owns = (st: Station): number => st.slice[0];

/**
 * How long the copy takes to come or go.
 *
 * Wider than `RAMP`, so the text is still readable while its scene is at its
 * faintest and has only just cleared when the next scene is fully in. It does
 * NOT fill the cut itself — outgoing and incoming both reach zero at the same
 * instant the scenes do, so the boundary is one clean beat of paper, framed on
 * both sides by text rather than smeared across it.
 */
const COPY_SWITCH = 0.026;

/**
 * The COPY's opacity — deliberately NOT `local().vis`.
 *
 * Two blocks of text at half opacity is not a cross-fade, it is a double
 * exposure: the headings land on top of each other and neither can be read. So
 * the copy is serial too, on the same rule as the scenes: block i rises over the
 * `COPY_SWITCH` after its own slice start and falls over the `COPY_SWITCH`
 * before the next slice start. Those windows touch but never overlap, so there
 * is always exactly one readable block and never two.
 *
 * The two schedules line up by construction: the instant the copy is blank is
 * the instant the scenes are blank, which is the instant `owns()` flips the
 * counter. One cut, everything changes, at once.
 */
export function copyVis(p: number, i: number): number {
  const here = owns(STATIONS[i]);
  const next = i + 1 < STATIONS.length ? owns(STATIONS[i + 1]) : 1.05;
  const rise = smoothstep((p - here) / COPY_SWITCH);
  const fall = smoothstep((next - p) / COPY_SWITCH);
  return Math.min(rise, fall);
}

/**
 * The funnel counter value at `p`: each station's number settles in as the
 * station takes ownership (odometer over the first quarter of its run), then
 * holds until the next one takes over.
 */
export function funnelValue(p: number): number {
  let prev = FUNNEL_START;
  for (let i = 0; i < STATIONS.length; i++) {
    const st = STATIONS[i];
    const start = owns(st);
    const next = i + 1 < STATIONS.length ? owns(STATIONS[i + 1]) : 1;
    if (p < start) return prev; // not ours yet: hold the previous number
    if (p < next) {
      const settleEnd = start + (next - start) * 0.25;
      if (p < settleEnd) {
        const k = smoothstep((p - start) / (settleEnd - start));
        return Math.round(prev + (st.count - prev) * k);
      }
      return st.count;
    }
    prev = st.count;
  }
  return prev; // past the last station
}
