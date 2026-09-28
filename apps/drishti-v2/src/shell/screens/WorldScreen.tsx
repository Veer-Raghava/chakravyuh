import { useMemo, useState } from "react";
import { fixtures } from "../../data/loader";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import styles from "./WorldScreen.module.css";

/**
 * World · MAYAJAAL (§11.6 + §12.2) — the synthetic world we built so we can grade
 * ourselves honestly, and the signature honesty flex: the observer-fraction curve.
 * Every number here is DATA now (FRONTEND-HANDOFF-V2 §1): the funnel, the naive
 * first-seen baseline, the 11–60% literature band, the recoverable ceiling and the
 * whole observer-fraction sweep are read from the `world.json` fixture — nothing is
 * hand-typed. The curve is PLOTTED from `world.origin_curve.l0_host`, so when the
 * canonical agency run lands it swaps in with zero code change. Drag the handle
 * (native range = keyboard + offline).
 */
const world = fixtures.world;

// L0 host-level sweep — the plotted curve (x = observer fraction, y = top-1 accuracy).
const L0 = world.origin_curve.l0_host;
const F_MIN = L0[0].fraction; // domain from the fixture's own sweep
const F_MAX = L0[L0.length - 1].fraction;
const NAIVE = world.naive_first_seen_top1 * 100; // naive first-seen baseline (flat, for contrast)
const CEIL_PCT = (world.recoverable_ceiling * 100).toFixed(1); // the ceiling we own, e.g. "41.5"
const BAND_LO = (world.literature_band[0] * 100).toFixed(0); // documented accuracy band, low end
const BAND_HI = (world.literature_band[1] * 100).toFixed(0); // …high end
const CLUSTER = world.headline.cluster_confidence; // same-owner anchor, e.g. 0.36

/** L0 top-1 accuracy at an arbitrary observer fraction — linear interp over the sweep, clamped. */
const accAt = (f: number) => {
  if (f <= L0[0].fraction) return L0[0].top1;
  if (f >= L0[L0.length - 1].fraction) return L0[L0.length - 1].top1;
  for (let i = 0; i < L0.length - 1; i++) {
    const a = L0[i], b = L0[i + 1];
    if (f >= a.fraction && f <= b.fraction) {
      const t = (f - a.fraction) / (b.fraction - a.fraction);
      return a.top1 + t * (b.top1 - a.top1);
    }
  }
  return L0[L0.length - 1].top1;
};

// canonical funnel — one source (world.json), shared with nav/stages.ts + the landing.
const FUNNEL = world.funnel.map((s) => ({ n: s.count.toLocaleString("en-US"), label: s.label }));

const DEFENCES = [
  { k: `${CEIL_PCT}% ceiling`, v: "We tell you the fraction of transactions that even contain the answer — and never pretend the dark part is light." },
  { k: "the same-owner dial", v: `${CLUSTER} same-owner confidence is a good, published number — and a tunable dial, not a hidden constant.` },
  { k: "a shortlist, not a name", v: "Origin is a ranked shortlist inside a confidence shell, so a thin margin can't masquerade as certainty." },
  { k: "doubt beside every flag", v: "Every “why flagged” carries its counter-evidence at the same moment — the case against, shown next to the case for." },
];

const GLOSSARY = [
  ["MAYAJAAL", "the synthetic world we built to grade ourselves"],
  ["KAVACH", "sealed intake — hash the bytes before we read them"],
  ["SETU", "untangling the network from the money"],
  ["JAAL", "the connection map — wire above, money below"],
  ["SHASTRA", "the origin estimate — where a transaction started"],
  ["BUDDHI", "the risk model"],
  ["VAANI", "the plain-English lead"],
  ["PRAMAAN", "the court-ready proof"],
];

// SVG plot geometry
const W = 640;
const H = 260;
const PAD = { l: 44, r: 16, t: 18, b: 34 };
const px = (f: number) => PAD.l + ((f - F_MIN) / (F_MAX - F_MIN)) * (W - PAD.l - PAD.r);
const py = (a: number) => PAD.t + (1 - a / 65) * (H - PAD.t - PAD.b);

/** Smooth path through plotted points (quadratic joins at midpoints) — reads like a curve,
 *  stays within the data's hull so the sweep never overshoots the band. */
const smooth = (pts: { x: number; y: number }[]) => {
  if (pts.length < 2) return "";
  let d = `M ${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const mx = (pts[i].x + pts[i + 1].x) / 2;
    const my = (pts[i].y + pts[i + 1].y) / 2;
    d += ` Q ${pts[i].x.toFixed(1)} ${pts[i].y.toFixed(1)} ${mx.toFixed(1)} ${my.toFixed(1)}`;
  }
  const last = pts[pts.length - 1];
  return d + ` L ${last.x.toFixed(1)} ${last.y.toFixed(1)}`;
};

const DEFAULT_OBS = (world.observer_fraction * 100).toFixed(0); // agency default, e.g. "60"
const DEFAULT_ATTRIB = (accAt(world.observer_fraction) * 100).toFixed(1); // L0 top-1 there

export function WorldScreen() {
  usePrefersReducedMotion();
  const [f, setF] = useState(world.observer_fraction);
  const a = accAt(f) * 100;

  const curve = useMemo(
    () => smooth(L0.map((p) => ({ x: px(p.fraction), y: py(p.top1 * 100) }))),
    [],
  );

  const ticks = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7].filter((t) => t >= F_MIN && t <= F_MAX);

  return (
    <section className={styles.screen}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>World</h1>
          <span className={styles.tag}>MAYAJAAL · मायाजाल</span>
        </div>
        <p className={styles.gloss}>
          The synthetic world we built so we can grade ourselves honestly — every transaction has a
          known truth, so we can measure exactly how much we see, and how much stays dark.
        </p>
      </header>

      {/* ── the funnel ────────────────────────────────────── */}
      <div className={styles.funnel}>
        {FUNNEL.map((s, i) => (
          <div key={i} className={styles.fStep} style={{ opacity: 1 - i * 0.11 }}>
            <span className={styles.fNum}>{s.n}</span>
            <span className={styles.fLabel}>{s.label}</span>
          </div>
        ))}
      </div>

      {/* ── the observer-fraction curve (the flex) ────────── */}
      <div className={styles.curveBlock}>
        <div className={styles.curveHead}>
          <div>
            <span className={styles.curveTitle}>the observer-fraction curve</span>
            <p className={styles.curveGloss}>
              How much of the network we listen to sets how much we can attribute. Drag it.
            </p>
          </div>
          <div className={styles.readout}>
            <div><span className={styles.roVal}>{(f * 100).toFixed(0)}%</span><span className={styles.roKey}>observed</span></div>
            <div><span className={styles.roVal} style={{ color: "var(--coral)" }}>{a.toFixed(1)}%</span><span className={styles.roKey}>attributable</span></div>
          </div>
        </div>

        <svg className={styles.plot} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`At ${(f * 100).toFixed(0)}% observer fraction, ${a.toFixed(1)}% of transactions become attributable.`}>
          {/* grid + axes */}
          {[0, 20, 40, 60].map((g) => (
            <g key={g}>
              <line x1={PAD.l} y1={py(g)} x2={W - PAD.r} y2={py(g)} stroke="var(--line)" strokeWidth={1} />
              <text x={PAD.l - 8} y={py(g) + 3} textAnchor="end" className={styles.axis}>{g}%</text>
            </g>
          ))}
          {ticks.map((t) => (
            <text key={t} x={px(t)} y={H - 12} textAnchor="middle" className={styles.axis}>{(t * 100).toFixed(0)}%</text>
          ))}
          {/* naive baseline */}
          <line x1={PAD.l} y1={py(NAIVE)} x2={W - PAD.r} y2={py(NAIVE)} stroke="var(--ink-soft)" strokeWidth={1.5} strokeDasharray="4 4" />
          <text x={W - PAD.r} y={py(NAIVE) - 5} textAnchor="end" className={styles.baselineLabel}>naive first-seen · {NAIVE.toFixed(1)}%</text>
          {/* our curve */}
          <path d={curve} fill="none" stroke="var(--riso-blue)" strokeWidth={2.5} strokeLinecap="round" />
          {/* the handle */}
          <line x1={px(f)} y1={PAD.t} x2={px(f)} y2={H - PAD.b} stroke="var(--coral)" strokeWidth={1} strokeDasharray="3 3" opacity={0.6} />
          <circle cx={px(f)} cy={py(a)} r={6} fill="var(--coral)" stroke="var(--paper)" strokeWidth={2} />
        </svg>

        <input
          className={styles.range}
          type="range"
          min={F_MIN}
          max={F_MAX}
          step={0.01}
          value={f}
          onChange={(e) => setF(parseFloat(e.target.value))}
          aria-label="Observer fraction"
        />
        <p className={styles.curveNote}>
          At the agency default we run — <strong>{DEFAULT_OBS}%</strong> of the network observed —
          ~<strong>{DEFAULT_ATTRIB}%</strong> of transactions become attributable at host level; the
          ceiling we own across the full sweep is <strong>{CEIL_PCT}%</strong>. The literature spans
          a {BAND_LO}–{BAND_HI}% band; the dashed line is the naive first-seen guess we beat.
        </p>
      </div>

      {/* ── four defences ─────────────────────────────────── */}
      <div className={styles.defences}>
        {DEFENCES.map((d) => (
          <div key={d.k} className={styles.defence}>
            <span className={styles.defKey}>{d.k}</span>
            <p className={styles.defVal}>{d.v}</p>
          </div>
        ))}
      </div>

      {/* ── about / offline ───────────────────────────────── */}
      <div className={styles.about}>
        <div className={styles.aboutHead}>
          <span className={styles.aboutTitle}>the layers, in plain words</span>
          <span className={styles.offline}><span className={styles.dot} /> offline · binds 127.0.0.1 · no network</span>
        </div>
        <dl className={styles.glossary}>
          {GLOSSARY.map(([k, v]) => (
            <div key={k} className={styles.gRow}><dt>{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      </div>
    </section>
  );
}
