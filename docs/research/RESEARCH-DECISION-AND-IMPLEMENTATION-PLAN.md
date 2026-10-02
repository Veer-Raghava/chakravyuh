# Research decision and implementation plan

Updated 2026-10-01. Read with the [implementation/literature audit](../BITCOIN-AML-MODEL-AUDIT.md), [living analysis](RESEARCH-SYNTHESIS.md) and [experiment journal](EXPERIMENT-JOURNAL.md). This document separates the current shipped system, the working experimental inference path, and the next production candidate. It does not claim every possible architecture has been tested or that the application remodel is complete.

## What has actually been implemented

JAAL has an opt-in ownership-evidence ledger and point-in-time snapshots. BUDDHI has a tested causal feature API with corrected gross flows and counterparties. SHASTRA has bounded five-second arrival features and strictly prior history. MAYAJAAL has deterministic effective-configuration replay repairs and actual chain/network roundtrip tests. These APIs and experiments exist in code; standard stages have not all been migrated to them.

Actual experiments cover learned change proposals, mixed-input screening, temporal/network ablations, multiple tabular classifiers, external trained graph models, custom typed temporal graph models, graph-shuffling controls, embedding→XGBoost/LightGBM, Isolation Forest, feature and graph autoencoders, source-correctness gates, frozen independent-world transfer and clustering-error propagation. Weight files, per-decision scores, source snapshots and manifests are retained. Some experiments were negative; those remain in the report.

A new opt-in **label-free offline causal XGBoost scorer** is implemented in `src/chakravyuh/buddhi/causal_inference.py`. It uses explicit observation windows and portable native model JSON plus a feature/calibration manifest. It outputs ranked scores, per-feature TreeSHAP contributions in raw margin space, subject membership and ownership evidence. It does not fit on the supplied capture, load answer keys or apply the failed confident-alert threshold. It is a working candidate engine; the main dashboard/stage route still uses the existing engine.

## Evidence that changes the architectural decision

- Matched causal tabular validation selected XGBoost. The original LightGBM remains a useful frozen deployment reference, but its historical full-capture topology metrics cannot justify superiority.
- Typed graph learning improves synthetic subject-window AP and, in the extended frozen new-seed panel, P@20. Seeds30011/40009: temporal P@20 .55/.95 against local XGBoost .30/.75; AP .2491/.2263 against .0719/.1494. The small tested graph model trains on CPU; no GPU purchase is required for it.
- Those gains shrink when measuring controller-window rather than fragmented subject-window retrieval. On the common canonical controller set, temporal AP .2028 versus local XGBoost .2133, P@20 .50 versus .45. This is an evaluation diagnostic using hidden controller keys, not analyst-side identity recovery.
- Adding weak change links lowers temporal controller AP to .1918 on the same controller set. More graph edges can damage useful evidence. Models do not eliminate ownership ambiguity.
- LightGBM with typed summaries increases test AP .0547→.1969; temporal embeddings→LightGBM reaches .2622/P@20 .90. Validation still selects local LightGBM within that supplementary comparison. Reporting the best test hybrid as the winner would be misleading.
- Nominal90%-precision validation thresholds fail on new worlds for AML and some source-answer policies. This blocks a90%confidence promise; it does not make a transparently evaluated ranked-lead workflow useless.
- IF/AE do not improve the selected AML ranking. Keep unusualness separate until its semantic usefulness is demonstrated.

None of these results establishes real Bitcoin-network accuracy. New seeds share MAYAJAAL mechanisms. Comparisons use matched protocols; external Elliptic results are separate tasks and must not be pooled with synthetic figures.

## Recommended Production Model

**XGBoost on causal engineered transaction/graph/temporal features, as the next CPU production candidate.** Preserve the shipped LightGBM model as the frozen reference until the optional scorer is integrated and the remaining release checks pass. No canonical model was overwritten.

## Why

This recommendation follows the actual matched tabular validation result, frozen-world tests, practical CPU inference and available signed TreeSHAP explanations. It is an incremental migration from one engineered tree model to another, with explicit versioned features and observation boundaries. The new scorer demonstrates that its trained artifact can run without evaluation labels and replay exactly.

The critical architectural improvement is the causal ownership/feature pipeline, not the booster brand. A small tuning comparison may retain LightGBM if it improves the declared review-budget metric under the same independent protocol. There is no claim that XGBoost generally dominates LightGBM. The typed temporal model is a credible challenger with better subject-level synthetic ranking, but stable controller/campaign yield, explanation fidelity and threshold semantics remain unresolved.

## Why Not the Other Models

- **Logistic Regression:** keep as the interpretable fitted baseline; nonlinear relational interactions merit a stronger challenger.
- **Random Forest / ExtraTrees:** actually tested; neither won the matched tabular selection. Retain controls if the data regime changes.
- **LightGBM:** preserve the incumbent, including its feature/SHAP advantages. Supplementary enriched/hybrid results are promising but not a validation-selected replacement for the CPU candidate.
- **GCN:** actually trained externally; engineered graph-feature LightGBM led external AP under our protocol. That result does not refute temporal graph learning on our typed problem.
- **GAT:** untrained here. Attention may help heterogeneous neighborhoods, but adds explanation and sampling questions; attention weights alone are not forensic reasons.
- **Temporal GCN / TGAT / canonical TGN:** event ordering and temporal interaction kernels may exceed our window GRU, but need actual matched implementation and future-only evaluation.
- **HGT / temporal heterogeneous GNN:** type-aware processing is justified as a research representation. Our custom typed model already demonstrates useful signal without a full Transformer; large HGT complexity has not yet shown incremental benefit.
- **Temporal encoder→XGBoost / LightGBM:** actually trained. Good AP and occasional P@20 gains, but selection changes with budget, controller projection reduces advantages, and embedding explanations need an encoder-side method.
- **IF / AE / graph AE:** unusualness is not illicitness. Actual anomaly/fusion results do not justify replacing or automatically altering supervised AML ranking.

## Recommended Baseline

**Logistic Regression** on the identical causal feature table and splits. Also retain frozen local LightGBM/XGBoost, a label-free graph-summary tree control, shuffled graph control and a larger capacity-matched MLP. The existing MLP has fewer active parameters than the temporal encoder, so it does not alone isolate graph structure from capacity.

## Recommended GPU/Research Model

**Implemented typed mean-message encoder + address-linked window GRU**, first with its neural head, then frozen embeddings plus either tree head. It runs on CPU at the tested scale. Treat an event-time TGN/TGAT or temporal HGT as a later experiment, and measure GPU benefit rather than labeling this model “GPU required.” No GPU-only product mode is approved.

## Recommended Anomaly Detector

**Experimental Isolation Forest in a separate unusual-activity queue.** It is not required by the main classifier and is not a reliable sender-absence detector. Validate novel benign behaviors and investigator usefulness before shipping. Do not fuse its raw score into AML confidence based on the present evidence.

## Explainability

**Signed TreeSHAP in raw model log-odds plus timestamped graph evidence and feature definitions.** The optional scorer verifies contribution sums. A positive contribution pushes the model toward the training target; it does not prove a crime. Platt calibration is separate from SHAP and is not a future-world guarantee.

For graph engines, require edge/event ablation, stable supporting paths and clear ownership assumptions. An embedding coordinate explanation cannot substitute for an explanation of the encoder's relationships. Display network announcers separately from inferred source candidates and verified controllers.

## Evaluation Metrics

Primary: deduplicated Precision@20/50, Recall@K and average precision (AP). Here AP is sklearn average precision, not a silently substituted trapezoidal PR integral. Publish subject-, controller-diagnostic-, transaction- and campaign-level metrics separately. Include per-window ranking, zero-positive windows, false campaigns, alert volume, positive prevalence, calibration/Brier/reliability, answered precision/coverage, latency, training cost, process RSS and artifact size.

Twenty highly ranked leads directly measure investigator workload. Accuracy can remain high by predicting every rare campaign participant negative. P@20 must count20 reviewed decisions when20 are available, with duplicate policy declared. Repeated controller/window decisions cannot be presented as20 distinct criminals. Correlated graph observations also invalidate naive independent-binomial uncertainty claims.

## Deployment Strategy

One approved default CPU engine, recorded model/feature/snapshot/enrichment versions, explicit experimental-engine provenance and deterministic replay. The optional causal XGBoost CLI is already implemented; integration is a release step, not an invisible switch. XGBoost is an optional installed dependency for this CLI and must be included in the eventual offline package. The current environment has3.2.0; no network installation was performed.

Do not silently choose a different model because a GPU is available. Hardware-dependent model choice changes forensic results and weakens reproducibility. A research console can compare saved model outputs; the investigator UI should show the engine version, evidence, observation window and limitations. No speculative Standard/Advanced toggle is warranted yet.

```text
CSV / JSON / XML observations + transaction bodies
                     |
             KAVACH / SETU validation
                     |
          available-at timestamps + lineage
                     |
       JAAL ownership claims with TX/time/method
                     |
         point-in-time graph and feature view
            /                |                \
           /                 |                 \
 CPU lead ranking      research graph lane   network evidence
 causal XGBoost        typed mean + GRU      causal SHASTRA
 (LGB reference)       head / frozen tree    rank + abstention
       |                      |                  |
 TreeSHAP + paths      model comparison only    candidates
       |                      |                  |
       +----------------------+------------------+
                             |
              ranked leads + separate uncertainty
                             |
                      VAANI / DRISHTI

Separate experimental unusualness queue: IF / reconstruction evidence
```

## Migration plan and actual status

| Phase | Already completed | Required next |
| --- | --- | --- |
| 0 — Freeze | Canonical model/capture preserved; source/runtime hashes, scores and recipes recorded | Export a stable application model card with artifact/split identifiers |
| 1 — Evaluate | Causal ledger/snapshot APIs, independent worlds, P@20/50/AP, leakage diagnosis and negative controls | Stage persistence, deduplicated review queue, rolling config/observer panels |
| 2 — Alternatives | Actual tabular, enriched tree, external graph and embedding-tree comparisons | Small matched tuning panel and capacity-matchedMLP; freeze before new tests |
| 3 — Temporal graph | Custom typed window GRU trained at60/180epochs; shuffled control and four frozen new worlds | Event-time model only if it addresses remaining measured errors |
| 4 — Compare | Common splits, separate calibration, per-window outputs, controller projection and resource timing | Campaign/controller workload, explanations, observer regimes and ambiguity stress tests |
| 5 — Decide | XGBoost CPU candidate; temporal graph retained as research; no failed confidence policy promoted | Integrate scorer/evidence interfaces, offline packaging and full release verification |

OutcomeA remains valid if an equally evaluated LightGBM improves operational yield. OutcomeB requires graph gains on the actual deduplicated workflow, not just subject AP. OutcomeC needs measured deployment cost; our small graph model already works onCPU. OutcomeD means leaving a graph model out if further controls remove its benefit. We do not need to force a neural network into the product.

## Answers to the14 requested questions

| Question | Current answer |
| --- | --- |
| 1. Is LightGBM appropriate? | Yes as a CPU engineered-feature model and frozen reference. Historical leaky metrics do not prove it is best; matched tabular validation favors XGBoost. |
| 2. What do graph features capture? | Aggregated flows, counterparties, fan-out, ownership-edge confidence/heuristics, peel/dwell/activity summaries. The tested pipeline does not contain every requested PageRank/centrality/distance feature. |
| 3. What can a temporal GNN add? | Learned relation-specific neighborhood interactions and history across windows; event-time versions could preserve finer ordering. It cannot recover information never observed. |
| 4. Does it improve this workflow? | It improves synthetic subject-window ranking on fresh worlds. Controller/campaign and confidence benefits are not yet established. |
| 5. Temporal GNN+XGBoost? | A working research challenger; not a proven production winner. |
| 6. LightGBM+graph features? | Credible CPU strategy. Enriched features materially improve AP in the supplementary test; selection and transfer still matter. |
| 7. Temporal heterogeneous GNN? | Types are meaningful; a small custom typed GRU is already tested. FullHGT is not currently necessary. |
| 8. Is IF necessary? | No. Separate novelty role only after semantic evaluation. |
| 9. Baseline? | LR plus local trees, graph-summary trees and topology/capacity controls. |
| 10. Production model? | CausalXGBoost is the next CPU candidate; current shippedLightGBM stays frozen until integration gates pass. |
| 11. Advanced model? | Customtypedwindow GRU research engine, CPU-capable. No GPU-required production promise. |
| 12. Website? | One validated engine/version, ranked evidence, explicit uncertainty and research status. No cosmetic model selector. |
| 13. Before SIH? | Persist causal evidence, integrate the tested tree scorer/SHAP, deduplicate review queues, expose source abstention, package offline and repair verification. |
| 14. Future work? | Event-timeTGN/TGAT/HGT, past-only pretraining, uncertainty-aware partitions, protocol-adjudicated cases, external/configuration shift and encoder explanations. |

## Why the tool still has a purpose

The defensible output is a better ordered set of observable leads with evidence and declared limits. A sender who never appears in the observations cannot be recovered from them. An ASN answer is not a host/person answer. A group inferred from common inputs is not a verified owner. We can still show money-flow paths, rank campaign-like behavior and abstain where source evidence is insufficient.

Our strongest credible contribution is an offline system with reproducible, point-in-time evidence and measured error propagation across these uncertain layers. A claim of research novelty requires further comparison and external validation; no claim of winning against500teams or of solving all attribution ambiguity is supported. The current experiments provide positive graph findings and concrete failure analyses, rather than a reason to abandon the project or to oversell it.


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
