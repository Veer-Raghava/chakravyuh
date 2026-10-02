# External Bitcoin graph-model experiment (R15)

## Decision supported by this experiment

Graph-feature LightGBM is the strongest tested AP configuration in this specific run. Its .6566 AP versus .6366 for local-only LightGBM is evidence that graph information can help a tree model. The trained GCN embedding hybrid reaches .6464 AP, below the engineered-feature control. This supports benchmarking handcrafted graph features before adding a learned representation. It does not prove that optimized temporal/heterogeneous GNNs are inferior or establish a production model for our synthetic application.

Script: `research/bitcoin/elliptic_graph_benchmark.py`. Final result and complete learning curves: `research/bitcoin/results/elliptic-graph-benchmark.json`. Initial result: `research/bitcoin/results/elliptic-graph-benchmark-60-epochs.json`. No project model/graph/default was changed.

## Data and protocol

Vendored named Elliptic export: 203,769 transaction nodes, 234,355 flow edges. Exactly 93 `Local_feature_*` attributes are inputs. Timestamp, all `Aggregate_feature_*` and extra `out_BTC_*` attributes are excluded. Unknown labels are retained as graph context and never treated as negatives. Only author-labeled illicit/licit nodes contribute supervised loss or evaluation. There are 11,184 labeled test nodes, of which 636 are illicit (5.69% prevalence). Missing-label selection can bias metrics and calibrated probabilities relative to the full transaction population.

| Role | Public time steps | Uses labels? |
|---|---|---|
| Fit model/scaler | 1–30 | Fit loss only on labeled nodes; scaler on all earlier nodes |
| Select neural checkpoint by AP | 31–34 | Validation labels only |
| Platt calibration | 35–37 | Calibration labels only |
| Select response threshold by F1 | 38–39 | Policy-validation labels only |
| Evaluate | 40–49 | Metrics only |

All fitting adjacency excludes later-period nodes/edges. No cross-step edges exist in this export, verified from all edges before fitting, so batching steps within a phase cannot introduce another step's graph neighborhood. Inference uses the observed unlabeled adjacency within each time step. This is snapshot-transductive, not sub-second online inference: no finer node/edge timestamps are supplied. Named local attributes are supplied by the vendor; their event-time provenance has not been independently certified. Restricting columns removes obvious neighbor-aggregate inputs but is not a proof that every local attribute is causal.

The public dataset was already used by this project. Both runs are exploratory comparisons, not a newly untouched confirmatory test. No reported metrics from different papers are combined with this table.

## Results at the extended budget

| Configuration | Test AP | Test F1 | Precision@20 | Best neural epoch |
|---|---:|---:|---:|---:|
| gcn | 0.2629 | 0.3537 | 0.15 | 215 |
| gcn_embedding_lightgbm | 0.6464 | 0.6356 | 1.00 | — |
| gcn_permuted | 0.1036 | 0.1884 | 0.00 | 235 |
| lightgbm_graph_features | 0.6566 | 0.6872 | 1.00 | — |
| lightgbm_local | 0.6366 | 0.6238 | 1.00 | — |
| mlp | 0.2993 | 0.5463 | 0.00 | 185 |
| sage_variant | 0.2779 | 0.5010 | 0.00 | 235 |
| xgboost_local | 0.6432 | 0.6562 | 1.00 | — |

All tree configurations use 300 rounds on identical fit labels. GNN/MLP maximum budget was increased from 60 to 240 epochs because all initial best validation checkpoints were at the budget boundary. Selection still uses validation AP, not test AP. The more-trained MLP/SAGE variant had much higher checkpoint-selection AP but worse later test AP than their initial versions. For example, final MLP validation AP .8914 versus test .2993; SAGE variant validation .9462 versus test .2779. This is evidence of poor generalization in this protocol. It is not enough to isolate whether overfitting, time shift, class composition or supplied feature distributions cause the gap; controlled diagnoses are next work. Do not choose the 60-epoch checkpoint after reading test results and call it independent validation.

True-graph GCN AP .2629 exceeds the within-step node-permuted graph control .1036. Thus this run does not support saying all topology is useless or that random wiring wins. A node permutation preserves graph shape and degree distribution, but relocates degree/neighbor patterns onto different feature-bearing transactions; it does not preserve each named transaction's degree. The relevant result is that the tested graph encoder remains substantially below the tabular and engineered-graph controls.

## Architecture and parameters

Let `A` be transaction-flow adjacency symmetrized by adding reverse edges; add identity/self loops and normalize `Ahat = D^-1/2 (A + I) D^-1/2`. Flow direction is preserved only by the engineered in/out degree fields, not by the symmetric GCN. All input feature standardization fits earlier steps only.

**GCN:** `H = ReLU(Ahat X W1 + b1)`, followed by `.2` dropout and `z = Ahat Dropout(H) W2 + b2`. Input 93, hidden 32, output 1; 3,041 learned parameters. Output sigmoid is a raw class score. AdamW learning rate .005, weight decay .0005; weighted BCE positive weight sqrt(negative/positive) measured from labeled fit nodes; full-batch CPU training, four threads, seed 42. Check validation every five epochs; select highest AP and restore that state.

**MLP control:** `H = ReLU(X W1+b1)`, `z = Dropout(H) W2+b2`; same widths, dropout, optimizer, labeled fit loss and checkpoint rule. It has no graph operator.

**SAGE variant:** `H = ReLU(concat(X,Ahat X) W1+b1)`, then `z = concat(Dropout(H),Ahat Dropout(H)) W2+b2`. The explicit self-feature path may preserve information lost by neighbor-only smoothing. 6,049 parameters. It uses symmetric normalization and self loops rather than canonical sampled mean GraphSAGE; named accordingly. No claim of exact GraphSAGE reproduction.

**Tree graph features:** concatenate 93 standardized local features, 93 normalized neighbor features `Ahat X`, and log1p in/out degree: 188 inputs. This is a simple local-neighborhood control, not a complete PageRank/motif/flow/time-feature pipeline. LightGBM: binary objective, 300 rounds, 31 leaves, min leaf 40, learning rate .05, L2=1, seed 42, four CPU threads, deterministic/force-column-wise. Local-only control uses the same recipe with 93 inputs.

**Embedding hybrid:** concatenate original local attributes with the selected trained GCN's 32 hidden outputs, yielding 125 inputs; train LightGBM on fit labels only. The encoder is fixed after checkpoint selection. No later labels train the encoder or booster. This demonstrates the hybrid, not an exhaustive search over encoders/head models.

**XGBoost local:** 300 trees, depth 5, lr .05, child weight 10, row/column subsample .9, default L2=1, CPU hist/four threads, seed 42.

All raw model probabilities are clipped at 1e-6, transformed to logits, then fitted to a logistic Platt mapping on calibration steps 35–37. Thresholds .01 through .99 are scored on policy steps 38–39 for F1, with lower threshold winning equal F1. Those fixed thresholds score test F1/precision/recall. AP/ROC-AUC/Brier/top-K and per-step ranking metrics are also stored. The top-20 metric is among known-labeled transaction candidates; it is neither wallet/entity precision nor a guarantee for unlabeled live alerts.

## Resource and reproducibility evidence

Final complete run: ~108.68 seconds CPU, whole-process peak RSS ~1.99 GiB. These are local end-to-end measurements, not per-request inference latency or a guaranteed deployment footprint. No CUDA, GPU, torch_geometric, network download or generated dataset. Runtime module versions: Torch 2.14.1+cpu, NumPy 2.4.6, Polars 1.17.1, sklearn 1.9.0, LightGBM 4.5.0, XGBoost 3.2.0. Optional research Torch/XGBoost versions are recorded here; they are not pinned production dependencies. Input/source SHA-256 hashes are stored in JSON.

The extended run initially failed during version-report construction because XGBoost could be imported while distribution metadata was absent; version metadata had also been inserted in the wrong parameter dictionary. Corrected to loaded module versions in report provenance, then reran the entire benchmark. Sparse tensor invariant checks are enabled. Both initial and final successful outputs plus failure events are retained.

## Literature context and next scientific checks

The original [Weber et al. Elliptic paper (2019)](https://arxiv.org/abs/1908.02591) motivates transaction-graph baselines. [Maganti (2026), When Graph Structure Becomes a Liability](https://arxiv.org/abs/2604.19514), motivates excluding future adjacency and testing shuffled topology. This latter work is a preprint; its page says code is to be released soon despite the abstract's release wording, so reproduction availability should not be assumed. Our split, supplied export, feature restriction, budgets and controls differ; its reported F1 values are not directly comparable with our table.

Next checks: multiple seeds and validation-only architecture/regularization choices; graph direction/residual connections; earlier-window model selection robustness; per-step class/feature shift; compare degree/neighbor features against richer motif/temporal engineered features; inspect labeled-sample bias; profile separate inference; only then test learned temporal/heterogeneous representations on causally valid project graphs. Public Elliptic contains transaction-flow relationships rather than observed IP/wallet ground truth, so these results do not answer JAAL clustering or SHASTRA source attribution.
