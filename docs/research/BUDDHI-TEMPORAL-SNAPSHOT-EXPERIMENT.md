# BUDDHI temporal snapshot and alert-policy experiments (R17/R19)

## What the experiments support

The deployable reference remains LightGBM while its prospective evaluation is repaired. We now have an implemented, tested opt-in snapshot feature pipeline and actual chronological model comparisons. The equal-duration research protocol selects XGBoost using validation P@20, then test P@20=.50 among subject-window decisions. That is a promising ranking result, not a proven production replacement or calibrated action policy.

The selected model's validation response precision does not persist: a threshold with 14/15 validation positives returns only 12/34 positives in later test decisions and ten false alerts in a window with no campaign activity. No confident-alert claim is justified by this operating point. The research finding is a concrete calibration/temporal robustness failure requiring correction and fresh-world confirmation.

## Causality and label repair

Legacy BUDDHI partitions are built from the full capture before the nominal timestamp split. Recomputing each partition at its decision cutoff prevents future ownership links from entering prior subjects. `buddhi/snapshot.py` uses only observed-prefix addresses, timestamped ownership evidence and current-window transactions. It excludes global learned source/ASN outputs and typology-hit artifacts until their own causal recipes exist. The end of each window is its decision time; in-window evidence is legitimate at that time. This is retrospective batch triage at declared cutoffs, not immediate prediction at first announcement. Availability of full transaction bodies at first_seen_us remains an explicit assumption.

MAYAJAAL does not initially assign `is_illicit` to an illicit actor class. The adversary assigns it after simulation to controllers participating in any completed/partially executed campaign. Thus full-capture labels can mark a controller based on later activity. This target could be used for explicit future-participation forecasting, but is not contemporaneous campaign detection.

The revised research target is **participation in an observed campaign transaction during the decision window**. Campaign TXIDs join observed transactions; a sender/input/output address owner is positive only when also listed as that campaign's participant. Known campaign cash-out exchanges are not marked merely for receiving an output if omitted from the participant list. This target is synthetic campaign involvement, not guilt or a statement that every transaction by that controller is illicit. Owner/campaign truth is used only for research labels/metrics and the explicitly named ownership oracle. The production snapshot API reads no ground truth.

The canonical capture contains 272 full-capture positive entities, but the broad 45/15/10/30% windows contain 100/114/40/52 active campaign controllers. The final matched-duration window contains zero. This difference materially changes interpretation of old static-label scores.

## Corrected flow semantics and costs

Legacy `_sides` assigns each input/output address the transaction's entire output sum, then sums those rows within a subject. Multiple co-owned inputs therefore duplicate money; recipients are credited outputs that went elsewhere. The snapshot API explodes each address with its actual paired amount and aggregates once per subject/transaction. Gross sent value is the sum of input satoshis contributed by its addresses; it includes change before that change returns. Gross received value is the sum of outputs paying its addresses. Balance is received minus gross sent, including the effect of fees.

A test transaction funded by two co-owned inputs of 100 + 200, with 250 paid to another subject, 40 returned as change and 10 fee, produces sender gross sent 300 / received 40 / balance −260, recipient received 250, one sent transaction and one counterparty on each side. The old aggregate would repeat whole-transaction output values instead. Counterparty count now refers to opposite-side predicted subjects, excluding self. Mean fee rate and equal-output fraction use unique subject sends. These definitions require retraining; existing canonical artifacts were not silently rescored.

Cluster shape formerly joined every active address to every other address in its subject before checking real evidence edges. The new equivalent implementation joins only actual edge endpoints to memberships. A 10,000-address test operates on two real edges instead of constructing 100 million member pairs. Legacy shape values are preserved. Public API documentation now explicitly states that windowing alone cannot certify full-graph/upstream evidence causality.

## Feature recipe

The snapshot version has 23 inputs: n_addresses, n_tx_sent, total_sent_sats, mean_sent_sats, n_tx_received, total_received_sats, mean_received_sats, balance_sats, n_counterparties, max_fan_out, n_coinbase_received, frac_equal_outputs, mean_fee_rate, median_dwell_us, min_edge_confidence, n_heuristics, n_script_types, fan_in_ratio, peel_chain_depth, peel_leak_frac, structuring_frac, burstiness and fee_anomaly.

Ten original origin/ASN/typology-fusion inputs are excluded. The remaining legacy morphological definitions have known limits: peel_chain_depth counts qualifying peel-shaped sends rather than verifying one UTXO-linked chain; median dwell tracks the same address's next send, not exact fund residence; fan_in_ratio is currently an input-count shape; structuring uses a fixed amount ladder. These are observable feature summaries, not proof of laundering. Ownership confidence remains an uncalibrated heuristic weight.

Missing numeric values become 0; signed log1p transforms numeric magnitude while retaining balance sign. A scaler fits training snapshots only. No owner ID, subject ID, campaign ID or label is a model input. Snapshots and training rows explicitly sort identifiers to stabilize histogram models, subsampling and tied ranked decisions. Owner lists are sorted; current matched controller diagnostics sort controller IDs before tie-breaking.

## Protocols and comparable targets

The initial protocol fits one 0–45% snapshot, calibrates 45–60%, selects 60–70%, tests 70–100%. Its unequal window durations can change activity-feature distributions; all results are retained as exploratory diagnostics. Static-label, initial window-label and unsorted-frame artifacts are separately archived.

The matched protocol divides elapsed observed time into ten equal intervals. Windows 1–4 fit; 5–6 calibrate; 7 selects the model; 8–10 test. Every window has its own point-in-time partition and activity labels. Calibration is Platt logistic regression on clipped raw-score logits. Multiple snapshots of a controller can exist across time, and do not constitute independent observations. Unseen-controller subject cohorts are reported using true owner overlap as an evaluation diagnostic only.

Four partition controls: singleton addresses, CIOH threshold .30, CIOH+weak change threshold .20, and true-owner oracle. The oracle groups addresses by hidden ownership and is deliberately unavailable in deployment; it is a diagnostic of aggregation headroom, not a candidate production model. Changing partitions changes subject examples, so subject AP across those controls is not an identical-target comparison. Controller diagnostics map every score to each contained true controller, penalizing scores contaminating licit controllers, and evaluate the common 11,116 active-controller test universe.

Within CIOH, LR/RF/ExtraTrees/XGBoost/LightGBM use identical inputs/splits. Model selection maximizes validation Precision@20, breaking ties with validation AP. Test results are then reported without changing the selection.

| Model (CIOH) | Validation P@20 | Test P@20, pooled | Test subject AP | Test controller AP |
|---|---:|---:|---:|---:|
| extra_trees | 0.50 | 0.30 | 0.1408 | 0.1610 |
| lightgbm | 0.75 | 0.45 | 0.0547 | 0.1677 |
| logistic | 0.20 | 0.35 | 0.0322 | 0.1078 |
| random_forest | 0.35 | 0.10 | 0.0612 | 0.0716 |
| xgboost | 0.75 | 0.50 | 0.1240 | 0.2237 |

XGBoost wins that validation rule. Its pooled test P@20=.50 includes subject-window decisions and can repeat controllers. Per-window P@20 is .40/.45/.00; these are not the same estimand as pooled P@20. LightGBM with the inaccessible oracle obtains pooled .75 and controller AP .4065, versus selected XGBoost controller AP .2237. This supports testing better entity resolution, but does not establish that any specific learned clusterer can recover the oracle benefit.

Model recipes: native LightGBM: 300 rounds, 31 leaves, minimum 40 rows per leaf, learning rate .05, L2=1, four threads, deterministic, seed 42. XGBoost: 300 trees of depth 5, learning rate .05, minimum child weight 10, row and column subsampling .9, CPU hist, four threads, seed 42. RF and ExtraTrees: 150 trees, depth 18, minimum leaf size 10, four threads, seed 42; sklearn defaults otherwise. Logistic regression C=1, maximum 1,000 iterations, seed 42. Full source/version snapshots and result hashes preserve exact recipes; no hyperparameter sweep or SOTA claim.

## Negative control and response thresholds

The last test interval has no observed campaign participants. AP is undefined there and stored as null, not manufactured as zero. Forced top-20 rankings nevertheless have zero precision, correctly exposing false-lead workload. The simulator samples campaign starts before the final tenth so campaigns can finish; this can yield empty late windows. Empty windows are valid negative controls, not an excuse to retune the world around a model. Future experiments should include steady/right-censored arrivals and favorable/stress observation regimes with declared parameters.

`snapshot_alert_policy.py` evaluates two exploratory validation targets: at least 10 decisions and observed precision ≥.80 or ≥.90, select maximum validation coverage, keep tied scores together. No test labels choose the thresholds. This analysis is post-benchmark research, not untouched confirmation. For selected XGBoost, the ≥.90 validation gate gives 14/15 correct (.9333) but later 12/34 correct (.3529); 10 of those false alerts occur in the zero-campaign window. The oracle's gate gives 13/14 validation correct and 11/13 test correct (.8462), with zero decisions in the empty window. Neither operating point achieves a scientific guarantee from observed validation precision. Oracle performance cannot be claimed for the real application.

This reinforces the need for temporal calibration checks, confidence bounds accounting for dependence, independent seeds and explicit abstention rather than score≥fixed threshold optimism. A low risk score does not prove innocence; an empty observed window does not prove there was no unseen illicit activity.

## Verification, artifacts and remaining work

Final focused tests: 70 passed, 3 skipped; existing MAPIE fixture warnings noted. Strict mypy passes changed snapshot/features/test source. Ruff/diff checks pass after formatting repairs. The matched benchmark completed ~160.98 seconds CPU with whole-process peak RSS ~1.22 GiB. No CUDA, package download, canonical dataset/model overwrite or commit. Score Parquets retain phase/window/subject/owner-label evidence and hashes solely under research results for subsequent analysis; these truth-bearing research files must never feed production.

Next: independent-seed BUDDHI model and policy transfer using these exact target/feature definitions; measured uncertainty under alternative JAAL partitions; learned-change partition integration in this benchmark; window-duration and repeated-owner controls; causal chain/motif/velocity features; causal origin fusion; then graph/temporal model comparison on these corrected targets. Dashboard changes should follow validated operating behavior, not whichever model sounds advanced.
