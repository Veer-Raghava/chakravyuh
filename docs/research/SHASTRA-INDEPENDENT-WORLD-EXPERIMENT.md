# SHASTRA independent-world operator-attribution experiment

Date: 2026-10-01. R23. Actual frozen-model CPU experiment; no production promotion.

## Question and protocol

Does the causal five-second candidate scorer and validation-selected answer policy preserve useful behavior beyond the stored agency-v2 capture?

We reconstructed the earlier causal LightGBM, train-only scaler and later Platt calibrator. Its canonical test produced **459/486 correct answered transactions**, exactly matching the earlier result; L1 direct top-1 matched to 1e-12. This checks the fitted recipe before transfer, rather than allowing a new fit to substitute for the baseline silently. The model/processing bundle was then saved and frozen.

The answer policy is unchanged: causal prior-weighted ASN aggregation, legacy separation ≥**.01**, at least two observed observers, and the existing blanket-Tor exclusion. Direct candidate/ASN ranking metrics are separately reported because this policy uses a different aggregation. Neither fresh world selected parameters, calibration or thresholds.

Generated worlds: seeds **1337 and 2026**, same effective configuration family, 20,000 entities, 24,000 requested payments, 48 observers, configured observer fraction .60. The full P2P simulation propagates transactions and records announcements in memory. Raw CSV/JSON/XML copies were not exported. Observed candidate histories use only strictly earlier events; candidate evidence stops five seconds after first observation. Test starts at 70% of each world's observed elapsed span; prior observed history remains available as it would during sequential deployment.

Peer ASN uses capture-supplied metadata, falling back to the fixed offline vendor lookup; network class comes entirely from that lookup, **not hidden entity type or true node class**. Consequently a fixed Tor database may not recognize every new seed-dependent Tor address. The origin node/ASN truth attaches only after observable feature extraction through the explicitly research-only label door. The classifier does not consume true-origin fields, entity IDs or IP strings as model inputs.

## Architecture and parameters

```text
Observed announcements + transaction payer address + fixed offline lookup
                                |
               five-second local evidence + strictly prior histories
                                |
            15 numeric fields + six network-class one-hot fields
                                |
             permitted log1p transforms + frozen train-only scaler
                                |
             CPU LightGBM → frozen Platt logistic calibration
                                |
           capped peer masses → candidate ASN sums → causal ASN prior
                                |
            fixed separation / observers / Tor answer policy
                                |
         operator shortlist + evidence, or insufficient evidence
```

Numeric fields are the 14 ordinary schema features excluding network-class code, plus causal ASN first-rank fraction. Log1p applies to nonnegative count/time fields; peer/ASN first-rank fractions, MLE logscore, Tor/hosting flags stay unlogged. One-hot classes are the existing six-code vocabulary. The resulting input has **21 columns**.

LightGBM: binary objective; 300 boosting rounds; 31 leaves; minimum 40 examples per leaf; learning rate .05; L2=1; deterministic column-wise CPU fit; four threads; seed42. The separate calibration block uses LogisticRegression(C=1,max_iter=1000,random_state=42) on clipped raw logits. Fit ends45%, calibration ends60%, validation60–70%, test final30%; five-second boundary-crossing fit/calibration decisions are excluded. This is the original frozen recipe, not a newly selected neural architecture.

For each transaction, calibrated peer masses are divided by their total only if the sum exceeds1. ASN masses sum candidate-peer masses. The policy multiplies each ASN mass by its causal first-rank prior; legacy top-two exponential normalization gives separation tanh((w1−w2)/2). The small .01 margin is specific to this recipe and is not interchangeable with a direct probability separation. Residual peer mass is **not calibrated missing-origin probability**.

## Measured outcomes

| Metric | Canonical capture replay | Fresh seed1337 | Fresh seed2026 |
|---|---:|---:|---:|
| Test transactions with candidates | 9,671 | 11,192 | 10,749 |
| Candidate binary AP | .3212 | .3609 | .2876 |
| Exact source peer present within five seconds | .4681 | .4920 | .4595 |
| Exact peer top1 | .2404 | .2668 | .2383 |
| Exact peer top3 | .3077 | .3360 | .3017 |
| Direct ASN top1 | .4580 | .4700 | .4599 |
| Direct ASN top3 | .7133 | .7222 | .7230 |
| Prior-weighted ASN top1 | .4564 | .4619 | .4576 |
| Fixed-policy correct / answered | 459/486 | 593/640 | 459/529 |
| Answer precision | .9444 | .9266 | .8677 |
| Answer coverage of observed test transactions | .0503 | .0572 | .0492 |

Fresh captures contained **911,294 and917,201 announcements**. There were33,455/33,795 network origin events across each whole run, of which350/339 had **no observer capture at all**. Those counts concern the whole simulation; they are not denominators for final-period precision. The scored denominator is transactions with observations/candidates; unobserved transactions cannot silently acquire an answer.

These figures demonstrate useful simulator-conditional selective attribution and show **failure to maintain the nominal 90% precision target in every world**. Direct ASN ranking remains near46–47%, while answering only roughly5% of observed cases raises precision. No GPU-heavy network architecture is required to obtain that bounded capability. Nothing here establishes real-network accuracy, full source recovery or a person's identity.

## Exact-peer absence changes answer quality

A posthoc truth-stratified diagnostic applies the same fixed policy, without changing selection:

| World | Source peer present: correct / answered | Source peer absent: correct / answered |
|---|---:|---:|
| Canonical | 392/395 (99.24%) | 67/91 (73.63%) |
| Fresh1337 | 548/553 (99.10%) | 45/87 (51.72%) |
| Fresh2026 | 383/394 (97.21%) | 76/135 (56.30%) |

This localizes a major failure mechanism: the answer policy is strong when the source peer was observed, but lacks a trustworthy observable gate identifying that situation. An ASN estimate can still be correct when the exact source peer is absent, because a relay may share its operator; this does not establish exact peer or human attribution. **The truth-based split is an inaccessible research diagnostic, never a production filter.** The earlier missing-source classifier did not qualify for reliable absence declarations. It cannot be replaced with this hidden flag.

The meaningful next research question is joint evidence sufficiency/answer selection under source censoring, rather than simply maximizing candidate-row AP. Preserve answer precision/coverage, false-absence rates, five-second candidate ceilings and operator/host grains as separate metrics. The tool can report insufficient evidence without falsely stating a real person does not exist in the dataset.

## Resource measurement, artifacts and limits

Two full fresh worlds plus canonical fitting/scoring completed in **83.19 seconds CPU**, peak process RSS **~2.33 GiB**. Per-world combined generation/extraction/scoring was37.68/39.00s. This is measured whole-experiment cost, not a per-transaction latency or minimum hardware claim. Persisted bundle/three transaction-score files/JSON summaries occupy about4MiB. No raw-format world export, GPU, dependency install, generated-data deletion or commit.

Scripts: `research/bitcoin/shastra_world_transfer.py`. JSON: `research/bitcoin/results/shastra-world-transfer.json`. Fitted bundle and research-only scores: `results/shastra-world-transfer/`. Separate source-presence diagnostic: `shastra-world-transfer-source-presence-diagnostic.json`. Each world summary is saved immediately on completion; SHA-256 input/source/bundle/score records and source snapshots preserve provenance.

All data still comes from one simulator family. Seeds were previously explored for JAAL; canonical test periods are consumed. Fixed offline enrichment and generator versions are part of the experiment. The separate R21 audit found a fresh same-seed chain does not replay stored canonical TXIDs, so historical generator/source reconstruction remains outstanding. Results are not a claim of pristine preregistered confirmation. Default SHASTRA stage remains unchanged; the opt-in causal implementation is not yet wired into its shipped artifact pipeline.

## R26 — Learned observable evidence-sufficiency gates

An actual13-input gate was trained to predict whether the frozen causal parent model's chosen ASN is correct. Inputs: candidate_mass, best_candidate_p, second_candidate_p, n_candidates, n_observers_in_tx, total_announcements, mean_peer_history, max_payer_history, p1, p2, separation, any_tor, legacy_separation. Count/history inputs receive the script's declared log transforms; gate StandardScaler fits only its training transactions. True source-presence and controller identity are excluded from inference inputs.

Parent fitting ends45% of elapsedtime and Plattcalibration ends60%. Gatefit60–65%, gatepolicyselection65–70%, testfinal30%; five-second boundary-crossing decisions are purged. This is exploratory: the original parent's .01 policy had already used60–70%, and these canonical/fresh-world scores were previously inspected. It is not a pristine nested confirmation.

Two models: standardized LogisticRegression(C1,max_iter1000,seed42); nativeLightGBM(binary,150rounds,15leaves,min_data_in_leaf40,learning_rate.05,fourthreads,seed42,deterministic). Policy maximizes validation answer count subject to≥100answers and observedprecision≥.90, at leasttwoobservers and noanyTor. Validation selectsLR,104/115correct, threshold.6806108057474762; LGB103/114, threshold.7893973216025532.

| Gate | World | Correct / answered | Precision | Coverage | Source-absent correct / answered |
| --- | --- | --- | --- | --- | --- |
| LR | Canonical | 732/833 | .8788 | .0861 | 131/221 |
| LR | Seed1337 | 869/1002 | .8673 | .0895 | 116/240 |
| LR | Seed2026 | 696/828 | .8406 | .0770 | 160/276 |
| LGB | Canonical | 780/907 | .8600 | .0938 | 149/258 |
| LGB | Seed1337 | 901/1044 | .8630 | .0933 | 102/231 |
| LGB | Seed2026 | 781/964 | .8102 | .0897 | 176/339 |

Coverage rises compared with the old abstainingpolicy, but observed≥90%validationprecision does not transfer. These gates are research candidates, not promoted decisions. Correct ASN when the exact sourcepeer is absent can result from nearby relays sharing the ASN; it does not recover the host/person. Gate correctness and source presence remain different targets.

The initial subgroup calculation mistakenly inverted integer0/1presence values instead of boolean masks. Main ranking, answers, precision, coverage and model selection were unaffected. Initial report/source remain archived; corrected report is in `research/bitcoin/results/source-sufficiency-gate/report.json`. A regression fixture explicitly covers integerpresence and verifies absence hits≤answers. Corrected run took3.24sCPU. No defaultSHASTRAmodel or policy changed.
