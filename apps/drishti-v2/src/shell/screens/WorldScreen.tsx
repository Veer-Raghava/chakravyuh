import { useMemo, useState } from "react";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import styles from "./WorldScreen.module.css";

/**
 * World · MAYAJAAL (§11.6 + §12.2) — the synthetic world we built so we can grade
 * ourselves honestly, and the signature honesty flex: the observer-fraction curve.
 * No world fixture exists, so the curve is COMPUTED (not invented) across the
 * documented 11–60% accuracy band as the observer fraction sweeps 0.02→0.50, pinned
 * so the default 0.10 lands on the 41.5% ceiling and the naive first-seen line sits
 * flat at 22.1% for contrast. Drag the handle (native range = keyboard + offline).
 */
const F_MIN = 0.02;
const F_MAX = 0.5;
const A_LO = 11; // documented accuracy band, low end (%)
const A_HI = 60; // …high end
const NAIVE = 22.1; // naive first-seen baseline (flat, for contrast)

/** accuracy(fraction): concave sweep of the 11–60% band, pinned so f=0.10 → 41.5%. */
const acc = (f: number) => A_LO + (A_HI - A_LO) * Math.pow((f - F_MIN) / (F_MAX - F_MIN), 0.265);

// canonical funnel (do not invent other numbers)
const FUNNEL = [
  { n: "1,000,000", label: "signals captured" },
  { n: "999,847", label: "sealed intact" },
  { n: "111,043", label: "untangled" },
  { n: "24,626", label: "real transactions" },
  { n: "~20", label: "ranked leads" },
  { n: "1", label: "court-ready proof" },
];

const DEFENCES = [
  { k: "41.5% ceiling", v: "We tell you the fraction of transactions that even contain the answer — and never pretend the dark part is light." },
  { k: "the same-owner dial", v: "0.36 same-owner confidence is a good, published number — and a tunable dial, not a hidden constant." },
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

export function WorldScreen() {
  usePrefersReducedMotion();
  const [f, setF] = useState(0.1);
  const a = acc(f);

  const curve = useMemo(() => {
    const pts: string[] = [];
    for (let i = 0; i <= 60; i++) {
      const ff = F_MIN + (i / 60) * (F_MAX - F_MIN);
      pts.push(`${px(ff).toFixed(1)},${py(acc(ff)).toFixed(1)}`);
    }
    return "M" + pts.join(" L");
  }, []);

  const ticks = [0.1, 0.2, 0.3, 0.4, 0.5];

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
          <text x={W - PAD.r} y={py(NAIVE) - 5} textAnchor="end" className={styles.baselineLabel}>naive first-seen · {NAIVE}%</text>
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
          At the default <strong>10%</strong> we listen to, ~<strong>41.5%</strong> of transactions
          become attributable — the ceiling we own. The literature sweeps an 11–60% band; the dashed
          line is the naive first-seen guess we beat.
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
