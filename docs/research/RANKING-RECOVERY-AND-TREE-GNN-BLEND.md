# Ranking recovery and a tree–temporal-GNN blend

2 October 2026. Executed supplementary analysis in response to the team's concern about average precision. This checkpoint measures how much suspicious activity is retrieved at different review budgets, and tests whether two existing models provide complementary rankings. It does not train new model weights or change the production engine.

## Why we ran this

High Precision@20 can coexist with moderate average precision. The first metric describes a small initial queue; the second reflects the full ranking. Improving the system therefore requires examining recovery at larger budgets, rather than replacing a difficult metric with a flattering one.

The canonical address-window test contains 57,105 decisions and 295 positives: 0.5166% prevalence. Average precision is not accuracy. Its approximate random-ranking reference is the prevalence. Positive address-window decisions can repeat an actor; neither the count nor the precision identifies people.

## Executed comparison

Inputs were the saved 329-feature address XGBoost scores from R37 and the saved temporal typed GRU scores from R47. Both score the same address-window keys. The script verifies uniqueness, full one-to-one alignment, identical target labels and identical phase assignments before combining scores.

Five tree weights were registered: 0, .25, .50, .75 and 1. For each weight `w`, the score is:

```text
blend_score = w * tree_score + (1 - w) * temporal_gnn_score
```

Validation average precision selects the weight, with validation P@20 as a secondary criterion and candidate order breaking further ties. The selected weight is **.75**. Only after selection does the script evaluate the frozen blend on test windows. Review-budget ties use subject ID for deterministic ordering.

The component scores were previously calibrated, but their weighted average has not been separately calibrated. Interpret it as a ranking score. This is not the earlier embedding-to-XGBoost architecture: it fuses final predictions from two separately fitted models.

## Results

| Model | Test AP | Hits in first 20 | First 50 | First 100 | First 500 | First 1,000 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rich graph-context XGBoost | .3148 | 20 | 43 | 68 | 115 | 154 |
| Temporal typed GNN | .2879 | 19 | 45 | 55 | 114 | 130 |
| Validation-selected 75% tree / 25% GNN | **.3381** | 20 | 41 | 68 | **128** | **158** |

At 500 reviews, the blend retrieves 43.39% of positives, compared with 38.98% for the tree. That is 13 additional positive address-window decisions at the same budget. AP improves by .0233 over the tree, approximately 7.4% relative. At 50 reviews the GNN alone is stronger: 45 positives versus 41 for the blend. Thus the blend improves aggregate AP and wider-budget recovery in this test, without dominating every workload.

All numbers above pool test windows 7–9. Per-window results, including the zero-positive final window, are preserved in the report. The test was already consumed in earlier research. Selecting weights on validation prevents direct test-weight optimization, but does not make this a fresh confirmatory test. This is evidence worth following up, not grounds for an immediate production replacement.

## Practical next steps

1. Compare the shipped baseline, rich LightGBM/XGBoost, temporal GNN and this frozen blend on a single explicitly matched decision target and chronological protocol. The shipped baseline needs its full-history feature dependencies audited before calling that comparison causal.
2. Register fresh world configurations before generation. Carry the selected blend weight unchanged into them, alongside both components. Include changes in campaign composition and observer coverage.
3. Measure review budgets per window as well as pooled rankings. Add campaign/controller yield for evaluation, and deployment-available evidence diversity for actual queue selection.
4. Diagnose missed campaign types on training/validation examples. Improve temporal sequence/flow features or model capacity only in response to a measured gap, with feature provenance checked.
5. Promote a hybrid only if it reliably improves the declared workload enough to justify two model runtimes, explanation handling and packaging. A GPU trial can widen the model search; it cannot guarantee that unobserved evidence becomes observable.

## Artifacts and reproduction

- Script: `research/bitcoin/ranking_recovery_analysis.py`
- Registered candidates and criterion: `research/bitcoin/results/ranking-recovery-analysis/design.json`
- Validation candidates, test metrics, per-window results and input/source SHA-256: `research/bitcoin/results/ranking-recovery-analysis/report.json`

```bash
UV_CACHE_DIR=/tmp/uv-cache POLARS_MAX_THREADS=4 uv run --offline --no-sync python research/bitcoin/ranking_recovery_analysis.py
```

The World screen now separates the public Elliptic benchmark, earlier rich tree comparisons, R47 neural controls and this supplementary blend. Public and synthetic results retain their own evaluation context. Abstracts and descriptions lead with the working capabilities and public-data evidence; the research-oriented description includes this exploratory blend with its status intact.
