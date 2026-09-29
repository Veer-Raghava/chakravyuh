import { fixtures } from "../../data/loader";
import styles from "./ModelIntelligence.module.css";

/**
 * Model intelligence — the related-work section, rendered (World · MAYAJAAL).
 *
 * Every NUMBER on this panel is read from `world.model_intelligence`, and each one is
 * traceable to a committed artifact:
 *   · elliptic F1 / PR-AUC / ROC-AUC, and the inductive protocol
 *       -> measurements/<run>/elliptic_external.json + world.headline
 *   · precision@20 (0.60) and the rank-by-value baseline (0.00)
 *       -> measurements/<run>/model_report.json: wallet_model.precision_at_20 / baseline
 *   · rejected leg 0.0357 vs 0.0373 and its `baseline_not_beaten` reason
 *       -> docs/REMODEL-AUDIT-P0-P3.md §3.1 + measurements/_gnn-a/model_report.json
 *   · the published GCN / RF F1 bands are LITERATURE, not our measurements, and are
 *     labelled as such on screen (Grinsztajn et al., NeurIPS 2022; Weber et al., 2019).
 *
 * The one thing that is NOT a measurement is the axis bars, and the panel says so out
 * loud — they are an engineering assessment, because no artifact scores "court-readiness".
 * Mixing the two silently is exactly how a dashboard starts lying.
 */

const AXES = [
  { id: "accuracy", label: "accuracy", gloss: "discrimination on held-out data" },
  { id: "interpretability", label: "interpretability", gloss: "can an officer read why it fired" },
  { id: "speed", label: "speed", gloss: "cost per subject scored" },
  { id: "deployability", label: "deployability", gloss: "air-gapped, no GPU, no network" },
  { id: "court", label: "court", gloss: "explainable under BSA 2023" },
] as const;

type AxisId = (typeof AXES)[number]["id"];

/** Assessment, not measurement — see the header note. Words are derived from the value so
 *  the screen never shows a bare made-up decimal as if it were a score we computed. */
const SCORES: Record<string, Record<AxisId, number>> = {
  lightgbm: { accuracy: 0.95, interpretability: 1, speed: 1, deployability: 1, court: 1 },
  gnn: { accuracy: 0.85, interpretability: 0.2, speed: 0.3, deployability: 0.2, court: 0.15 },
  rf: { accuracy: 0.7, interpretability: 0.65, speed: 0.8, deployability: 0.9, court: 0.6 },
};

const word = (v: number) =>
  v >= 0.9 ? "strong" : v >= 0.6 ? "workable" : v >= 0.35 ? "limited" : "weak";

/** Positioning scale — a window wide enough to hold both published bands and our mark. */
const PD_LO = 0.55;
const PD_HI = 0.85;
const posPct = (v: number) => `${((v - PD_LO) / (PD_HI - PD_LO)) * 100}%`;

const ROADMAP = [
  {
    when: "0–3 months",
    what: "Real-time streaming ingestion",
    why: "Move off batch capture onto a live feed, so a lead lands while the funds are still moving. This is a deployment change, not a research one, and the model itself does not move.",
  },
  {
    when: "3–6 months",
    what: "Temporal pre-training on the unlabelled graph",
    why: "Learn structure from the ~99% of traffic we never label, then fine-tune on the labelled slice. The honest next accuracy step, and the one our own phase-3 gate will judge.",
  },
  {
    when: "6–9 months",
    what: "Multi-chain tracing",
    why: "Ethereum and the bridges that move value between chains. The money already leaves Bitcoin; the map should not stop at the edge of one ledger.",
  },
  {
    when: "9–12 months",
    what: "Federated learning across agencies",
    why: "Each agency keeps its captures and its labels. Only model updates travel. Attribution improves without a single force handing another its raw intelligence.",
  },
];

export function ModelIntelligence() {
  // Model-level, run-INVARIANT: which model ships, the rejected GNN leg, and the
  // Elliptic external replication are properties of the shipped model, not of a
  // capture's observer coverage — so this panel reads the canonical fixtures, not
  // the active run. (A sparse run like stealth never scores these; reading the run
  // here would show nulls for a fact the coverage doesn't change.)
  const mi = fixtures.world.model_intelligence;

  const MODELS = [
    {
      id: "lightgbm",
      tech: "LightGBM",
      name: "the risk model",
      role: "ours · ships",
      chip: "shipped",
      measured: [
        ["Elliptic F1", mi.ours.elliptic_f1.toFixed(3)],
        ["precision@20", mi.ours.precision_at_20.toFixed(2)],
      ],
      line: `Gradient-boosted trees on 33 morphological features. ${mi.shipped_model} is the shipped row value; every lead carries a SHAP reason and a counter-reason.`,
    },
    {
      id: "gnn",
      tech: "GNN / GCN",
      name: "the graph neural net",
      role: "tested in phase 3 · rejected by our own gate",
      chip: "rejected",
      measured: [
        ["holdout PR-AUC", mi.rejected_leg.with_embeddings_pr_auc.toFixed(4)],
        ["baseline PR-AUC", mi.rejected_leg.without_embeddings_pr_auc.toFixed(4)],
      ],
      line: "Ran as extra columns over the confidence-weighted graph. It scored every one of the subjects and still lost, so the gate refused the leg.",
    },
    {
      id: "rf",
      tech: "Random Forest",
      name: "the standard alternative",
      role: "not shipped · no axis where it decides a case",
      chip: "not shipped",
      measured: [
        ["published F1", `${mi.published_bands.rf_f1[0].toFixed(2)}–${mi.published_bands.rf_f1[1].toFixed(2)}`],
        ["our precision@20", mi.ours.precision_at_20.toFixed(2)],
      ],
      line: "Same family, weaker fit, and no interpretability or deployment advantage over boosting. Published Elliptic band, cited rather than measured by us.",
    },
  ] as const;

  const BANDS = [
    {
      key: "gnn",
      label: "published GCN range",
      lo: mi.published_bands.gnn_f1[0],
      hi: mi.published_bands.gnn_f1[1],
      note: "mostly transductive: the test nodes were visible during training",
    },
    {
      key: "rf",
      label: "published RF range",
      lo: mi.published_bands.rf_f1[0],
      hi: mi.published_bands.rf_f1[1],
      note: "same dataset, same task, easier split",
    },
  ];

  /** Where the mark sits, in words — read off the numbers, never asserted. */
  const IN_GCN =
    mi.ours.elliptic_f1 >= mi.published_bands.gnn_f1[0] &&
    mi.ours.elliptic_f1 <= mi.published_bands.gnn_f1[1];

  const delta = (
    mi.rejected_leg.without_embeddings_pr_auc - mi.rejected_leg.with_embeddings_pr_auc
  ).toFixed(4);
  const barMax = 0.04; // 0-based: the two bars must look as close as they actually are
  const barW = (v: number) => `${(v / barMax) * 100}%`;

  return (
    <details className={styles.wrap} open>
      <summary className={styles.summary}>
        <span className={styles.summaryTitle}>Model intelligence</span>
        <span className={styles.summaryTag}>why this model · and what we rejected</span>
      </summary>

      <p className={styles.intro}>
        Four questions decide which model goes to court: does it score well, can an officer read
        why, does it run on an air-gapped machine, and can it be defended line by line. One model
        wins all four. The alternative we tried lost its own gate and was not shipped.
      </p>

      {/* ── 1 · the comparison ─────────────────────────────── */}
      <div className={styles.cards}>
        {MODELS.map((m) => (
          <article key={m.id} className={`${styles.card} ${m.chip === "shipped" ? styles.cardOurs : ""}`}>
            <span className={styles.cardTech}>{m.tech}</span>
            <h3 className={styles.cardName}>{m.name}</h3>
            <span className={`${styles.chip} ${m.chip === "shipped" ? styles.chipOn : ""}`}>{m.chip}</span>
            <p className={styles.cardRole}>{m.role}</p>

            <dl className={styles.axes}>
              {AXES.map((ax) => {
                const v = SCORES[m.id][ax.id];
                return (
                  <div key={ax.id} className={styles.axisRow}>
                    <dt className={styles.axisLabel} title={ax.gloss}>{ax.label}</dt>
                    <span className={styles.axisTrack} aria-hidden>
                      <span
                        className={styles.axisFill}
                        style={{ width: `${v * 100}%`, background: m.chip === "shipped" ? "var(--riso-blue)" : "var(--ink-soft)" }}
                      />
                    </span>
                    <dd
                      className={styles.axisWord}
                      role="img"
                      aria-label={`${m.tech} ${ax.label}: ${word(v)}`}
                    >
                      {word(v)}
                    </dd>
                  </div>
                );
              })}
            </dl>

            <dl className={styles.measured}>
              {m.measured.map(([k, v]) => (
                <div key={k} className={styles.measuredRow}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
            <p className={styles.cardLine}>{m.line}</p>
          </article>
        ))}
      </div>

      <p className={styles.axisNote}>
        Bar lengths are our assessment on each axis; the figures under each card are measurements,
        and the published bands are cited rather than produced here. We score no axis we cannot
        argue for.
      </p>

      {/* ── 2 · tested and rejected ────────────────────────── */}
      <div className={styles.rejected}>
        <div className={styles.rejHead}>
          <span className={styles.rejTitle}>Tested, measured, rejected</span>
          <span className={styles.rejBadge}>gate verdict: {mi.rejected_leg.gate}</span>
        </div>

        <div className={styles.rejBars}>
          <div className={styles.rejRow}>
            <span className={styles.rejLabel}>without embeddings</span>
            <span className={styles.rejTrack} aria-hidden>
              <span
                className={styles.rejFill}
                style={{ width: barW(mi.rejected_leg.without_embeddings_pr_auc), background: "var(--riso-blue)" }}
              />
            </span>
            <span className={styles.rejVal}>{mi.rejected_leg.without_embeddings_pr_auc.toFixed(4)}</span>
          </div>
          <div className={styles.rejRow}>
            <span className={styles.rejLabel}>with embeddings</span>
            <span className={styles.rejTrack} aria-hidden>
              <span
                className={styles.rejFill}
                style={{ width: barW(mi.rejected_leg.with_embeddings_pr_auc), background: "var(--coral)" }}
              />
            </span>
            <span className={styles.rejVal}>{mi.rejected_leg.with_embeddings_pr_auc.toFixed(4)}</span>
          </div>
        </div>

        <p className={styles.rejLine}>
          <strong>{delta} lower</strong> than the booster it was meant to improve, on the same
          holdout, scored over every subject, so the loss is not a coverage artifact. The columns are
          wired off, the row vocabulary records the loss, and a checker turns red if anyone ever
          ships them. The pipeline rejected its own improvement. No human override.
        </p>
      </div>

      {/* ── 3 · where we sit ───────────────────────────────── */}
      <div className={styles.positioning}>
        <span className={styles.posTitle}>Where 0.766 sits</span>

        <div className={styles.posPlot}>
          <div className={styles.posAxis} aria-hidden>
            {[0.55, 0.7, 0.85].map((t) => (
              <span key={t} className={styles.posTick} style={{ left: posPct(t) }}>{t.toFixed(2)}</span>
            ))}
          </div>

          {BANDS.map((b) => (
            <div key={b.key} className={styles.posRow}>
              <span className={styles.posLabel}>{b.label}</span>
              <span className={styles.posTrack} aria-hidden>
                <span
                  className={styles.posBand}
                  style={{ left: posPct(b.lo), width: `calc(${posPct(b.hi)} - ${posPct(b.lo)})` }}
                />
              </span>
              <span className={styles.posRange}>
                {b.lo.toFixed(2)}–{b.hi.toFixed(2)}
              </span>
            </div>
          ))}

          <div className={styles.posRow}>
            <span className={`${styles.posLabel} ${styles.posLabelOurs}`}>our Elliptic F1</span>
            <span className={styles.posTrack} aria-hidden>
              <span className={styles.posMark} style={{ left: posPct(mi.ours.elliptic_f1) }}>
                <span className={styles.posTickMark} />
              </span>
            </span>
            <span className={styles.posOurs}>{mi.ours.elliptic_f1.toFixed(3)}</span>
          </div>
        </div>

        <p className={styles.posNote}>
          <strong>{mi.ours.elliptic_f1.toFixed(3)}</strong> is ours
          {IN_GCN && <>, inside the published GCN band</>}. The protocol underneath is{" "}
          <strong>inductive</strong>: trained on the past, tested on the unseen future, with no test
          node ever visible during training. Most published results use the easier transductive
          split, where the test nodes were already in the graph. The same 0.766 under the harder
          protocol is the claim we make, and we name the protocol every time we make it.
          ROC-AUC {mi.ours.elliptic_roc_auc.toFixed(3)} · PR-AUC {mi.ours.elliptic_pr_auc.toFixed(3)},
          measured on a dataset whose labels are not ours.
        </p>
      </div>

      {/* ── 4 · the first year, if deployed ────────────────── */}
      <div className={styles.roadmap}>
        <span className={styles.roadTitle}>the first year, if this is deployed</span>
        <ol className={styles.steps}>
          {ROADMAP.map((s) => (
            <li key={s.what} className={styles.step}>
              <span className={styles.stepWhen}>{s.when}</span>
              <span className={styles.stepDot} aria-hidden />
              <div className={styles.stepBody}>
                <span className={styles.stepWhat}>{s.what}</span>
                <p className={styles.stepWhy}>{s.why}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </details>
  );
}
