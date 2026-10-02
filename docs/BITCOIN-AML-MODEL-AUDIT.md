# Bitcoin AML Model Selection & Architecture Audit

**Project:** CHAKRAVYUH / DRISHTI · SIH26146  
**Audit date:** 30 September 2026; experimental update 1 October 2026  
**Repository examined:** `c08138382b45adbc38864ace8c2377f1f5ba7203`  
**Canonical synthetic run:** `agency-v2`, seed 42, agency observer regime, observer fraction 0.60  
**Updated decision:** preserve the shipped LightGBM as the frozen reference. Matched causal experiments now favor XGBoost as the next CPU production candidate, with a working opt-in label-free scorer and TreeSHAP. A trained typed temporal window model is a promising CPU-capable research challenger; no automatic model replacement or confident-alert threshold is promoted. See [current decision and implementation plan](research/RESEARCH-DECISION-AND-IMPLEMENTATION-PLAN.md).

**Experimental follow-up:** Actual tabular, external graph, typed temporal graph, frozen independent-world and anomaly experiments now exist. See [living synthesis](research/RESEARCH-SYNTHESIS.md), [trained typed temporal models](research/TEMPORAL-HETEROGENEOUS-GRAPH-EXPERIMENT.md), [anomaly experiments](research/AML-ANOMALY-EXPERIMENT.md) and [append-only journal](research/EXPERIMENT-JOURNAL.md). Historical scores below retain their original protocol; they are not interchangeable with causal subject-window results.

This audit separates **observed implementation**, **saved measurements**, **new diagnostic calculations**, **published evidence**, and **proposed work**. A proposal in the master playbook or remodel plan is not evidence that it ships. Literature research used primary papers and official documentation; searches covered approximately 2019–2026, with older foundational references where necessary. It is a targeted architecture review, not an exhaustive systematic review or an independent reproduction of every paper.

## 1. Scope and evidence

The requested system ingests offline Bitcoin chain/network metadata, correlates IPs, wallets and transactions, performs genuine ML detection, and produces explainable ranked investigative leads. This is a different task from predicting Bitcoin prices, Ethereum phishing, or naming a transaction's origin host. Those tasks cannot supply interchangeable benchmark scores.

Read first: [CLAUDE.md](../CLAUDE.md), [master playbook](../CHAKRAVYUH-MASTER-PLAYBOOK.md), [active remodel plan](CHAKRAVYUH-REMODEL-PLAN.md), [P0–P3 audit](REMODEL-AUDIT-P0-P3.md), [data contracts](DATA-CONTRACTS.md), [frontend handoff](FRONTEND-HANDOFF-V2.md), [feature dictionary](FEATURES.md), and [historical performance measurements](PERF.md). Current frontend: `apps/drishti-v2`; `apps/drishti` is the older application.

| Question | Authoritative implementation / artifact |
| --- | --- |
| Risk features and aggregation | `src/chakravyuh/buddhi/features.py` |
| Booster, SHAP, conformal prediction | `src/chakravyuh/buddhi/model.py`, `recipe.py`, `stage.py` |
| Split and labels | `src/chakravyuh/eval/split.py`, `labels.py` |
| Ranking, AP, ROC-AUC, entity recall | `src/chakravyuh/eval/metrics.py` |
| External dataset and recipe | `src/chakravyuh/eval/external.py`, `vendor/elliptic/README.md` |
| Optional structural embedding | `src/chakravyuh/buddhi/embed.py`, `__main__.py` |
| Graph and tracing | `src/chakravyuh/jaal/{build,cluster,trace,mixer,stage}.py` |
| Network estimator inputs | `src/chakravyuh/shastra/{features,schema,estimate,stage}.py` |
| Synthetic labels | `src/chakravyuh/mayajaal/{adversary,entities,chain}.py` |
| Lead selection and explanations | `src/chakravyuh/vaani/{stage,evidence,counters,gloss}.py` |
| Current figures | `measurements/agency-v2/{model_report,elliptic_external}.json`, generated `scores/_meta.json` |
| Dashboard claims | `apps/drishti-v2/src/shell/screens/{WorldScreen,ModelIntelligence}.tsx` |

The saved artifacts remain unchanged. New diagnostic figures and hashes are in [audit JSON](audits/bitcoin-aml-ranking-2026-09-30.json), reproduced without training or overwriting reports:

```bash
.venv/bin/python scripts/audit_aml_ranking.py --run agency-v2 --out /tmp/bitcoin-aml-audit.json
```

## 2. Existing implementation: what actually ships

### 2.1 Two learned tasks, not one interchangeable model

**BUDDHI** is the illicit-risk model. It trains a native LightGBM binary classifier on **wallet subjects**: a predicted address cluster, or a singleton address not placed in a cluster. It does not directly train a temporal transaction-node classifier. Transaction-level evaluation maps input-address subject scores onto transactions using their maximum score.

**SHASTRA** estimates transaction origin candidates. Its ensemble also uses LightGBM, followed by Platt scaling when enough calibration examples exist; first-spy, timing estimation and ASN rollup provide other signals. Its target is candidate origin, not illicitness. BUDDHI receives summaries of SHASTRA outputs. Improving one task does not automatically improve the other.

The canonical score table contains **87,896 subjects**, all marked `gbm_v2`. No trained GCN, GAT, TGAT, TGN or HGT ships in this run. No independent Isolation Forest or autoencoder is implemented in BUDDHI. Morphology rules provide inputs to a genuinely fitted classifier; the classifier is not simply those rules renamed as AI.

### 2.2 LightGBM training

Pinned package: `lightgbm==4.5.0` in `pyproject.toml`. Native `lgb.train` avoids the sklearn-wrapper compatibility issue documented in `model.py`.

| Setting | Current value |
| --- | --- |
| Objective / rounds | Binary log loss / 300 rounds |
| Learning rate / leaves | 0.05 / 31 |
| Minimum examples per leaf / L2 | 40 / 1.0 |
| Feature / bagging fractions | 1.0 / 1.0 |
| Execution | CPU, one LightGBM thread, deterministic, row-wise histogram construction |
| Seed | Run seed; 42 for `agency-v2` |
| Imbalance adjustment | No explicit `scale_pos_weight`, `is_unbalance`, sample weighting or resampling in this recipe |
| Hyperparameter selection | Fixed parameters; no separate tuning-validation window or early stopping in the risk recipe |
| Input preprocessing | Numeric arrays; nulls become missing values. No global standardization in the default tree path |
| Categories | No native categorical feature declaration in BUDDHI; script diversity and other numeric summaries are used |
| Artifact lifecycle | Booster and calibrators exist in memory during stage training/scoring; this path does not save a reusable fitted model bundle |

The last quarter of training subjects, ordered by first activity, is used for conformal calibration; the earlier three quarters fit the booster. Saved metadata records **45,834 fit subjects**, **506 illicit fit subjects**, and **15,279 calibration subjects**. The 506 positives are the booster-fit count, not the calibration-positive count. Class-conditional calibration requires at least ten calibration examples per class and at least fifty calibration rows overall.

The installed recipe already runs offline on CPU. LightGBM supports missing values, categorical inputs and ranking objectives, but those capabilities should not be confused with enabled settings in our code. Weighted training may improve retrieval while damaging probability estimates; benchmark it and calibrate separately. [Official LightGBM parameters](https://lightgbm.readthedocs.io/en/stable/Parameters.html).

### 2.3 Complete current feature list: 33 inputs

| Group | Columns | Information captured / qualification |
| --- | --- | --- |
| Subject / ownership | `n_addresses`, `min_edge_confidence`, `n_heuristics`, `n_script_types` | Active cluster size, weakest heuristic link, heuristic diversity, address-format diversity; heuristic ownership is uncertain |
| Sends | `n_tx_sent`, `total_sent_sats`, `mean_sent_sats` | Activity count and outgoing-value distribution summaries |
| Receipts | `n_tx_received`, `total_received_sats`, `mean_received_sats`, `n_coinbase_received` | Incoming activity/value; mining-like behavior can supply counter-evidence |
| Flow / neighborhood | `balance_sats`, `n_counterparties`, `max_fan_out`, `fan_in_ratio` | Net flow, distinct counterparties, largest output/input multiplicity |
| Mixing / fees | `frac_equal_outputs`, `mean_fee_rate`, `fee_anomaly` | Equal-output participation and fee behavior; equal outputs do not prove mixing |
| Time | `median_dwell_us`, `burstiness` | Receipt-to-next-send delay and coefficient of variation of send gaps |
| Morphology | `peel_chain_depth`, `peel_leak_frac`, `structuring_frac`, `n_typologies`, `n_typology_txns` | Peel-like sends, value peeled, amounts under fixed round thresholds, detector-hit diversity/count |
| Host-origin fusion | `mean_p_origin`, `mean_origin_margin`, `frac_origin_abstained`, `frac_top1_tor`, `mean_n_announcements` | Confidence, separability, refusal rate, Tor share, observed propagation breadth |
| Operator-origin fusion | `mean_p_asn`, `mean_asn_margin`, `frac_l1_abstained` | Operator confidence, separation and refusal rate |

**Semantic corrections:** `fan_in_ratio` is actually the **maximum input-address count**, not a ratio. `peel_chain_depth` is the **number of peel-shaped sent transactions**, not the maximum linked-chain depth; the JAAL tracer's actual chain-depth result is not consumed here. The feature glossary currently overstates that depth. `burstiness` is gap variability, not automatically a transactions-per-hour rate. `fee_anomaly` is deviation from a window-wide median, not a fitted tail probability. Round-number bands are synthetic morphology proxies, not evidence that a Bitcoin reporting threshold exists.

**Present graph information:** counterparties, fan-in/out, soft-cluster structure, flow statistics, mixing morphology and indirect peer/origin signals. These are substantive graph-derived inputs, even though the final classifier consumes a table.

**Absent from the default risk matrix:** explicit degree/in-degree/out-degree columns, PageRank, betweenness, clustering coefficient, connected-component size, graph distance, suspicious-neighbor counts, direct wallet↔IP reuse counts, ASN identity/churn, geo-country identity, source/destination port statistics, rolling transaction-velocity rates, and actual multi-hop tracer depth. Some information exists upstream, in graphs, normalized peers, or lead counters; existence in the application does not mean the classifier consumes it.

SHASTRA has richer **candidate-level** network inputs: relative arrival time/rank, observer counts/blindness, announcement spread/breadth, peer activity and earliest-arrival frequency, graph peer degree, payer-linked announcements, and Tor/hosting/network-class indicators. BUDDHI receives compressed origin summaries, not this full matrix. Ports remain useful attribution evidence without being risk-model inputs. Unknown ASN and missing observations need explicit missingness handling rather than criminality defaults.

### 2.4 Graph representation

JAAL writes node/edge Parquet tables, with a Kùzu-backed graph path and graph views. The canonical graph has **163,577 nodes** and **1,206,827 edges**. Types extend beyond the prompt's simplified IP/wallet/TX triad: address, transaction, peer, cluster and ASN.

| Actual edge kind | Meaning | `agency-v2` count |
| --- | --- | ---: |
| `SPENDS` | Address → transaction input | 71,371 |
| `RECEIVES` | Transaction → output address | 150,833 |
| `ANNOUNCED_BY` | Transaction → observed announcing peer | 905,382 |
| `HOSTED_IN` | Peer → ASN | 2,954 |
| `SAME_OWNER` | Confidence-weighted heuristic address relationship | 36,357 |
| `MEMBER_OF` | Address → predicted cluster | 39,930 |

There is no explicit wallet→wallet transfer or transaction→transaction temporal edge kind in that saved edge table. Those relationships can be derived by traversing fund-flow edges, but a future learner would need a deliberate projection and timestamps. Exact UTXO spend links are preferable to inventing pairwise flows between every input and output. Bulk metadata may not provide previous-output references; any resulting flow inference must carry that limitation.

`SAME_OWNER` is not an identity fact: CIOH is confidence-weighted, change-address evidence is weaker, and CoinJoin-like transactions are set aside. JAAL's P2 tracer and mixer marks are useful evidence already built; feeding them into BUDDHI remains a separate integration task.

### 2.5 Scores, queue and explanations

`risk_score` is the booster's raw binary probability output. BUDDHI does **not** apply SHASTRA's Platt calibrator to illicit risk. Class-conditional MAPIE/LAC conformal prediction returns label sets, not a calibrated probability. Output states are `{0}` likely licit, `{1}` likely illicit, `{0,1}` unclear, and `{}` abstain.

The canonical population includes **14,427 likely-illicit**, **21,207 likely-licit**, and **52,262 unclear** subjects. VAANI retains every subject whose label is not `LIKELY_LICIT`, including unclear cases, and sorts by risk score with deterministic subject-ID tie-breaking. Consequently the queue has **66,689 leads**, not just twenty. A budgeted top-20 view is a retrieval policy, not a twenty-alert system.

Explainability is implemented with `shap.TreeExplainer`, retaining five feature contributions by **absolute magnitude**. Their values are on the native booster's log-odds scale, not five probability percentages. Signed contributions need to remain visible: a negative contribution is mitigating evidence. VAANI uses offline templates and linked evidence/counter-evidence, including `would_clear`; no hosted LLM is required.

`conf_low/conf_high` are currently generated by multiplying the score by `1 ± CONFORMAL_BAND` and clamping, or returning `[0,1]` for an ambiguous set. This is a **heuristic display band**, not a learned confidence interval and not a conformal probability interval. Relabel or replace it before presenting it as statistical certainty. SHAP explains model behavior; it does not establish a criminal fact, causal attribution, or legal admissibility.

## 3. Measurements: useful retrieval, incomplete validation

### 3.1 Saved canonical reports

| Metric / grain | Saved value | Interpretation |
| --- | ---: | --- |
| Actor/subject holdout count | 26,783 | New subjects under current first-activity policy |
| Illicit subjects (diagnostic replay) | 492 / 26,783 = 1.837% | About 1:53 illicit-to-licit; not the old plan's 0.6% figure |
| Precision@20 | 0.600 | Twelve illicit subjects in the twenty highest scores |
| Recall@20 | 0.024390 | Those twelve are only 2.44% of holdout illicit subjects |
| Actor PR-AUC field | 0.064920 | Repository's custom AP calculation; tie caveat below |
| Actor ROC-AUC | 0.591407 | Modest discrimination across the whole holdout |
| Transaction PR-AUC / ROC-AUC | 0.100579 / 0.691194 | Max input-subject score over 9,671 later transactions |
| Transaction Precision@20 | 0.400 | Eight illicit transactions among twenty |
| “Campaign recall” | 0.954082 = 187 / 196 | Actually illicit-entity hit recall, using `in_set_1` |
| Holdout conformal coverage, licit / illicit | 0.683466 / 0.947154 | Target is 0.90; majority coverage materially misses it |
| Abstain rate | 0.000 | Empty-set refusal only; ambiguity remains common |
| Rank-by-received-value baseline P@20 | 0.000 | Beats one weak rule, not RF/XGBoost/LR |

A classifier predicting every subject licit would obtain about **98.16% accuracy** here and find no investigative lead. This is why accuracy is unsuitable as the headline. Conversely, twelve hits in twenty can be operationally useful without implying that the model reliably finds most crime.

### 3.2 New read-only diagnostic replay

The companion script reproduces the saved subject universe and majority-label policy; it does **not** fix the temporal issues described below.

| Diagnostic | Value |
| --- | ---: |
| Precision@50 | 0.440 = 22 / 50 |
| Recall@50 | 0.044715 |
| Threshold-grouped AP (sklearn reference) | 0.065583 |
| Precision / recall / F1 at raw-score threshold 0.5 | 0.328571 / 0.046748 / 0.081851 |
| Brier score | 0.020058 |
| Constant holdout-prevalence Brier reference | Approximately 0.018032 |

The constant-prevalence comparison is a retrospective diagnostic, not a deployable forecast. Nevertheless, the risk probabilities do not beat even that reference on Brier score. A high top-K yield and poor probability calibration can coexist.

**Precision@50 is not implemented in the production evaluator.** The 0.44 above is an audit calculation, not a shipped dashboard metric. Synthetic threshold precision/recall/F1 and Brier are likewise absent from its current report; external Elliptic precision/recall/F1 are already reported.

### 3.3 AP arithmetic requires repair

`eval.metrics._auc(..., pr=True)` calls its result PR-AUC but computes a sequential average precision after sorting ties with licit examples first. It fails to group equal-score thresholds. With labels `[1,1,0]` and three identical scores, current AP is **0.583333**; standard threshold-grouped AP is **0.666667**. ROC-AUC correctly uses tied midranks. Both AUC paths return 0.0 when only one class exists, where an undefined/null result would be clearer.

Specify **average precision (AP)** versus trapezoidal PR-AUC explicitly. Fix tied-score handling, keep deterministic ID ties for top-K, and re-measure all candidate models together. Preserve historical reports with their evaluator version; do not quietly replace their arithmetic.

### 3.4 External validation is real, but narrower than the UI claimed

Saved `elliptic_external.json`: **29,379 training-window** labeled rows and **17,185 test** rows; F1 **0.766174**, precision **0.892052**, recall **0.671429**, ROC-AUC **0.936546**, reported AP **0.778296**. Threshold classification uses raw score ≥ 0.5, not conformal class membership. The training-window count includes the calibration partition.

This leg **retrains the same LightGBM/conformal recipe** on external numeric features. It does not apply the synthetic-trained model unchanged to real Bitcoin and does not validate IP-origin attribution. The edge list is not used. The vendored named export has **182 predictors after ID/time**, unlike the original 165 non-time predictors; external local/aggregate feature timing and dataset provenance require review. The feature file's SHA-256 is recorded, but label and edge hashes should also be recorded.

Its boundary is `min_time + floor(0.7 × time_span)`: for steps 1–49 this is 34, so training uses **1–33** and test **34–49**. The original 34/15 split uses training **1–34** and test **35–49**. That difference alone prevents a fair leaderboard comparison, in addition to different feature exports, thresholds, calibration and tuning.

The classic headerless feature CSV needs an explicit loader mode: current `pl.read_csv` assumes a header. Advertising both classic and named exports as interchangeable without format detection risks treating a first data row as column names. Frozen raw feature normalization may also embody information outside our training cut; it cannot be certified causal solely by sorting rows later.

## 4. Mandatory leakage and evaluation audit

**Verdict:** chronological intent is implemented, but the entire pipeline cannot currently be certified as strictly inductive or point-in-time leakage-free. Quarantining labels is valuable and insufficient by itself.

### 4.1 What the current split does correctly

The outer boundary is determined from the observable capture span with `train_fraction=0.7`. Transactions strictly before it belong to training; later ones belong to holdout. A subject is assigned by its earliest observed member activity. BUDDHI recomputes amount/activity/morphology summaries per outer half instead of directly using whole-capture address totals. Labels enter through a run-ID keyed door; training labels are filtered by the boundary. No raw truth column, IP string or address ID is included among the 33 model features.

This is substantially better than a shuffled split, but it evaluates **new subjects** after the boundary. Subjects appearing earlier are not rescored as returning subjects in the holdout queue. The operational system needs both new-entity and returning-entity evaluation.

### 4.2 Remaining leakage or validity risks

| Finding | Status / why it matters | Required correction |
| --- | --- | --- |
| Whole-capture SHASTRA inputs | **Confirmed code behavior.** `payer_links` explicitly uses the entire capture; peer activity, earliest-arrival frequency and graph degree also come from whole-capture tables | Recompute train-origin features from a prefix; for later scoring use only evidence available by the declared cutoff |
| Origin-fusion backdoor | **Confirmed dependency risk.** BUDDHI's windowed sends join origin outputs produced with the preceding whole-capture inputs | Fit upstream estimators on earlier data; use forward out-of-fold origin scores for downstream training |
| Cluster identities from full graph | **Confirmed design.** `subjects()` reads full-capture cluster membership before assigning train/holdout | Rebuild clustering at every cutoff; record when a heuristic edge became known |
| Later same-owner edges between early addresses | **Unblocked by current checks.** Both endpoints can exist early while the co-spend revealing ownership happens later; endpoint activity cannot date the relationship | Attach an `observed_at_us` / evidence-TX timestamp to edges; window by edge availability |
| Full typology detection, then hit filtering | **Potential sequence leakage.** Filtering hit TXIDs by window does not establish that detecting the sequence required no later hop | Run typology/tracing on the prefix, not on the completed capture |
| Fit versus calibration features | **Confirmed temporal mismatch.** Both partitions receive subjects aggregated across the entire outer training window; early fit rows can use events after the calibration partition starts | Recompute features with causal cutoffs for the fit, tuning and calibration periods separately |
| Window-wide fee reference | **Confirmed batch hindsight.** Median is calculated across the whole half | Fit an earlier reference or maintain a rolling past-only reference for point-in-time evaluation |
| Entity/campaign overlap | Predicted-subject disjointness does not establish ground-truth-owner or campaign independence across halves | Report overlap; add campaign/owner holdout stress tests and cluster-aware uncertainty estimates |
| Synthetic lifetime labels | Participants are labeled after completed campaigns; an early row can carry a label defined by later involvement | Declare entity-status labels versus event illicitness; timestamp involvement for event evaluation |
| Optional embedding edge filter | Endpoint first-seen times do not date `SAME_OWNER`/`MEMBER_OF`; un-timestamped clusters can bridge future structure | Event-time edges and historical cluster snapshots |
| Optional embedding preprocessing | **Confirmed comparability bug.** Each half independently fits standardization and an SVD basis; kind columns are also derived separately | Freeze feature vocabulary, scaler and projection on train; transform future graphs in that same coordinate system |
| Embedding promotion gate | Holdout labels decide availability after scoring; repeated use turns test into a selection set | Promote on validation only; evaluate the chosen architecture once on locked test |
| Transaction-level score timing | Subject score over a whole half is applied to all its later transactions, including earlier events in that half | Publish as retrospective batch scoring or use score-at-event-time inference |
| Queue versus evaluator population | Report ranks all holdout subjects; UI queue filters conformal states and includes subjects across the capture | Evaluate exactly the displayed eligible queue and its duplicate suppression |

These findings do not imply direct truth-file leakage by the default feature module. They show **future observable information** and graph membership can leak even when labels are perfectly quarantined. The amount of resulting optimism remains unmeasured; do not invent a corrected score.

**Quantified JAAL-topology audit (2026-10-01):** a prefix-only rebuild of JAAL components compared with the full-capture components confirms material leakage. JAAL's saved `SAME_OWNER` edges have null timestamps on all 36,357 rows and no transaction ID, while BUDDHI assigns subjects from the full-capture component file before applying its time split. Among 89,847 addresses first observed before the split, threshold 0.20's full graph asserts 373,100 same-cluster pairs; 191,656 (51.37%) do not exist in the prefix-only partition. 20,490 early addresses sit in components enlarged by later activity. At threshold 0.30, 120,113 of 267,458 early pairs (44.91%) are similarly future-dependent. See `docs/research/BUDDHI-UNCERTAINTY-RESEARCH.md` and `research/bitcoin/results/buddhi-jaal-sensitivity/buddhi-temporal-topology-audit.json`. This does not estimate how much the model score is inflated; it establishes that the reported chronological evaluation is not point-in-time safe. All agency-v2 BUDDHI metrics must be treated as retrospective diagnostics until graph snapshots are rebuilt at each fit, calibration, validation, and test cutoff.

### 4.3 Retrospective batch and prospective forecasting must be distinct

The PS requires offline **bulk analysis**, so using all evidence in an uploaded capture at investigation time can be legitimate. Call that a retrospective batch protocol. It does not support the stronger claim that a model trained without future information predicts each transaction when it happens.

Report two evaluations where useful:

1. **Frozen-model later-batch retrieval:** fit only historical batches; analyze a completed later capture. Future-within-capture evidence is allowed only within the declared later batch. Training examples must not be rebuilt with test-batch evidence.
2. **Point-in-time chronological replay:** score each event or daily cutoff using prior history and evidence available then. Update graph and memory in a documented order. No later relationship, confirmation or label enters the prediction.

For selection, use **earlier TRAIN → later VALIDATION → later CALIBRATION → untouched TEST**. If examples are scarce, use forward-chaining folds inside TRAIN/VALIDATION and reserve a final calibration interval. Choose timestamp blocks, not random row fractions; keep tied timestamps and TX candidate groups together. Purge examples whose feature or outcome windows cross cutoffs, and apply a gap when the label maturation horizon requires it. Fit imputation/scaling/embeddings on training only. Later inference may use previously observed history; it should not gratuitously delete all train-to-test edges.

## 5. Synthetic dataset: what performance establishes

MAYAJAAL simulates transactions and network observation; `adversary.apply_typologies()` marks entities that actually participated in completed campaigns as illicit and assigns their campaign morphology. Labels are **not** a direct Boolean threshold over the 33 features. However, campaign moves produce peels, mixing, fan-out and related behaviors, while our engineered features and typology detectors measure those same behaviors.

That is **generator–detector coupling**, even without label-file leakage. It can favor trees when morphology is encoded as thresholds. It can also favor a GNN if the synthetic graph is constructed around recognizable laundering motifs; complexity does not remove circular validation.

The promised per-campaign `detectability`/evasive mechanism in the remodel plan is not implemented in the adversary code inspected. Do not describe it as a tested robustness feature. Current modest AP also shows the dataset has not simply yielded near-perfect classification.

Before a model replacement, run independently seeded worlds; altered dwell/fan-out/amount policies; unseen campaign families; evasive long-dwell and CoinJoin-heavy cases; and benign exchanges, miners, batch payments and wallet consolidation that resemble suspicious morphology. Hold out complete campaigns across selection folds. Audit which network/operator proxies correlate with synthetic labels. Ablate `n_typologies` and `n_typology_txns` to separate learning from the detector's hand-engineered signal.

External Elliptic replication helps validate a **training recipe** on independent labels. It does not establish synthetic-to-real transfer, the correctness of wallet clustering, or real network-origin accuracy. Elliptic++ can later support actor/transaction tests but supplies no matching P2P IP observations. No public benchmark reviewed here validates our entire IP-wallet-TX fusion task.

## 6. Literature review: evidence ledger

Results below describe **each paper's own protocol**. They are not a cross-paper ranking. “Code not verified” means this review did not establish an available author implementation, not that none exists. Offline reproduction requires legally obtained data, pinned wheels/source, checkpoints and preprocessing; a public abstract alone is insufficient.

### 6.1 Direct Bitcoin / cryptocurrency evidence

**P1 — Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics (2019).** Mark Weber, Giacomo Domeniconi, Jie Chen, Daniel Karl I. Weidele, Claudio Bellei, Tom Robinson, Charles E. Leiserson. Elliptic: 203,769 TX nodes, 234,355 edges, 4,545 illicit and 42,019 licit labels; 166 features including time and neighborhood summaries. Illicit-node classification; LR, RF, MLP, GCN/Skip-GCN, EvolveGCN and embedding hybrids. **Temporal train 1–34, test 35–49.** Illicit F1: RF/all-features 0.788, RF+GCN embeddings 0.796, GCN 0.628, Skip-GCN 0.705; temporal comparison EvolveGCN 0.720. Reports precision/recall and micro-F1. Features help RF substantially; post-market-shutdown degradation remains. Dataset released; exact experiment code not verified here. CPU tabular reproduction is realistic; GNN reproduction needs additional dependencies. This is not evidence that GNNs or trees always win. [Primary paper](https://arxiv.org/html/1908.02591).

**P2 — Phishing Scam Detection on Ethereum: Towards Financial Security for Blockchain Ecosystem (2020).** Weili Chen, Xiongfeng Guo, Zhiguang Chen, Zibin Zheng, Yutong Lu. Filtered Ethereum dataset: 534,820 addresses, 323 phishing labels, 7,795,044 transactions. Cascade graph/statistical features and dual-sampling LightGBM ensemble; address phishing classification. **Five-fold cross-validation, not future-only evaluation.** Table 1: ensemble F1 0.8122, precision 0.8196, recall 0.8050, AUC 0.8097; ordinary LightGBM performs poorly there. Highlights imbalance handling and graph-derived tabular inputs. Code/data release promised; runnable author package not verified. Offline feasible after extraction, but the large ensemble is not our lightweight recipe. Ethereum account phishing differs from Bitcoin UTXO AML; these metrics cannot validate BUDDHI. [IJCAI paper](https://www.ijcai.org/proceedings/2020/0621.pdf).

**P3 — Inspection-L: Self-Supervised GNN Node Embeddings for Money Laundering Detection in Bitcoin (2022).** Wai Weng Lo, Gayan K. Kulatilleke, Mohanad Sarhan, Siamak Layeghy, Marius Portmann. Original Elliptic scale and features as P1. DGI-trained GIN encoder followed by RF on embeddings plus local/all features. **Encoder trains on 34 historical graphs; frozen encoder extracts embeddings for 15 later graphs.** Precision/recall/F1/ROC-AUC; all-features+embeddings F1 0.828, embedding-only F1 0.061. Remains vulnerable to temporal shift. Reports Linux, 12 GB RAM and P100 16 GB GPU. Exact author code availability not verified here; concept reproducible offline with PyTorch/PyG and data. This supports a conditional hybrid experiment, not embeddings replacing interpretable features. [Primary paper](https://arxiv.org/html/2203.10465).

**P4 — Detecting Anomalous Cryptocurrency Transactions: an AML/CFT Application of Machine Learning-based Forensics (2022 preprint).** Nadia Pocher, Mirko Zichichi, Fabio Merizzi, Muhammad Zohaib Shafiq, Stefano Ferretti. Elliptic, 203,769 nodes / 234,355 edges; local and aggregate features. Supervised illicit-TX classification compared across conventional classifiers, GCN and GAT. Illicit F1: GCN 0.844, GAT 0.723, RF with aggregates 0.782. Precision/recall and micro-F1 also reported. **A complete causal temporal split/adjacency contract was not established from the inspected methods; treat as protocol-unverified.** GAT overfitting required strong regularization. Exact runnable author code not verified. Offline reproduction possible with graph libraries, but reported performance should not be transferred to our split. [Primary paper](https://arxiv.org/html/2206.04803).

**P5 — Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics (2023, KDD).** Youssef Elmougy, Ling Liu. Elliptic++: 203k transactions, 822,942 addresses, approximately 1.27M temporal address occurrences; enhanced TX attributes and 56 actor features. Four graph views: TX flow, actor interaction, address–TX and entity clusters. LR/RF/XGB/MLP/LSTM; illicit actor and TX classification. **Train steps 1–34, test 35–49.** Refined RF: TX precision/recall 0.986/0.727, actor 0.921/0.802. Also analyzes feature importance and model agreement. Feature export, repeated actors and preprocessing differ from our subject task. [Author dataset repository](https://github.com/git-disl/EllipticPlusPlus) is available; full experiment reproduction requires checking its scripts/protocol. CPU-friendly after data preparation. Multiple node types help feature engineering too; the dataset does not imply an HGT requirement. [Primary paper](https://arxiv.org/html/2306.06108).

**P6 — The Shape of Money Laundering: Subgraph Representation Learning on the Blockchain with the Elliptic2 Dataset (2024).** Claudio Bellei, Muhua Xu, Ross Phillips, Tom Robinson, Mark Weber, Tim Kaler, Charles E. Leiserson, Arvind, Jie Chen. 49,299,864 cluster nodes, 196,215,606 edges, 121,810 labeled subgraphs; 43 node/95 edge features supplied but omitted in reported training. Subgraph suspicious-flow classification; GLASS versus GNN-Seg/Sub2Vec. **Random 80/10/10 split, not chronological.** GLASS test PR-AUC 0.208, ROC-AUC 0.889, **micro-F1** 0.933. Linux experiments used 160 CPU cores/1.2 TB RAM, no GPU. An [official dataset/tool guide](https://github.com/MITIBMxGraph/Elliptic2) is available; large offline replication still needs resource and data-access planning. Useful evidence for multi-hop subgraph tasks; resources and labels differ drastically from our app. The micro-F1 is not illicit-class F1. [Primary paper](https://arxiv.org/html/2404.19109).

**P7 — Detecting Anomalies in Blockchain Transactions using Machine Learning Classifiers and Explainability Analysis (2024).** Mohammad Hasan, Mohammad Shahriar Rahman, Helge Janicke, Iqbal H. Sarker. IEEE Bitcoin 2011–2013 data: 30,248,134 records, only 108 malicious, twelve attributes including malicious-related quantities. Tree/voting/stacking classifiers, XGBCLUS resampling and SHAP. Training/test separation with sampling on training is described; **chronological test protocol not established**. Reports TPR/FPR/ROC-AUC; gradient boosting with XGBCLUS ROC-AUC 0.92. Audit label-derived “malicious” inputs before reproduction. Exact author code not verified; CPU possible but full-data memory is substantial. Supports explanation and imbalance experiments, not direct comparison with Elliptic or our anomaly branch. [Primary paper](https://arxiv.org/html/2401.03530).

**P8 — Graph Network Models To Detect Illicit Transactions In Block Chain (2024 preprint).** Hrushyang Adloori, Vaishnavi Dasanapu, Abhijith Chandra Mergu. Original Elliptic scale; local/all features, embeddings. LR/RF/XGBoost/GCN/GAT/GAT-ResNet illicit classification. **Temporal 34/15 split stated.** Precision, recall, illicit and micro-F1; results discussion says RF and XGBoost outperform the other models despite the abstract emphasizing GAT-ResNet potential. Numerical result figure not independently transcribed here. Extensive graph training/tuning; no separate untouched selection protocol established. Exact author code not verified. Offline concept feasible, but this is lower-weight preprint evidence with internal claim/result tension, not a SOTA justification. [Primary paper](https://arxiv.org/html/2410.07150).

**P9 — When Graph Structure Becomes a Liability: A Critical Re-Evaluation of Graph Neural Networks for Bitcoin Fraud Detection under Temporal Distribution Shift (2026 preprint).** Saket Maganti. Elliptic scale; 165 non-time raw features, alternative adjacency constructions. RF/XGB/LR/MLP/GCN/GraphSAGE/GAT and hybrids; train ≤34, later test, ten-seed comparisons. Reported illicit F1: RF 0.821, XGB 0.775, GraphSAGE 0.688; precision/recall/AUC also reported. **Quality caveat:** methods explicitly use test-period F1 for early stopping; final test is therefore not untouched. Abstract claims released code but comments say “Code to be released soon”; availability not established. Main benchmarks on M4 CPU/16 GB, selected T4 checks. Useful leakage warning and hypothesis, not decisive evidence against temporal GNNs, which remain future work there. [Primary paper](https://arxiv.org/html/2604.19514).

**P10 — Illicit Bitcoin transaction detection via feature-gated temporal graph learning (2026, Scientific Reports).** Na Han, Ruixian Zhang, Xiaoyun Liu, Haining Zhang. Original Elliptic scale; 94 local inputs, unknown nodes retained as graph context. FG-EGCN combines EvolveGCN-H-style evolution, preserved feature branch, adaptive gate and focal loss. **Historical 34 steps versus later 15; best validation-F1 checkpoint.** Illicit precision/recall/F1 0.834/0.722/0.774; micro-F1 0.971. Exact validation boundaries require reproduction review. PyTorch 2.3; reported hardware A100 40 GB. Processed splits/embeddings unavailable at submission, available on request; code release not established. Promising feature-preserving temporal design, but no P@20 result or network-IP task. Offline reproduction needs obtaining artifacts; reported GPU is not a proven minimum. [Primary paper](https://www.nature.com/articles/s41598-026-53783-y).

**P11 — Bidirectional fusion heterogeneous graph networks for semi-supervised Bitcoin transaction anomaly detection in dynamic transaction graphs (2026, PLOS One).** Bo Xiao, Wei Yin. Elliptic++ variant: 203,769 TX nodes, 920,691 address nodes, four relation types; 167 TX/56 address dimensions. BF-HGN: GCN/RGCN, evolving bidirectional recurrence and pseudo-anomaly generation. Illicit labels are hidden into unknown during training. **Train 1–30, validation 31–35, test 36–49.** Reported TX/address F1 0.6301/0.5784; precision/recall too. Address count and supervision differ from P5; bidirectional inference must be checked against event-time availability. Dataset linked; author model code not established. CPU/GPU timings not established. Offline research plausible after implementation, but not comparable to our fully supervised risk recipe and no IP nodes. [Primary paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0351051).

**P12 — An Explainable Machine Learning Framework for Detecting Illicit Bitcoin Wallets with Graph Temporal Features (2025).** Mario Trerotola, Davide Calvaresi, Domenico Parente. Institutional publication record describes Elliptic, Chainabuse and a recent-transaction sample; graph/temporal/monetary features, RF and SHAP under three labeling scenarios; F1 up to 0.92. **Screened, not accepted as benchmark evidence:** full paper download was unavailable in this audit; dataset size, exact split, temporal causality, all metrics and code availability remain unverified. Offline reproduction cannot be certified. Relevant explanation-first direction; no inference that 0.92 is achievable here. [Author institution record](https://publications.hevs.ch/index.php/publications/show/3228).

### 6.2 Foundational temporal, heterogeneous and anomaly methods

| Paper / authors / year | Dataset, size and task | Features, split, metrics and findings | Limitations, code and offline feasibility |
| --- | --- | --- | --- |
| [Inductive Representation Learning on Temporal Graphs](https://arxiv.org/html/2002.07962), Da Xu, Chuanwei Ruan, Evren Körpeoglu, Sushant Kumar, Kannan Achan, 2020 (TGAT) | Wikipedia 9,227 nodes/157,474 events; Reddit 11k/672,447; industrial 170,243/2,135,762. Future links and dynamic node labels | Time encoding plus attention over past interactions and edge features; chronological evaluation and held-out unseen nodes. AP/accuracy; inductive Wikipedia AP 0.9399 | Not Bitcoin AML; link AP is not illicit AP. [Author code](https://github.com/StatsDLMathsRecomSys/Inductive-representation-learning-on-temporal-graphs); offline after dependency/data packaging |
| [Temporal Graph Networks for Deep Learning on Dynamic Graphs](https://arxiv.org/html/2006.10637), Emanuele Rossi, Ben Chamberlain, Fabrizio Frasca, Davide Eynard, Federico Monti, Michael Bronstein, 2020 | Wikipedia/Reddit as above; Twitter 8,861 nodes/119,872 events. Future links/dynamic classification | Node memory, timed messages, GRU updates and sampled attention; chronological 70/15/15. AP/ROC-AUC and efficiency comparisons favor TGN variants | General event graphs, no Bitcoin illicit P@K. Stateful replay adds burden. [Author code](https://github.com/twitter-research/tgn); offline feasible, CPU possible |
| [EvolveGCN: Evolving Graph Convolutional Networks for Dynamic Graphs](https://arxiv.org/abs/1902.10191), Aldo Pareja, Giacomo Domeniconi, Jie Chen, Tengfei Ma, Toyotaro Suzumura, Hiroki Kanezashi, Tim Kaler, Tao B. Schardl, Charles E. Leiserson, 2019 preprint / AAAI 2020 | Dynamic link/edge/node tasks, including Elliptic; Bitcoin size as P1, other graph sizes differ | Snapshot GCN parameters evolved by GRU/LSTM. Temporal evaluation; task-specific F1/MRR measures. Bitcoin findings also documented in P1 | Snapshot resolution differs from microsecond P2P events. [Author code](https://github.com/IBM/EvolveGCN); offline feasible with graph dependencies |
| [Heterogeneous Graph Transformer](https://arxiv.org/abs/2003.01332), Ziniu Hu, Yuxiao Dong, Kuansan Wang, Yizhou Sun, 2020 | Open Academic Graph, 179M nodes/2B edges; academic downstream tasks | Type-dependent attention/transforms, relative temporal encoding, heterogeneous sampling. Reports improvements against its own GNN baselines | Not an AML dataset or causal Bitcoin validation; task splits/metrics require task-specific review. [Author code](https://github.com/acbull/pyHGT); our small sampled graph feasible offline, original scale unsuitable |
| [GNNExplainer: Generating Explanations for Graph Neural Networks](https://arxiv.org/abs/1903.03894), Rex Ying, Dylan Bourgeois, Jiaxuan You, Marinka Zitnik, Jure Leskovec, 2019 | Synthetic motif and real graph benchmarks; node/graph explanations, not Bitcoin risk | Learns feature/edge masks; evaluates explanation accuracy on motifs and qualitative real cases; no chronological AML test | Explanations need fidelity/stability tests; not crime proof. [Author code](https://github.com/RexYing/gnn-model-explainer); offline, potentially costly per lead |
| [Variational Graph Auto-Encoders](https://arxiv.org/abs/1611.07308), Thomas N. Kipf, Max Welling, 2016 | Cora/Citeseer/Pubmed citation graphs; link reconstruction, not Bitcoin anomalies | GCN encoder and latent decoder; held-out links, AP/ROC-AUC; no temporal AML split | Reconstruction is not calibrated illicitness. [Author code](https://github.com/tkipf/gae); offline small-graph baseline only |
| [GRASPED: Graph Anomaly Detection using Autoencoder with Spectral Encoder and Decoder](https://arxiv.org/abs/2508.15633), Wei Herng Choong, Jixing Liu, Ching-Yu Kao, Philip Sperl, 2025 preprint | Real-world graph anomaly benchmarks; full sizes/protocol not verified in abstract | Spectral graph encoder plus structural/attribute reconstruction; reports improvements, no numeric AML claim adopted here | General anomaly research; Bitcoin applicability, time split and exact runnable code not established. Not a reason to add GAE before SIH |

“Temporal GCN” is a family, not a single standard model. Snapshot GCN+GRU/LSTM and EvolveGCN are different from continuous-time TGAT and memory-based TGN. HGT already has a relative temporal encoding mechanism; adding timestamps to static edges alone still does not guarantee causal event replay. [EvolveGCN](https://arxiv.org/abs/1902.10191), [HGT](https://arxiv.org/abs/2003.01332).

### 6.3 Tabular foundations and explanation support

[XGBoost: A Scalable Tree Boosting System](https://arxiv.org/abs/1603.02754) (Tianqi Chen, Carlos Guestrin, 2016) and [LightGBM: A Highly Efficient Gradient Boosting Decision Tree](https://papers.nips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html) (Guolin Ke, Qi Meng, Thomas Finley, Taifeng Wang, Wei Chen, Weidong Ma, Qiwei Ye, Tie-Yan Liu, 2017) establish scalable boosting systems, not a Bitcoin ranking winner. Both have mature offline implementations. Tree SHAP can explain either; CPU histogram training is available for both. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

[Why do tree-based models still outperform deep learning on typical tabular data?](https://papers.neurips.cc/paper_files/paper/2022/hash/0378c7692da36807bdec87ab043cdadc-Abstract-Datasets_and_Benchmarks.html) (Léo Grinsztajn, Edouard Oyallon, Gaël Varoquaux, 2022) studies 45 tabular datasets and training/tuning behavior. It motivates a strong tree baseline; it does **not** provide an Elliptic GCN/RF performance band. The old World panel's attribution of such bands to this paper was unsound.

### 6.4 What is and is not comparable

Compare candidate models only within one dataset/export, label policy, target grain, chronological cut, feature-availability policy, tuning budget and evaluator. P1/P3/P5/P8 all state temporal evaluation; the previous dashboard's blanket “published GNN results use easier transductive splits” was false. Even a temporal label split does not by itself prove prefix-only feature and adjacency construction.

P6 is a random **subgraph** task with micro-F1. P11 hides illicit training labels and uses a different address export. P2 is Ethereum phishing with cross-validation. P9 has test-based checkpoint selection. P12 has an unverified full protocol. None supplies a fair numerical comparison to our 0.766 external F1. Our synthetic subject AP, external TX F1, and host/ASN accuracy must remain separate.

## 7. Models against the actual workflow

### 7.1 Classical and tabular models

**Logistic Regression:** mandatory simple learned baseline. Train regularized coefficients on the same features after train-only imputation, log transforms for heavy-tailed positive quantities and scaling. Compare unweighted and class-weighted fits; calibrate if weighted. Coefficients and signed feature contributions are accessible, although correlated features weaken causal interpretation. Low CPU/memory cost. Limited nonlinear interactions unless engineered explicitly.

**Random Forest:** serious challenger, not a “weaker model” already rejected. Handles nonlinear patterns and mixed feature scales, supports class/sample weighting, and permits permutation importance and Tree SHAP. Constrain depth/minimum leaf size; numerous unconstrained trees can consume substantial RAM and slow explanation. Bagging robustness does not remove temporal shift or label leakage. Current code has no matched RF experiment; historical Bitcoin evidence makes it worth testing.

**XGBoost:** serious challenger with CPU histogram training, regularization, missing-value handling, imbalance weights and SHAP. Sorted classifier scores already produce a ranked queue. Pairwise/listwise ranking objectives require meaningful query groups and relevance labels; do not invent query groups merely to call it a ranker. Extra dependencies and a second recipe are justified only by a matched performance or operational gain. [Official XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

**LightGBM:** fits the existing 33-column problem well and preserves current contracts. Efficient nonlinear tabular learning can combine morphology, graph summaries and temporal statistics without loading a learned graph encoder at inference. It does not inherently model sequences: the temporal information is what the feature builder supplies. Native categorical handling could later represent validated categories, but encoding operator IDs may memorize synthetic network assignments. A high-cardinality identifier is not automatically a useful category. Current package/version settings remain authoritative; no library upgrade is implied by this audit.

### 7.2 Static graph models

**GCN:** learns shared transformations of neighborhood-aggregated features. A homogeneous transaction-flow graph is a cheap research comparator; an IP-wallet-TX graph needs type treatment or careful projection. Can exploit multi-hop context but may smooth illicit actors toward legitimate exchanges; sparse changing neighborhoods, uncertain ownership and relay noise are serious issues. A few graph layers do not reconstruct an arbitrarily long laundering path. Small CPU training is possible, GPU helps larger experiments. [GCN foundation](https://arxiv.org/abs/1609.02907).

**GAT:** learns attention-weighted neighborhoods rather than fixed normalized averages; multiple heads increase edge activation costs. May suppress irrelevant neighbors, but cannot infer trustworthy attribution just because attention is high. Attention weights are not sufficient investigator explanations. Static GAT needs extra engineering for time and node/edge types; it has no demonstrated matched advantage here. [GAT foundation](https://arxiv.org/abs/1710.10903).

### 7.3 Temporal and heterogeneous models

**Temporal GCN / EvolveGCN:** snapshots plus recurrence capture changing graph distributions, with evolving parameters rather than a fixed identity embedding. Suitable for coarse daily/batch evolution; snapshotting can blur ordering and dwell inside a batch. Requires graph snapshots, recurrent-state discipline and more tuning. Evaluate a feature-residual branch if explored; do not discard raw features simply to force structural learning.

**TGAT:** functional time encoding and attention over neighbors available before a query time can learn whether timing and relational context jointly indicate rapid forwarding or repeated coordination. Sampling depth can grow computation substantially. It is an attractive stateless research comparator, but historical transactions with mostly new addresses may provide little reusable sequence signal.

**TGN:** timed messages and persistent node memory can represent behavior of returning wallets/peers between events. Requires predictable memory reset, chronological replay, checkpointing, cold-start behavior and an explicit score-before-update policy. A transaction is usually a one-time node, so useful state generally resides in wallets, peers or actors. Being a temporal graph does not establish that this synthetic graph rewards persistent memory.

**Heterogeneous GNN / HGT:** type- and relation-specific processing can distinguish money movement from peer announcements and uncertain same-owner evidence. This avoids treating a relay relationship as a transfer. It can learn paths such as wallet→TX→peer→ASN and wallet→TX→wallet→TX while respecting their different meanings. Benefits require informative, time-dated relations and reliable synthetic variation; adding types creates parameters, sampling and explanation burden. Start with a small relation-aware GraphSAGE/RGCN-style encoder before an HGT-scale model. [HGT](https://arxiv.org/abs/2003.01332), [GraphSAGE](https://arxiv.org/abs/1706.02216).

**Temporal heterogeneous GNN:** the closest conceptual match to the full PS, but the most demanding implementation. Preserve typed events, source-port/observer identities where available, time gaps, money amounts and edge confidence. Add temporal sampling/memory only after static typed learning improves on a matched feature baseline. IP reuse behind NAT, Tor, relays and shared infrastructure is not proof of wallet ownership; uncertain evidence must not become hard identity edges.

### 7.4 Temporal GNN → XGBoost and temporal hetero-GNN → XGBoost

Both architectures are technically coherent: train a historical encoder, concatenate its frozen embeddings with engineered columns, and learn a downstream boosted classifier. But selecting XGBoost as the head is not dictated by graph theory. Compare a linear head, LightGBM head and XGBoost head **only after the embedding signal earns its cost**.

There are two failure modes beyond overfitting: supervised encoder embeddings generated on their own fit labels can overstate downstream value, and new embeddings may change distribution when the encoder is retrained. Use forward out-of-fold training embeddings for supervised encoders; freeze transform vocabulary, weights and state policy for validation/test. For self-supervision, train the encoder only on allowed historical graphs. Preserve raw features and run embeddings-only, features-only and combined ablations.

SHAP on embedding dimensions explains the head, **not the upstream graph path**. A hybrid needs encoder-level edge/time attribution, perturbation tests and evidence links. Adding XGBoost does not magically make opaque learned embeddings transparent. No matched temporal hybrid experiment exists here; deploy neither K nor L as a second engine today.

## 8. Graph summaries versus learned representations

Current LightGBM can already learn nonlinear combinations of fund flow, fan-out, counterparties, cluster confidence, delay, burst variability and network-attribution uncertainty. It is therefore a strong **architecture baseline**, although current discrimination is modest and evaluation needs repair.

Compression loses **which** neighbors are connected, edge direction/type sequences, ordering beyond chosen summaries, multi-hop path dependencies, repeated coordination through shared peers, and the coupling of amount/time at each hop. Two wallets with identical 33 features necessarily receive identical booster predictions even if one funds a structured chain and the other has unrelated retail payments. A trained typed temporal encoder may distinguish those contexts.

However, ordinary message-passing GNNs also compress neighborhoods and can fail to distinguish certain structures. More layers can oversmooth. Neither a GNN nor PageRank guarantees discovery of money-laundering semantics. Recover some missing signal first through causal, analyst-readable features: actual traced peel depth, rolling send rates, direct observed-peer reuse, typed in/out degree, and confidence-weighted neighborhood aggregates. Expensive betweenness centrality over a million edges is not a default requirement.

**Is the lost information worth a GNN here? Not yet established.** We have adequate graph size for a small prototype, but few independent illicit campaigns and uncertain network links. No trained temporal model or rich-feature ablation has measured its incremental top-K yield. The SVD add-on losing is one negative experiment, not proof that relational information is irrelevant.

### 8.1 The optional P3 experiment has a design confound

`embed.py` constructs degree-by-relation, confidence and log-value summaries plus type indicators, performs two confidence-weighted aggregation hops, and reduces to eight SVD coordinates. It reads no labels and trains no neural parameters. The reported gate-scale experiment scores **0.0357 versus 0.0373 AP**; these are a different run from canonical 0.064920.

The two windows independently define node/relation columns, standardize and fit SVD. Sign pinning makes one execution reproducible, but cannot align two separately learned bases: `embed_00` need not mean the same direction in training and holdout. This can depress the hybrid irrespective of useful graph signal. Preserve the negative result and qualify it as an **untrained structural-summary experiment with preprocessing confounds**. The gate marks the optional leg unavailable; it should not be described as a trained temporal GNN rejected by science.

## 9. Anomaly detection and risk fusion

The supervised model detects resemblance to labeled illicit behavior. A dedicated novelty detector addresses a different question: **what looks unusual even when it does not resemble known illicit examples?** The PS's “detect anomalies” language motivates a small unsupervised branch, but does not mandate Isolation Forest by name.

| Alternative | Role and cost | Decision |
| --- | --- | --- |
| Isolation Forest | Label-free isolation on engineered columns; CPU-friendly, modest model size, train-only imputation/log preprocessing and frozen reference distribution needed | Preferred auxiliary novelty baseline |
| Tabular autoencoder | Reconstruction of normal behavior; needs scaling, architecture, training and threshold tuning; can learn to reconstruct anomalies too | Defer unless IF fails on an independently defined novelty task |
| Graph autoencoder / VGAE | Reconstructs relations and possibly attributes; structural/attribute surprise | Defer: expensive graph preparation, degree bias, uncertain edges and no clear reconstruction-to-illicitness mapping |

Isolation Forest scores depend on the reference distribution. Fit on past training data, preferably a documented mostly-benign reference with sensitivity analysis for contamination. `contamination` determines a cutoff policy, not a measured prevalence of crime. `-score_samples` can be ranked, but is not P(illicit); turn it into a train-reference percentile for display and report unseen-pattern retrieval separately. [Official Isolation Forest API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).

**Cleanest first architecture:** keep the main supervised risk queue, add a separate budgeted novelty queue with shared graph evidence and explicit deduplication. Show “unusual behavior” without implying guilt. No arbitrary `0.7 × classifier + 0.3 × anomaly` sum. If validation demonstrates incremental useful cases at the same review budget, test anomaly percentile as an additional LightGBM input using forward training folds, or learn a documented fusion policy. Measure precision/recall of the final merged queue, not just its ingredients.

Isolation Forest is not required to replace LightGBM and is not yet proven to improve it. It is the cheapest defensible implementation to test for explicit label-free anomaly coverage before SIH if capacity remains after evaluation fixes.

## 10. Evaluation contract: prioritize investigative yield

The target is an analyst's limited review budget. Accuracy can be 98.16% here simply by predicting every holdout subject licit; that is not a functioning AML queue.

| Metric | What it answers | Required reporting |
| --- | --- | --- |
| Precision / Recall / illicit F1 | How reliable and complete thresholded detection is | Threshold fixed on validation; TP/FP/FN counts; abstention policy |
| ROC-AUC | Pairwise ranking of positives above negatives | Secondary; many negatives can hide poor review yield |
| Average precision (AP) / PR-AUC | Retrieval across thresholds under imbalance | Primary global ranking measure; standard AP plus prevalence; distinguish trapezoidal PR area |
| Precision@20 / Precision@50 | Yield within a practical alert budget | Primary operational measures on the actual eligible, deduplicated queue |
| Recall@20 / Recall@50 | Fraction of known positives found within budget | Explicit denominator; subject, entity and campaign grains separately |
| Brier / log loss / reliability curves | Whether predicted probabilities match outcomes | Only after independent probability calibration; calibration population and bin counts |
| Conformal coverage / set size / abstention | Whether prediction sets include true labels | Per class and time window; coverage is not probability calibration |
| Latency / throughput / peak RSS / disk / model bytes | Whether deployment is practical | Hardware, thread count, row/node/edge sizes, cold/warm state, feature and model time separately |

**Precision@20 = true suspicious subjects among the first 20 eligible alerts / 20.** Twelve true positives in 20 reviews means 60% yield; it does not imply 60% of all illicit activity was recovered. Canonical recall@20 is only 12/492 = 2.44%. Precision@50 is 22/50 = 44% in the diagnostic all-holdout ranking; it must still be measured after the production queue's filters and duplicate handling. If fewer than K alerts exist, report `hits / available`, coverage and count, rather than silently changing the denominator or padding.

Define budget **per capture or review period**, score available subjects at that period's cutoff, then aggregate both micro counts and per-period results. A single global top-20 over a week hides poor daily performance. Freeze score-tie ordering without consulting labels. Report uncertainty across independent generator seeds and campaign/time blocks; a naive row bootstrap understates dependence among connected subjects. Small positive counts require counts and intervals, not only decimals. Report top-K true campaign coverage using `campaigns.parquet` and participant mappings, with a documented criterion for “campaign discovered.” Never rename any-member class-set inclusion as that metric.

For probability calibration, reserve a later validation/calibration interval after model selection; use Platt/logistic or isotonic calibration only when its sample size is adequate. Calibration does not automatically improve ranking. Audit Brier against a prevalence predictor and plot per-time reliability: canonical raw Brier 0.02006 is worse than the constant-prevalence diagnostic 0.01803. This is not a calibrated-probability success. Conformal calibration should remain distinct, and chronological nonexchangeability limits formal coverage claims. [Official calibration guidance](https://scikit-learn.org/stable/modules/calibration.html), [standard AP definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).

For benchmark comparison, freeze data hashes, features, partitions, independent training seeds, alert policy, budget and hardware. Compare LR/RF/XGBoost/LightGBM on identical engineered inputs; separately compare local-only versus graph/temporal/network features. Validation selects models; untouched test confirms the selection once. A practically meaningful improvement means additional unique useful leads at equal analyst budget, stable across windows and seeds, with no unacceptable recall, latency or explanation regression. Predeclare this criterion with stakeholders rather than inventing a winner score.

## 11. Explainability: model reasons and observable evidence

Tree SHAP is the strongest current fit because the input vocabulary can be tied to transaction and graph observations. XGBoost and RF also support TreeExplainer; LR provides transparent coefficient contributions after documenting scales. RF impurity importance is global and can favor high-cardinality features; use held-out permutation importance for global checks. None of these explanations prove criminality or causal attribution. [TreeExplainer documentation](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html).

Current SHAP values explain raw booster log-odds. Preserve the base value, model output space, signed feature contribution, feature value/window and source references. Highest absolute contribution can be a counter-reason; do not describe all top-five items as reasons to suspect. If a calibration layer changes scores, distinguish explanation of the booster from the calibration mapping. Correlated typology summaries can share or shift attribution.

A defensible explanation record should say: “Review priority: high. Short median dwell time and elevated fan-out increased the model score; uncertain origin linkage reduced supporting confidence. These are observed behavioral indicators.” Provide the actual wallet → transaction → recipient chain with timestamps, amounts and edge confidence. Do not generate “multiple wallets share the same IP” from current features unless the observation is explicitly computed and traceable. Avoid showing `0.93` as 93% chance of criminality without validated probability semantics. Do not show the current heuristic `risk_low/risk_high` as a confidence interval.

GAT attention is a learned message weight, not a sufficient forensic explanation. GCN/GAT can use GNNExplainer-style subgraph/feature attribution, but attribution stability, edge perturbation and fidelity need tests. TGN adds event history and memory provenance; HGT adds typed relations, not automatic human reasons. Hybrid XGBoost SHAP on `embedding_17` explains a coordinate, not a laundering path; a second encoder explanation is needed. The GNN research acceptance gate must therefore include an analyst-readable path explanation with uncertain edges disclosed. [GNNExplainer primary paper](https://arxiv.org/abs/1903.03894).

## 12. Hardware and offline deployment

**The current booster is CPU-only by configuration; no CUDA is required.** Native LightGBM and SHAP operate locally. The broader application is heavier than the model: graph construction, joins, per-subject explanations, validation and export consume time and memory.

The existing [performance record](PERF.md) measured a Ryzen 7 7840HS machine, 16 logical CPU threads, about 15.9 GB RAM plus 4 GB zram, NVMe storage and Linux. Historical S10 BUDDHI took **31.4 s, peak 2,065 MiB RSS** for its complete stage, not isolated training or one-subject inference. KAVACH peaked at **8,886 MiB**; VAANI took **341.3 s**. A larger historical 2.74M-announcement capture exhausted memory around 10.6 GB process RSS on that machine. These measurements have different run provenance from the current audit; do not present them as fresh canonical timings.

The canonical graph has 163,577 nodes and 1,206,827 edges; bulk announcement rows dominate that count. “One million rows” does not mean one million blockchain transactions. Current generated run storage is approximately 1.4 GB, with the vendored Elliptic feature file around 670 MB. Package dependencies and datasets separately; disk and peak join memory grow with capture size.

| Model family | CPU training/inference | GPU status | Resource implications for this app |
| --- | --- | --- | --- |
| LR | Highly feasible; cheap inference | Unnecessary | Dense/sparse feature matrix and scaling dominate |
| RF | Feasible; parallel training, larger forests increase RAM/model bytes | Unnecessary | Bound depth/trees; benchmark batch inference |
| LightGBM / XGBoost | Highly feasible on 33 engineered columns; current LightGBM stage measured above | Optional acceleration, not a requirement | Keep bounded threads and native CPU artifact |
| IF | Feasible; modest subsampling cost | Unnecessary | Additional features/reference preprocessing and forest |
| GCN / GAT | Small sampled graphs can train and infer on CPU | Recommended for substantial repeated training; GAT heavier | Sampling, activation tensors and graph libraries add overhead |
| Temporal GCN / TGAT / TGN | Technically CPU-capable; event/neighborhood processing may be slow | Recommended for experiments, not mathematically mandatory | Time-respecting sampling, history/memory storage, reset/replay cost |
| HGT / temporal hetero encoder | CPU possible at small scale; less practical for tuning | Recommended | Typed relation batching and temporal machinery compound cost |
| AE / GAE | Tabular AE feasible; graph AE less convenient | Optional / recommended for larger graph AE | Decoder sampling and reconstruction objective need tuning |

**Practical procurement guidance, not a measured minimum:** retain 16 GB RAM for the demonstrated bounded CPU capture; prefer 32 GB for larger captures, concurrent services and benchmark headroom. A 4–8 GB machine may run isolated booster inference but has not been shown to run the entire pipeline. Benchmark exact judge hardware before committing. Do not publish sub-millisecond latency or a minimum 8 GB VRAM without measuring it.

For a sampled research encoder, an 8–16 GB GPU is a reasonable initial experiment budget, not a guaranteed requirement or sufficient capacity. One float32 64-dimensional node matrix here is roughly 40 MiB; training needs additional activations, gradients, neighbor batches, graph indexes and possibly per-head edge tensors. Full-batch attention can consume far more than that base matrix. Source papers using P100/A100 hardware do not establish minimum VRAM. If GPU is absent, the CPU production pipeline must continue with the same approved LightGBM version. An optional encoder can run on a workstation before deployment and export frozen scores, but data freshness, inductive coverage and artifact provenance still need validation.

**Deployment gap:** the current BUDDHI path retrains from run-associated labels and does not persist/load a reusable fitted booster/calibration bundle. On an unlabeled operational capture, an empty fitted training set leads to the neutral fallback, not a previously learned detector. Before claiming general offline detection, implement a versioned CPU artifact with booster text, ordered feature schema, training-only transforms, calibration parameters, temporal cutoff, dependency manifest and checksums, then prove label-free inference on a new capture. Do not rely on a generated CSV score file as the deployable model. Bundle installers/wheels and optional research dependencies locally; test on a network-disabled Linux machine.

## 13. Qualitative model comparison

“Graph,” “temporal,” and “heterogeneous” describe native modeling below; tree models can consume summaries of all three. “Fit” is an engineering assessment for this repository, not a benchmark score.

| Model | Tabular | Graph | Temporal | Heterogeneous | Anomaly | Explainability | CPU | GPU | Complexity | Fit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. Logistic Regression | Strong baseline | Engineered summaries | Engineered summaries | Engineered summaries | No | Coefficients/contributions | Friendly | Unnecessary | Low | Required sanity baseline |
| B. Random Forest | Strong | Engineered summaries | Engineered summaries | Engineered summaries | No | Tree SHAP/permutation | Friendly | Unnecessary | Moderate | Worth benchmarking |
| C. XGBoost | Strong | Engineered summaries | Engineered summaries | Engineered summaries | No | Tree SHAP | Friendly | Optional | Moderate | Worth benchmarking |
| D. LightGBM | Strong | Engineered summaries | Engineered summaries | Engineered summaries | No | Tree SHAP | Friendly | Optional | Moderate | Retain production candidate |
| E. GCN | Node attributes | Strong local aggregation | Requires snapshots/features | Requires adapters | No | Subgraph methods | Feasible small | Recommended larger | High | Controlled ablation later |
| F. GAT | Node attributes | Learned neighbor weights | Requires extensions | Requires adapters | No | Attention plus fidelity-tested attribution | Feasible small | Recommended larger | High | No current deployment case |
| G. Temporal GCN | Node attributes | Strong | Snapshot evolution | Requires extension | No | Temporal attribution engineering | Feasible small | Recommended | High | Snapshot research candidate |
| H. TGAT | Event/node attributes | Strong | Continuous-time encoding | Requires extension | No | Event attribution engineering | Feasible small | Recommended | High | Event research alternative |
| I. TGN | Event/node attributes | Strong | Event memory/message updates | Requires extension | No | Memory/event provenance needed | Feasible small | Recommended | High | Temporal research foundation |
| J. HGT | Typed attributes | Strong | Time support requires protocol/design | Strong | No | Typed subgraph attribution | Feasible small | Recommended | High | Typed graph ablation |
| K. Temporal GNN → XGBoost | Strong head | Learned embedding | Strong encoder | Encoder-dependent | No | Two-stage explanations | Head friendly; encoder costly | Recommended encoder | Very high | Conditional research only |
| L. Temporal hetero-GNN → XGBoost | Strong head | Learned embedding | Strong encoder | Strong encoder | No | Two-stage explanations | Head friendly; encoder costly | Recommended encoder | Very high | Defer until encoder adds yield |
| M. Isolation Forest | Strong novelty baseline | Summaries | Rolling summaries | Summaries | Strong novelty role | Feature/path diagnostics | Friendly | Unnecessary | Low–moderate | Auxiliary novelty trial |
| N. Autoencoder | Reconstruction | Summaries | Requires sequence variant | Requires design | Reconstruction | Residuals, not criminal reasons | Feasible | Optional | Moderate–high | Deferred |
| O. Graph autoencoder | Attributes if designed | Reconstruction | Requires temporal decoder | Requires typed decoder | Structural novelty | Residual edges need interpretation | Feasible small | Recommended larger | High | Deferred |

## 14. Requirement decision matrix

Importance is ordinal: **mandatory** constraints are deployment gates; **high** requirements determine useful detection; **medium** requirements shape development. No weighted numeric total is meaningful without measured common-protocol experiments. TH-GNN means a custom time-respecting heterogeneous encoder, not an installed model.

| Requirement | Importance | RF | XGBoost | LightGBM | GCN | GAT | TGN | HGT | TH-GNN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Offline Linux | Mandatory | Straightforward | Straightforward | Already demonstrated | Package graph stack | Package graph stack | Package event stack | Package typed stack | Most packaging work |
| CPU feasibility | Mandatory default | Strong | Strong | Strong | Small/sampled | Small/sampled | Possible; costly | Small/sampled | Possible; costly |
| Graph modeling | High | Summaries | Summaries | Existing summaries | Native local | Native attention | Native event graph | Native typed graph | Native typed event graph |
| Temporal modeling | High | Features | Features | Existing summaries | Extension | Extension | Native event memory | Protocol/design needed | Native by design |
| IP/Wallet/TX heterogeneity | High | Summaries | Summaries | Partial current summaries | Type encoding | Type encoding | Relation extension | Native | Native |
| Ranked alerts | High | Score ranking | Score ranking | Working queue | Classifier head | Classifier head | Task head needed | Task head needed | Task head needed |
| Explainability | High | Tree SHAP | Tree SHAP | Implemented; semantics need repair | Extra attribution | Extra attribution | Extra event attribution | Extra typed attribution | Largest explanation burden |
| Training complexity | Medium | Moderate | Moderate | Current deterministic path | High | High | High | High | Very high |
| Dataset suitability | High | Plausible; untested here | Plausible; untested here | Measured synthetic retrieval | Benefit unproven | Benefit unproven | Event/label design first | Typed edge reliability first | Too many unvalidated choices now |
| SIH demo practicality | High | CPU benchmark | CPU benchmark | Best existing integration | Research-only now | Research-only now | Research-only now | Research-only now | Future conditional prototype |

The tradeoff is not “no graph versus graph.” It is transparent engineered summaries versus learned relational representations under sparse, synthetic supervision and uncertain peer edges. The latter earns deployment only through incremental validated queue yield and reliable explanations. The current default passes the CPU/integration constraints; its scientific claims remain conditional on leakage repair.

## 15. Recommended architecture

```text
CSV / JSON / XML capture + offline reference data
                      │
                      ▼
       deterministic ingestion + provenance
                      │
                      ▼
    time-bounded typed graph (IP / wallet / TX)
       soft links retain evidence + confidence
                      │
                      ▼
    causal tabular / temporal / graph summaries
                      │
          ┌───────────┴─────────────────┐
          ▼                             ▼
 approved CPU LightGBM            optional Isolation Forest
 + frozen artifact               + past reference distribution
          │                             │
          ▼                             ▼
 supervised priority queue        separate novelty queue
 + validated calibration          unusual ≠ illicit
          │                             │
          └───────────┬─────────────────┘
                      ▼
        budget policy + deduplication + ranking
                      │
           ┌──────────┴───────────┐
           ▼                      ▼
   signed SHAP reasons    timestamped graph evidence
           └──────────┬───────────┘
                      ▼
             Drishti dashboard

SEPARATE RESEARCH BENCH, only after evaluation gates:
 same cutoff/splits → causal typed temporal encoder
                    → head vs embedding + LightGBM/XGBoost
                    → compare yield, cost and explanations
                    → promote only if independently justified
```

Risk fusion above means a tested queue policy, not an unvalidated arithmetic mixture. The research lane is deliberately outside the shipping path. A CPU default plus an optional GPU backend is technically possible but **not yet a product requirement**: we have one trained detector, no validated neural alternative and no evidence that switching improves an investigation.

## 16. Model visibility and World frontend recommendation

| UI option | UX and reproducibility | Technical / scientific / demo consequence | Decision |
| --- | --- | --- | --- |
| A. One approved production model | Consistent queue; run records exact model version | Least maintenance; strongest honest current demo; About explains deployment and evaluation limits | **Use now** |
| B. Standard/Advanced selector | Changing engines changes priorities; need explicit rescoring/new run | Two artifact schemas, availability checks, comparable budgets, explanations and regression tests; “advanced” implies unearned superiority | Only after both engines pass promotion gates and users need a choice |
| C. Automatic backend selection | Convenient but same capture may score differently across machines | Must expose resolved model/version, preserve deterministic replay, never silently substitute different risk semantics | Avoid performance-driven silent model switching |

Hardware acceleration of the **same validated model** may be automatic when numerical/reproducibility requirements hold. Changing from LightGBM to a temporal GNN is a different model and requires an explicit recorded analysis configuration, not GPU detection alone.

World should show a read-only “Detection engine: CPU / offline” status, observed canonical Precision@20, a separately labeled external Elliptic replication, and conditional evaluation/research gates. Remove arbitrary accuracy/court bars, pooled literature F1 bands, claims that RF is inferior here, and the claim that a temporal GNN was trained and rejected. Rename the existing 95.4% “campaign recall” to **illicit-entity hit rate**, disclose inclusion of ambiguous prediction sets, and stop equating it with top-K recovery. The negative structural-summary trial stays visible with its different-run provenance and preprocessing caveat. Keep model internals in World/About; operational alerts emphasize observable reasons and evidence.

Do not expose a disabled “GPU Advanced” option before a real backend exists. When the research model is reproducibly useful, describe it as an optional resource-intensive engine with measured hardware needs, not a superior default. A judge can inspect the architecture report and actual evidence without an artificial two-model selector.

## 17. Migration plan: keep the baseline, improve the evidence

This is an implementation plan, **not a claim these backend changes have been performed**. This audit preserves the model and saved data. Prioritize Phase 0/1 and reusable offline inference before SIH; the exact deadline was not provided.

### Phase 0 — Freeze current baseline

1. Archive canonical run ID, seed/config, source commit, ordered 33-feature list, feature/schema hashes, saved score/evaluation artifacts and dependency versions. The companion JSON already records input hashes and diagnostic metrics.
2. Persist the fitted native LightGBM booster and conformal/calibration state during a controlled rerun; currently there is no serialized fitted artifact to freeze. Preserve original output hashes and distinguish that rerun from historical results.
3. Save explicit subject/TX membership for outer training, inner fit, calibration and holdout; retain cutoff and label-resolution policy. Record current custom AP alongside standard AP without overwriting history.
4. Version the ranking/filter/deduplication policy and map analyst explanations to the same artifact. Demonstrate identical replay.

**Exit gate:** reproducible baseline bundle, fixed splits and honest baseline card; no claim of prospective validity yet.

### Phase 1 — Improve evaluation and remove leakage

1. Define retrospective batch and prospective objectives separately. For prospective mode, rebuild SHASTRA rollups, cluster discovery and behavioral summaries from information available at each cutoff; preserve edge discovery timestamps and prediction-time label availability.
2. Use earlier TRAIN → later VALIDATION → untouched future TEST. Fit internal transforms, SVD, probability calibration and conformal sets without future rows. Avoid treating independent per-window SVD coordinates as interchangeable.
3. Report both known-entity future activity and new-entity generalization. Use separate generator seeds/campaign templates for robustness tests; prevent generator identity artifacts and duplicate examples across splits.
4. Replace custom AP with threshold-grouped standard AP; add P@20/P@50/R@K to actual queue and all-scored ranking; report positive counts, confusion matrices, calibration and class-specific conformal coverage.
5. Repair campaign metrics against campaign ground truth and report unique entity/campaign yield at fixed review budget. Mark single-class AUC/AP undefined rather than zero.
6. Implement/version model export and label-free inference; resolve score and heuristic-bound UI semantics.

**Exit gate:** leakage tests pass; immutable test manifest; a new unlabeled capture uses the approved model; meaningful queue metrics and resource measurement exist. Do not promise the old 0.60 P@20 will survive these corrections.

### Phase 2 — Benchmark realistic alternatives

Train LR, RF, XGBoost and current LightGBM on identical causal features and splits with comparable bounded tuning budgets. Evaluate class-weighted versus unweighted boosting on validation; class weighting can distort probability calibration. Include rank-by-value and relevant rule baselines, not only an especially weak baseline.

Run feature-group ablations: local transaction only → temporal → graph/typology → network attribution. Add inexpensive missing features only with causal implementation and evidence paths. Test Isolation Forest as a separate novelty queue against withheld attack templates and benign distribution shifts. Measure actual review yield after deduplication.

**Exit gate:** comparison report includes uncertainty, identical-data provenance, signed explanations, CPU training/inference/RSS and artifact size. Select on validation and confirm once on test. Retain LightGBM if alternatives do not show a stable useful improvement.

### Phase 3 — Prototype temporal graph learning only if justified

Proceed only when residual errors demonstrate a missing sequential/typed relation signal and labels/graph realism are adequate. Start small: static relational encoder or TGN-style temporal encoder with wallet/TX/observed-peer relation types, confidence as an edge feature and bounded neighborhood sampling. Time-respecting sampling must reject future messages; reset/replay event memory across experiments; prevent labels from entering graph features.

Compare learned head, embedding + LightGBM and embedding + XGBoost. Generate out-of-fold **forward** training embeddings or frozen past-only self-supervised embeddings; use one fitted encoder/schema across validation and test. Do not use globally supervised embeddings for downstream training/holdout. Test edge-confidence sensitivity, disconnected/unseen subjects and label-free inference. A large custom temporal HGT is a later extension, not the first experiment.

**Exit gate:** encoder adds stable unique top-K hits on validation under equal budget; paths are explainable; CPU fallback remains; measured resource needs are acceptable. Otherwise stop.

### Phase 4 — Compare identically

Use the reserved future test once for the preselected finalists, same budgets, same timestamps, same candidate population, same evidence thresholds. Report P@20/P@50/AP/recall/calibration, per-window/seed variability and latency/RSS. Investigate whether improvements come from extra inputs rather than graph learning: give the tree the same raw/summarized information wherever feasible. Report transductive access separately from unseen-node induction.

**Exit gate:** evidence identifies incremental model benefit, not graph leakage, richer inputs or extra tuning.

### Phase 5 — Decide and document

| Outcome | Deployment action |
| --- | --- |
| A. LightGBM remains best practical detector | Keep it; ship improved features/evaluation/explanations |
| B. GNN materially improves yield and meets deployment requirements | Promote a versioned graph engine only after hardware, explanation and regression gates |
| C. GNN improves yield but is too expensive | Keep CPU LightGBM; optional offline research/GPU processing only when users benefit |
| D. No meaningful GNN benefit | Archive negative result; do not add a selector or permanent dependency |

Promotion is reversible: keep the approved CPU artifact, record model version per run and prohibit silent rescoring of existing cases. No deadline-driven substitution with an unvalidated model.

## 18. Explicit answers to the 14 project questions

1. **Is LightGBM appropriate?** Yes as the current production candidate: real learned detector, rich engineered inputs, existing SHAP and CPU integration. Current evaluation is insufficient to establish prospective real-world reliability.
2. **What does graph engineering capture?** Counterparty counts, fan-out, input aggregation, CIOH/change clusters, local flow/typology summaries and attributed network uncertainty. It does not currently compute PageRank, centrality, actual peel depth or full typed event representations.
3. **What would a temporal GNN capture?** Learned multi-hop relation/value/time-conditioned context, event order and evolving shared-entity state beyond fixed aggregate columns. It still needs causal observations and an appropriate training task.
4. **Would it materially improve this workflow?** Unknown. No trained temporal-GNN comparison exists here; synthetic morphology, few campaigns and uncertain links can limit benefit. Measure incremental unique top-K yield first.
5. **Use XGBoost + temporal GNN?** Not now. Benchmark XGBoost alone; test a hybrid only after the encoder demonstrates benefit against a simple head and LightGBM hybrid.
6. **Use LightGBM + graph features?** Yes. Retain the current approach and make the summaries causal and accurately named before increasing complexity.
7. **Use a temporal heterogeneous GNN?** Conditional research path, not mandatory production. IP/wallet/TX semantics justify a typed design if learned relational information proves useful.
8. **Is Isolation Forest necessary?** No named algorithm is necessary. A small independent novelty branch is useful to test for the explicit anomaly requirement; IF is the pragmatic first candidate, not a replacement classifier or unvalidated fusion weight.
9. **Baseline?** Logistic Regression on identical engineered features, plus non-ML budget baselines; RF and XGBoost are comparative challengers.
10. **Production model?** Versioned CPU LightGBM with causal graph/temporal/network summaries, repaired evaluation, frozen inference and faithful SHAP.
11. **GPU/advanced model?** No shipping backend yet. Research a small time-respecting typed TGN-style encoder if residual errors and validation justify it; compare direct and boosted heads.
12. **Website?** One detection engine status, provenance-separated measured results, observable evidence and conditional research gates. No artificial model selector or unmeasured model scores.
13. **Implement before SIH?** Preserve LightGBM; export/load it for unlabeled offline inference; repair leakage/metrics/score semantics; benchmark inexpensive baselines; test IF if time permits. The deadline needs explicit scheduling, not speculative GNN promises.
14. **Future work?** Typed temporal encoders, subgraph/campaign detection, embedding hybrids, richer anomaly decoders and optional GPU operation only after validated benefit. Real-data transfer and graph realism need independent study.

## 19. Deliverables and verification of this audit change

This change adds the report, a read-only diagnostic tool (writes a new aggregate JSON only; refuses overwrite), the hashed canonical diagnostic artifact, and revised World content. It does not retrain or replace BUDDHI, alter saved scores, or implement the proposed migration. The tracked frontend build is refreshed for offline use. Original measurement reports are preserved after running validation.

| Verification | Result |
| --- | --- |
| Diagnostic replay against companion JSON | Byte-identical; source hashes unchanged |
| Python Ruff checks / formatting / mypy | Passed repository-wide during `make verify` |
| Frontend TypeScript + production build | Passed; existing large-bundle warning remains |
| Playwright desktop 1440×1000 / mobile 390×844 | No runtime errors; engine panel has no horizontal overflow; canonical figures and corrected claims checked |
| Keyboard disclosure | Enter collapses and reopens engine panel |
| `make validate-data RUN=agency-v2` | 58 checks, 0 failed; passing current gates does not resolve the temporal risks identified above |
| `make verify` | Stops in S00 on existing `tests/test_api.py::test_serialize_never_names_the_quarantine`: committed `src/chakravyuh/api/serialize.py` reads `measurements`; later stage gates did not run |

The API failure is present in the examined source commit and unrelated to these UI/doc changes. It should be resolved through the repository's evaluation/inference separation design, not by weakening the quarantine test as part of a content update. Screenshots: [desktop engine panel](audits/screenshots/bitcoin-aml-engine-desktop.png), [mobile engine panel](audits/screenshots/bitcoin-aml-engine-mobile.png).

## Recommended Production Model

**Causal XGBoost with engineered transaction/graph/temporal features, as the next CPU production candidate.** The original LightGBM stays frozen as the currently shipped reference until standard-stage/UI integration and release verification pass. The new opt-in scorer already runs without labels and reproduces all ten causal windows exactly.

## Why

The architecture retains informative relational/behavioral summaries and signed feature explanations. The initial audit favored the integrated LightGBM pending experiments; the subsequent matched causal tabular validation selected XGBoost. Its frozen scorer now has exact replay and native TreeSHAP verification. Typed temporal models improve fresh-world subject ranking, but controller projection reduces their advantage and confidence thresholds fail under shift. Preserve both evidence and limitations; booster choice does not replace causal feature construction. The latest decision and migration details are in the linked research plan.

## Why Not the Other Models

- **Logistic Regression:** essential baseline; linear interactions may miss composite typologies.
- **Random Forest:** now tested as a causal CPU challenger; it did not win the matched tabular validation selection. No integrated production replacement established.
- **XGBoost:** selected by matched causal tabular validation; retain as a serious challenger. Frozen thresholds fail under world shift, so it is not yet a confident-alert production replacement.
- **GCN/GAT:** useful static-neighborhood experiments but lack native event history and incur additional explanation/graph deployment work.
- **Temporal GCN/TGAT/TGN:** a custom typed windowGRU now demonstrates incremental synthetic ranking benefit; canonical event-time versions remain untrained and need separate controlled comparison.
- **HGT/temporal heterogeneous GNN:** semantically appropriate types, but uncertain edges, custom temporal machinery and sparse campaign labels make production premature.
- **Temporal encoder → XGBoost hybrids:** measured AP gains survive fresh worlds, but validation selection changes with training budget and P@20 gains are inconsistent. Keep as a research challenger with encoder-state/explanation provenance.
- **Isolation Forest/AE/GAE:** novelty is not illicitness. Use a separate evaluated anomaly role; do not replace supervised prioritization.

## Recommended Baseline

**Logistic Regression on the identical causal engineered feature table**, with train-only transforms and validation-selected regularization/weights. Include value/rule ranking controls; benchmark RF and XGBoost fairly.

## Recommended GPU/Research Model

**Implemented custom typed mean-message encoder + causal address-linked windowGRU**, comparing a neural head and embedding→XGBoost. It trains onCPU and improves fresh-world ranking; it is not a canonicalTGN/HGT implementation. No advanced production mode until workload/calibration/explanation gates pass. Event-timeTGN/TGAT/HGT remain future research, with GPU needs measured rather than assumed.

## Recommended Anomaly Detector

**Isolation Forest as an experimental separate novelty queue**, not a necessary AML classifier component. Actual IF/AE/typedGAE tests do not justify AMLscorefusion; validate semantic unusualness and review usefulness before deployment.

## Explainability

**Signed Tree SHAP plus timestamped, confidence-labeled graph evidence and source lineage.** Explain booster output space honestly; probabilities require calibration. Conformal prediction sets and heuristic score bounds are different objects.

## Evaluation Metrics

**Precision@20, Precision@50, standard AP/PR reporting and Recall@K** on the actual deduplicated queue; illicit precision/recall/F1, ROC-AUC, probability calibration, class-wise conformal coverage, true campaign yield, latency, training time, RSS and artifact size. Use chronological/rolling tests and independent synthetic seeds; publish denominators and uncertainty.

## Deployment Strategy

**One approved offline CPU model with a reusable artifact and a reproducible run manifest.** Test the complete Linux stack without internet or GPU. Keep a separate conditional research lane; add GPU processing only for a proven benefit, with measured hardware needs and an intact CPU default. Show engine status and provenance in World, not a speculative Standard/Advanced selector.














ok,, good job u have done,, you actually done good job, i want u to do one thing now,, that is i just want u to do an extrodanary intense research about what are the methods(models) which have been teseted on this bitcoin,, i want u to not just think of that, but think of every possiile technolgy or hybrid mixing of bigg, weried cobinattioon, everything and anythhing, thing is i have a really stong laptop, (and jsut in case u need some really gpu heavy stuff, i can ask my friend he has it),, so this reasearch should give u really good info about whatis ther what is good (u can even expereeiment which no one hase ever did, maybe some upcoming new ones) so i want u to figure out few stuff, and thenn i want u too workk on them,, like its a reasearch task from our side,, we'll explore diffrent kinds stuff and see the outcome figure what is nice (if something is not possibile we can say we'll do that in future) u dont have to even fix with our linear way of apply stuff,matter of fact u are not bound to not even a single rule  restriction said in entire project(expect for the fact that u can commit anything), u are all free, do intense intnese websearches,, but on a secondary  thought im understanding that,, this entire thing could not matter becuae we could have done clusttering only bad in jall, such that our clusters are dog shit and doesnt really carry any meaning,, cause we are doing logical stuff of ai/ml/dl stuff just becuase our entire base is on uncertinity,, soo before that it would be really smart if u do the clusttering part really well,, in jaal before messing arround with them,  so in this jall part figure out every possibile thing that ppl eveer treid in internet, if  u think if any of the model, or technique or logic is even usefull,, we'll try, themm,, thing is our process slowly turened in to reasearch side, researching everything and try various stuff and doing later proper analytics on eachh of the observation,, making a educated intrepeation,, so no there are only 2 rules of mulip input and change attribution right,, take u r time, do intense researcch work (meaning experiement by tring if one thing is nice for us  and actually report of stuff for futrue analysis) then spend time with sastra alot, like man,, it feals like on highest level of uncertiatinyty, cause first uncertinity is did we even make perfect clustters of exact wallet,, then it get mutiplie with the next inertiantiy of finding pottentiall prediction of jaal, finding out the wallet,, then finding out finally the actuall orgin from peers, it looks beyond impossibile, causee it makes no sense,, leaving even this uncetaitny, the observage coverage part only is unceertain,, when we dont even know wheter even the actuall person who made a  transaction not even present in the dataset we have,, how will even find them,, its logically impossibile,, so what do we do, would we be somehow able to figure that a way to say, no, the actuall user is not at all present here, thats impressive too,, annd nextly i think we are using light gbm here right,maybe take ur time and figure out with good research, what are other options,, we'll experiment all most strongest possibile ones, we'll improve inetranll architectures of jaal, buddhi and sastra layers,, making it undoubtadly strongest possibile thing in the entire problem statment that anyone can ever think,, do not atall think linearrly, like do not think like  "yeah this the problem, and yeah this is the solution


## Research checkpoint R34–R40: ownership-independent detection

The latest experiments materially change the dependency argument: observable address/TX/IP detection can run without accepting JAAL ownership merges. Rich329-feature XGBoost/LightGBM controls, address-only typed models, paired frozen-world transfer, controller alias diagnostics and evidence-diverse queues were actually executed. Raw address P@20 must not be presented as distinct-controller precision.

The complete measured results and integration boundary are in [Address-level detection and uncertainty isolation](research/ADDRESS-ATOMIC-DETECTION-AND-UNCERTAINTY-ISOLATION.md). This supplements the earlier model comparison. The shipped LightGBM remains frozen; the23-feature causal XGBoost CLI and329-feature research challenger are separate artifacts. No default backend replacement or real-network reliability claim is made.


## R42–R45: working investigative engine and SIH direction

The useful research now has a concrete product path. A portable329-feature graph-context XGBoost engine reproduces the research scores, generates explained evidence packets on observation-only inputs and runs with Torch unavailable. World now includes a real packet viewer with localJSONimport/export, model contributions and linked monetary/network evidence. It is independent of the active-run metrics and defaultLightGBMstage.

The strongest measured workload result for this tree model is controller-windowretrieval11→33and9→16under a frozen evidence-diversity policy in two syntheticworlds, with an address-precision tradeoff and repeated-window counting disclosed. Our publicEllipticexperiment also provides positive evidence for graph-feature trees. Read [the SIH investigative engine report](research/SIH-INVESTIGATIVE-ENGINE.md) for actual implementation, exact329-feature recipe, tests, runtime, command and a five-minute demonstration.

Prioritize full ingestion-to-case integration and a smooth offline review experience next. Use temporal/heterogeneous neural models as controlled challengers where they retrieve extra useful evidence. This is a positive capability strategy, not a guarantee of globalnovelty or competitionplacement.
