# SHASTRA attribution audit: what it can and cannot establish

> Update after R21–R23: Fresh frozen-policy network transfer is now measured in [SHASTRA-INDEPENDENT-WORLD-EXPERIMENT.md](SHASTRA-INDEPENDENT-WORLD-EXPERIMENT.md): 92.66%/86.77% precision at 5.72%/4.92% coverage. The old timed-out-generator interpretation was superseded by R16 adapter profiling; source sufficiency and historical simulator replay remain unresolved.

**Status:** interim code-and-artifact audit, 2026-10-01  
**Scope:** current peer-origin/L1 estimator, point-in-time risks, recoverability, synthetic-world fit, and the next controlled experiments. This is not a claim of real-world Bitcoin origin attribution.

## Executive finding

SHASTRA is not a generic graph model. It is a source-peer ranking pipeline: deterministic first-spy and timing-MLE baselines plus a supervised CPU LightGBM candidate scorer, rolled up from peer IP to ASN/country. Its current features include observation timing/coverage, global peer-history statistics, peer graph degree, a shared-input-address/payer history, network class, and an analytic timing score. It therefore already uses useful relational/network evidence, though some summaries are lossy and some are full-capture rather than point-in-time safe.

The canonical `agency-v2` result is **not currently easy to use as a per-transaction L1 attribution product**. The learned model's offline ranking diagnostics report L1 top-1 0.4595 and top-3 0.7188 over the synthetic observed transactions, but the actual saved `origin_l1.parquet` abstains on 99.9817% of transactions. Its precision when it does act is 0.3333 on six rows (two correct). This is a small-denominator result, not a reliable operational precision estimate. The much larger 0.9345 “recoverable ceiling” means the true ASN is represented among candidate peers for that share under this generated world; it does not mean the model estimates it correctly, and it does not identify a person.

The first SHASTRA improvement should be a validated operating-point/abstention study and point-in-time feature correction, not a GNN. Existing work already measured a likely L1-only abstention defect: `tor_present` is triggered if *any candidate* is Tor, even when the transaction truth is not Tor. In the saved review, this refused 11,014 rows, only 952 of which were truly Tor, and the non-abstaining counterfactual had L1 top-1 0.4477. This is promising but remains a counterfactual metric, not promoted behavior; it needs a clean validation-selected rule and an untouched chronological test.

## Current implementation inspected

`src/chakravyuh/shastra/stage.py` reads normalized announcements, peers, transactions, the SETU arrival/ASN tables, JAAL graph edges, JAAL clusters, and addresses. It writes per-candidate estimates, one L1 operator row per transaction, and four heuristic typology-hit families. Labels enter through the CLI/evaluation door and are masked to the training window; inference-stage outputs do not include truth.

The candidate grain is one `(txid, peer_ip)` row. `src/chakravyuh/shastra/schema.py` currently gives the model 15 columns:

| Feature | Meaning / principal caveat |
|---|---|
| `delta_first_us`, `rank_in_tx` | Candidate arrival relative to the first observer and within-tx ordering. |
| `n_announcements`, `n_observers_seen`, `n_observers_blind`, `announce_spread_us`, `n_candidates` | How much and how broadly the candidate was observed. These are useful but depend on observer topology and capture regime. |
| `peer_frac_rank_one`, `peer_n_txids` | Peer-wide frequency of being first and transaction count, computed in SETU across the full capture. Future history can enter a nominal holdout feature. |
| `peer_degree` | Degree in JAAL's fused graph, also full-run/static in the present pipeline. It counts all edge kinds and has no event provenance. |
| `payer_shared` | Number of transactions linking the first input address to the peer; explicitly grouped over all announcements/transactions, including future events. This is both a useful linkage prior and a point-in-time leakage path. |
| `net_class_code`, `is_tor_exit`, `is_hosting` | Geo/vendor-derived peer class, if the optional local lookup was available. Categorical code is fed numerically to LightGBM. |
| `mle_logscore` | Analytic arrival-timing likelihood using earliness, dispersion, a rank-one prior, and configured relay-delay mean. It is a model-based score under MAYAJAAL's propagation assumptions, not independent evidence. |

No learned GNN appears in SHASTRA. The network graph is summarized as peer degree and a global peer-history prior; the arrival matrix is summarized by timing likelihood. The supervised model is native LightGBM binary classification (300 rounds, 31 leaves, minimum leaf 40, L2=1, deterministic single-thread CPU). Labels mark whether each candidate peer equals the known source peer. The first 70% time window supplies labelled rows; within that training window, the earliest 75% fits the booster and latest 25% calibrates raw scores using Platt logistic regression. At the canonical fit: 637,019 candidate rows, 23,116 txids, 11,259 positive rows, and 159,255 calibration rows.

The production score is not a calibrated probability of a legal person's identity. Candidate scores are capped so their per-transaction mass is at most one, with residual mass intended to mean “source not in this observed candidate set.” The candidate-level abstention policy prioritizes any Tor-class candidate, single-observer cases, too few announcements, and low top-two separation. L1 then aggregates candidate mass by ASN using ASN-wide first-rank frequency and can abstain for cross-ASN ambiguity. Calibration is applied to a global candidate classifier; no run-specific reliability diagram, Brier score, ECE, or confidence interval was found in the current origin report.

## Saved canonical measurements and their denominators

The reviewed artifact is `measurements/agency-v2/origin_accuracy.json` (seed 42, observer fraction 0.60; 33,049 broadcast transactions, 32,787 with an observed candidate). It contains 70/30 chronological reporting, but features are not all recomputed from history available at each row.

| Quantity | Saved value | Interpretation |
|---|---:|---|
| L0 correct source host present among candidate peers | 0.4824 | Candidate-set ceiling at host grain, all broadcasts denominator. |
| L1 correct source ASN present among candidate peers | 0.9345 | Candidate-set ceiling at ASN grain; not model accuracy. |
| Learned L1 ranking top-1 / top-3 | 0.4595 / 0.7188 | Ranking comparison over the observed estimate population; does not include abstention in top-1. |
| Shipped L1 acted coverage | 0.000182 | Six decisions among 32,787 transactions (reported rate is rounded). |
| Shipped L1 precision when acted | 0.3333 | Two correct among six decisions; highly uncertain. |
| Shipped L1 `cross_asn_ambiguous` | 21,706 | One principal abstention reason. |
| Learner fit/calibration | 637,019 / 159,255 candidate rows | Not 637k independent transactions; rows within each tx are correlated. |

These metrics answer separate questions. Candidate-set recoverability measures observational support. Ranking top-k measures ordering. Coverage says how many calls are made. Precision-when-acted measures correctness among calls. None can be substituted for another; the denominator and unit need to appear together in the UI/report.

## Leakage and validity findings

The chronological *label* mask is present and the calibrator is fitted on a later tail within training. But the model's feature substrate is built globally before the split:

1. SETU's `peers.parquet` computes `frac_rank_one` and `n_txids` across the entire capture; SHASTRA uses these on earlier and later rows.
2. `payer_links()` groups `(payer, peer)` over the entire announcement set, then joins the all-window count back to each transaction. Future transactions by a reused payer can change a training or holdout feature.
3. `peer_degree()` reads JAAL `graph/edges.parquet`. Current JAAL `SAME_OWNER` edges are full-capture, lack event timestamp/TXID, and therefore cannot be reconstructed as-of a cutoff. R09 already established this exact provenance issue for BUDDHI; SHASTRA also consumes that graph for peer degree and typology uses full-run clusters.
4. The feature/label rows for one transaction are grouped, but peer and payer history link rows across time. Row-random validation would be invalid; the current top-level time split is better, but does not fix global feature look-ahead or dependence between candidate rows.
5. The origin model is trained/evaluated on the same capture's simulator mechanics. There is one canonical seed. Existing independent-seed simulator generation attempt exceeded its 10-minute CPU budget and produced no metric. Therefore no cross-seed robustness or real-network transfer has been demonstrated.

Typology hits (`fan_out`, `coinjoin_like`, `peel_chain`, `structuring`) are rule-based morphology, not a trained anomaly model. They use full-run subject clusters and transaction histories; although they are evidence for case review, their saved `window_us=0` and lack of point-in-time bounds make them unsuitable as causal features without rebuilding snapshots. The names/behaviors overlap MAYAJAAL's generated campaign moves, so evaluate generator-label coupling explicitly before presenting their detection performance.

The current L1 abstention rule also appears overbroad for its target grain: a Tor peer candidate triggers `tor_present` for the whole transaction, even though L1 is an operator estimate and the candidate Tor exit need not be the source. Existing project audit measured this as a likely bug, not a settled fix. Keep L0 host Tor caution separate from L1 operator uncertainty; determine behavior with validation and a later test.

## Literature context (primary sources)

The peer-source problem is a network-inference task with known limits, not simply a model leaderboard. Fanti and Viswanath formalize Bitcoin's pre-/post-2015 propagation observation models as epidemic source inference and analyze near-optimal estimators; their evidence is simulated using a 2015 real topology snapshot, not modern labeled live-source ground truth ([NeurIPS 2017 paper](https://papers.nips.cc/paper/6735-deanonymization-in-the-bitcoin-p2p-network)). A measured-data study collected transaction announcements from more than a hundred modified clients and used a Naive Bayes model to associate addresses with clients, emphasizing that message propagation can support probabilistic linkage and is computationally cheap ([Biryukov, Khovratovich & Pustogarov, “Deanonymisation of clients in Bitcoin P2P network,” 2014](https://doi.org/10.1109/SP.2014.33); [PLOS follow-up / full methods](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0207000)). These are not directly comparable with our simulator's accuracy: collection vantage, protocol, labels, unit, observer coverage, and split differ.

The literature on Dandelion/Dandelion++ and Clover is primarily about changing propagation to resist source inference, not improving AML attribution. Dandelion++ explicitly studies deanonymization when protocol assumptions are violated ([Fanti et al., 2018](https://doi.org/10.1145/3224424)). Clover evaluates a simulated alternative relay design and reports lower first-spy precision under its attacker assumptions; these results support modeling protocol/evasion changes as stress tests, not importing those values as SHASTRA targets ([Franzoni & Daza, 2021](https://arxiv.org/abs/2109.00376)). The source papers distinguish a transaction's originating node from a person; network attribution cannot on its own close that identity gap.

## Same-capture LightGBM feature/threshold experiment (R11)

To answer whether graph/peer features add value and whether the default abstention is overly strict, a research-only script fit three deterministic LightGBM variants on the existing agency-v2 capture. The split was chronological: first 60% for model fit/calibration (the model helper internally uses the first 45% to fit and the 45–60% tail to Platt-calibrate), next 10% for threshold selection, final 30% for one test. Threshold selection was predeclared as the **maximum validation coverage** among candidate L1 separation floors with at least 100 answered rows and observed precision at least 90%. Floors were `{0, .0025, .005, .0075, .01, .0125, .015, .02, .04, .08, .15}`. The final test was not used to choose a threshold.

| Feature set | L0 host top-1 / top-3 | L1 ASN top-1 / top-3 | Validation policy |
|---|---:|---:|---|
| Full 15 features | .252 / .321 | .459 / .716 | floor .01; 137/144 correct (95.14%) |
| Drop direct peer-rank, peer-count, graph-degree, payer-history columns (11 remain) | .203 / .292 | .426 / .704 | no floor met the 100-answer and 90%-precision constraint |
| Local timing/observation only (7 features) | .188 / .253 | .405 / .697 | no floor met the constraint |

The selected full-model floor .01 produced **492/510 correct L1 answers** on the untouched final period: observed precision 96.47%, Wilson 95% interval 94.49–97.76%, and coverage 510/9,671 = 5.27% of holdout transactions with candidates. By comparison, the production .04 floor made only 1 decision on this test slice (incorrect). This supports the conclusion that the shipped .04 operating point is too strict for this fitted run and that the full feature set adds useful simulator signal relative to the smaller ablations.

This result is **not promotion-ready**. (1) It is one world/seed and simulator-conditional. (2) Peer-rank and payer/peer history and graph degree in the full model still use full-capture aggregates, so future evidence leaks into this nominal test. (3) `mle_logscore` itself includes a global peer-rank prior; therefore the “drop direct global peer/payer columns” ablation does not remove every route by which peer history enters. (4) The threshold validation/test transactions are one time stream, not independent worlds; the Wilson interval only describes binomial sampling uncertainty under a fixed policy and does not account for simulator or temporal dependence. (5) The answered object is a synthetic ASN/operator label, not the originating human. These figures warrant a causalized repeat and independent-seed experiment; they do not justify presenting 96.5% as a general attribution guarantee.

Reproducibility: `research/bitcoin/shastra_feature_ablation.py`; JSON `research/bitcoin/results/shastra-feature-ablation/shastra-feature-ablation.json`; final source SHA-256 `d868b8daad9a2cc5d66b9d6f2ea15167c97f26009b944d50c3f4149bd656cab5`; result SHA-256 `fbf57d22db8d026b7874eeb5d112fe8cb7105eedcd0cc1a148b8effab02ad0d6`. Inputs, metrics by validation/test, thresholds, feature lists, fit sizes, elapsed time, and limitations are in the JSON. Runtime was about 43 seconds CPU; no GPU or dependency install. The research script rewrites only its own small result JSON and does not alter canonical signals, models, reports, or generated data.

## Next experiments, in priority order

1. **Freeze and hash the current candidate frame, feature names, split boundary, and artifacts.** Keep the current inference outputs as a baseline; do not compare a mutated run to its own overwritten metrics.
2. **Point-in-time ablation:** compare (A) current all-capture features, (B) peer/payer aggregates computed only before each scoring timestamp/cutoff, and (C) no history/graph aggregates; retain event-time-only arrivals for each tx. Report L0/L1 top-k, abstention/coverage, precision at fixed coverage, PR-AUC only where a binary probability task is defined, and calibration/Brier on future time blocks.
3. **Uncertainty/decision curve:** on validation only, sweep L1 separation and evidence thresholds; show coverage vs precision and compare expected workload at 20/50/100 alerts. Pick an operating point before test. Add bootstrap intervals at transaction/day or campaign blocks, not candidate rows.
4. **Abstention audit:** isolate `tor_present`, low-announcement, single-observer, and cross-ASN-ambiguity slices. Test candidate-Tor vs true-origin-Tor separately. Promote only if an L1 policy improves coverage at a stated precision on untouched future blocks.
5. **Baselines/ablations before neural models:** first-seen, payer linkage, global vs causal Bayesian/Naive Bayes peer prior, logistic regression, LightGBM feature-family ablations. The published Bayesian user-identification method is a relevant low-cost comparator. For network-aware models, only test a graph/temporal embedding if causal LightGBM leaves measurable residual error tied to propagation neighborhood or sequence structure.
6. **MAYAJAAL validity:** separate train and test seeds/worlds; alter observer placement and fraction; include missing-source/Tor/VPN/CGNAT/port-sharing regimes; perform a generator audit so no label is a direct function of a feature family under test. A distribution-preserving faster simulator path is needed before repeating the timed-out full independent seed.

For the unresolved-source question, the measurable target in MAYAJAAL is `source_in_observed_candidate_set` and calibrated unknown mass under controlled censoring. No model can prove that a real person is absent from a partial dataset merely because there is no matching candidate; the correct product behavior is “not observed / insufficient evidence at the selected coverage,” with a measured false-absence rate under simulator censoring. This is a statistical coverage claim, not a proof of non-presence.

## Current recommendation

Keep LightGBM as the current deployable candidate scorer and preserve first-spy, timing-MLE, and payer-linkage as required baselines. Do not claim the current thresholded L1 output is operationally successful until abstention and point-in-time features are reevaluated. MAYAJAAL is valuable as a controlled measurement instrument, but its results must be labelled simulator-conditional; pair it with published Bitcoin chain datasets for transaction/AML transfer and avoid claiming real P2P origin accuracy from chain-only data. A GNN is not justified yet: first learn whether the existing temporal/peer signal survives causalization and out-of-seed testing.

## Audit of this research step

Inspected `CLAUDE.md` previously in the broader project audit, plus SHASTRA stage/feature/schema/estimator code, saved agency-v2 `_meta.json`, effective config, origin report, MAYAJAAL specification, prior BUDDHI topology audit, and experiment journal. Browsed primary/venue/author sources listed above. This step changed only research documentation/journal/progress; no production model, graph, frontend, keys, generated capture, dependencies, or user data were modified. No training or GPU job was run in this substep. Full generation remains disk-constrained (about 265 MB free at check), and the previous independent-seed generation attempt hit a 10-minute CPU stop with no output. No commit made.


## Causal candidate features and actual model/hybrid experiment (R12)

New opt-in API: `src/chakravyuh/shastra/causal.py`; reproducible runner: `research/bitcoin/causal_origin_benchmark.py`; full parameters, input/source SHA-256 hashes, time boundaries, timings and counts: `research/bitcoin/results/causal-origin-benchmark.json`. Production stage/model artifacts remain unchanged.

**Information available:** each transaction uses announcements within five seconds of its first observation. Every peer/ASN/payer history is an as-of join strictly before that first observation; the observer count is explicit configuration, not future-capture enumeration. Static peer enrichment assumes a fixed lookup snapshot. Full-capture SETU aggregates, static JAAL degree, and full-capture ASN priors are excluded. A simplified arrival score uses causal peer first-rank frequency, observed lead and spread; it is not an exact network likelihood. Tests confirm that appending future transactions or observations after the horizon cannot change past features.

**Training:** first 45% of elapsed time fits the classifiers and scaler; 45–60% fits Platt calibration; 60–70% selects response thresholds; final 30% evaluates. Training/calibration/validation exclude decisions whose five-second horizon reaches the next boundary. The already-used final time block is a research comparison, not an untouched final scientific test. Numeric count/time features use log1p, history fractions and analytic score retain their scales, and six-way network-class one-hot encoding yields 21 inputs. No illicit-transaction labels are used: this experiment predicts source peers/ASNs.

| Model | Candidate AP | Host top-1 | ASN top-1 | ASN top-3 |
|---|---:|---:|---:|---:|
| extra_trees | 0.3027 | 0.2337 | 0.4517 | 0.7123 |
| gbm_mean | 0.3261 | 0.2412 | 0.4597 | 0.7169 |
| lightgbm | 0.3212 | 0.2404 | 0.4580 | 0.7133 |
| logistic | 0.2402 | 0.2212 | 0.4457 | 0.7124 |
| logit_stack | 0.3375 | 0.2396 | 0.4565 | 0.7144 |
| neural_mlp | 0.3376 | 0.2370 | 0.4523 | 0.7116 |
| random_forest | 0.3187 | 0.2392 | 0.4541 | 0.7078 |
| xgboost | 0.3263 | 0.2421 | 0.4570 | 0.7170 |

All eight configurations use identical causal candidate rows and time blocks. The MLP has 21→64→32→1 linear layers, ReLU hidden activations, sigmoid output, 3,521 parameters; 12 epochs, batch 2,048, AdamW lr .001/weight decay .001, BCE positive weight sqrt(negative/positive), CPU seed 42. Native LightGBM: 300 rounds, 31 leaves, min leaf 40, lr .05, L2=1, four threads, deterministic/column-wise. XGBoost: 300 depth-5 trees, lr .05, min child weight 10, subsample/column fraction .9, L2=1, CPU hist/four threads. RF/ExtraTrees each 120 trees, depth 18, min leaf 20; RF bootstrap sample .6. Logistic regression uses C=1, maxiter 1,000. The mean hybrid averages calibrated GBM outputs; the logit stack trains logistic regression on raw LightGBM/XGBoost/MLP outputs in the out-of-fit 45–60% block.

The MLP improves candidate AP over LightGBM (.3376 vs .3212) while ASN top-1 is lower (.4523 vs .4580). The logit stack has similar candidate AP and fails to produce a convincing operational lift. The GBM mean has the highest ASN top-1 (.4597), a small same-world gain requiring paired/independent-world validation. Candidate P@20/P@50 equal 1 for all models; these are peer-candidate rankings, not AML investigative alerts or transaction-level accuracy.

**Response policy:** predeclared floor grid, at least 100 validation decisions and ≥90% observed validation precision, maximize coverage. Causal prior-weighted ASN aggregation with legacy exp/softmax separation selected .01 for LightGBM: validation 138/144=95.83%, test 459/486=94.44%, coverage 486/9,671=5.03%. Direct mass separation did not meet the validation gate for LightGBM at the tested floors. Mean-GBM direct separation with Tor veto passed validation (90.6%) but fell to 85.3% test precision; selecting a validation target does not guarantee future reliability. Softmax over already small weighted masses compresses separation to tanh((w1-w2)/2); changing aggregation is a distinct model/calibration experiment and must not reuse the old threshold. A margin is not a calibrated confidence probability.

**Missing source:** 46.81% of test transactions have their true source IP in the five-second candidate set. This is a host candidate ceiling, not an ASN ceiling, identity rate or absence proof. A supervised absence gate trains on raw parent-model outputs in 45–60% (avoiding same-block Platt-label reuse), calibrates in 60–65%, selects in 65–70%, tests afterward. AP .6563 versus absence prevalence .5319; AUC .6527, Brier .2263. No threshold met ≥50 validation decisions at ≥90% precision, so it makes zero absence claims. Isolation Forest is worse than random on this target (AUC .4454, AP .4749); do not interpret anomaly as missing-source evidence. Its score has no probability/Brier interpretation. “Insufficient observed evidence” remains defensible; “the person is absent” does not.

**Resources:** full eight-model run ~36.84 seconds CPU, whole-process peak RSS ~2.57 GiB. LightGBM fit ~1.63s and prediction over all 848,723 candidates ~.52s; XGBoost fit ~1.64s/predict ~.45s. These are local measurements, not deployment guarantees or per-request latency. MLP fit timing includes inference; its near-zero separate predict field is instrumentation overhead, not neural inference speed. No CUDA/package download.

**Limitations:** one simulator seed; candidate observations are dependent; source IP rather than person/ownership is the target; lookup snapshot assumption; five-second horizon changes the candidate population; no fresh-world test; no scientifically established winner. Earlier R11 used global features, so its numbers are not the same recipe. The initial R12 diagnostic artifact is retained separately; the rerun purges boundary horizons, removes same-block calibration reuse from the absence gate, and removes inappropriate Brier scoring of Isolation Forest novelty.


## R41 update: frozen answer policy fails under observer thinning

A paired nested capture test with 48, 24 and eight active observers, all causal histories rebuilt and no model refit, produced answered-source-ASN precision 94.4%, 51.1% and 26.4%. Answer coverage rose as evidence declined. The original .01 score-gap threshold cannot be presented as portable confidence. See [the complete coverage stress report](SHASTRA-OBSERVATION-COVERAGE-STRESS.md). Matching registry count alone would not prove matching placement or true coverage. No replacement policy is validated yet.
