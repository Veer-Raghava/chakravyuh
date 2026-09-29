import { useEffect, useMemo, useRef, useState } from "react";
import { useScroll } from "../../scroll/ScrollContext";
import styles from "./Chakravyuh.module.css";

/**
 * ST.HERO — CHAKRAVYUH, the ringed formation (the whole metaphor, station zero).
 *
 * One bold even line on warm paper: an Archimedean spiral winding ~6 laps in to a
 * small centre hook, with a single mouth at the bottom, sealed by a thin latch.
 * "Easy to enter, near-impossible to exit" — the way out is right there and it does
 * not open. So the mouth is a real gap in the outer wall with a real latch across
 * it, not a decoration.
 *
 * The maze is a GRAPH and the dot is an AGENT, not a keyframe:
 *  - Cells are (corridor, sector). One cell along the spiral drops a hair of radius,
 *    so a single scalar `v` is both position and path. v↔v+1 is a corridor move; a
 *    DOOR (gap punched in the spiral wall) links v↔v+SECT; a SPOKE (radial wall
 *    grown across a corridor) blocks v→v+1.
 *  - The dot runs a real depth-first search with a visited set and a stale view of
 *    the walls, so its dead ends, pauses, reversals and flinches when a wall re-knits
 *    under it are all emergent. A few walls re-knit at a time; every closure is
 *    verified against "all cells still reach the mouth" and reverted if it would
 *    strand a region, so the maze is always solvable and the dot never cheats.
 *  - Past the settle point the sim freezes: state is snapshotted, a real BFS route
 *    locks in, and everything after that reads scroll position — scrub back and
 *    forth and it replays exactly.
 *
 * Painted as flat SVG in the DOM (§5.5) but split across two layers on purpose: the
 * walls are ONE path with a cached composited raster, and only the small live layer
 * (spokes, route, latch, comet, signal) repaints per frame. At 190 separate nodes
 * the dot's motion re-rasterised every wall — 15fps on a software renderer. The
 * walls keep the whole frame budget for the other eight stations.
 */
const TAU = Math.PI * 2;
const TURNS = 7; // walls drawn (turn 0 = the fixed outer silhouette)
const SECT = 24; // sectors per turn
const CORR = TURNS - 1; // corridors between the walls
const V = CORR * SECT; // cells in the graph

const R_OUT = 1; // outer turn radius, unit space
const PITCH = 0.128; // radial drop per lap
const WALL = 0.032; // the one bold line weight
const TH0 = Math.PI / 2; // u=0 points DOWN (svg +y) — the mouth is at the bottom
const GATE = 0.009; // mouth gap, half-width in u (a shade over one corridor of arc)
const DOOR_GAP = WALL * 3.3; // how much wall a door removes

const DOT_R = 0.026; // the signal
const TAIL = 14; // comet samples
const LEAD = 0.33; // how far ahead of the signal the locked thread is drawn
const SPEED = 0.00095; // units per ms — constant on the ground, not per cell

// ---- scroll choreography (fractions of the whole page) -----------------------
// The hero owns a complete story before anything else is allowed on screen:
// the walls settle, the route locks, the latch opens, the signal walks out,
// and the formation dissolves. Only then does MAYAJAAL begin to rise — the last
// wall clears at the same p the world's slice starts (P_FADE_B === HERO_END in
// landing/stations.ts), so the two never share the stage. Nothing else may
// overlap the escape: with two scenes going at once the eye leaves the dot,
// which is the one thing this beat is about.
//
// Each moving beat gets a wide window on purpose. Crunched together the escape
// reads as a flinch; spread, it reads as the signal deciding, waiting for the
// gate, and then committing.
const P_SETTLE_A = 0.008; // the churn starts dying here — almost at once, so the
// very first nudge of scroll visibly does something
const P_SETTLE_B = 0.04; // …and is dead here: snapshot + BFS
const P_ROUTE = 0.04; // the walk begins — the same instant the route locks, so
// there is no stretch where the maze has stopped living but nothing moves yet
const P_GATE = 0.068; // the latch gives way — the walk is done, and the signal
// holds at the mouth while the gate opens
const P_EXIT = 0.078; // the dot crosses the mouth
const P_GONE = 0.1; // …and is gone. The escape is complete here.
const P_FADE_A = 0.1; // walls begin to dissolve — only now, with the signal out
const P_FADE_B = 0.142; // …and are gone exactly as the world is fully here

const CHURN_GAP = 460; // ms between wall changes while the page sits still
const MAX_DOORS = 5;
const DOOR_FLOOR = 2; // keep a couple of openings standing, so the resolved maze
// still shows the way through rather than sealing back into a plain spiral
const MAX_SPOKES = 9;
const REVEAL_MS = 1600; // the line draws itself in, mouth → eye

const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
function smoothstep(a: number, b: number, x: number) {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
}

// ---- geometry: one scalar v is the whole position ---------------------------
const rOf = (v: number) => R_OUT - (v / SECT + 0.5) * PITCH;
const aOf = (v: number) => TH0 + ((v + 0.5) / SECT) * TAU;

const ARC_STEPS = 7;
function arcPath(m: number, u0: number, u1: number) {
  let d = "";
  for (let i = 0; i <= ARC_STEPS; i++) {
    const u = u0 + ((u1 - u0) * i) / ARC_STEPS;
    const r = R_OUT - (m + u) * PITCH;
    const th = TH0 + u * TAU;
    d += (i ? "L" : "M") + (r * Math.cos(th)).toFixed(5) + " " + (r * Math.sin(th)).toFixed(5);
  }
  return d;
}

type Geometry = {
  /** the whole spiral as ONE continuous path, mouth → eye */
  wallD: string;
  wallLen: number;
  /** arc length from the path start to the start of arc (m*SECT+s) */
  at: number[];
  /** the centre hook */
  eye: { d: string; len: number };
  /** radial wall geometry, indexed by the corridor edge v→v+1 it blocks */
  spokes: string[];
  bolt: string;
};

function buildGeometry(): Geometry {
  // The point list IS the path. `d` and the door cut positions are both derived
  // from this one array, so a gap cannot drift off the arc it belongs to.
  //
  // Measuring each arc separately and summing looked equivalent, and was not: the
  // mouth stops turn 0 a fraction short, so the seam joining it to turn 1 is a
  // real chord. The renderer counted it; the arithmetic did not. Five hundredths
  // of a unit — and the innermost arcs are only 0.04 long, so every door in the
  // last two laps landed a whole cell away from the passage it was meant to open.
  const pts: { x: number; y: number }[] = [];
  const arcStart: number[] = [];
  for (let m = 0; m < TURNS; m++) {
    for (let s = 0; s < SECT; s++) {
      // the one break in the figure: the mouth, centred on the bottom
      const u0 = m === 0 && s === 0 ? GATE : s / SECT;
      const u1 = m === 0 && s === SECT - 1 ? 1 - GATE : (s + 1) / SECT;
      for (let i = 0; i <= ARC_STEPS; i++) {
        const u = u0 + ((u1 - u0) * i) / ARC_STEPS;
        const r = R_OUT - (m + u) * PITCH;
        const th = TH0 + u * TAU;
        const x = r * Math.cos(th);
        const y = r * Math.sin(th);
        const last = pts[pts.length - 1];
        // arcs are contiguous: where one ends the next begins, so that point is
        // already in the list. Where it is NOT (the mouth seam) the join is a
        // real segment and must be counted.
        if (i === 0 && last && Math.abs(last.x - x) < 1e-9 && Math.abs(last.y - y) < 1e-9) {
          arcStart.push(pts.length - 1);
          continue;
        }
        if (i === 0) arcStart.push(pts.length);
        pts.push({ x, y });
      }
    }
  }

  const cum = [0];
  for (let i = 1; i < pts.length; i++) {
    cum.push(cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
  }
  const wallLen = cum[cum.length - 1];
  // where each arc begins, as a distance along the drawn path
  const at = arcStart.map((i) => cum[i]);

  let wallD = "";
  for (let i = 0; i < pts.length; i++) {
    wallD += (i ? "L" : "M") + pts[i].x.toFixed(5) + " " + pts[i].y.toFixed(5);
  }

  // the centre hook — the maze stops here
  const eyeR = (u: number) => R_OUT - TURNS * PITCH - u * PITCH * 0.44;
  let eyeD = "";
  let eyeLen = 0;
  let ex = 0;
  let ey = 0;
  for (let i = 0; i <= 26; i++) {
    const u = (1.6 * i) / 26;
    const r = eyeR(u);
    const th = TH0 + u * TAU;
    const x = r * Math.cos(th);
    const y = r * Math.sin(th);
    if (i) eyeLen += Math.hypot(x - ex, y - ey);
    eyeD += (i ? "L" : "M") + x.toFixed(5) + " " + y.toFixed(5);
    ex = x;
    ey = y;
  }

  // Radial wall geometry, indexed by the corridor edge v→v+1 it blocks — so it
  // is addressed by the SAME index as the bit that owns it. The spiral's seam
  // (s = SECT-1) has no crossing between two cells, so it keeps an empty slot.
  const spokes: string[] = new Array(V - 1).fill("");
  for (let v = 0; v < V - 1; v++) {
    if (v % SECT === SECT - 1) continue;
    const u = ((v % SECT) + 1) / SECT;
    const th = TH0 + u * TAU;
    const c1 = Math.cos(th);
    const s1 = Math.sin(th);
    const rOut = R_OUT - (Math.floor(v / SECT) + u) * PITCH;
    const rIn = rOut - PITCH;
    spokes[v] =
      `M${(rOut * c1).toFixed(5)} ${(rOut * s1).toFixed(5)}` +
      `L${(rIn * c1).toFixed(5)} ${(rIn * s1).toFixed(5)}`;
  }

  return { wallD, wallLen, at, eye: { d: eyeD, len: eyeLen }, spokes, bolt: arcPath(0, -GATE, GATE) };
}

// ---- graph helpers ----------------------------------------------------------
function nbrs(v: number, spoke: Uint8Array, door: Uint8Array, out: number[]) {
  out.length = 0;
  if (v > 0 && !spoke[v - 1]) out.push(v - 1);
  if (v < V - 1 && !spoke[v]) out.push(v + 1);
  if (v >= SECT && door[v - SECT]) out.push(v - SECT);
  if (v < V - SECT && door[v]) out.push(v + SECT);
  return out;
}

/** BFS from the mouth; null when a closure has stranded a region */
function reachAll(spoke: Uint8Array, door: Uint8Array) {
  const seen = new Uint8Array(V);
  const q = [0];
  seen[0] = 1;
  let n = 1;
  const buf: number[] = [];
  for (let h = 0; h < q.length; h++) {
    nbrs(q[h], spoke, door, buf);
    for (const w of buf) {
      if (!seen[w]) {
        seen[w] = 1;
        n++;
        q.push(w);
      }
    }
  }
  return n === V ? seen : null;
}

/** the one viable route from `from` out to the mouth cell 0 */
function route(from: number, spoke: Uint8Array, door: Uint8Array) {
  const prev = new Int32Array(V).fill(-1);
  const seen = new Uint8Array(V);
  const q = [from];
  seen[from] = 1;
  const buf: number[] = [];
  for (let h = 0; h < q.length; h++) {
    const v = q[h];
    if (v === 0) break;
    nbrs(v, spoke, door, buf);
    for (const w of buf) {
      if (!seen[w]) {
        seen[w] = 1;
        prev[w] = v;
        q.push(w);
      }
    }
  }
  const path: number[] = [];
  for (let cur = 0; cur !== -1; cur = prev[cur]) {
    path.push(cur);
    if (cur === from) break;
  }
  return path.reverse();
}

const SLOTS = MAX_SPOKES + 3; // live spoke DOM nodes; geometry assigned on demand

export function Chakravyuh({ reduced }: { reduced: boolean }) {
  const GEO = useMemo(buildGeometry, []);
  const { progress } = useScroll();

  const [vp, setVp] = useState(() => ({
    w: typeof window === "undefined" ? 1440 : window.innerWidth,
    h: typeof window === "undefined" ? 900 : window.innerHeight,
  }));
  useEffect(() => {
    const on = () => setVp({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);

  const narrow = vp.w < 1120;
  const rpx = narrow ? Math.min(vp.w * 0.4, vp.h * 0.26) : Math.min(vp.w * 0.26, vp.h * 0.37);
  const BOX = 1.46;
  const size = 2 * BOX * rpx;

  const wrapRef = useRef<HTMLDivElement>(null);
  const wallRef = useRef<SVGPathElement>(null);
  const spokeRef = useRef<(SVGPathElement | null)[]>([]);
  const cometRef = useRef<SVGPathElement>(null);
  const dotRef = useRef<SVGGElement>(null);
  const routeRef = useRef<SVGPathElement>(null);
  const boltRef = useRef<SVGPathElement>(null);
  const eyeRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    let seed = 42;
    const rand = () => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return seed / 0x7fffffff;
    };

    const S = {
      spoke: new Uint8Array(V),
      door: new Uint8Array(V),
      nSpoke: 0,
      nDoor: 0,
      doorRev: 0, // bumped on every door change — the wall dash only rebuilds then
      v: V - 1, // the dot starts at the centre hook
      vf: V - 1,
      target: -1,
      stack: [V - 1] as number[], // the route walked so far — DFS, so backtracking is real
      visited: new Uint8Array(V), // where it has already been
      moves: 0,
      blind: 0, // ms until it looks at the walls again
      timer: 900,
      dwell: 0,
      startle: 0,
      hop: 0,
      resolved: false,
      /** the locked route AS POINTS, in unit space, out through the mouth */
      pts: [] as { x: number; y: number }[],
      nCells: 0, // how many of those points are maze cells (the rest are the exit)
      vlen: [] as number[], // arc length at each point — the thread's ruler
      routeLen: 0,
      s: 0, // how far along the route the dot has committed, in units
      pos: null as { x: number; y: number } | null,
      tail: [] as { x: number; y: number }[],
      last: 0,
      mounted: 0,
      hidden: false, // once the hero is over the loop stops touching the DOM at all
      lastWall: "",
      lastDashRev: -1,
      lastDot: "",
      lastDotO: "",
      lastComet: "",
      lastRoute: "",
      lastGate: -1,
      lastFade: -1,
    };
    S.visited[V - 1] = 1; // it starts at the centre hook, so that cell is already done

    const slots = Array.from({ length: SLOTS }, () => ({ v: -1, k: 0 }));
    let raf = 0;
    let lastEye = "";

    // The dot does NOT get to see the maze. It plans on a stale copy of the walls
    // and only re-opens its eyes every so often — so when a wall re-knits under it
    // the plan breaks and it flinches. That surprise is the whole performance.
    const belief = { spoke: new Uint8Array(V), door: new Uint8Array(V) };
    const look = () => {
      belief.spoke.set(S.spoke);
      belief.door.set(S.door);
    };
    const edge = (a: number, b: number, spoke: Uint8Array, door: Uint8Array) => {
      const d = Math.abs(a - b);
      if (d === 1) return spoke[Math.min(a, b)] === 0;
      if (d === SECT) return door[Math.min(a, b)] === 1;
      return false;
    };
    const linked = (a: number, b: number) => edge(a, b, S.spoke, S.door);
    const believed = (a: number, b: number) => edge(a, b, belief.spoke, belief.door);
    /** a wall moved: let the dot reconsider that spot on its next pass */
    const forget = (a: number, b: number) => {
      S.visited[a] = 0;
      S.visited[b] = 0;
    };

    // position of the dot at fractional v — the whole motion model
    const px = (v: number) => {
      const r = rOf(v);
      const th = aOf(v);
      return { x: r * Math.cos(th), y: r * Math.sin(th) };
    };

    /**
     * An open door is a hole punched in the middle of its wall arc. Because the
     * spiral is one continuous path we can cut every door with a single dash
     * pattern — a closed run, a gap, the next closed run, and a trailing gap so
     * the pattern never repeats back over the walls.
     */
    const arcLenOf = (arc: number) =>
      (arc + 1 < GEO.at.length ? GEO.at[arc + 1] : GEO.wallLen) - GEO.at[arc];

    /**
     * An open door is a hole punched in the middle of its wall arc. Because the
     * spiral is one continuous path we can cut every door with a single dash
     * pattern — a closed run, a gap, the next closed run, and a trailing gap so
     * the pattern never repeats back over the walls. Rebuilt only when the door
     * set actually changes, never per frame.
     */
    const wallDash = () => {
      const cuts: number[] = [];
      for (let i = 0; i < V - SECT; i++) {
        if (!S.door[i]) continue;
        const arc = (Math.floor(i / SECT) + 1) * SECT + (i % SECT);
        cuts.push(GEO.at[arc] + (arcLenOf(arc) - DOOR_GAP) / 2);
      }
      if (!cuts.length) return `${GEO.wallLen}`;
      cuts.sort((a, b) => a - b);
      let out = "";
      let pos = 0;
      for (const c of cuts) {
        out += `${(c - pos).toFixed(4)} ${DOOR_GAP} `;
        pos = c + DOOR_GAP;
      }
      return out + `${(GEO.wallLen - pos).toFixed(4)} 1000`;
    };

    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      const wrap = wrapRef.current;
      if (!wrap) return;
      const dt = S.last ? Math.min(now - S.last, 64) : 16;
      S.last = now;
      if (!S.mounted) S.mounted = now;
      const p = progress.current ?? 0;
      const reveal = reduced ? 1 : clamp01((now - S.mounted) / REVEAL_MS);

      // Past the hero the walls are gone and this loop costs nothing at all —
      // the other eight stations get the whole frame budget back.
      const gone = p > P_FADE_B + 0.03;
      if (gone !== S.hidden) {
        S.hidden = gone;
        wrap.style.visibility = gone ? "hidden" : "visible";
      }
      if (gone) return;

      // ---------- entrance: the line draws itself in, mouth → eye ------------
      const wall = wallRef.current;
      if (wall) {
        const k = reduced ? 1 : smoothstep(0, 1, reveal);
        if (k < 1) {
          const key = k.toFixed(4);
          if (key !== S.lastWall) {
            S.lastWall = key;
            wall.style.strokeDasharray = `${GEO.wallLen}`;
            wall.style.strokeDashoffset = `${GEO.wallLen * (1 - k)}`;
          }
        } else if (S.doorRev !== S.lastDashRev) {
          S.lastDashRev = S.doorRev;
          wall.style.strokeDasharray = wallDash();
          wall.style.strokeDashoffset = "0";
        }
      }
      if (eyeRef.current) {
        const k = reduced ? 1 : clamp01((reveal - 0.8) / 0.24);
        const key = k.toFixed(4);
        if (key !== lastEye) {
          lastEye = key;
          eyeRef.current.style.strokeDasharray = `${GEO.eye.len}`;
          eyeRef.current.style.strokeDashoffset = `${GEO.eye.len * (1 - k)}`;
        }
      }

      // ---------- churn: a few walls re-knit while the page sits still ------
      const alive = reduced ? 0 : 1 - smoothstep(P_SETTLE_A, P_SETTLE_B, p);
      if (!S.resolved) {
        if (alive <= 0.001) {
          S.resolved = true;
          // The route is locked — and it ends outside the maze, not at the last
          // cell: the way out is part of the path, so the dot's escape is the same
          // motion continued rather than a separate animation.
          const cells = route(Math.round(S.vf), S.spoke, S.door);
          // It starts from where the dot actually IS, not from the centre of the
          // nearest cell. Snapping to the centre was a visible jump the frame the
          // walk took over — the dot had been mid-corridor — and the comet drew a
          // chord across it. Prepending the live position costs one extra vertex.
          S.pts = [S.pos ?? px(S.vf), ...cells.map(px)];
          S.nCells = S.pts.length;
          S.pts.push({ x: Math.cos(TH0) * (R_OUT - 0.02), y: Math.sin(TH0) * (R_OUT - 0.02) });
          S.pts.push({ x: Math.cos(TH0) * (R_OUT + 0.24), y: Math.sin(TH0) * (R_OUT + 0.24) });
          S.vlen = [0];
          for (let i = 1; i < S.pts.length; i++) {
            const a = S.pts[i - 1];
            const b = S.pts[i];
            S.vlen.push(S.vlen[i - 1] + Math.hypot(b.x - a.x, b.y - a.y));
          }
          S.routeLen = S.vlen[S.vlen.length - 1];
        } else if (reveal > 0.98) {
          S.timer -= dt * alive;
          if (S.timer <= 0) {
            S.timer = CHURN_GAP * (0.7 + rand() * 0.8);
            const doorIdx = Math.floor(rand() * (V - SECT));
            const spokeIdx = Math.floor(rand() * (V - 1));
            const closing = rand() < 0.45 && S.nSpoke + S.nDoor > 1;
            if (closing && rand() < 0.5 && S.nSpoke < MAX_SPOKES) {
              // a wall may strand a region — apply, verify, revert if it does
              if (S.spoke[spokeIdx] === 0 && spokeIdx % SECT !== SECT - 1) {
                S.spoke[spokeIdx] = 1;
                if (reachAll(S.spoke, S.door)) {
                  S.nSpoke++;
                  forget(spokeIdx, spokeIdx + 1);
                } else S.spoke[spokeIdx] = 0;
              }
            } else if (closing && S.nDoor > DOOR_FLOOR) {
              // close an OPEN door, chosen from the open ones — picking a random
              // index instead would almost always miss, and doors would only ever
              // accumulate: five standing gaps and then nothing left to re-knit.
              let want = Math.floor(rand() * S.nDoor);
              let at = -1;
              for (let i = 0; i < V - SECT; i++) {
                if (S.door[i] && want-- === 0) {
                  at = i;
                  break;
                }
              }
              if (at >= 0) {
                S.door[at] = 0;
                if (reachAll(S.spoke, S.door)) {
                  S.nDoor--;
                  S.doorRev++;
                  forget(at, at + SECT);
                } else S.door[at] = 1;
              }
            } else if (S.nDoor < MAX_DOORS && rand() < 0.6) {
              if (S.door[doorIdx] === 0) {
                S.door[doorIdx] = 1;
                S.nDoor++;
                S.doorRev++;
                forget(doorIdx, doorIdx + SECT);
              }
            } else {
              const at = S.spoke.findIndex((x) => x === 1);
              if (at >= 0) {
                S.spoke[at] = 0;
                S.nSpoke--;
                forget(at, at + 1);
              }
            }
          }
        }
      }

      // ---------- spokes grow and retract ----------------------------------
      // Spokes live in the live layer, not with the walls: a wall growing across a
      // corridor is a per-frame animation, and it must not re-rasterise the maze.
      const held = new Set<number>();
      for (const sl of slots) if (sl.v >= 0) held.add(sl.v);
      for (const sl of slots) {
        if (sl.v >= 0 && S.spoke[sl.v] === 0) {
          held.delete(sl.v);
          sl.v = -1; // retract in place: k decays, so it still animates out
        }
      }
      for (let i = 0; i < SLOTS; i++) {
        const node = spokeRef.current[i];
        if (!node) continue;
        const sl = slots[i];
        if (sl.v < 0 && sl.k < 0.05) {
          // hand this settled-free slot the first standing spoke nobody holds
          let at = -1;
          for (let v = 0; v < V - 1; v++) {
            if (S.spoke[v] === 1 && !held.has(v)) {
              at = v;
              break;
            }
          }
          if (at >= 0) {
            held.add(at);
            sl.v = at;
            node.setAttribute("d", GEO.spokes[at]);
          }
        }
        const want = sl.v >= 0 ? 1 : 0;
        if (Math.abs(want - sl.k) > 0.002) {
          sl.k += (want - sl.k) * Math.min(1, dt / 300);
          node.style.strokeDasharray = `${PITCH}`;
          node.style.strokeDashoffset = `${PITCH * (1 - sl.k)}`;
          node.style.opacity = `${clamp01(sl.k * 4) * 0.92}`;
        }
      }

      // ---------- the dot: an agent probing for the way out -----------------
      if (reduced) {
        S.vf = V - 1;
        S.pos = px(V - 1);
      } else if (S.resolved) {
        // Scroll-driven and deterministic: the dot commits to the locked route and
        // walks it out. Index space, not length space, so it lands exactly on the
        // drawn polyline — the thread and the dot then agree by construction.
        //
        // The walk is LINEAR in p. An eased curve put the dot's peak speed in the
        // middle of the traverse, so it crawled, then lunged, then crawled — read
        // as the animation running at its own tempo instead of being scrubbed by
        // the scroll. Linear means one wheel notch is always the same distance.
        const last = S.pts.length - 1;
        const walk = clamp01((p - P_ROUTE) / (P_GATE - P_ROUTE));
        const out = smoothstep(P_EXIT, P_GONE, p);
        const idx = Math.min(last, walk * (S.nCells - 1) + out * 2);
        const i0 = Math.floor(idx);
        const i1 = Math.min(last, i0 + 1);
        const f = idx - i0;
        const a = S.pts[i0];
        const b = S.pts[i1];
        S.pos = { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
        S.s = S.vlen[i0] + (S.vlen[i1] - S.vlen[i0]) * f;
        S.hop = out * (1 - out) * 1.2; // the leap as it clears the mouth
      } else if (reveal > 0.98) {
        S.blind -= dt;
        if (S.blind <= 0) {
          look(); // it opens its eyes again — and the maze may have moved
          S.blind = 1400;
        }
        if (S.dwell > 0) {
          S.dwell -= dt; // a held beat — the thinking
        } else if (S.target >= 0) {
          if (!linked(S.v, S.target)) {
            // a wall re-knit onto the plan: flinch, look again, choose anew
            S.target = -1;
            S.dwell = 320;
            S.startle = 1;
            look();
          } else {
            const dv = S.target - S.vf;
            const a = px(S.vf);
            const b = px(S.target);
            const dist = Math.hypot(b.x - a.x, b.y - a.y);
            const step = (dt * SPEED * Math.abs(dv)) / Math.max(dist, 1e-6);
            S.vf = Math.abs(dv) <= step ? S.target : S.vf + (dv > 0 ? step : -step);
            if (S.vf === S.target) {
              const arrived = S.target;
              S.target = -1;
              // backtracking re-arrives at the parent already on the stack
              if (S.stack.length > 1 && S.stack[S.stack.length - 2] === arrived) S.stack.pop();
              else S.stack.push(arrived);
              S.v = arrived;
              if (++S.moves > 3 * V) {
                // insurance: churn keeps editing the map under the search
                S.visited.fill(0);
                S.moves = 0;
              }
              if (arrived === 0) S.startle = 1; // at the mouth, and it will not open
            }
          }
        } else {
          const cell = S.v;
          // Depth-first over what it LAST saw: outward is the pull (the way out is
          // out), and a door is a real choice, so it scores a little higher.
          let best = -1;
          let bestScore = -Infinity;
          for (const w of [cell - 1, cell + 1, cell - SECT, cell + SECT]) {
            if (w < 0 || w >= V || S.visited[w] || !believed(cell, w)) continue;
            const score =
              (rOf(w) < rOf(cell) ? 1 : 0) +
              (Math.abs(w - cell) === SECT ? 0.3 : 0) +
              rand() * 0.15;
            if (score > bestScore) {
              bestScore = score;
              best = w;
            }
          }
          if (best >= 0) {
            S.visited[best] = 1;
            S.target = best;
            const from = S.stack.length > 1 ? S.stack[S.stack.length - 2] : cell;
            const turn = Math.sign(best - cell) !== Math.sign(cell - from);
            S.dwell = turn || Math.abs(best - cell) === SECT ? 110 + rand() * 130 : 0;
          } else if (S.stack.length > 1) {
            // dead end: pause, then reverse and walk back the way it came
            S.target = S.stack[S.stack.length - 2];
            S.dwell = 230 + rand() * 130;
            S.startle = Math.max(S.startle, 0.5);
          } else {
            // it has seen the whole maze and found no way out — so it looks again
            S.visited.fill(0);
            S.visited[cell] = 1;
            S.moves = 0;
            look();
            S.dwell = 420;
          }
        }
        S.startle = Math.max(0, S.startle - dt / 300);
      }

      // ---------- paint: the comet, the signal, the route, the latch --------
      // Every write is guarded: at rest this touches nothing, so the maze never
      // re-rasterises for a frame in which nothing actually changed.
      const pos = S.pos ?? px(S.vf);
      const head = S.tail[0];
      const gap = head ? Math.hypot(pos.x - head.x, pos.y - head.y) : 0;
      // A jump that size is a seek (a flung scroll, a nav bead), not a walk. Drop
      // the comet instead of drawing a chord straight across the rings.
      if (gap > 0.06) {
        S.tail.length = 0;
        if (cometRef.current && S.lastComet !== "") {
          S.lastComet = "";
          cometRef.current.setAttribute("d", "");
        }
      }
      const moved = !head || gap > 0.0035;
      if (moved) {
        S.tail.unshift(pos);
        if (S.tail.length > TAIL) S.tail.pop();
      }

      if (dotRef.current) {
        const bob = 1 + S.hop * 0.6 + S.startle * 0.3;
        const tf = `translate(${pos.x.toFixed(4)} ${pos.y.toFixed(4)}) scale(${bob.toFixed(3)})`;
        if (tf !== S.lastDot) {
          S.lastDot = tf;
          dotRef.current.setAttribute("transform", tf);
        }
        const ex = reduced ? 0 : clamp01((p - P_EXIT) / (P_GONE - P_EXIT));
        const o = `${1 - clamp01((ex - 0.6) / 0.4)}`;
        if (o !== S.lastDotO) {
          S.lastDotO = o;
          dotRef.current.style.opacity = o;
        }
      }

      // the comet: one tapered ribbon, so a moving dot costs one write not sixty
      if (moved && cometRef.current && S.tail.length > 1) {
        const n = S.tail.length;
        let d = "";
        const back: number[] = [];
        for (let i = 0; i < n; i++) {
          const c = S.tail[i];
          const b = S.tail[Math.max(i - 1, 0)];
          const f = S.tail[Math.min(i + 1, n - 1)];
          let dx = f.x - b.x;
          let dy = f.y - b.y;
          const m = Math.hypot(dx, dy) || 1;
          dx /= m;
          dy /= m;
          const w = DOT_R * 0.8 * (1 - i / n);
          d += (i ? "L" : "M") + (c.x - dy * w).toFixed(4) + " " + (c.y + dx * w).toFixed(4);
          back.push(c.x + dy * w, c.y - dx * w);
        }
        for (let i = back.length - 2; i >= 0; i -= 2) {
          d += "L" + back[i].toFixed(4) + " " + back[i + 1].toFixed(4);
        }
        d += "Z";
        if (d !== S.lastComet) {
          S.lastComet = d;
          cometRef.current.setAttribute("d", d);
        }
      }

      // The thread ahead of the dot — not the whole route. Drawing all ninety-odd
      // cells at once just outlines the spiral in yellow; a short window sliding in
      // front of the signal says the same thing (the way is known now) and stays
      // quiet. One dash pattern: nothing, then the window, then nothing for ever.
      const rn = routeRef.current;
      if (rn && S.routeLen > 0) {
        if (rn.getAttribute("d") === null) {
          let d = "";
          for (let i = 0; i < S.pts.length; i++) {
            d += (i ? "L" : "M") + S.pts[i].x.toFixed(4) + " " + S.pts[i].y.toFixed(4);
          }
          rn.setAttribute("d", d);
        }
        // The thread drains with the signal: it only ever covers the path still
        // ahead, so as the dot leaves the last cell the window runs off the end
        // of the path by itself, and the fade kills the stub. The window stays
        // short even with motion off — the route IS the spiral, so drawing all
        // of it just outlines every ring in butter.
        const out = reduced ? 0 : smoothstep(P_EXIT, P_GONE, p);
        const key = `${S.s.toFixed(4)}|${out.toFixed(3)}`;
        if (key !== S.lastRoute) {
          S.lastRoute = key;
          rn.style.strokeDasharray = `0 ${S.s.toFixed(4)} ${LEAD} 100000`;
          rn.style.opacity = (0.9 * (1 - out)).toFixed(3);
        }
      }

      if (boltRef.current) {
        const k = reduced ? 1 : clamp01((p - P_GATE) / (P_EXIT - P_GATE));
        if (k !== S.lastGate) {
          S.lastGate = k;
          const g = GATE * (1 - k);
          boltRef.current.setAttribute("d", g > 0.0002 ? arcPath(0, -g, g) : "");
          boltRef.current.style.opacity = `${1 - k}`;
        }
      }

      // The dissolve rides the wrapper's own transform (a compositor move) rather
      // than a transform inside the SVG, which re-rastered every wall per frame.
      //
      // The curve is biased so the walls clear EARLY within the window. On a plain
      // crossfade the maze is still at half opacity at the moment the world is at
      // half, and two half-scenes on one screen read as a smear rather than as one
      // thing leaving and another arriving. Leading the fade spends a beat on bare
      // paper instead — which is the point: the formation is gone, then the world.
      const k = smoothstep(P_FADE_A, P_FADE_B, p);
      const fade = 1 - (1 - k) * (1 - k);
      if (fade !== S.lastFade) {
        S.lastFade = fade;
        wrap.style.opacity = `${1 - fade}`;
        const s = reduced ? 1 : 1 + fade * 0.2;
        wrap.style.transform = `translate(-50%, -50%) scale(${s.toFixed(4)})`;
      }
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [GEO, progress, reduced]);

  const anchor = narrow ? { left: "50%", top: "33%" } : { left: "73%", top: "46%" };
  const box = { width: size, height: size, ...anchor };

  return (
    <div className={styles.wrap} aria-hidden="true">
      <div ref={wrapRef} className={styles.bloom} style={box}>
        {/* the walls — one continuous line, on its own cached layer */}
        <svg className={`${styles.svg} ${styles.walls}`} viewBox={`${-BOX} ${-BOX} ${2 * BOX} ${2 * BOX}`}>
          <path
            ref={wallRef}
            d={GEO.wallD}
            fill="none"
            stroke="var(--ink)"
            strokeWidth={WALL}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            ref={eyeRef}
            d={GEO.eye.d}
            fill="none"
            stroke="var(--ink)"
            strokeWidth={WALL}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {/* everything that moves */}
        <svg className={styles.svg} viewBox={`${-BOX} ${-BOX} ${2 * BOX} ${2 * BOX}`}>
          <g fill="none" strokeLinecap="round" strokeLinejoin="round">
            {Array.from({ length: SLOTS }, (_, i) => (
              <path
                key={i}
                ref={(n) => {
                  spokeRef.current[i] = n;
                }}
                stroke="var(--ink)"
                strokeWidth={WALL * 0.86}
                opacity={0}
              />
            ))}
            {/* the locked route — a plotted thread, never a stripe */}
            <path ref={routeRef} stroke="var(--butter)" strokeWidth={WALL * 0.3} opacity={0} />
            {/* the latch across the mouth */}
            <path ref={boltRef} d={GEO.bolt} stroke="var(--ink-soft)" strokeWidth={WALL * 0.5} />
            {/* the comet — a signal that has been somewhere */}
            <path ref={cometRef} fill="var(--coral)" opacity={0.32} d="" />
            <g ref={dotRef}>
              <circle r={DOT_R * 2.5} fill="var(--coral)" opacity={0.14} />
              <circle r={DOT_R * 1.65} fill="var(--coral)" opacity={0.3} />
              <circle r={DOT_R} fill="var(--coral)" />
            </g>
          </g>
        </svg>
      </div>
    </div>
  );
}
