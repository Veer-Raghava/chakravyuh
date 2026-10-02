# Trained temporal heterogeneous graph experiments — R25 and R28

Date: 2026-10-01. Research implementations actually trained on CPU. No canonical model, dashboard backend or saved capture has been replaced. The result is a promising graph challenger with unproven operational calibration, not a claim of real-network accuracy or human identification.

## Implementations and evidence

- `research/bitcoin/temporal_hetero_benchmark.py`: custom typed mean-message neural network, static and temporal variants, matched local controls and embedding→XGBoost hybrid.
- `research/bitcoin/typed_graph_transfer.py`: frozen inference on newly generated P2P captures, no transfer fitting.
- `research/bitcoin/tests/test_temporal_graph_contract.py`: four adversarial contract tests, actually passed.
- Initial artifacts: `research/bitcoin/results/temporal-hetero-benchmark/`.
- Longer budget: `research/bitcoin/results/temporal-hetero-extended/`.
- Each directory preserves weights, feature scalers, model JSON and truth-bearing research score Parquets. Keep those evaluation labels outside the serving pipeline.

This is **not a reproduction of HGT, TGN, TGAT or EvolveGCN**. Typed relation transforms are motivated by [R-GCN](https://arxiv.org/abs/1703.06103). Unlike [EvolveGCN](https://arxiv.org/abs/1902.10191), our model updates node states rather than evolving convolution parameters. Unlike the event-based [TGN framework](https://arxiv.org/abs/2006.10637), it uses fixed windows and address-linked recurrent state. These distinctions matter for any paper or UI claim.

## Target, observation boundary and split

The target is **observed in-window participation by a synthetic campaign controller**, aggregated to an inferred subject. It is neither real-world guilt nor an immutable wallet label. Labels attach after label-free feature construction. A subject is positive if any of its members maps to an owner participating in observed campaign transactions in that window. Consequently incorrect ownership merges can contaminate supervision. Oracle controller labels are evaluation-only.

Ten equal-duration observation windows: first four fit; next two calibrate; window six (zero-based) selects checkpoints/models; final three test. JAAL ownership evidence is bounded at each window end with threshold .30 (CIOH-only for this experiment). Feature scaling fits only first-four-window rows. Decisions are made **at the window end**, so current-window context is available; this is not a per-transaction real-time claim. Repeated subjects/controllers across windows are allowed. A controller-held-out task remains separate.

Canonical pooled test has 42,006 subject-window decisions and 223 positives (0.531%). The last test window has zero campaign positives. Pooled P@20 can concentrate alerts in one window; per-window results are stored and must accompany an operational claim. Repeated controllers need deduplication and controller/campaign yield before claiming 20 independent leads.

## Exact graph and inputs

Node types:

1. Inferred wallet subject: 23 causal features.
2. Transaction: six observed body features.
3. Announcing IP: nine window-local observation/enrichment features.

Relations are directed and separately parameterized: subject→transaction funding; transaction→subject receipt; IP→transaction announcement. Announcer is not assumed to be source. Identifiers index edges and address memory but are not numerical model inputs. There are no true-controller links, label-neighbor counts, true change labels or simulator node-class inputs.

Subject columns, in order:

```text
n_addresses, n_tx_sent, total_sent_sats, mean_sent_sats, n_tx_received, total_received_sats, mean_received_sats, balance_sats, n_counterparties, max_fan_out, n_coinbase_received, frac_equal_outputs, mean_fee_rate, median_dwell_us, min_edge_confidence, n_heuristics, n_script_types, fan_in_ratio, peel_chain_depth, peel_leak_frac, structuring_frac, burstiness, fee_anomaly
```

These are engineered summaries, including exact gross input/output flows and opposite-side counterparties. Gross input includes subsequently returned change, so it is not an inferred external-payment amount. Ten legacy global attribution/typology columns are excluded. `matrix()` uses the frozen signed-log transform from the tabular comparison and then fit-only StandardScaler.

TX columns: `n_in`, `n_out`, `total_out_sats`, `fee_sats`, `fee_rate_sat_vb`, `has_equal_outputs`. Nonnegative log1p precedes scaling. IP columns: log1p announcement count, unique TX count and unique observer count, plus six-way fixed offline network-class one-hot. Scaling also fits only training windows. The canonical graph has approximately 12k–17k subjects and ~3k TX nodes per window; exact counts are in report JSON.

For newly generated worlds, all graph TX times are rebuilt from the first observed announcement; unobserved transactions are excluded. Address availability is recomputed from observed inputs/outputs. This assumes complete transaction-body availability at first announcement. It does not model body retrieval delays or reproduce malformed export/quarantine faults in the canonical capture.

## Neural architecture, equations and parameters

All types are projected separately to width 32 with Linear+ReLU. Let `mean_R` aggregate only actual directed relation edges, with zero output for empty neighborhoods. The first typed message update is:

```text
encoded_subject = ReLU(Linear23→32(subject_features))
encoded_tx      = ReLU(Linear6→32(tx_features))
encoded_ip      = ReLU(Linear9→32(ip_features))

tx_context = ReLU(encoded_tx
                  + W_funds * mean(encoded_subject at funding edges)
                  + W_announces * mean(encoded_ip at announcing edges))

subject_context = ReLU(W_self * encoded_subject + bias
                       + W_receives * mean(tx_context at receipt edges)
                       + W_spends * mean(tx_context at funding edges reversed))
```

`W_funds`, `W_announces`, `W_receives`, `W_spends` are separate bias-free 32×32 learned matrices. The self update is a biased 32→32 linear layer. This can learn relation-specific interactions from neighborhoods that are lost in a single degree/fan-out summary. It is still finite-depth mean aggregation, so it does not reconstruct all paths, preserve every order within a window, or resolve ambiguous ownership.

The temporal variant applies `GRUCell(32,32)` to current subject context and pooled prior embeddings. Memory follows addresses previously observed in earlier windows, allowing subject IDs/partitions to change. Prior state can be associated with several addresses; repeated membership weights that pooling. It is not verified owner tracking. A subject merge can carry contaminated memory. States are detached between windows (truncated gradients); inference updates them without labels across all ten windows. Within-window event ordering is summarized by engineered features; GRU captures inter-window history.

Dropout .20 precedes a biased Linear32→1 sigmoid classifier. Initial budget 60 epochs, extended budget 180; checkpoints every five epochs maximize validation AP. AdamW lr .001, weight decay .001; gradient norm clip 5; seed42; four CPU threads. Loss is binary cross entropy with positive weight `sqrt(n_negative/n_positive)` = 13.354832 on fit rows. Each fit window makes an optimizer update and resets/rebuilds its causal memory sequence each epoch.

The registered module has 12,833 parameters for every variant, but unused modules must not inflate the effective-capacity comparison: local MLP uses 1,857 parameters; static typed model uses 6,497; temporal model uses all 12,833. A genuinely capacity-matched larger MLP is still an open control. The graph-permutation control is stronger evidence about relation alignment than MLP alone.

Scores use Platt logistic calibration on clipped probability logits in windows four/five. Calibration is a fitted mapping, **not proof of probability validity under future-world shift**. Family choice is validation P@20 followed by AP. No test-based winner is promoted.

## Tabular and hybrid controls

Local XGBoost receives the same 23 scaled subject columns. Typed-feature XGBoost receives those plus mean TX/IP contexts on incoming and outgoing relations, constructed without labels. The hybrid receives 23 local columns plus the learned 32-dimensional temporal embedding (55 inputs).

XGBoost: 300 trees, max depth5, learning rate.05, min child weight10, subsample.9, column sample.9, histogram tree method, four threads, seed42. Supervised encoder fitting and tree fitting use the same fit rows. That is a two-stage feature-learning experiment, **not an out-of-fold stacking claim**. Encoder coordinates must remain frozen/versioned across inference. Forward cross-fitting or past-only self-supervised pretraining is a worthwhile later comparison.

Shuffled control permutes subject endpoints within each window while retaining graph size and degrees. It breaks correspondence between relational position and subject features/labels; address memory stays correct. Its worse result supports informative relationship alignment, but does not isolate every possible generator shortcut or parameter-capacity effect.

## Initial 60-epoch results

| Model | Selected epoch | Validation P@20 | Validation AP | Test P@20 | Test AP |
| --- | --- | --- | --- | --- | --- |
| mlp | 55 | 0.40 | 0.0950 | 0.30 | 0.0817 |
| temporal_embeddings_xgboost | tree | 0.85 | 0.3160 | 0.65 | 0.2244 |
| typed_static | 60 | 0.70 | 0.2814 | 0.90 | 0.2537 |
| typed_temporal_gru | 45 | 0.80 | 0.2811 | 0.85 | 0.2736 |
| typed_temporal_shuffled | 60 | 0.35 | 0.0979 | 0.40 | 0.0796 |
| xgboost_local | tree | 0.75 | 0.1666 | 0.50 | 0.1240 |
| xgboost_typed_features | tree | 0.35 | 0.2463 | 0.60 | 0.2270 |

Validation chose `temporal_embeddings_xgboost`. Static GNN and shuffled model selected epoch60, so an extended budget was justified. Temporal graph test AP improved over local XGBoost, but the chosen hybrid's P@20 was lower than either neural graph head. Selection and test outcomes are both shown.

Initial run: 41.59s, peak process RSS 1.39GiB. This includes graph building/training/scoring in this process, not a deployed inference SLA or whole-machine RAM guarantee.

## Frozen independent P2P-world transfer of initial models

Seeds10007/20011 were recorded before generation. Models, scalers, calibration and thresholds were frozen. Every canonical score replayed exactly (maximum error0.0 for all five candidates). Each policy chose maximum validation coverage with ≥10 answers and observed ≥90% precision. No new-world threshold fitting.

| New seed | Model | Test P@20 | Test AP | Fixed-policy correct / answered | Precision |
| --- | --- | --- | --- | --- | --- |
| 10007 | mlp | 0.20 | 0.0430 | 0 / 0 | no policy |
| 10007 | temporal_embeddings_xgboost | 0.65 | 0.2318 | 16 / 33 | 0.485 |
| 10007 | typed_static | 0.70 | 0.1738 | 15 / 21 | 0.714 |
| 10007 | typed_temporal_gru | 0.55 | 0.1786 | 8 / 17 | 0.471 |
| 10007 | xgboost_local | 0.75 | 0.1421 | 33 / 68 | 0.485 |
| 20011 | mlp | 0.25 | 0.0681 | 0 / 0 | no policy |
| 20011 | temporal_embeddings_xgboost | 0.90 | 0.2114 | 29 / 41 | 0.707 |
| 20011 | typed_static | 0.70 | 0.1985 | 20 / 26 | 0.769 |
| 20011 | typed_temporal_gru | 0.80 | 0.1990 | 21 / 27 | 0.778 |
| 20011 | xgboost_local | 0.90 | 0.1300 | 28 / 55 | 0.509 |

Both new seeds share the generator family; this is internal transfer, not real Bitcoin validation. The hybrid's AP advantage survives on both worlds. Its P@20 is below local XGBoost on one world and tied on the other. **Every feasible frozen ≥90%-validation policy falls below90% on transfer.** Better AP cannot justify confident adjudication. Full transfer cost 128.74s and 2.03GiB peak process RSS, including two actual P2P simulations.

## Extended 180-epoch sensitivity

| Model | Selected epoch | Validation P@20 | Validation AP | Test P@20 | Test AP |
| --- | --- | --- | --- | --- | --- |
| mlp | 80 | 0.40 | 0.0977 | 0.25 | 0.0766 |
| temporal_embeddings_xgboost | tree | 0.80 | 0.2233 | 0.95 | 0.2768 |
| typed_static | 65 | 0.70 | 0.2836 | 0.90 | 0.2555 |
| typed_temporal_gru | 95 | 0.80 | 0.2830 | 0.75 | 0.2701 |
| typed_temporal_shuffled | 65 | 0.35 | 0.0991 | 0.45 | 0.0828 |
| xgboost_local | tree | 0.75 | 0.1666 | 0.50 | 0.1240 |
| xgboost_typed_features | tree | 0.35 | 0.2463 | 0.60 | 0.2270 |

Validation now chooses `typed_temporal_gru`, selected at epoch95; static picks65, shuffled65, MLP80. Thus the original endpoint concern is resolved at this budget. The longer hybrid reaches test P@20 .95 but is **not** the validation-selected winner. Reporting only that number would conceal selection instability and use the test to choose a favorite.

Runtime 75.75s, peak process RSS 1.45GiB. Frozen transfer on new seeds30011/40009 completed; results are recorded below. Do not reuse the initial transfer worlds as new confirmation.

## Explainability, hardware and release decision

This modest model actually trains on CPU; GPU is not required for the tested architecture. PyTorch runtime must be packaged offline. Larger event-memory/HGT models may benefit from a GPU, but no measured minimum VRAM is established here.

Tree SHAP can explain engineered XGBoost features. SHAP on embedding coordinate17 explains a learned coordinate, not a money-flow path. To promote the graph model, implement edge/event ablation and analyst-readable causal paths with ownership uncertainty, then test fidelity and stability. Attention alone would not solve that problem. Evidence paths are useful even when model attribution remains separate.

Keep the CPU LightGBM reference, benchmark XGBoost, and retain this trained typed temporal candidate for continued validation. Do not expose a fabricated GPU-only engine selector. A production switch requires controller/campaign deduplicated workload evaluation, multiple untouched configurations, observation-coverage shifts, calibrated selective policies, packaging and explanation tests. The useful scientific question has changed: graph information is demonstrably helpful on these synthetic worlds, but the operational benefit and trustworthy decision threshold remain unresolved.

## Verification and provenance caveats

Four adversarial tests pass: directed mean aggregation and empty neighbors; changing future graphs and all labels leaves past fixed-weight predictions unchanged; prior memory can influence later predictions; integer source-presence diagnostics use boolean masks. These test inference properties, not the entire data pipeline. Existing snapshot/provenance tests separately cover cutoff construction and flow conservation.

Sources are archived by SHA256. Extended training launched the `94020c...` source; Ruff later reordered only imports while that process was running, so its end-of-run filesystem digest is `a6d59a...`. Both files are preserved; substantive training code is identical. Never treat a hash collected at process exit as automatic proof of exactly the loaded module. Initial pre-refactor source, transfer build refactor and corrected diagnostic versions are also retained. This distinction is recorded in the manifest rather than hidden.

## Extended-model transfer on untouched seeds30011/40009

The extended models, scalers, Platt mappings and policies were frozen before these new worlds were generated. Canonical replay errors remained exactly0.0 for all five candidates. No transfer labels were used for fitting or selection.

| Seed | Model | Test P@20 | Test AP | Policy correct/answered | Precision |
| --- | --- | --- | --- | --- | --- |
| 30011 | mlp | 0.20 | 0.0200 | 0/0 | no feasible validation policy |
| 30011 | temporal_embeddings_xgboost | 0.35 | 0.2658 | 0/0 | no feasible validation policy |
| 30011 | typed_static | 0.70 | 0.1617 | 14/33 | 0.424 |
| 30011 | typed_temporal_gru | 0.55 | 0.2491 | 19/48 | 0.396 |
| 30011 | xgboost_local | 0.30 | 0.0719 | 8/33 | 0.242 |
| 40009 | mlp | 0.35 | 0.0730 | 0/0 | no feasible validation policy |
| 40009 | temporal_embeddings_xgboost | 1.00 | 0.2153 | 0/0 | no feasible validation policy |
| 40009 | typed_static | 0.80 | 0.2129 | 22/26 | 0.846 |
| 40009 | typed_temporal_gru | 0.95 | 0.2263 | 32/38 | 0.842 |
| 40009 | xgboost_local | 0.75 | 0.1494 | 33/54 | 0.611 |

The validation-selected temporal model improves AP and P@20 over local XGBoost on both worlds. Its threshold precision still fails90% (.396/.842). The hybrid has no qualifying ≥10-answer90%-precision validation threshold, even though its test ranking can be strong. This is a useful distinction between a ranked queue and a defensible confident-answer policy.

Combined CPU cost 140.82s, peakprocessRSS 2.39GiB. Same simulator family and network assumptions; configuration/regime transfer and real-world confirmation remain open.
