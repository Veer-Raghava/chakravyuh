# CHAKRAVYUH research synthesis — living, provisional conclusions

For a positive-findings-first explanation and exact reading order, start with [the research catch-up guide](START-HERE-RESEARCH-CATCHUP.md). It explains windows, queues, trained GNNs and the distinction between experiments and the current product.

Updated 2026-10-01. Current recommendation: [decision and implementation plan](RESEARCH-DECISION-AND-IMPLEMENTATION-PLAN.md). The causal XGBoost scorer is implemented and tested; the shipped LightGBM remains frozen pending integration. This is the requested analysis alongside the append-only action/experiment journal. It is **not** a completed research program or a final claim of superiority. Exact scripts, feature recipes, hashes, experiment counts and failures are in `EXPERIMENT-JOURNAL.md`, `events.jsonl`, layer reports and `research/bitcoin/results/`.

Latest completed checkpoint: R45. Start with [the working SIH investigative engine](SIH-INVESTIGATIVE-ENGINE.md). Read [ownership-independent detection and evidence diversity](ADDRESS-ATOMIC-DETECTION-AND-UNCERTAINTY-ISOLATION.md) and [observation-coverage stress](SHASTRA-OBSERVATION-COVERAGE-STRESS.md). Earlier conclusions below retain their historical context; the later updates supersede the assumption that every downstream task must depend on JAAL clusters.

## What makes the system useful despite uncertainty

A transaction-forensics system can rank observable leads, show supporting money-flow/network evidence, and identify the limits of its observations without naming the sender. Source-IP presence, source-ASN ranking, address ownership, illicit behavior and human identity are different targets. Successful evidence at one does not prove the next. Multiplying heuristic scores from these stages would assume probability calibration and dependence properties that we have not established.

The useful outputs are ranked AML leads at a declared investigator workload, reversible ownership hypotheses with transaction/time provenance, and selectively answered network attribution with measured precision and coverage. These are useful bounded goals. Perfect owner recovery and guaranteed human identification are unsupported goals. Our current MAYAJAAL worlds establish internal behavior, not real Bitcoin-network performance.

We cannot honestly promise uniqueness against 500 applicants or claim that existing graph/deanonymization literature is unexplored. An auditable offline evidence system, controlled observation-coverage experiments, leakage-resistant evaluation and explicit failure analysis are a credible project contribution. A new scientific method requires reproducible improvement on independent worlds and external evidence, plus a clear comparison with prior art. That proof remains future work.

## Current experimental calls

1. **JAAL:** current weak change links can collapse unrelated controllers. CIOH-only improves partition precision; learned change links have exploratory value. Never treat the constants .36/.25 as pair probabilities or connected components as verified identities. The new ledger keeps each transaction claim and availability time. Five canonical snapshots match prefix rebuilds, enabling forward evaluation. This fixes provenance, not incorrect ownership hypotheses.
2. **BUDDHI:** keep LightGBM as the deployable reference while rebuilding evaluation with point-in-time partitions. Existing nominal chronological scores use full-capture JAAL topology. They are retrospective diagnostics. Conformal set inclusion is not an actionable alert decision; broad inclusion previously produced ~1.84% campaign precision. Current ±15% score bands are not calibrated confidence intervals. Do not declare a production improvement until a fixed alert policy passes corrected evaluation.
3. **SHASTRA:** the actual causal six-model/two-hybrid experiment retained source-ASN ranking near .46; a validation-selected LightGBM response policy achieved 459/486 correct at 5.03% same-world test coverage. Neural candidate AP improvement did not give a superior operational attribution policy. This is useful selectivity, not full recovery or a real-network guarantee. Fresh-network transfer now measured 92.66% and 86.77% precision at 5.72% and 4.92% coverage. Source absence strongly degrades answers; the 90% target does not hold in every world. Observer-regime and external confirmation remain necessary.
4. **Missing source:** supervised five-second candidate-absence ranking was moderately informative, but no tested threshold qualified for reliable absence declarations. Isolation Forest performed poorly for this target. Display insufficient observed evidence; do not state that a person is absent from the dataset. Unusualness is not missingness.
5. **External graph models:** actual local/graph-feature trees, trained MLP/GCN/SAGE variant, shuffled-graph control and embedding hybrid were compared on identical public time blocks. The first 60-epoch run favored engineered-graph LightGBM on AP. The extended 240-epoch run retained engineered-graph LightGBM as the AP leader (.6566 versus embedding-hybrid .6464). Neural validation gains failed to generalize to later test steps; both budgets remain exploratory. Full architecture/parameters and limitations are in `EXTERNAL-GRAPH-MODEL-EXPERIMENT.md`.

## The working architecture and its upgrade path

```text
CSV / JSON / XML observations + transaction bodies
                         |
              KAVACH / SETU ingestion
                         |
      versioned events + observation-availability times
                         |
               JAAL ownership claim ledger
            (transaction, time, method, weight)
                         |
               point-in-time graph views
                         |
              +----------+-----------+
              |                      |
       BUDDHI AML ranking       SHASTRA source ranking
       engineered features      bounded arrival evidence
       + LightGBM reference      + strictly prior history
              |                      |
       workload policy          validated answer/abstain policy
              |                      |
              +----------+-----------+
                         |
          evidence + score provenance + separate uncertainty
                         |
                   VAANI / DRISHTI
```

The new causal/provenance APIs are opt-in; the shipped stage defaults have not been migrated. The diagram describes the direction under evaluation, not the already completed application wiring. Research GNNs remain separate until they improve the actual operational metric at acceptable cost. Model availability should not silently change forensic results. A future approved backend needs a recorded model/feature/snapshot version; analyst UI should expose the evidence and limitations first.

## Exact causal SHASTRA recipe

A transaction decision occurs five seconds after first observed announcement. The local candidate set includes only announcements within that horizon. Candidate records count observed announcements/observers, lead/rank/spread and network class. Peer transaction counts, first-rank fractions, payer-peer reuse and ASN first-rank fractions are joined strictly before the transaction's first observation. Registry observer count is explicit. A fixed offline enrichment snapshot supplies network class/ASN; mutable lookup data needs its own history. Prior peer degree is reconstructed from previously observed distinct transaction links and a known ASN link.

Numeric count/time fields use log1p; prior fractions, booleans and the simplified arrival score do not. Six-way network class one-hot encoding plus 15 numeric fields produces 21 inputs. Scaling fits only the first training block. LightGBM uses binary objective, 300 rounds, 31 leaves, minimum 40 rows per leaf, learning rate .05, L2=1, four CPU threads and seed 42. Platt scaling learns a logistic mapping from clipped raw probability logits in a later calibration block. It does not establish group/sequence calibration or identity certainty.

Candidate scores are capped by dividing their sum only when it exceeds one; this preserves residual mass but does not calibrate that mass as probability of an unseen source. ASN candidates sum peer masses; the historical-prior variant multiplies by a causal first-rank frequency and applies the legacy exponential normalization. Its top-two relative separation equals `tanh((w1-w2)/2)`, so small weighted masses produce small margins. A .01 threshold is recipe-specific, not transferable to direct mass aggregation. The benchmark keeps both variants separate.

Fit/calibration/policy/test blocks span 0–45%, 45–60%, 60–70%, and final 30% of elapsed time. Boundary-crossing five-second decisions are purged. Hyperparameters, selected thresholds, hashes and limitation notes are in the result JSON. The final block was already reused in this research; a fresh world is required for confirmatory promotion.

## Experiment coverage and remaining work

| Method family | What actually happened | Interpretation / next requirement |
|---|---|---|
| Logistic regression, RF, ExtraTrees, XGBoost, LightGBM | Trained in causal SHASTRA benchmark; tree/LR alternatives also in ownership-link experiments | Real comparisons; target-specific, not interchangeable AML/ownership/source results |
| CPU MLP | Trained for causal peer scoring and external transaction classification | Greater candidate AP is not automatically better operational precision/coverage |
| Mean ensemble / logistic stacking | Actual source-score experiments | No convincing operational gain sufficient for promotion |
| GCN | Actual external supervised training and node-permuted topology control | 240-epoch extension completed; validation gains did not carry to later test steps |
| GraphSAGE | Actual explicitly named symmetric-normalization variant | Canonical sampled mean/attention variants remain untested |
| GNN embeddings → LightGBM | Actual external experiment | Compare with engineered-neighbor feature control before adding complexity |
| Isolation Forest | Actual source-absence experiment | Poor for this target; AML novelty role requires separate labels and evaluation |
| Fixed normalized propagation + SVD | Already implemented optional BUDDHI path | Fixed embedding, not trained neural representation |
| GAT / temporal GCN / TGAT / TGN / HGT | Literature investigation; not trained in this run | Need trustworthy causal typed/event graph, reproducible environment and CPU/GPU resource profile |
| Autoencoder / typed graph autoencoder | Actually trained, R27/R29 | Weaker AML ranking than supervised controls; no semantic novelty confirmation |
| Contrastive graph pretraining | Untrained research candidate | Past-only pretraining and matched controls required |
| Bayesian ownership / partition sampling / open-set origin model | Design candidates; not validated yet | Explicit dependency/coverage assumptions; no multiplication of uncalibrated scores |

Completed: separate BUDDHI snapshot benchmark, three JAAL worlds, frozen BUDDHI world transfer and two fresh SHASTRA P2P captures. Immediate sequence: finish historical full-network replay, test untouched observer-regime/config panels and evidence-sufficiency policies; measure pipeline error propagation under controlled partition quality; run graph/temporal alternatives only on causally valid inputs. Preserve realistic favorable regimes and stress tests side by side. Do not tune the simulator or labels to make the chosen detector look successful.

## What remains incomplete

Preregistered untouched-world/regime confirmation (initial seed-transfer experiments completed), historical full-network/source replay audit (chain mismatch recovered and loader fixed in R24), reliable missing-source/answer gate, canonical stage integration of repaired BUDDHI snapshots and persistence of the new ownership ledger, source policy migration, semantic anomaly validation, canonical event-time TGN/TGAT/HGT experiments, end-to-end UI provenance updates for new experiments, and a final production decision remain incomplete. KAVACH/SETU/VAANI were inspected where relevant but not comprehensively remodeled in these experiments. No commit or claim of complete research has been made.


## Update after R16–R20

Actual independent full-size chain worlds now exist as reproducible in-memory experiments (seeds 1337/2026/9001); the earlier timeout was caused by a quadratic research adapter, not demonstrated inability of the generator. Frozen change-output AP transfers at .908–.920. Full-partition F1 improves consistently from weak-change .391–.399 to learned-change .431–.437. Recall remains low, so the model cannot promise complete owner recovery.

BUDDHI has an implemented opt-in causal snapshot API with exact monetary flows, actual-edge shape joins and contemporaneous campaign-activity research labels. Five tabular models were tested on identical CIOH snapshots. Equal-duration validation selects XGBoost; pooled test subject-window P@20=.50. The hidden true-owner diagnostic reaches .75 and controller AP .4065, versus real CIOH XGBoost .2237, suggesting aggregation headroom without proving it is attainable.

Reliable response thresholds remain unresolved: ≥.90 observed validation precision yielded only .3529 later precision for selected XGBoost, with ten false decisions in an empty campaign window. This failure blocks confident production promotion. Separate ranking, probability calibration, abstention and workload; use negative controls. Preserve LightGBM as the deployable reference until a corrected independent-world comparison supports a switch. Detailed recipe and findings: `BUDDHI-TEMPORAL-SNAPSHOT-EXPERIMENT.md`.


## R21–R22: frozen world transfer separates ranking from confidence

Canonical matched XGBoost/scaler/calibration reconstructed with exact score replay (max error 0.0); fixed .3815895021 threshold unchanged on new worlds. Independent full-chain seeds 1337/2026 pooled P@20=.95/.75, but fixed-policy precision .710/.400. Fresh same-seed42 P@20=.50/threshold precision .424. That fresh42 chain shares zero TXIDs with stored canonical artifacts: it is NOT a verified observation-only replay. Historical simulator/source replay audit pending. All fresh AML worlds observe complete chain; seeds share generator family and were previously used for JAAL.

Negative-class tail multiplicity experiment: Bonferroni/BY no alerts; BH 17/17 and 5/6 correct in two new-world windows, none elsewhere. These are diagnostics without established exchangeability/valid-p-value conditions; no production guarantee or promotion. Detailed report: `BUDDHI-WORLD-TRANSFER-AND-SELECTIVE-ALERTS.md`. Independent SHASTRA network captures completed; results and source-presence diagnosis are in R23 below.


## R23: SHASTRA fresh-network results

Frozen causal LightGBM/scaler/Platt/.01 policy:92.66% precision in one new world (593/640,92.66%,5.72%coverage), but86.77% in the other (459/529,4.92%coverage). Direct ASN ranking .470/.460. Two fresh captures ~900k announcements each completed within83.19s combined experiment, peak RSS~2.33GiB, no raw exports. Simulator-conditional useful selective leads, not general90% guarantee or human attribution. Host-present answered slices97–99%correct; host-absent slices52–56%correct. That flag is research truth, not an available gate. Observation sufficiency and missing-source uncertainty remain the decisive next question. See `SHASTRA-INDEPENDENT-WORLD-EXPERIMENT.md`; stage defaults still not migrated.


## R24: simulator replay bug resolved, historical chain recovered

The fresh42/canonical mismatch was isolated to JSON script-weight order: loading original configuration reproduces all32,787captured TXIDs and318campaign TXIDs. The sorted effective file held equal parameter values but selected script categories in a different cumulative order. Loader now canonicalizes weighted category order and honors saved n_transactions absent explicit override. New regression compares complete chain/population/campaign/P2P worlds after sorted JSON roundtrip for two seeds. Current generator recipe is versioned; frozen historical artifacts stay preserved. Exact historical dirty-source/network replay and external/regime validation remain distinct from this recovered chain. See `MAYAJAAL-CONFIG-REPLAY-AUDIT.md`.


## R25–R30: graph learning now has measured evidence

Actually trained typed wallet-subject/TX/announcing-IP models with learned32-dimensional context and causal address-linkedGRU memory. Initial temporal AP .2736 versus matched localXGBoost .1240; shuffling relational assignment reducesAP to.0796. The validation-selected initial embedding-tree hybrid retainsAP gains on untouched seeds10007/20011 (.2318/.2114 versus local.1421/.1300), but P@20 is not consistently higher.

An extended180-epoch budget resolves endpoint-checkpoint concerns and validation now selects the temporal neural head at epoch95. Frozen new worlds30011/40009 improveP@20 .55/.95 versus local.30/.75 andAP .2491/.2263 versus .0719/.1494. This is evidence to keep developing the typed graph challenger. It is not real-network confirmation. All feasible nominal90%-validation threshold policies fail90% on at least these transfer worlds. No production model is replaced.

The tested graph model trains onCPU in75.75s/~1.45GiBprocessRSS. It does not require a GPU. The model is a custom typed windowGRU, **not canonicalHGT/TGN/TGAT**. The initial MLP has fewer active parameters, so a capacity-matched MLP remains necessary alongside the already-run shuffled-graph control. Temporal embeddings→XGBoost is viable research, but its selection instability, state provenance and embedding explanation burden remain.

Actual AMLIsolationForest, featureautoencoder and typedgraphautoencoder experiments completed. Validation-selectedIFfusion underperforms parent testP@20 .45vs.50. Neither featureAE norIF retrieves positives in top20. GraphAE retrieves6/20 butAP .0207. Keep unusualness separate; no demonstrated reason to fuse it intoAMLconfidence.

Actual observable SHASTRAcorrectness gates increased coverage to7.7–9.0%, but precision84.1–87.9% did not meet nominal90%. These gates cannot prove senderabsence. Initial integer-mask diagnostic bug was preserved, repaired and regression-tested; main decision results were unaffected. Detailed model recipes and result tables are in `TEMPORAL-HETEROGENEOUS-GRAPH-EXPERIMENT.md` and `AML-ANOMALY-EXPERIMENT.md`; recent literature retrieval/quality notes are in `RECENT-LITERATURE-ADDENDUM.md`.

The next engineering priorities remain: preserve the proof-carrying point-in-time JAAL ledger in stage artifacts; migrate repaired feature construction into persistent label-free scoring; measure stable deduplicated review queues and selective answers; test observer/configuration shifts; explain graph decisions using edge/event interventions. The existing API quarantine violation still blocks full verification. These items are explicitly unfinished; actual experiments are implemented, but the whole application has not been remodeled.


## R30–R33: clustering propagation, tree controls and usable inference

Frozen detectors were evaluated under CIOH-only and weak-change partitions. The initial controller universes differed, so a second comparison uses their shared 21,014 controller-window rows and verifies identical labels. Weak links lower temporal AP .2028→.1918; local XGBoost AP .2133→.2249, with unchanged P@20. This is a consumed-world sensitivity, not a universal claim that every merge lowers every score. More importantly, projected controller metrics reduce the apparent subject-level graph advantage. Full results: `OWNERSHIP-ERROR-AND-TREE-CONTROLS.md`.

Matched LightGBM local/typed-summary/temporal-embedding controls also completed. Enriched features improve test AP .0547→.1969; embeddings→LightGBM reaches .2622. Validation still selects local LightGBM. These results support richer graph engineering and continued neural comparisons without selecting whichever test number looks best.

The new `buddhi.causal_inference` module is a working opt-in CPU engine with a portable XGBoost artifact, explicit observation window, point-in-time ownership/features, ranked scores and checked raw-margin TreeSHAP. It reproduces all ten prior causal score windows exactly (max error0.0), and an actual stripped-input subprocess run succeeds with only observation/model files. It does not integrate the failed confident-alert threshold or replace the standard stages. The portable export needed the fitted calibrator's float32 precision; the mismatch and fix are audited.

The current recommendation is causal XGBoost as the next CPU production candidate, with the shipped LightGBM retained as the frozen reference until integration passes. The typed temporal encoder remains a promising CPU-capable research challenger. Detailed commands and outputs: `CAUSAL-OFFLINE-INFERENCE.md`. Broader application migration, configuration-shift confirmation, deduplicated workload and full verification remain unfinished.


## R34–R40 update: clustering errors need not invalidate observable evidence

Actual address-only graph training and frozen transfer now show that detection can use address/TX/announcer relationships without consuming any ownership ledger. The production snapshot API has an explicit address mode with a corruption-isolation regression test. Causal SHASTRA already uses captured observations and prior address/peer histories independently of JAAL partitions. Proposed architecture should preserve these parallel evidence paths.

Controller-aware evaluation corrects an important overstatement risk: canonical address XGBoost's20positivealerts represent only5controllers. We therefore tested observable transaction-evidence diversification, with truth attached only after selection. A frozen .25 Jaccard cap improved static controller-window retrieval14→30 and7→12 across two regenerated transfer worlds, but reduced address precision. Repeated-window counts are not distinct controllers over the entire capture. Evidence diversity is not verified ownership and remains a research queue.

Richer329-feature graph summaries are now actual XGBoost/LightGBM controls. Frozen common-controller-validation-selected XGBoost achieved distinct-controller P@20 .90/.30 on two new worlds; static address graph achieved .95/.45. Neither establishes universal superiority. Keep causal tree integration as the practical path and compare both representation choices on controller-aware workloads before replacing the default.

A constructive toy using actual SHASTRA features proves source-presence ambiguity can remain even with perfect deterministic computation. The correct engineering response is explicit attribution abstention while preserving transaction evidence. This does not support declaring source absence from the current capture.

Read [the detailed address/uncertainty report](ADDRESS-ATOMIC-DETECTION-AND-UNCERTAINTY-ISOLATION.md) for actual models, features, parameters, tables, failure records and reproduction paths. These are useful architectural findings, not claimed global novelty or proof of real-network reliability.


### R41: observation regime is part of the attribution contract

Frozen SHASTRA policy precision collapses94.4%→51.1%→26.4% as a nested capture drops from48to24to8activeobservers, while answering more often. This consumed-world stress invalidates exporting the original score-gap threshold across observation regimes. Unsupported capture conditions require explicit policy abstention; no replacement is validated yet. Read [the full observation stress report](SHASTRA-OBSERVATION-COVERAGE-STRESS.md). AML evidence remains independently useful.


## R42–R45: working investigative engine and SIH direction

The useful research now has a concrete product path. A portable329-feature graph-context XGBoost engine reproduces the research scores, generates explained evidence packets on observation-only inputs and runs with Torch unavailable. World now includes a real packet viewer with localJSONimport/export, model contributions and linked monetary/network evidence. It is independent of the active-run metrics and defaultLightGBMstage.

The strongest measured workload result for this tree model is controller-windowretrieval11→33and9→16under a frozen evidence-diversity policy in two syntheticworlds, with an address-precision tradeoff and repeated-window counting disclosed. Our publicEllipticexperiment also provides positive evidence for graph-feature trees. Read [the SIH investigative engine report](SIH-INVESTIGATIVE-ENGINE.md) for actual implementation, exact329-feature recipe, tests, runtime, command and a five-minute demonstration.

Prioritize full ingestion-to-case integration and a smooth offline review experience next. Use temporal/heterogeneous neural models as controlled challengers where they retrieve extra useful evidence. This is a positive capability strategy, not a guarantee of globalnovelty or competitionplacement.
