# SHASTRA observation-coverage stress test

R41, executed 2026-10-01. This paired experiment exposes a serious transfer failure in the frozen causal source-ASN answer policy. It does not change the standard application backend or claim reliable source absence detection.

## Method

Start with the canonical capture and frozen R23 LightGBM/scaler/Platt model and answer policy. Select nested active observer sets of 48, 24 and eight by SHA-256 order of observer-IP strings, before evaluating performance. Filter announcements to those observers. Recompute **all** causal candidate/history features from each reduced capture; no original-capture history columns enter the model. Pass the actual active observer count into the registered feature calculation. Hold supplied offline peer metadata fixed.

Every result uses the same original captured test-transaction cohort, 9,671 TXIDs. Those TXIDs fix the evaluation population, not the policy's input. Features and decisions use only the thinned observations. Transactions that disappear are counted instead of silently removed from the full-capture denominator. The baseline itself excludes transactions never observed in the original capture, so this is not a full-world coverage estimate.

The answer policy remains its original validation choice: prior-weighted ASN score gap at least .01, at least two observers within the decision horizon, and no Tor-class candidate. No policy, model or threshold refits on reduced captures. Full 48-observer replay exactly reproduces 459 correct answers among486.

## Actual results

| Active observers | Observed test TXs | True source in five-second candidates | Correct / answered ASN predictions | Answer precision | Coverage of full-capture test |
| --- | --- | --- | --- | --- | --- |
| 48 | 9671 | 0.468 | 459 / 486 | 0.944 | 0.050 |
| 24 | 9664 | 0.247 | 1206 / 2361 | 0.511 | 0.244 |
| 8 | 9643 | 0.081 | 2145 / 8120 | 0.264 | 0.840 |

The policy becomes **more willing to answer while its precision collapses**. This invalidates applying its nominal confidence threshold unchanged across capture regimes. Median candidate count falls26→13→5; median legacy gap rises .00199→.00583→.04485; median candidate mass rises .3465→.4831→.9519. Model scores and the gap are responding to altered observations, not measuring calibrated certainty about the hidden source.

The raw score construction aggregates candidate probability mass by ASN, multiplies by a past-first-arrival prior, then calculates `tanh((w1 - w2) / 2)`. This is a ranking/separation heuristic. It is not a posterior over all possible observed and unobserved sources. A larger observed-candidate gap can coexist with a missing true source. Changes in observer-count features, available rivals, histories and prior distributions occur together; these diagnostics do not isolate a single causal mechanism.

Among answered transactions whose actual originating host is absent from the five-second candidate set, correct ASN answers are67/91,584/1,671 and1,631/7,455. An ASN may be correct even when the host is absent, because another observed peer shares the operator. This is why source-host presence and source-ASN correctness must be evaluated separately. Truth presence never gates production decisions here.

## Engineering decision

Do not export the .01 threshold as a general confidence guarantee. A source model needs a versioned observation contract: active monitors, placement/coverage assumptions, capture horizon, peer lookup version and supported calibration regimes. Known unsupported regimes should produce an unsupported-policy/insufficient-evidence outcome until separately evaluated. Matching observer count alone cannot establish matching network coverage or exchangeability.

A future gate should learn correctness or candidate-set sufficiency from observable evidence, be calibrated on separate worlds/regimes, and be evaluated for both answered precision and coverage, including absent-source cases. R26's learned gates already failed the90% target in transfer; they are not a solved replacement. An explicit unobserved-source possibility or compatible-source confidence set is scientifically preferable to forcing every prediction into the observed candidate list, but requires a validated propagation/observation model.

Keep the nominal demo world and these harder regimes separately labeled. Making every synthetic world difficult is unnecessary; hiding difficult cases is equally indefensible. Baseline/easy worlds demonstrate the working pipeline, while preregistered stress worlds measure its failure boundaries. Stronger GPUs cannot supply unobserved distinguishing evidence.

This finding strengthens the argument for parallel AML evidence, reversible ownership hypotheses and source abstention. It does not justify discarding transaction intelligence because exact sender identification is uncertain.

## Limits and reproducibility

This is nested post-capture thinning of a **consumed canonical world**, not a newly simulated propagation network, random-placement study or independent performance confirmation. One deterministic nested subset does not quantify variance across observer placements. More seeds and placement patterns remain required. Supplied peer metadata is held fixed. No full-world coverage or reliable source-absence claim follows.

Execution: `UV_CACHE_DIR=/tmp/uv-cache uv run --offline --no-sync python research/bitcoin/shastra_observer_thinning.py`. The script uses a fixed output directory and refuses to reuse it. Outputs include per-regime scores, summaries, observer ordering, model/source hashes and observable shift diagnostics under `research/bitcoin/results/shastra-observer-thinning/`. Total three-case inference/feature work took about4.76seconds, excluding interpreter/model load overhead.
