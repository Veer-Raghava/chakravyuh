# Address-level detection, ownership uncertainty and distinct investigative leads

Updated 2026-10-01. Experiments R34–R40. This report separates implementation correctness, simulator performance and real-world claims. All measured results below come from actual CPU executions. None establishes human identity or real Bitcoin generalization.

## The architectural finding

JAAL's ownership clustering is uncertain, but ownership recovery need not be a prerequisite for every useful output. Transaction inputs, outputs and captured announcements give observable relationships even when their controllers are unknown. We implemented an explicit address partition in the causal feature builder, trained graph models on that representation, and tested frozen models on independently generated P2P worlds.

`buddhi.snapshot.build(..., partition_mode="address")` assigns one observed address per subject. It ignores the entire ownership ledger, including deliberately corrupted maximum-weight claims. It does not call ownership edge selection or clustering. The default remains `"heuristic"`; existing callers keep their behavior. Research graph construction additionally skips ownership-evidence extraction in address mode. A regression test makes both ownership routines raise if called, inserts incorrect claims, and verifies unchanged features and singleton membership.

This creates three separate questions:

1. Which observed address/transaction behavior deserves investigation?
2. Which addresses might share a controller, and what evidence supports that hypothesis?
3. Which network source or operator is compatible with the capture, and is there enough evidence to answer?

Only the first requires a detection ranking. The second remains a reversible ownership hypothesis. The third requires an independent observation model. The implemented causal SHASTRA candidate generator takes announcements, peer metadata and transaction histories; it does not consume JAAL partitions. Its first-input-address history is a proxy, not a verified sender identity.

This is a useful engineering boundary, not a claim that address-level graph learning is new to the literature.

```text
             Captured observations + transaction bodies
                              │
                Availability-bounded event ledger
                              │
          ┌───────────────────┼──────────────────────┐
          ▼                   ▼                      ▼
 Address/TX/IP evidence   JAAL ownership claims   SHASTRA candidates
 No ownership merges     Method/time/TX provenance  Prior histories
          │                   │                      │
 Causal features/model   Reversible hypotheses   Source-ASN ranking
          │                   │                      │
 Scores + explanations   Optional grouped view    Answer or abstain
          │                   │                      │
 Evidence-diverse queue ───────┴──────────────────────┘
                              │
                   Investigator dashboard
```

This is a proposed integration architecture. The snapshot modes, research models, optional tree scorer and causal source estimator exist; the complete parallel dashboard workflow is not yet implemented. Never multiply their scores as if they were independent calibrated probabilities.


## R34: actual address graph training

We first registered a threshold of 1.0, above all current ownership weights, then trained 180 epochs using the existing causal window protocol. The later explicit address mode reproduces that representation: frozen transfer replay errors are exactly zero. Labels attach only after feature/graph construction.

Windows 0–3 fit models and feature scalers; 4–5 fit Platt calibration; 6 selects checkpoints/model families; 7–9 evaluate future windows. This is a single consumed canonical world, not an untouched external benchmark. The target is observed campaign participation, not legal guilt.

| Address representation model | Validation P@20 | Validation AP | Test P@20 | Test AP |
| --- | --- | --- | --- | --- |
| Local MLP | .35 | .1145 | .30 | .0764 |
| Typed static message model, selected | 1.00 | .3129 | .90 | .2738 |
| Typed model with GRU memory | 1.00 | .3060 | .80 | .2193 |
| Shuffled-subject graph control | .40 | .1019 | .65 | .1035 |
| Local XGBoost | .65 | .1280 | .55 | .0538 |
| Typed-mean-feature XGBoost | .25 | .1986 | .60 | .1902 |
| Temporal embedding → XGBoost | 1.00 | .2643 | .80 | .2041 |

Runtime: 68.25 seconds, approximately 1.43 GiB peak process RSS. The selected static model has 6,497 active parameters. The common module registers 12,833 parameters, including inactive temporal components. These are custom directed mean-message models, **not** reproductions of HGT, TGN or TGAT. Full equations and training settings are in [the temporal graph report](TEMPORAL-HETEROGENEOUS-GRAPH-EXPERIMENT.md).

R35 froze all transformations, weights and calibration before generating seeds 50021 and 60013. Address-static P@20 was .70/.40, and AP .1930/.0856. The hybrid was stronger on those particular address rankings, but was not the validation-selected model. Small selected-answer counts, alias repetition and simulator shift prevent a confidence guarantee.

## R36: address precision can inflate investigator yield

An address is not a controller. Repeated addresses and repeated time windows can consume alert slots. We projected scores to hidden controller keys **only for research evaluation**, compared the common controller universe, and also deduplicated controllers across the entire test period. These answer keys are unavailable to the deployed system.

The canonical static address model's top 20 address-window alerts contained 18 positives but only six distinct positive controllers. The temporal embedding hybrid's 16 positive alerts represented only two distinct positive controllers. The richer address XGBoost below achieved 20/20 positive address-window alerts but represented only five distinct controllers.

The address-static model's test P@20 after oracle controller deduplication was .45, not its raw .90. This does not mean the detector is useless; it means raw address precision answers a different question. Controller aggregation uses a maximum score, which is a ranking diagnostic, **not a calibrated controller probability**.

Recommended operational evaluation includes address/transaction precision, distinct lead yield, repeated-evidence burden, and declared investigator workload. A prototype cannot claim production entity deduplication merely because MAYAJAAL provides hidden keys.

## R37: stronger handcrafted graph controls

We trained both XGBoost and LightGBM on a richer, entirely observable graph compression. This checks whether the apparent neural advantage came from giving trees weaker relational inputs.

Each transaction context has 38 dimensions: six local transaction fields, nine mean announcing-IP fields, and 23 mean funding-subject fields. For each receiving and spending relation, summarize transaction contexts by:

- log(1 + degree), one dimension;
- mean, population standard deviation, minimum and maximum, 38 dimensions each.

Each relation contributes 153 dimensions. Adding the 23 local subject fields gives **329 inputs**. Empty neighborhoods produce zeros. Accumulation uses float64, with variance clamped at zero after rounding. Unit tests verify a large-offset variance example, directionality, permutation invariance and empty-neighborhood behavior. Base scalers fit only windows 0–3.

XGBoost: 300 trees, depth 5, learning rate .05, minimum child weight 10, row/column sampling .9, CPU histogram algorithm, four threads, seed 42. LightGBM: 300 rounds, 31 leaves, minimum 40 observations per leaf, learning rate .05, L2 penalty 1, deterministic CPU settings and four threads.

| Representation and model | Validation P@20 / AP | Test P@20 / AP |
| --- | --- | --- |
| CIOH XGBoost, 329 features | .55 / .3542 | .90 / .3228 |
| CIOH LightGBM, 329 features | .50 / .2697 | .95 / .2847 |
| Address XGBoost, 329 features | .65 / .3287 | 1.00 / .3148 |
| Address LightGBM, 329 features | .20 / .2526 | .40 / .2011 |

The actual four-model training took 33.97 seconds. These subject metrics are not directly comparable across partitions: subjects, prevalence and alias count change. On common controller-window validation, CIOH rich XGBoost was selected by P@20 then AP. Its distinct-controller test P@20 was .50/AP .1977. Rich CIOH LightGBM had .50/.2493, but its larger test AP does not authorize test-based selection.

Handcrafted summaries discard exact neighbor identities, connectivity arrangement, detailed ordering and interactions beyond the specified neighborhoods. Learned graph representations can retain some of that information. Our results do not yet establish that the discarded information makes a GNN operationally preferable. The stronger tree control substantially narrows that argument.

## R38: a constructive source-identifiability limit

We executed two toy propagation worlds with positive link delays and the same transaction body:

```text
World A: observed peer P originates at t=100 → observer O receives at t=101
World B: hidden H originates at t=99 → P relays at t=100 → O receives at t=101

Observer capture in both: P → O, same TXID/body, t=101
```

Both captures and all actual causal SHASTRA candidate features are exactly equal, while the true originating host, its presence in the capture and its ASN differ. The demo uses documentation IP ranges and private ASNs. It is a constructive toy, not a Bitcoin Core reproduction or an estimate of how often ambiguity occurs.

Any deterministic model given these identical observations must produce the same answer in both worlds; at least one origin answer must therefore be wrong. A probabilistic model can express assumptions or a set of possibilities, but cannot recover the distinguishing observation from computation alone. Additional observers, topology evidence or validated propagation assumptions may help.

The defensible interface is “insufficient evidence for source attribution” when appropriate. We have **not** established a reliable policy declaring “the actual source is absent.” AML transaction evidence can remain useful even when source identification is unresolved. See [the source attribution audit](SHASTRA-ATTRIBUTION-AUDIT.md).

## R39: paired frozen models on new P2P worlds

Seeds 70017 and 80029 were registered before world generation. Each world was generated once and shared between the address and CIOH representations. Three frozen models per representation were tested: static typed graph model, richer XGBoost and richer LightGBM. All six canonical prediction replays had maximum error 0.0. No model, scaler or calibrator fitted on a transfer world.

The primary challenger was CIOH rich XGBoost, chosen by canonical common-controller validation. We report every model, including failures. Worlds contain respectively 32,823/33,167 observed transactions and 901,643/915,186 announcements, with 48 observers each. Total run time was 135.13 seconds on CPU.

| Seed | Representation | Model | Subject-window P@20 | Distinct-controller P@20 | Distinct-controller AP |
| --- | --- | --- | --- | --- | --- |
| 70017 | cioh | lightgbm_distribution_features | 0.65 | 0.65 | 0.3838 |
| 70017 | cioh | typed_static | 0.75 | 0.75 | 0.2388 |
| 70017 | cioh | xgboost_distribution_features | 1.00 | 0.90 | 0.4101 |
| 70017 | address | lightgbm_distribution_features | 0.90 | 0.60 | 0.3364 |
| 70017 | address | typed_static | 1.00 | 0.95 | 0.2711 |
| 70017 | address | xgboost_distribution_features | 1.00 | 0.60 | 0.3335 |
| 80029 | cioh | lightgbm_distribution_features | 0.60 | 0.40 | 0.2573 |
| 80029 | cioh | typed_static | 0.90 | 0.35 | 0.1725 |
| 80029 | cioh | xgboost_distribution_features | 0.60 | 0.30 | 0.2333 |
| 80029 | address | lightgbm_distribution_features | 0.45 | 0.15 | 0.2081 |
| 80029 | address | typed_static | 1.00 | 0.45 | 0.2310 |
| 80029 | address | xgboost_distribution_features | 0.95 | 0.25 | 0.2196 |

The primary model retrieved 18/20 and 6/20 suspicious distinct controllers. The address-static model retrieved 19/20 and 9/20 after oracle deduplication. Neither wins every metric in every world. The primary model's AP was .4101/.2333; the address-static model's AP was .2711/.2310. These are meaningful simulator rankings, not guaranteed future precision. The second world's positive-controller prevalence was lower (.46% versus 1.36%), and its ranking is harder. We have not established the causal reason for the performance difference.

Independent seeds within the same generator family are useful internal checks, not evidence of generalization to actual laundering, new simulator mechanisms or different observation regimes. Max-pooled controller Brier values in the raw report must not be read as calibrated entity confidence.

## Current engineering decision

Preserve the shipped LightGBM baseline. Keep the implemented causal XGBoost CLI as an opt-in CPU candidate; its 23-feature portable artifact is a different model from the richer 329-feature research challenger. Do not conflate them or silently change the dashboard backend.

Develop parallel observed-evidence and ownership-hypothesis views. Strong ownership evidence may improve a ranking, but uncertain merges should remain traceable and reversible. Evaluate both representation paths using the same captured worlds and the same controller-aware research protocol.

Keep the custom temporal/typed graph model as a research challenger. A GPU is not necessary for the experiments reported here. Canonical HGT/TGN/GAT, larger capacity-matched local networks, realistic propagation shifts, topology-aware source confidence sets and packaged UI integration remain future work. No current result justifies automatically switching the investigator's model based on hardware availability.

The project can contribute an offline, auditable investigative workflow that contains uncertainty instead of concealing it. Neither a guaranteed source finder nor a universal superiority claim follows from these experiments.

## Reproduction and audit artifacts

- Training: `research/bitcoin/temporal_hetero_benchmark.py --epochs 180 --partition-mode address --ownership-threshold 1.0 --output NEW_DIRECTORY`.
- Rich controls: `research/bitcoin/relational_summary_controls.py`.
- Frozen paired transfer: `research/bitcoin/rich_relation_transfer.py`.
- Source ambiguity: `research/bitcoin/source_ambiguity_demo.py`.
- Raw reports, scores, native model files and frozen transforms: `research/bitcoin/results/`.
- Action history: [experiment journal](EXPERIMENT-JOURNAL.md) and `events.jsonl`.

Existing scripts can contain fixed output paths; use archived results or update an explicit destination before rerunning rather than overwriting evidence. Exact source snapshots and SHA-256 manifests distinguish historical executed code from subsequently formatted files.

## R40: observable evidence diversity, actually evaluated
A score-only queue can spend many slots on addresses supported by the same transactions. We implemented a greedy selector using **only** ranked subject IDs, scores and observed transaction-set Jaccard overlap. It never sees ownership truth or illicit labels. Nonempty evidence eligibility and a top-2,000 candidate pool are fixed across every policy. It selects 20 leads per window, if available.

Policies were registered before evaluation: score-only, maximum pairwise Jaccard .50, .25 and zero. The canonical validation objective was distinct positive controllers retrieved, measured only after selection. Ties retain the earlier listed policy. Both static and rich-XGBoost rankings selected .25. This is an exploratory single-window policy choice, not a guaranteed optimal queue.

The first runner accidentally checked the phase string `validation`, while the dataset uses `val`. That produced an empty result, which is preserved as `report-initial-phase-error.json` and excluded from conclusions. Corrected phase filters and an explicit 16-row/window-policy assertion repair the experiment. A test collection failure from a missing research import path was also corrected. No failed run is treated as evidence.

| World | Address scorer | Policy | Distinct positive controllers in test windows 7 / 8 / 9 | Positive addresses among 60 selected |
| --- | --- | --- | --- | --- |
| canonical | typed_static | score_only | 3 / 5 / 0 | 31 / 60 |
| canonical | typed_static | jaccard_025 | 4 / 8 / 0 | 12 / 60 |
| canonical | xgboost_distribution_features | score_only | 2 / 5 / 0 | 22 / 60 |
| canonical | xgboost_distribution_features | jaccard_025 | 3 / 7 / 0 | 10 / 60 |
| 70017 | typed_static | score_only | 5 / 4 / 5 | 57 / 60 |
| 70017 | typed_static | jaccard_025 | 10 / 13 / 7 | 31 / 60 |
| 70017 | xgboost_distribution_features | score_only | 3 / 3 / 5 | 43 / 60 |
| 70017 | xgboost_distribution_features | jaccard_025 | 9 / 17 / 7 | 35 / 60 |
| 80029 | typed_static | score_only | 4 / 3 / 0 | 39 / 60 |
| 80029 | typed_static | jaccard_025 | 5 / 7 / 0 | 14 / 60 |
| 80029 | xgboost_distribution_features | score_only | 4 / 5 / 0 | 35 / 60 |
| 80029 | xgboost_distribution_features | jaccard_025 | 5 / 10 / 1 | 16 / 60 |

The frozen .25 policy increased distinct positive controller retrieval in both generated worlds, while reducing address precision. For static scoring, controller-window yield increased from 14 to 30 in seed 70017 and from 7 to 12 in seed 80029. Those are sums across three windows; the same controller may be counted again in another window. They are not distinct controllers across the entire period.

The underlying scores had already been evaluated in R39. We froze the canonical policy, regenerated exactly the same worlds, verified observed-TXID hashes, and used the saved scores with no new training or transfer-based policy selection. This is confirmation of policy transfer on previously evaluated worlds, not an untouched model benchmark. The two replays took 37.49 and 36.86 seconds respectively (use the raw report for exact runtime).

Less repeated transaction evidence is not proof of different ownership. Conversely, distinct evidence can belong to one controller. The selector leaves all identities unresolved and may suppress useful cooperating-counterparty alerts. It should remain an optional research queue until campaign-level retrieval, workload tradeoffs and new observation regimes are evaluated. In the canonical empty-campaign test window all policies still return 20 false alerts: diversity does not solve the separate question of when to abstain from issuing alerts.

Reports: `research/bitcoin/results/evidence-diversity/` and `evidence-diversity-transfer/`. Selector tests check repeated evidence, empty support and the exact Jaccard boundary. Source snapshots preserve executed versions before formatting.


## Subsequent coverage check and verification

R41 exposed a frozen source-policy failure under reduced observation coverage: see [SHASTRA coverage stress](SHASTRA-OBSERVATION-COVERAGE-STRESS.md). The latest broad focused regression is92passed/3skipped; strict production checks and research lint pass. Standard stage/UI migration and full release verification remain unfinished. Checkpoint hashes are in `R25-R41-manifest.json`.
