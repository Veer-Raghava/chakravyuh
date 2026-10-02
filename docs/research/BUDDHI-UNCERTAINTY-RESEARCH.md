# BUDDHI research: risk ranking under JAAL uncertainty

> Update after R21–R23: Subsequent corrected snapshot, label/accounting, frozen-world transfer and selective-alert experiments are documented in [BUDDHI-TEMPORAL-SNAPSHOT-EXPERIMENT.md](BUDDHI-TEMPORAL-SNAPSHOT-EXPERIMENT.md) and [BUDDHI-WORLD-TRANSFER-AND-SELECTIVE-ALERTS.md](BUDDHI-WORLD-TRANSFER-AND-SELECTIVE-ALERTS.md). Original full-capture results below remain retrospective; no production model was promoted.

**Status:** interim research report, 2026-10-01; chronology audit amended  
**Scope:** BUDDHI's current risk model, held-out evaluation, and a paired JAAL-threshold sensitivity experiment. This is one synthetic generator/seed and does not establish real-chain performance.  
**Evidence classes:** repository code, saved evaluation reports, and the research-only experiment in `research/bitcoin/buddhi_jaal_sensitivity.py`.

## Current implementation

BUDDHI scores one row per JAAL connected component, plus one row per observed address not in a non-singleton component. It computes many activity features over pre/post-boundary transactions and declares a 70% chronological train split, with a later 25% tail inside the training subjects for calibration. **However, the current evaluation is not strictly inductive or point-in-time safe:** BUDDHI reads JAAL components built from the entire capture before assigning subjects to the time split. Future `SAME_OWNER` links can therefore change early subject IDs, combine early training features/labels, and leak post-boundary evidence. Windowing transactions alone does not cure this topology leak. Treat all current agency-v2 BUDDHI scores and the paired threshold experiment below as full-graph retrospective diagnostics, not prospective chronological performance, until JAAL snapshots are rebuilt at each cutoff.

The production classifier is native LightGBM, binary objective, 300 boosting rounds, 31 leaves, minimum 40 rows per leaf, L2=1, deterministic single-thread CPU training. Its 33 model features combine transaction/activity and flow (counts, amounts, counterparties, fan-in/fan-out, dwell, fee), JAAL structure (member count, weakest link confidence, number of heuristics, script types), SHASTRA origin/ASN estimates and abstention shares, typology hits, and six morphological features. It uses LightGBM TreeSHAP for top-five local feature contributions. Risk ranking is the raw booster score. Mondrian class-conditional conformal prediction supplies class-set inclusion, not a calibrated probability interval.

There is an optional eight-column graph representation. Despite the internal `--gnn` flag and `gbm_gnn_v2` model name, `buddhi/embed.py` explicitly does **not** implement a trained GNN: it performs two-hop confidence-weighted mean propagation (`A_hat^2 X`) followed by exact SVD, without labels or learned graph weights. That is a fixed SGC-style linear representation. The canonical agency-v2 run did not request this option, so no comparison exists yet. Calling this leg a tested GNN would overstate the implementation.

The training target is illicit status aggregated to each hard JAAL subject by address majority (ties licit). The holdout label uses the same majority rule over that subject's holdout addresses. This gives a consistent target, but a false JAAL merge can blend controllers and dilute or invert a subject's label; a split can fragment one illicit controller into many independently scored subjects. BUDDHI's subject score is not automatically a person-level risk probability.

## Canonical agency-v2 result and its limits

The frozen canonical report records 26,783 holdout subjects and class imbalance 1:53. It reports actor PR-AUC 0.06492 and ROC-AUC 0.59141; actor Precision@20 0.60 (12 of the top 20 subjects) and Recall@20 0.02439. Transaction PR-AUC is 0.10058 and transaction Precision@20 is 0.40. These are different ranking grains and should stay separate. Because the current topology is full-capture, these are descriptive retrospective figures, not valid forward-time estimates. Precision@20 is operationally useful only with its denominator, prevalence, and alert definition shown.

The report's campaign recall, 187/196 = 95.41%, initially looks like a strong campaign-detection result. Audit of the code shows `_campaign_recall` counts an entity caught when any of its holdout addresses appears in a predicted subject whose conformal set includes class 1. This is *class-set inclusion*, not a workload-bounded alert decision. On the paired experiment's exact baseline, class-1 inclusion flags 10,149 entities; 9,962 are licit and 187 illicit. Descriptive campaign precision is 187/10,149 = 1.84%. This is an enormous false-positive set. Report campaign recall beside campaign precision, number flagged, and alert coverage, or do not present it as operational detection performance. The ranked raw risk score and conformal set membership answer different questions. These rates inherit the full-graph retrospective limitation above.

The conformal wrapper achieved calibration-tail Mondrian coverage in the saved evaluation report of 0.9472 for illicit subjects and 0.6835 for licit subjects, versus a nominal 0.90 target. Do not claim exact 90% holdout coverage from the calibration quantile: these are finite synthetic data and the test distribution need not match the calibration tail. In addition, calibration subjects inherit the full-capture topology, so exchangeability/point-in-time validity is not established. The saved `conf_low/conf_high` is a fixed ±15% band around the raw score (or `[0,1]` for ambiguous sets), not a statistically derived confidence interval. It should not be labelled as a calibrated risk interval.

## Confirmed future-topology leakage

`jaal.cluster._star()` writes `SAME_OWNER` edges with null timestamp and no transaction identifier. `buddhi.features.subjects()` consumes the complete `graph/clusters.parquet`, then BUDDHI assigns train/holdout subjects. A future co-spend can therefore merge early addresses before training. `cluster_shape()` also sees accepted evidence edges without event time. The optional embedding treats edges with no timestamped endpoint as static and includes them in both windows; it is not safe for a chronological split either.

The separate, label-free topology audit rebuilt the JAAL partition from pre-boundary transactions and compared it with the canonical full-capture partition on the 89,847 addresses first seen before the boundary. At threshold 0.20, the full graph asserts 373,100 same-cluster address pairs among those early addresses; only 181,444 are supported by pre-boundary evidence. The remaining 191,656 pairs (51.37% of the full-graph early pairs) appear only after future evidence is added. 20,490 early addresses belong to components enlarged by later activity; 1,584 components span early and holdout addresses. At threshold 0.30, 120,113 of 267,458 early same-cluster pairs (44.91%) are absent from the early-only partition; 18,982 early addresses are in enlarged components. These are not corrected BUDDHI scores; they quantify that its supposed chronological subject/feature construction sees future topology. Provenance and counts are in `research/bitcoin/results/buddhi-jaal-sensitivity/buddhi-temporal-topology-audit.json`.

The paired 0.20/0.30 model comparison reproduces the canonical full-graph numbers exactly at 0.20, but that is an implementation parity check, not validation of its temporal protocol. Its deltas are descriptive transductive sensitivity only; do not promote threshold 0.30 from them.

## Paired JAAL threshold sensitivity experiment

**Question:** what changes downstream if BUDDHI receives the measured CIOH-only partition instead of the current CIOH-plus-change partition?  
**Method:** preserve the canonical data, split, features, seed (42), LightGBM parameters, calibration and scoring. Recompute connected components from the existing `SAME_OWNER` evidence at thresholds 0.20 and 0.30; 0.30 retains the 0.36 CIOH links and excludes the 0.25 change links. Recompute BUDDHI features and retrain for each partition. Training labels are obtained from `eval.labels.wallet_labels`; held-out truth enters aggregate scoring only. Production graph and score files are not touched. Input hashes and all metrics are in `research/bitcoin/results/buddhi-jaal-sensitivity/buddhi-jaal-sensitivity.json`.

**Protocol correction:** both partitions are full-capture components. R09 below shows that 51.37% of early-address same-cluster pairs at .20 require a post-boundary edge. Therefore, every BUDDHI score in the table is a retrospective/transductive diagnostic; none is a valid prospective time holdout metric. The pairwise JAAL values describe this full observed graph and do not certify point-in-time cluster quality.

| Quantity | Threshold 0.20 (current) | Threshold 0.30 (CIOH only) | Change |
|---|---:|---:|---:|
| JAAL pair precision | 0.5883 | 0.7959 | +20.76 pp |
| JAAL pair recall | 0.2979 | 0.2882 | −0.97 pp |
| JAAL pair F1 | 0.3955 | 0.4231 | +2.76 pp |
| Non-singleton impure clusters | 1,524 / 6,532 | 1,163 / 6,061 | −361 impure clusters |
| Largest cluster | 187 | 111 | −76 |
| BUDDHI actor PR-AUC | 0.06492 | 0.06905 | +0.00413 |
| BUDDHI actor ROC-AUC | 0.59141 | 0.59384 | +0.00243 |
| Actor Precision@20 | 0.60 (12/20) | 0.90 (18/20) | +6 hits in a 20-case list |
| Actor Recall@20 | 0.02439 | 0.03607 | +0.01168 |
| Transaction PR-AUC | 0.10058 | 0.11549 | +0.01491 |
| Transaction Precision@20 | 0.40 (8/20) | 0.35 (7/20) | −1 hit |
| Campaign recall by class-1 set inclusion | 187/196 = 0.9541 | 186/196 = 0.9490 | −1 campaign |
| Entities flagged by class-1 set inclusion | 10,149 | 9,964 | −185 |
| Campaign precision by class-1 set inclusion | 0.01843 | 0.01867 | +0.00024 |

The baseline rerun reproduces the saved canonical actor PR-AUC, ROC-AUC, actor and transaction Precision@20, and campaign recall exactly. This supports that the experiment follows the same split and model recipe. The precision/recall tradeoff agrees with JAAL's existing result: excluding weak change links substantially improves pair precision with a small pair-recall loss. BUDDHI actor PR-AUC improves modestly and the top-20 actor list changes materially; transaction top-20 is slightly worse; entity campaign recall changes by one. There is no single monotonic improvement across all grains.

The striking campaign precision is not evidence the model has no ranking value: it is specifically the consequence of interpreting conformal class-set inclusion as an alert action. The UI and evaluation should distinguish `risk ranking`, `class set includes illicit`, and `actionable alert after workload/precision policy`. The latter needs a validation-selected threshold or top-K budget, then untouched chronological test reporting, including false campaigns flagged.

## Research decisions and next experiments

1. Keep LightGBM as the current CPU-capable model implementation, but suspend claims that its current synthetic chronological metrics establish prospective performance. First make the feature/JAAL evaluation causal.
2. Treat class-set membership as uncertainty coverage, not an alert flag. Revise reporting to include entity/campaign precision, number flagged, false alert rate, top-K precision/recall, and calibration by time slice.
3. Re-run threshold sensitivity across multiple independent worlds/seeds and across JAAL perturbations that alter merges and splits, not merely two fixed confidence cuts. Rebuild graph partitions from prefix-only evidence for every model fit/calibration/test cutoff; preserve edge transaction ID and observation timestamp. The prior full second-seed generator attempt exceeded the 10-minute CPU budget; profile the generator or create a distribution-preserving fast sampler before repeating.
4. Add a campaign-level decision rule tuned only on validation (for example precision at a stated analyst workload) and report performance on a later test window. Consider entity-level bootstrap confidence intervals because 20 alerts and 196 campaigns are small denominators.
5. Evaluate whether the optional SGC/SVD structural representation adds value over the exact LightGBM features on identical rows/splits. Call it a fixed graph embedding; reserve “trained GNN” for a model that learns graph parameters. Check SVD memory/time before enabling it on the full graph.
6. Test label sensitivity: true-controller labels as an oracle upper bound; operational JAAL subject labels; and plausible merge/split perturbations. Do not make the synthetic majority label's confidence appear greater than the cluster evidence supports.

**Conclusion:** LightGBM is still a reasonable CPU model for these engineered tabular and graph-derived features, but current full-capture JAAL membership leaks future topology across its nominal chronological split. The threshold experiment only establishes transductive sensitivity; the campaign set-inclusion metric has very low precision. The next priority is a causal point-in-time graph/evaluation pipeline, then workload-aware ranking, label/cluster uncertainty propagation, and multi-seed robustness—not adding a fancier neural model before those defects are handled.
