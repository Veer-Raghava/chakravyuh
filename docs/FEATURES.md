# FEATURES — the vocabulary BUDDHI's model is allowed to see

One row per wallet subject: a predicted cluster from `graph/clusters.parquet`, or an address no
`SAME_OWNER` edge linked to anything. Every feature is computed over the subject's own window —
pre-boundary transactions for a train subject, post-boundary for a holdout subject — so no feature
can see a subject's future. `p_origin` from the origin estimator is an input here, not a separate
output.

The glosses below are the ones `wallet_scores.parquet`'s `top_features` names, and the same
vocabulary `FEATURE_GLOSSES` in `src/chakravyuh/buddhi/features.py` carries. A SHAP row may name a
feature; this file is what the name means.

| Feature | Plain English |
|---|---|
| `n_addresses` | how many of its addresses were active in its window |
| `n_tx_sent` | transactions it sent in its window |
| `total_sent_sats` | satoshis it sent in its window |
| `mean_sent_sats` | average size of its sends |
| `n_tx_received` | transactions that paid it in its window |
| `total_received_sats` | satoshis it received in its window |
| `mean_received_sats` | average size of its receipts |
| `balance_sats` | received minus sent inside its window |
| `n_counterparties` | distinct wallets it transacted with |
| `max_fan_out` | most addresses it paid in a single transaction |
| `n_coinbase_received` | block rewards it collected; mining pools look like this |
| `frac_equal_outputs` | share of its transactions with equal-value outputs, a coinjoin mark |
| `mean_fee_rate` | average fee per vbyte its sends paid |
| `median_dwell_us` | typical gap between one of its receipts and its next send |
| `min_edge_confidence` | confidence of the weakest link holding its cluster together |
| `n_heuristics` | how many clustering heuristics contributed to its cluster |
| `n_script_types` | distinct address formats its active addresses use |
| `mean_p_origin` | average origin confidence on the transactions it sent |
| `mean_origin_margin` | how far ahead the top origin candidate usually was |
| `frac_origin_abstained` | share of its sends the origin estimator refused to answer |
| `frac_top1_tor` | share of its sends whose top origin candidate is a Tor exit |
| `mean_n_announcements` | average propagation breadth of its sends |

The trivial baseline the model has to beat ranks subjects by `total_received_sats` alone and is
measured through `chakravyuh.eval.metrics`; its precision-at-20 is recorded in
`measurements/<run>/baseline_wallet.json`. A model precision-at-20 above 0.9 on this generator is
leakage, not skill, and the gate treats it as such.
