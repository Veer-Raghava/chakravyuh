import { useMemo, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { fixtures } from "../../data/loader";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import styles from "./WorldScreen.module.css";

/**
 * World · MAYAJAAL (§11.6 + §12.2) — the synthetic world we built so we can grade
 * ourselves honestly, and the signature honesty flex: the observer-fraction curve.
 * Every number here is DATA (FRONTEND-HANDOFF-V2 §1): the pipeline counts, the naive
 * first-seen baseline, the 11–60% literature band, the recoverable ceiling, the
 * held-out campaign recall and the elliptic replication F1 are all read from the
 * `world.json` fixture — nothing is hand-typed. The curve is PLOTTED from
 * `world.origin_curve.l0_host`, one point per measured rung, so another run's fixture
 * swaps in with zero code change. Drag the handle (native range = keyboard + offline).
 */
const world = fixtures.world;

/**
 * The train/test split, read from the fixture rather than asserted (§1.1): a run that ever split
 * differently must not be described as this one. Unknown protocols render as their raw string.
 */
const PROTOCOL_GLOSS: Record<string, string> = {
  inductive_time_ordered: "trained only on the past, tested on what came after",
};
const PROTOCOL = world.protocol
  ? { raw: world.protocol, gloss: PROTOCOL_GLOSS[world.protocol] ?? null }
  : null;

// The three measured sweeps, all from world.json: operator (the hero), exact host (the
// honest secondary) and the top-k shortlist. x = observer fraction, y = accuracy.
const L1 = world.origin_curve.l1_asn;
const L0 = world.origin_curve.l0_host;
const L3 = world.origin_curve.l3_shortlist;
const F_MIN = L1[0].fraction; // domain from the fixture's own sweep
const F_MAX = L1[L1.length - 1].fraction;
const NAIVE = world.naive_first_seen_top1 * 100; // naive first-seen baseline (flat, for contrast)
const BAND_LO = (world.literature_band[0] * 100).toFixed(0); // documented accuracy band, low end
const BAND_HI = (world.literature_band[1] * 100).toFixed(0); // …high end
// The measured same-owner pair precision over the addresses JAAL observed. It is NOT the
// full-cluster 0.36 the contract quotes — cluster_metrics.json says so in its own metric_note
// — so we name it for what it is and never call it "the dial".
const CLUSTER_PRECISION = world.headline.pair_precision;

/** A measured fraction as a whole-number percent, or null when not measured (null ≠ 0). */
const pct = (x: number | null, digits = 1): string | null =>
  x == null ? null : (x * 100).toFixed(digits);

// The honesty ceiling is measured at THIS run's observer fraction — it is not a constant, and a
// less-observed world honestly reports a lower one. null when the run has no ceiling measured.
const CEIL_PCT = pct(world.recoverable_ceiling);
// …and it is measured PER GRAIN. Dividing operator accuracy by the host ceiling (or by an
// accuracy) would flatter us either way; the gauge only ever divides like by like.
const L1_CEIL = world.ceilings?.l1_asn ?? null;
const L1_TOP1 = world.headline.l1_top1;
// Our operator accuracy as a share of the most any estimator could score at that grain.
const CAPTURED = L1_CEIL ? (L1_TOP1 / L1_CEIL) * 100 : null;
const LIFT = world.naive_first_seen_top1 ? L1_TOP1 / world.naive_first_seen_top1 : null;
const RECALL_PCT = pct(world.headline.campaign_recall);
const ELLIPTIC = pct(world.headline.elliptic_f1);
const ELLIPTIC_AUC = pct(world.headline.elliptic_roc_auc);

/** Top-1 accuracy at an arbitrary observer fraction — linear interp over a sweep, clamped. */
const accAt = (curve: { fraction: number; top1: number }[], f: number) => {
  if (f <= curve[0].fraction) return curve[0].top1;
  if (f >= curve[curve.length - 1].fraction) return curve[curve.length - 1].top1;
  for (let i = 0; i < curve.length - 1; i++) {
    const a = curve[i], b = curve[i + 1];
    if (f >= a.fraction && f <= b.fraction) {
      const t = (f - a.fraction) / (b.fraction - a.fraction);
      return a.top1 + t * (b.top1 - a.top1);
    }
  }
  return curve[curve.length - 1].top1;
};

// the pipeline — one source (world.json), shared with nav/stages.ts + the landing. It is NOT
// a shrinking funnel: it branches at BUDDHI, where one transaction leaves several owner groups,
// so a later count can honestly exceed an earlier one. The rows say so themselves.
const PIPELINE = world.funnel.map((s) => ({
  n: s.count.toLocaleString("en-US"),
  label: s.label,
  layer: s.layer,
}));

/**
 * The defence list. Each entry carries a number this run actually measured; an entry whose
 * measurement is absent is DROPPED, never printed as a zero — an external validation that did
 * not run and one that scored zero are opposite claims (§1). `world.defences` names the checks,
 * so the elliptic entry disappears when its leg did not run.
 */
const DEFENCES = [
  CEIL_PCT != null && {
    k: `${CEIL_PCT}% host ceiling`,
    v: "The share of transactions whose exact announcing host the capture even contains — measured at this run's observer fraction, and far below the operator ceiling, because most observers never heard the host at all. We print both rather than the flattering one.",
  },
  RECALL_PCT != null && {
    k: `${RECALL_PCT}% campaign recall`,
    v: "Held-out wallet recall: of the illicit campaigns in the test window, the share the risk model caught. Measured at actor level, separately from the transaction level.",
  },
  ELLIPTIC != null && {
    k: `${ELLIPTIC}% elliptic F1`,
    v: "The same method, run unchanged on an independent published dataset whose labels are not ours. It replicates there because the method travels, not because we tuned to it.",
  },
  CLUSTER_PRECISION != null && {
    k: "same-owner precision",
    v: `${CLUSTER_PRECISION.toFixed(3)} measured precision on same-owner address pairs we observed — held to our own metric note, and never dressed up as a different number.`,
  },
  {
    k: "a shortlist, not a name",
    v: "Origin is a ranked shortlist inside a confidence shell, so a thin margin can't masquerade as certainty.",
  },
  {
    k: "doubt beside every flag",
    v: "Every “why flagged” carries its counter-evidence at the same moment — the case against, shown next to the case for.",
  },
].filter((d): d is { k: string; v: string } => Boolean(d));

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
const DEFAULT_L1 = (accAt(L1, world.observer_fraction) * 100).toFixed(1); // operator top-1 there
const DEFAULT_L0 = (accAt(L0, world.observer_fraction) * 100).toFixed(1); // host top-1 there

export function WorldScreen() {
  const reduced = usePrefersReducedMotion();
  const [f, setF] = useState(world.observer_fraction);
  const l1 = accAt(L1, f) * 100;
  const l0 = accAt(L0, f) * 100;

  // The host and operator sweeps carry `top1`; the shortlist sweep carries `topk` under its
  // own k. One plotter, both shapes — the y value is whatever that sweep measured.
  const path = (curve: { fraction: number; top1?: number; topk?: number }[]) =>
    smooth(curve.map((p) => ({ x: px(p.fraction), y: py((p.top1 ?? p.topk ?? 0) * 100) })));
  const paths = useMemo(
    () => ({ l1: path(L1), l0: path(L0), l3: path(L3) }),
    [],
  );

  // The pipeline flows in: each count rolls up from zero as its row lands. Reduced motion
  // gets the settled numbers straight from the DOM (they are rendered there already).
  const funnelNums = useRef<(HTMLSpanElement | null)[]>([]);
  useGSAP(
    () => {
      if (reduced) return;
      gsap.from(`.${styles.fStep}`, { opacity: 0, y: 8, duration: 0.5, stagger: 0.07, ease: "power2.out" });
      world.funnel.forEach((s, i) => {
        const el = funnelNums.current[i];
        if (!el) return;
        const counter = { v: 0 };
        gsap.to(counter, {
          v: s.count,
          duration: 0.9,
          delay: i * 0.07,
          ease: "power2.out",
          onUpdate: () => { el.textContent = Math.round(counter.v).toLocaleString("en-US"); },
        });
      });
    },
    { dependencies: [reduced] },
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

      {/* ── the headline numbers ──────────────────────────── */}
      <div className={styles.headline}>
        <div className={styles.hCard}>
          <span className={styles.hVal}>{(L1_TOP1 * 100).toFixed(1)}%</span>
          <span className={styles.hKey}>operator named correctly</span>
          <p className={styles.hNote}>
            {CAPTURED != null && L1_CEIL != null && (
              <>
                <strong>{(CAPTURED).toFixed(0)}% of the theoretical maximum</strong> — the
                operator ceiling is {(L1_CEIL * 100).toFixed(1)}%
              </>
            )}
            {LIFT != null && <> · <strong>{LIFT.toFixed(2)}×</strong> the naive first-seen guess ({NAIVE.toFixed(1)}%)</>}.
          </p>
        </div>
        {RECALL_PCT != null && (
          <div className={styles.hCard}>
            <span className={styles.hVal}>{RECALL_PCT}%</span>
            <span className={styles.hKey}>campaign recall</span>
            <p className={styles.hNote}>
              We flag at least one transaction from {RECALL_PCT}% of the criminal campaigns in
              the held-out window. One thread is enough to pull the chain.
            </p>
          </div>
        )}
        {ELLIPTIC != null && (
          <div className={`${styles.hCard} ${styles.hCardReal}`}>
            <span className={styles.hVal}>{ELLIPTIC}%</span>
            <span className={styles.hKey}>F1 · tested on real data</span>
            <p className={styles.hNote}>
              Same model, real data — F1 {ELLIPTIC}%{ELLIPTIC_AUC != null && <> · ROC-AUC {ELLIPTIC_AUC}%</>} on the
              Elliptic dataset. Published, independently labelled, not ours.
            </p>
          </div>
        )}
      </div>

      {/* ── the pipeline ──────────────────────────────────── */}
      <div className={styles.funnel}>
        {PIPELINE.map((s, i) => (
          <div key={s.layer} className={styles.fStep} style={{ opacity: 1 - i * 0.07 }}>
            <span className={styles.fLayer}>{s.layer}</span>
            <span
              className={styles.fNum}
              ref={(el) => { funnelNums.current[i] = el; }}
            >
              {s.n}
            </span>
            <span className={styles.fLabel}>{s.label}</span>
          </div>
        ))}
      </div>
      <p className={styles.curveNote}>
        This is a pipeline, not a shrinking funnel — it <strong>branches at BUDDHI</strong>, where one
        transaction leaves several owner groups scored, so a later count can honestly exceed an earlier
        one. Every count is read from the artifact that proves the stage ran.
      </p>

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
            <div><span className={styles.roVal}>{l1.toFixed(1)}%</span><span className={styles.roKey}>operator named</span></div>
            <div><span className={styles.roVal} style={{ color: "var(--teal)" }}>{l0.toFixed(1)}%</span><span className={styles.roKey}>host named</span></div>
          </div>
        </div>

        <svg className={styles.plot} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`At ${(f * 100).toFixed(0)}% observer fraction, ${l1.toFixed(1)}% of transactions are attributable at operator level and ${l0.toFixed(1)}% at host level.`}>
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
          {/* the three granularities — operator is the hero, host the honest secondary */}
          <path d={paths.l3} fill="none" stroke="var(--butter)" strokeWidth={2} strokeLinecap="round" />
          <path d={paths.l0} fill="none" stroke="var(--teal)" strokeWidth={2} strokeLinecap="round" />
          <path d={paths.l1} fill="none" stroke="var(--riso-blue)" strokeWidth={2.5} strokeLinecap="round" />
          {/* the handle */}
          <line x1={px(f)} y1={PAD.t} x2={px(f)} y2={H - PAD.b} stroke="var(--coral)" strokeWidth={1} strokeDasharray="3 3" opacity={0.6} />
          <circle cx={px(f)} cy={py(l1)} r={6} fill="var(--coral)" stroke="var(--paper)" strokeWidth={2} />
        </svg>

        <div className={styles.legend}>
          <span className={styles.lgItem}><span className={styles.lgSw} style={{ background: "var(--riso-blue)" }} /> operator (ASN) — the hero</span>
          <span className={styles.lgItem}><span className={styles.lgSw} style={{ background: "var(--teal)" }} /> exact host — officer-only, and capped far lower</span>
          <span className={styles.lgItem}><span className={styles.lgSw} style={{ background: "var(--butter)" }} /> top-{L3[0].k} shortlist</span>
        </div>

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
          ~<strong>{DEFAULT_L1}%</strong> of transactions get their operator named and ~
          <strong>{DEFAULT_L0}%</strong> their exact host. Every point is a measured run, not a
          projection.
          {CEIL_PCT != null && (
            <>
              {" "}At this fraction the honesty ceiling — the share that even contains the answer — is{" "}
              <strong>{CEIL_PCT}%</strong> at host level and{" "}
              <strong>{L1_CEIL != null ? `${(L1_CEIL * 100).toFixed(1)}%` : "—"}</strong> at operator level;
              the rest is dark and we say so.
            </>
          )}{" "}
          The literature spans a {BAND_LO}–{BAND_HI}% band; the dashed line is the naive first-seen
          guess we beat.
        </p>
      </div>

      {/* ── the defences — every number this run actually measured ── */}
      <div className={styles.defenceBlock}>
        <div className={styles.aboutHead}>
          <span className={styles.aboutTitle}>
            the honesty checks · {world.run_id} · {world.observer_regime} regime ·{" "}
            {(world.observer_fraction * 100).toFixed(0)}% of the network observed
          </span>
          {PROTOCOL && (
            <span className={styles.aboutTitle}>
              {PROTOCOL.gloss ? `split: ${PROTOCOL.gloss}` : `split: ${PROTOCOL.raw}`}
            </span>
          )}
        </div>
        <p className={styles.curveNote}>
          This run's checks: {world.defences.join(" · ")}
          {ELLIPTIC == null &&
            " — the elliptic replication did not run for this run, so it is absent here rather than shown as a zero"}
          .
        </p>
        <div className={styles.defences}>
          {DEFENCES.map((d) => (
            <div key={d.k} className={styles.defence}>
              <span className={styles.defKey}>{d.k}</span>
              <p className={styles.defVal}>{d.v}</p>
            </div>
          ))}
        </div>
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
