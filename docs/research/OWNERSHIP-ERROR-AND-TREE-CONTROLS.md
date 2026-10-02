# Ownership-error propagation and matched tree controls — R30 / R31

Date:2026-10-01. All detector weights, scalers and calibration mappings were frozen. The experiment changes the input ownership partition, not the training procedure. Hidden controller keys are used only for evaluation projection.

## Common controller-window comparison

Each subject score is assigned to every represented true controller, then maximized within a controller/window. A false merge can therefore raise a legitimate controller score. The first comparison had different represented universes:21,014 rows at CIOHthreshold.30 and21,278 at weak-change threshold.20. Both raw results remain saved. The corrected comparison uses their intersection, with matching labels verified:21,014 controller-windows,54positive. This conditions on representation by both partitions; it is not analyst-side owner identification.

| Model | CIOH P@20 | Weak-change P@20 | CIOH AP | Weak-change AP |
| --- | --- | --- | --- | --- |
| mlp | 0.25 | 0.25 | 0.0832 | 0.0780 |
| typed_static | 0.45 | 0.45 | 0.1854 | 0.1659 |
| typed_temporal_gru | 0.50 | 0.50 | 0.2028 | 0.1918 |
| xgboost_local | 0.45 | 0.45 | 0.2133 | 0.2249 |
| temporal_embeddings_xgboost | 0.50 | 0.50 | 0.2094 | 0.1925 |

Weak change links reduce AP for all three learned graph variants. LocalXGBoost AP increases slightly while P@20 is unchanged; input damage is not guaranteed to lower every metric for every detector. This single consumed-world sensitivity is not a universal theorem or a retraining comparison.

The temporal subject-window advantage does not establish superior controller yield: CIOH temporal AP.2028 versus local XGBoost.2133, P@20.50 versus.45. Controller-window rows still repeat a controller over time. Campaign yield and an actual deduplicated analyst queue remain necessary.

R30 cost66.82sCPU including repeated snapshot building. Raw and common-universe JSON/score files are in `research/bitcoin/results/partition-error-propagation/`. The original differing-denominator result was retained; no misleading raw comparison was promoted.

## Matched LightGBM controls

The same causal23-feature table and first-four fitting windows were used. Native LightGBM:300rounds,binaryobjective,31leaves,min40rows per leaf,learning_rate.05,L2=1,fourthreads,seed42,deterministic columnwise fitting. Typed summaries match the XGBoost control (meanTX/IPcontexts incoming/outgoing); hybrid input is23local+32frozen temporal dimensions from the180-epoch encoder. Platt fits windows4/5; window6selectsP@20thenAP; windows7–9test.

| Model | Validation P@20 | Validation AP | Test P@20 | Test AP |
| --- | --- | --- | --- | --- |
| lightgbm_local | 0.75 | 0.1245 | 0.45 | 0.0547 |
| lightgbm_typed_features | 0.25 | 0.1926 | 0.45 | 0.1969 |
| temporal_embeddings_lightgbm | 0.70 | 0.2325 | 0.90 | 0.2622 |

Validation selects local LightGBM; enriched/hybrid test AP gains are real measurements but not a validation-selected champion. This establishes that engineered relation summaries recover substantial signal and that choosing XGBoost as an embedding head is not automatically necessary. HybridLightGBM has not been transferred to new worlds here. All candidates need identical independent configuration and controller/campaign evaluation before a scientific production winner claim.

R31 cost23.91sCPU. Native boosters, calibrated score files and report are in `research/bitcoin/results/typed-lightgbm-controls/`. No canonical engine was replaced.
