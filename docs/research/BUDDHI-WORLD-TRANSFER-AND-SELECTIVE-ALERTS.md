# Frozen BUDDHI world transfer and selective alerts

Date: 2026-10-01. Experiments R21–R22. Exploratory findings, **no production promotion**.

## What was tested

The model selected earlier using canonical validation Precision@20 (then AP) was XGBoost. We reconstructed its exact training recipe, scaler and logistic calibration from the earlier matched windows and replayed all saved scores with maximum absolute error **0.0**. We then froze that bundle and the validation-selected alert threshold **0.38158950209617615**. The three new-world evaluations did not fit any model, scaler, calibrator or response threshold.

The input remains the 23-feature opt-in snapshot version described in [the snapshot report](BUDDHI-TEMPORAL-SNAPSHOT-EXPERIMENT.md): actual gross satoshi flows, opposite-side subject counterparties, activity and topology summaries. Graph evidence is bounded at each decision window end. No source/operator predictions or full-capture typology artifacts enter this model. Feature preprocessing applies signed log1p, then a scaler fit on canonical fitting rows; missing numeric values become zero. The classifier uses 300 trees, depth 5, learning rate .05, minimum child weight 10, row/column sampling .9, histogram tree construction, four CPU threads and seed 42. Logistic calibration fits the separate canonical calibration block, with C=1/max_iter=1000. Complete executable recipe and fitted bundle are preserved.

Each full-size generated world has 20,000 entities and requests 24,000 payments; resulting transaction counts include extra campaign/block transactions. Observable weak change is reconstructed from SETU's logic; the generator's hidden change-output index is never passed into the graph/features. Only research labels and evaluation use latent owners/campaign participants. The target means **observed campaign participation within the decision window**; it does not prove guilt or label every transaction of an owner illicit.

## Results

All entries concern pooled subject-window decisions from the last three equal-duration windows. Some controllers recur. Different worlds have different positives/prevalence; this is a transfer study, not an identical-target model contest.

| World | Positive subject decisions / all decisions | AP | Precision@20 | Precision@50 | Fixed threshold correct / answered | Precision |
|---|---:|---:|---:|---:|---:|---:|
| Canonical captured world | See preserved snapshot report | .1240 | .50 | See JSON | 12/34 | .3529 |
| Fresh chain seed 42 | 140/41,835 | .1498 | .50 | .52 | 14/33 | .4242 |
| Fresh chain seed 1337 | 543/48,944 | .1600 | .95 | .72 | 44/62 | .7097 |
| Fresh chain seed 2026 | 290/47,823 | .0860 | .75 | .40 | 20/50 | .4000 |

P@20 by consecutive test window:

| World | Window 7 | Window 8 | Window 9 |
|---|---:|---:|---:|
| Canonical | .40 | .45 | .00 |
| Fresh seed 42 | .60 | .25 | .00 |
| Fresh seed 1337 | .95 | .70 | .40 |
| Fresh seed 2026 | .25 | .50 | .40 |

The model has useful seed-dependent ranking signal. **Its fixed threshold did not preserve the intended 90% precision.** A score with logistic calibration is not thereby a portable confidence certificate. Campaign activity differs substantially: seed 1337 has 46/58/38 active true controllers in these windows, seed 2026 has 34/37/19, while canonical's final window has none. These are not equally hard instances.

## A replay problem uncovered

**Resolved chain diagnosis in R24:** weighted script-key order changed on sorted effective JSON reload. Original configuration reproduced every stored captured/campaign TXID. Loader replay is now repaired, with actual-world tests. See [MAYAJAAL-CONFIG-REPLAY-AUDIT.md](MAYAJAAL-CONFIG-REPLAY-AUDIT.md). R21 fresh42 still remains a different chain realization; its scores are preserved as measured.

The fresh seed-42 chain shares **zero transaction IDs** with the stored canonical chain/capture, and its campaign transaction IDs also differ. It is a same-seed new generation, **not a verified observation-only control**. This supersedes the preliminary observation-bridge wording in the experiment runner/commentary. The historical capture's generator/source versions and full effective reconstruction need an independent replay audit. Network censoring also differs because the new AML worlds observe the complete chain, but we cannot attribute result differences solely to that factor.

There is no claim of transfer to real Bitcoin. Seeds 1337/2026 had already been used for JAAL experiments; they were new to this frozen AML score evaluation but are not pristine holdouts for the whole research program. Future confirmation needs a preregistered untouched seed/config panel and a recoverable simulator/source manifest.

## Statistical selection experiment

A separate lightweight runner retained the fixed XGBoost ranking and used **28,820 negative calibration decisions** to score a candidate's null tail:

```text
p = (1 + number of calibration negatives scoring >= candidate) / 28,821
```

All score ties count conservatively. A verified positive-slope Platt mapping preserves raw XGBoost ordering, so the tail comparisons do not acquire new ranking information from calibration fitting. None of the test labels chooses a p-value cutoff. Each decision window is a separate test family.

| Procedure | Nominal setting | Observed result |
|---|---|---|
| Bonferroni | Family-wise error level .05 | No decisions in any evaluated window |
| Benjamini–Yekutieli | FDR level .10 | No decisions in any evaluated window |
| Benjamini–Hochberg | FDR level .10 | Seed 1337 window 7: 17/17 correct; seed 2026 window 8: 5/6 correct; no decisions elsewhere |

The p-value floor is **1/28,821 ≈ 3.47e-5**. Bonferroni's individual cutoffs for 12k–16k candidates are smaller than that floor, so this finite calibration set cannot generate discoveries under that rule. BY similarly provides little power here. BH can select a small group when multiple candidates occupy the extreme tail, but its dependence and p-value-validity conditions are not established for these changing graph partitions and recurring controllers.

**These are conditional-assumption diagnostics, not certified error guarantees.** BY can accommodate arbitrary dependence among valid p-values; it cannot repair invalid p-values caused by temporal/conditional shift. Zero decisions prevents false alerts but also retrieves no investigative leads. Do not present it as a superior operational detector. The simple tail implementation is not a reproduction of the full cfBH or SCoRE algorithms.

## What recent statistical literature contributes

- **Angelopoulos, Bates, Fisch, Lei and Schuster — Conformal Risk Control (ICLR 2024; manuscript revised 2025):** controls expected bounded monotone losses; code is public. A selected false-alert fraction is not automatically such a loss. The paper explicitly treats non-monotone risks separately. This supports precise risk definitions before adding a conformal wrapper. [Primary full text](https://arxiv.org/html/2208.02814v4).
- **Jin and Candès — Selection by Prediction with Conformal p-values (JMLR 2023):** studies model-based shortlisting with false-selection control under exchangeability; simulations, hiring and drug discovery, not Bitcoin. Code is linked. It targets our operational question more directly than class-label prediction-set inclusion; dependent campaign windows need an assumption audit. [Primary paper](https://jmlr.org/papers/v24/22-1176.html).
- **Zecchin, Hellström, Park, Shamai and Simeone — Generalization and Informativeness of Weighted Conformal Risk Control Under Covariate Shift (2025):** links set efficiency to training and shift; localization experiments. Its covariate-shift setting keeps the conditional label distribution fixed. Our campaign scheduling/observation changes do not establish that condition, so weighting alone cannot supply its guarantee. [Primary full text](https://arxiv.org/html/2501.11413v1).
- **Bai and Jin — Conformal Selective Prediction with General Risk Control (March 2026 preprint):** SCoRE distinguishes marginal and selective deployment risk, with e-values and exchangeability-based guarantees plus covariate-shift extensions. Simulations, drug discovery, clinical predictions and LLM abstention; public code. Worth a controlled follow-up, not a Bitcoin benchmark result or already implemented guarantee. [Primary full text and code link](https://arxiv.org/html/2603.24704v1).

These papers report different tasks and risk objectives; no published metric is compared numerically to our Bitcoin scores. Full reproduction and dataset-size/split extraction for their application studies remain pending; the review above concerns verified mathematical scope and applicability, not a completed benchmark replication.

## What to implement next

Keep the shipped LightGBM reference unchanged until corrected evaluation and a usable alert policy justify promotion. Retain XGBoost as a meaningful CPU challenger. Improve causal ownership/amount-flow/sequence features, then evaluate new policies on untouched worlds, including genuinely empty and ongoing-campaign windows. Measure workload-bounded ranking separately from selective confidence. An analyst can review prioritized evidence without accepting every ranked subject as a positive finding.

The experiment took **65.60 seconds CPU**, peak process RSS **~1.75 GiB**, and persisted roughly **1.5 MiB** of fitted bundle/scores rather than exporting large raw worlds. No GPU, dependency installation, generated-world deletion or commit. Scripts: `research/bitcoin/buddhi_world_transfer.py`, `snapshot_conformal_tail.py`. Results: `buddhi-world-transfer.json`, `buddhi-seed42-replay-diagnostic.json`, `snapshot-conformal-tail.json`. Exact source versions and SHA-256 records are preserved under `research/bitcoin/source-snapshots/`; labels remain research-only.
