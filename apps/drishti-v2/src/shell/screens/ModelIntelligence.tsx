import graphTests from "../../data/fixtures/graph-experiments.json";
import research from "../../data/fixtures/research-progress.json";
import { useRun } from "../../data/RunContext";
import { InvestigationPreview } from "./InvestigationPreview";
import styles from "./ModelIntelligence.module.css";

type ComparisonRow = { name: string; ap: number; p20: number; observation: string };

function ComparisonTable({ rows }: { rows: ComparisonRow[] }) {
  return (
    <div className={styles.tableScroll}>
      <table>
        <thead><tr><th>Model we tested</th><th>Test AP</th><th>Top-20 precision</th><th>What we observed</th></tr></thead>
        <tbody>{rows.map((m) => (
          <tr key={m.name}><td>{m.name}</td><td>{m.ap.toFixed(4)}</td><td>{(m.p20 * 100).toFixed(0)}%</td><td>{m.observation}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}

export function ModelIntelligence() {
  const { fixtures } = useRun();
  const integrated = fixtures.world.model_intelligence.shipped_model === "causal-relational-xgboost";
  return (
    <details className={styles.wrap} open>
      <summary className={styles.summary}>
        <span className={styles.summaryTitle}>
          From graph intelligence to investigative leads
        </span>
        <span className={styles.summaryTag}>CPU · offline · explainable</span>
      </summary>
      <p className={styles.intro}>
        Follow the money, connect it to captured network observations, and open
        the evidence behind each model-ranked lead. The working research engine
        uses typed graph context while keeping address ownership as a separate
        investigative hypothesis.
      </p>
      <div className={styles.cards}>
        <article className={`${styles.card} ${styles.cardOurs}`}>
          <span className={styles.cardTech}>Current application engine</span>
          <h3 className={styles.cardName}>{integrated ? "XGBoost + typed graph context" : "LightGBM + graph features"}</h3>
          <span className={`${styles.chip} ${styles.chipOn}`}>CPU default</span>
          <p className={styles.cardLine}>
            {integrated ? "329 engineered address, transaction and announcing-peer inputs. A frozen CPU model feeds evidence-diverse Leads and newly signed Proof packets." : "33 engineered transaction, graph and network inputs. Signed SHAP contributions and graph evidence support this archived run's risk queue."}
          </p>
        </article>
        <article className={styles.card}>
          <span className={styles.cardTech}>Implemented graph-context engine</span>
          <h3 className={styles.cardName}>329 graph-context inputs</h3>
          <span className={styles.chip}>Portable CPU model</span>
          <p className={styles.cardLine}>
            XGBoost learns from address activity, incoming and outgoing
            transaction neighborhoods, funding addresses and announcing peers.
            Native TreeSHAP explains its predictions.
          </p>
          <p className={styles.cardLine}>
            The portable implementation reproduced both research representations
            across all ten windows exactly. The integrated graph run now routes its own
            leads, evidence and signatures through the main investigation views.
          </p>
        </article>
        <article className={styles.card}>
          <span className={styles.cardTech}>Measured research result</span>
          <h3 className={styles.cardName}>More distinct leads to review</h3>
          <dl className={styles.measured}>
            {research.worlds.map((w) => (
              <div key={w.seed} className={styles.measuredRow}>
                <dt>Synthetic world {w.seed}</dt>
                <dd>
                  {w.before} → {w.after}
                </dd>
              </div>
            ))}
          </dl>
          <p className={styles.cardLine}>
            We tested a frozen transaction-evidence diversity policy. It
            increased suspicious controller-window retrieval across three test
            windows for the graph-context XGBoost model. A controller can recur
            across windows.
          </p>
          <p className={styles.cardLine}>
            This trades address precision for wider investigative coverage.
            These are research measurements, not metrics for the active capture.
          </p>
        </article>
      </div>
      <section className={styles.graphTests}>
        <span className={styles.cardTech}>Public Bitcoin data · completed experiment</span>
        <h3 className={styles.sectionTitle}>Graph context helped on Elliptic, too.</h3>
        <p className={styles.body}>
          We compared trained graph models, embedding hybrids and feature-based
          trees on 203,769 Bitcoin transaction nodes and 234,355 flow edges.
          Graph-feature LightGBM achieved 0.6566 average precision and 20 positive
          transactions in its pooled top 20, improving AP over matched local LightGBM.
        </p>
        <ComparisonTable rows={graphTests.ellipticModels} />
        <p className={styles.body}>
          Earlier time steps trained the models; steps 40–49 supplied the test.
          Only labeled transactions were scored: 636 illicit among 11,184
          test transactions (5.69%). Unknown labels remained graph context.
          This public-data comparison is separate from our synthetic experiments
          and from metrics for the active capture.
        </p>
        <p className={styles.note}>Source: {graphTests.ellipticSource} · 300 tree rounds · up to 240 neural epochs · exploratory comparison</p>
      </section>
      <section className={styles.graphTests}>
        <span className={styles.cardTech}>Synthetic Bitcoin + network evidence · stronger tree controls</span>
        <h3 className={styles.sectionTitle}>We tested rich graph features with both tree engines.</h3>
        <p className={styles.body}>
          These earlier R37 experiments use 329 inputs describing local activity,
          incoming and outgoing transaction neighborhoods, funding subjects and
          captured announcing peers. Address XGBoost reached AP 0.3148 with 20
          positives among its pooled top 20.
        </p>
        <ComparisonTable rows={graphTests.richModels} />
        <p className={styles.body}>
          Address and common-input-grouped rows score different subjects; their
          metrics are not interchangeable. These are research models, distinct
          from the application's 33-input LightGBM default. They were not newly
          trained as part of the later R47 neural replay.
        </p>
        <p className={styles.note}>Source: {graphTests.richSource} · 300 rounds per model · chronological fit/calibration/validation/test</p>
      </section>
      <section className={styles.graphTests}>
        <span className={styles.cardTech}>Understanding the measurements</span>
        <h3 className={styles.sectionTitle}>A strong first queue and complete recovery are different goals.</h3>
        <div className={styles.metricGrid}>
          <article className={styles.metricCard}>
            <strong>19 / 20</strong>
            <h4>Relevant decisions in the GNN's first 20</h4>
            <p>95% pooled Precision@20: relevance at a small review budget.</p>
          </article>
          <article className={styles.metricCard}>
            <strong>0.2879 AP</strong>
            <h4>Quality across the whole ranking</h4>
            <p>Average precision rewards finding positives early throughout the list. It is not 28.79% accuracy.</p>
          </article>
          <article className={styles.metricCard}>
            <strong>0.52%</strong>
            <h4>Positive prevalence in this test</h4>
            <p>295 positive decisions among 57,105. A random ranking has an approximate AP reference of 0.0052.</p>
          </article>
        </div>
        <p className={styles.body}>
          The first 19 positives recover 6.44% of all positives. Recovering more
          requires reviewing farther down the list while controlling false
          alerts. Address-window decisions can repeat an actor; they are not
          distinct people or verified identities.
        </p>
        <details className={styles.controls}>
          <summary>How we tested the graph benefit · GNNs and relationship controls</summary>
          <p className={styles.body}>
            R47 used the same synthetic test windows 7–9 for these models.
            Validation selected the temporal GRU. Disrupting graph alignment
            reduced its AP from 0.2879 to 0.0778, supporting the value of real
            relationships beyond local features.
          </p>
          <ComparisonTable rows={graphTests.models} />
          <p className={styles.body}>
            Temporal GNN per-window P@20 was 65%, 100% and 0%; the last window
            contained no positives. Pooled top-20 performance is not a promise
            of 95% precision in every window. These custom typed mean/GRU models
            ran on CPU; they are not canonical TGN, TGAT or HGT reproductions.
          </p>
          <p className={styles.note}>Source: {graphTests.source} · 60-epoch budget · consumed synthetic world</p>
        </details>
      </section>
      <section className={styles.graphTests}>
        <span className={styles.cardTech}>New exploratory test · saved-score blend</span>
        <h3 className={styles.sectionTitle}>Can trees and temporal memory work together?</h3>
        <p className={styles.body}>
          We tested five blend weights using saved predictions. Validation AP
          selected 75% graph-context XGBoost + 25% temporal GNN. Its test AP
          increased to 0.3381. This combines two existing models; it does not
          retrain a new encoder or establish calibrated blend probabilities.
        </p>
        <div className={styles.tableScroll}>
          <table>
            <thead><tr><th>Model</th><th>Test AP</th><th>Hits / 20 reviews</th><th>Hits / 50</th><th>Hits / 100</th><th>Hits / 500</th></tr></thead>
            <tbody>{graphTests.recoveryModels.map((m) => (
              <tr key={m.name}>
                <td>{m.name}</td><td>{m.ap.toFixed(4)}</td>
                <td>{m.budgets["20"].hits} / 20</td><td>{m.budgets["50"].hits} / 50</td>
                <td>{m.budgets["100"].hits} / 100</td><td>{m.budgets["500"].hits} / 500</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className={styles.body}>
          At 500 reviews the blend retrieves 128 of 295 positives (43.39%),
          compared with 115 for the tree and 114 for the GNN. At 50 reviews the
          GNN alone retrieves more. There is no single winner at every workload.
          The next promotion test is a complete matched benchmark across
          independent worlds, with actor diversity and review cost measured.
        </p>
        <p className={styles.note}>Source: {graphTests.recoverySource} · repeated actors possible · exploratory reused-test analysis · production engine unchanged</p>
      </section>
      <InvestigationPreview />
      <section className={styles.roadmap}>
        <h3 className={styles.sectionTitle}>The investigation workflow</h3>
        <ol className={styles.steps}>
          <li className={styles.step}>
            <span className={styles.stepWhen}>Observe</span>
            <div>
              <span className={styles.stepTitle}>
                Keep transaction and network evidence connected
              </span>
              <p className={styles.body}>
                Inputs, outputs, amounts and timed announcements form the
                evidence graph. Address-level detection can operate without
                first merging wallets into an owner.
              </p>
            </div>
          </li>
          <li className={styles.step}>
            <span className={styles.stepWhen}>Prioritize</span>
            <div>
              <span className={styles.stepTitle}>
                Learn patterns, then reduce repeated evidence
              </span>
              <p className={styles.body}>
                A trained model ranks leads. The queue compares their supporting
                transactions so repeated evidence does not consume every review
                slot.
              </p>
            </div>
          </li>
          <li className={styles.step}>
            <span className={styles.stepWhen}>Investigate</span>
            <div>
              <span className={styles.stepTitle}>
                Explain, trace and export
              </span>
              <p className={styles.body}>
                Open signed feature contributions, exact transaction amounts and
                observed peer links. Export a structured evidence queue for
                further investigation.
              </p>
            </div>
          </li>
        </ol>
        <p className={styles.note}>
          The preview is an executed synthetic research snapshot. Full stage
          integration and validation under new observation regimes are the next
          engineering milestones.
        </p>
      </section>
    </details>
  );
}
