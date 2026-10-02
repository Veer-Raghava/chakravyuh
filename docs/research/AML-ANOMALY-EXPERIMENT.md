# AML anomaly detection and measured risk fusion — R27 / R29

Date:2026-10-01. These models were actually fitted on the causal synthetic subject windows. They are research artifacts; no production score changed.

The experiment asks whether label-independent unusualness identifies campaign participants and whether it adds value to supervised ranking. It does not assume unusual means criminal. The data do not yet have independent, adjudicated novelty labels, so this experiment cannot establish semantic anomaly-detection quality.

## Exact methods

**Isolation Forest:**200 estimators, max_samples1024, random_state42, four threads. Fit windows0–3. One control fits all rows without selecting by illicit labels; another fits known-negative training rows. The second uses supervised filtering and is named accordingly. Ranking uses negative sklearn score_samples so larger means more unusual. No probability interpretation.

**Feature autoencoder:**23→64→8→64→23, ReLU hidden layers and linear reconstruction output,4,127 parameters. AdamW lr.001/weightdecay.001,40epochs,batches2048,seed42,fourCPUthreads. Train all fitting rows without label filtering. Use fit-only signed-log/StandardScaler features; score mean squared reconstruction error across23 dimensions. Reconstruction loss is not a probability of laundering.

**Fusion:**frozen XGBoost raw probability logits plus IF score and/or AE error, standardized on windows4–5, then logistic regression fit to labels in those later calibration windows. Four choices: parent alone; parent+IF; parent+AE; parent+IF+AE. Using raw parent logits avoids reusing a parent Platt transformation trained on those same labels. Family selection uses validation P@20 then AP inwindow6; evaluation uses finalthreewindows. No detector or fusion fits test labels. No threshold or illicit-probability guarantee is introduced.

**Typed graph autoencoder:**same23subject/6TX/9IPinputs as the graph classifier, width32 relation-specific mean encoder; separate32×32 bilinear decoders for funding, receipt and announcement links. Logit is transformed-source dot target divided by sqrt32. Positive edges are contrasted with type-correct randomly corrupted targets; actual relation edges are excluded from negatives. Each relation's positive and negative BCE terms receives equal weight.30epochs fixed before evaluation, AdamW lr.001/weightdecay.001,clip5,seed42,fitfirstfourwindows only. No class labels are used in fitting or checkpoint selection.

For inference, mean positive-edge negative log likelihood is aggregated over each subject's incoming/outgoing observed money links. Empty money neighborhoods scorezero. This is link surprise conditioned on the current graph, not held-out link prediction: observed edges participate in both encoding and reconstruction. Random negatives are easier than degree-matched hard negatives; common high-degree links can dominate. The implementation inherits unused classifier/GRU parameters; those receive no gradients and are not part of the anomaly decision. Do not mistake registered parameter count for active model capacity.

## Matched results

| Method | Validation P@20 | Validation AP | Test P@20 | Test AP |
| --- | --- | --- | --- | --- |
| autoencoder_all | 0.00 | 0.0345 | 0.00 | 0.0204 |
| isolation_all | 0.00 | 0.0298 | 0.00 | 0.0135 |
| isolation_known_negative | 0.00 | 0.0319 | 0.00 | 0.0138 |
| parent_ae | 0.70 | 0.1486 | 0.25 | 0.1075 |
| parent_if | 0.80 | 0.1773 | 0.45 | 0.1167 |
| parent_if_ae | 0.75 | 0.1726 | 0.45 | 0.1198 |
| parent_only | 0.75 | 0.1666 | 0.50 | 0.1240 |
| Typed graph link autoencoder | 0.10 | 0.0169 | 0.30 | 0.0207 |

Canonical test prevalence is0.531% (223/42,006subject-window rows). These are the same synthetic target/splits as the tabular and typed graph experiments. They are not comparable with published Elliptic anomaly scores under different supervision/splits.

Validation selects **parent_if**. Its test P@20 .45/AP .1167 are below parent-only .50/.1240. The triple fusion improves some secondary ranking outcomes relative to individual fusions but also does not beat parent AP. We therefore **do not integrate anomaly fusion into the AML score** on these results. Choosing another fusion from test would conceal the validation outcome.

All-data IF and feature AE each retrieve zero campaign participants in top20/top50. This is evidence against their proposed use as campaign prioritizers on these features; it is not proof that they fail to detect unusual legitimate activity. The graph autoencoder retrieves6/20 but AP .0207 versus supervised XGBoost .1240. Its testROC-AUC .3517 indicates widespread inversion/mismatch despite a few useful extremes. Do not flip the score based on the test; any orientation change needs new validation and confirmation.

## Role in the application

Keep novelty separate: an “unusual observed activity” queue can satisfy the anomaly-detection use case if its behavior is demonstrated, explained and validated against declared unusualness scenarios. Label it as unusualness, show high-error/rare features and examples of benign unusual behavior. Do not show an IF/AE score as AML confidence or source-absence probability, and do not silently add it to the supervised score.

Isolation Forest is the simplest CPU novelty candidate, but is **not necessary for the main classifier**, and this run supplies no operational reason to prefer the neural or graph autoencoder. A novelty queue still needs controlled novel-vs-familiar benign and campaign regimes, investigator usefulness measures, duplicate suppression and review budgets. Leave it experimental until those tests pass.

## Cost, commands and reproducibility

IF+AE+fusion completed in23.36sCPU. Typed link autoencoder completed in31.35sCPU, peakprocessRSS1.35GiB. No GPU was required. This is process benchmark timing, not an inference SLA. All models and truth-bearing score files stay under research results.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --offline --no-sync python research/bitcoin/aml_anomaly_benchmark.py
UV_CACHE_DIR=/tmp/uv-cache uv run --offline --no-sync python research/bitcoin/typed_graph_autoencoder.py
```

Saved recipes/reports:
`research/bitcoin/results/aml-anomaly-benchmark/report.json` and
`research/bitcoin/results/typed-graph-autoencoder/report.json`.
Source/model/data hashes and runtime versions are in the R25–R29 manifest; original report hashes remain unchanged. No independent novelty-world confirmation or production promotion is claimed.
