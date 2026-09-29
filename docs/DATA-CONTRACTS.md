# DATA CONTRACTS

**Frozen.** This file is the boundary between people working in parallel. Claude Code is
denied write access to it in `.claude/settings.json`. If code cannot meet a contract, that
is a finding to report, not a contract to edit.

Conventions used throughout:

- All money is **satoshis, as `int64`**. Never BTC as a float anywhere inside the pipeline.
  A float BTC value loses precision at the eighth decimal, and this project prints numbers
  into an evidence packet.
- All times are **UTC microseconds since epoch, as `int64`**, column suffix `_us`. Human
  readable timestamps exist only at the display layer.
- Array valued columns in CSV are **pipe separated** with no spaces: `addr1|addr2|addr3`.
  In Parquet they are real `list` types.
- Every stage output directory also contains `_meta.json`. Its schema is at the end.
- `null` is meaningful and always distinguished from zero or empty. A missing ASN is null,
  not `0` and not `"unknown"`.

---

## 1 · Capture rows, the input contract

This is the problem statement's own schema and it is the only part of this document we did
not choose. One row is **one announcement of one transaction by one peer**. The chain
columns repeat across every row announcing the same `txid`.

MAYAJAAL writes this. KAVACH reads this. A real file from NTRO must also load here.

| Column | Type | Required | Notes |
|---|---|---|---|
| `timestamp` | string or int | yes | ISO 8601 with timezone, or epoch seconds, or epoch ms. KAVACH detects and normalises. |
| `src_ip` | string | yes | IPv4 or IPv6. The announcing peer. |
| `dst_ip` | string | yes | The observing node that received the announcement. |
| `src_port` | int | yes | Ephemeral port on the announcing side. Load bearing for CGNAT attribution. |
| `dst_port` | int | yes | Usually 8333. |
| `txid` | string | yes | 64 lowercase hex characters. |
| `input_addresses` | list[string] | yes | Pipe separated in CSV. May be empty for a coinbase transaction. |
| `output_addresses` | list[string] | yes | Pipe separated. At least one. |
| `input_amounts` | list[int] | yes | Satoshis. Same length as `input_addresses`. |
| `output_amounts` | list[int] | yes | Satoshis. Same length as `output_addresses`. |
| `geo_country` | string | no | ISO 3166-1 alpha-2 of `src_ip`. Null allowed. |
| `asn` | int | no | Autonomous system number of `src_ip`. Null allowed. |

### Our optional extensions

Marked optional because a real NTRO file will not have them. Every consumer must work when
they are absent. Never make one of these required.

| Column | Type | Notes |
|---|---|---|
| `fee_sats` | int | Inputs total minus outputs total. Derivable, but cheap to carry. |
| `vsize` | int | Virtual size in vbytes. Enables fee rate. |
| `script_types` | list[string] | One per output: `p2pkh`, `p2sh`, `p2wpkh`, `p2wsh`, `p2tr`. |
| `block_height` | int | Null while unconfirmed. |
| `msg_type` | string | `inv` or `tx`. Real captures distinguish these. |
| `observer_id` | string | Which of our listening nodes saw it. Enables observer-fraction analysis. |

### Invariants KAVACH must assert on load

1. `len(input_addresses) == len(input_amounts)` on every row.
2. `len(output_addresses) == len(output_amounts)` on every row.
3. `txid` matches `^[0-9a-f]{64}$`.
4. Every `txid` appears at least once.
5. Rows sharing a `txid` have identical chain columns. If they do not, the file is
   corrupt and KAVACH quarantines those rows rather than guessing.
6. `sum(input_amounts) >= sum(output_amounts)` for non-coinbase rows.

Rows failing any check go to `sealed/rejected.parquet` with a `reject_reason`. Nothing is
silently dropped, because a count that does not reconcile is worse than a rejection you can
point at.

---

## 2 · Ground truth, quarantined

Written by MAYAJAAL into `ground_truth/`. Readable only by `src/chakravyuh/eval/`. A test
greps the source tree to prove no other package references this path.

`ground_truth/origins.parquet`

| Column | Type | Notes |
|---|---|---|
| `txid` | string | |
| `true_origin_ip` | string | L0. The peer that actually created and first sent it. Officer-only: never the headline scoring key, kept for the redacted host line inside `packet.json`. |
| `true_origin_asn` | int32 | L1 (the hero). The network operator's ASN, read from the region table, not from the masked `node.asn`. |
| `true_origin_as_org` | string | L1. The operator's name (e.g. the region's `org`, or the Tor/VPN operator label). |
| `true_origin_net_class` | string | L1. One of `residential`, `hosting`, `mobile`, `tor_exit`, `vpn_suspect`, `unknown`. |
| `true_origin_country` | string | L2. The 2-letter region country, read from the region table. |
| `true_origin_entity_id` | string | |
| `broadcast_us` | int64 | When the originator first sent it, which no observer sees. |
| `used_tor` | bool | |
| `used_vpn` | bool | |
| `observed_by_n` | int32 | How many of our observers saw any announcement of it. |

`ground_truth/entities.parquet`

| Column | Type | Notes |
|---|---|---|
| `entity_id` | string | |
| `entity_type` | string | `individual`, `merchant`, `exchange`, `mining_pool`, `mixer`, `darknet_market`, `ransomware`, `scam`, `mule`, `service` |
| `is_illicit` | bool | |
| `typologies` | list[string] | `peel_chain`, `structuring`, `fan_out`, `pass_through`, `coinjoin_like`, or empty |
| `addresses` | list[string] | Every address this entity truly owns. The clustering answer key. |
| `ips` | list[string] | |
| `behind_cgnat` | bool | |

`ground_truth/campaigns.parquet`, one row per laundering campaign, so a typology can be
scored as a whole rather than transaction by transaction.

| Column | Type | Notes |
|---|---|---|
| `campaign_id` | string | |
| `typology` | string | |
| `entity_ids` | list[string] | |
| `txids` | list[string] | In intended order. |
| `start_us`, `end_us` | int64 | |
| `total_sats` | int64 | |

**Rule with no exceptions.** No column name in this section may appear in any observable
artifact. `truth-checker` asserts this. If `is_illicit` ever shows up in
`normalised/`, everything measured after that point is void.

---

## 3 · `sealed/`, written by KAVACH

`sealed/rows.parquet` is the capture, coerced to types, nothing else changed. Same grain,
same row count as the input minus rejections. Columns are those in section 1 with these
normalisations applied:

- `timestamp` becomes `ts_us` `int64`. The original string is kept in `ts_raw` `string`.
- `input_amounts` and `output_amounts` become `list[int64]` in satoshis. If the source was
  decimal BTC, `_meta.json` records `amount_unit_detected: "btc"`.
- `src_ip` and `dst_ip` stay strings. Also emitted: `src_ip_version` `int8`.
- A stable `row_id` `int64` is added, being the zero-based index in the original file order.
  Order is never relied on for logic, but a row must be citable in an evidence packet.

`sealed/rejected.parquet`: the rejected rows plus `reject_reason` `string`, and `row_id`.

`sealed/INPUT.sha256`: one line per input file, `<sha256>  <filename>`.

`sealed/manifest.json`:

```json
{
  "input_files": [{"path": "...", "bytes": 0, "sha256": "..."}],
  "rows_read": 0, "rows_sealed": 0, "rows_rejected": 0,
  "reject_reasons": {"reason": 0},
  "amount_unit_detected": "sats",
  "timestamp_format_detected": "iso8601",
  "columns_present": [], "columns_missing_optional": [],
  "sealed_at_us": 0, "code_version": "git sha", "tool_version": "0.1.0"
}
```

`rows_read` must equal `rows_sealed + rows_rejected`. A test asserts it. This single equality
is what lets you answer "did you lose any data" with a number instead of a shrug.

---

## 4 · `normalised/`, written by SETU

This is where the grain splits. Everything downstream reads from here, not from `sealed/`.

`normalised/announcements.parquet`, one row per announcement. The network layer.

| Column | Type | Notes |
|---|---|---|
| `row_id` | int64 | Traces back to `sealed/rows.parquet`. |
| `txid` | string | |
| `peer_ip` | string | Was `src_ip`. Renamed because "src" stops meaning anything once you know it is usually a relay. |
| `peer_port` | int32 | |
| `observer_ip` | string | Was `dst_ip`. |
| `observer_port` | int32 | |
| `seen_us` | int64 | |
| `rank_in_tx` | int32 | 1 for the earliest announcement of this txid in this capture. |
| `delta_first_us` | int64 | `seen_us` minus the earliest `seen_us` for this txid. Zero for rank 1. |
| `geo_country` | string | Enriched if null on input. |
| `asn` | int32 | Enriched if null on input. |
| `as_org` | string | From the ASN database. Null if unavailable. |
| `net_class` | string | `residential`, `hosting`, `mobile`, `tor_exit`, `vpn_suspect`, `unknown`. From offline lists in `vendor/`. |
| `peer_seen_count` | int32 | How many distinct txids this peer announced in this capture. |
| `msg_type` | string | Null if absent on input. |

`normalised/transactions.parquet`, one row per txid. The chain layer.

| Column | Type | Notes |
|---|---|---|
| `txid` | string | Primary key. |
| `first_seen_us` | int64 | Minimum `seen_us` across announcements. |
| `last_seen_us` | int64 | |
| `n_announcements` | int32 | The number that matters. Mean is around nine. |
| `n_distinct_peers` | int32 | |
| `announce_spread_us` | int64 | `last_seen_us` minus `first_seen_us`. |
| `input_addresses` | list[string] | |
| `output_addresses` | list[string] | |
| `input_amounts` | list[int64] | |
| `output_amounts` | list[int64] | |
| `n_in`, `n_out` | int32 | |
| `total_in_sats`, `total_out_sats` | int64 | |
| `fee_sats` | int64 | Zero for coinbase. |
| `fee_rate_sat_vb` | float64 | Null if `vsize` absent. |
| `is_coinbase` | bool | True when `n_in == 0`. |
| `has_equal_outputs` | bool | Two or more outputs of identical value. CoinJoin-like signal. |
| `change_index` | int32 | Index of the suspected change output, or -1 if undetermined. |
| `block_height` | int32 | Null if absent. |

`normalised/addresses.parquet`, one row per distinct address.

| Column | Type | Notes |
|---|---|---|
| `address` | string | Primary key. |
| `script_type` | string | Inferred from the prefix if `script_types` was absent. |
| `first_seen_us`, `last_seen_us` | int64 | |
| `n_tx_in`, `n_tx_out` | int32 | Appearances as an input and as an output. |
| `total_received_sats`, `total_sent_sats` | int64 | |
| `balance_sats` | int64 | Received minus sent, within this capture only. |
| `dwell_time_us` | int64 | Median gap between receiving and spending. |

`normalised/peers.parquet`, one row per distinct `peer_ip`.

| Column | Type | Notes |
|---|---|---|
| `peer_ip` | string | Primary key. |
| `n_announcements` | int32 | |
| `n_txids` | int32 | |
| `mean_rank` | float64 | Average `rank_in_tx`. A peer that is consistently first is interesting. |
| `frac_rank_one` | float64 | Fraction of its announcements that were the earliest seen. |
| `distinct_ports` | int32 | Many ports from one IP suggests CGNAT or a busy host. |
| `geo_country`, `asn`, `as_org`, `net_class` | | As above. |
| `first_us`, `last_us` | int64 | |

`normalised/asn_rollup.parquet`, one row per observed `asn` (a null `asn` is its own row: the
honest unresolved-operator bucket). This is the substrate L1 (operator-level) attribution scores
against — candidate origin peers collapse onto a few ASNs, so an aggregate keyed on ASN is where an
origin guess becomes defensible.

| Column | Type | Notes |
|---|---|---|
| `asn` | int32 | Primary key. Null is the unresolved-operator row, not dropped. |
| `as_org` | string | The operator label. Null when no `vendor/` list resolved it. |
| `geo_country` | string | The operator's region. Null when unresolved. |
| `n_peers` | int32 | Distinct peers on this ASN. |
| `n_announcements` | int32 | Announcements from those peers. |
| `n_txids` | int32 | Distinct transactions those announcements covered. |
| `frac_rank_one` | float64 | Announcement-weighted: does traffic on this ASN tend to be the earliest an observer saw? |
| `n_residential`, `n_hosting`, `n_mobile`, `n_tor_exit`, `n_vpn_suspect`, `n_unknown` | int32 | Distinct-peer counts per `net_class`. |

`normalised/arrival.parquet`, the per-transaction arrival matrix the timing estimator reads:
`{txid -> [(observer_id, peer_ip, seen_us)]}` as a tidy long table, one row per announcement.
Sorted on `(txid, seen_us, observer_id)` so the earliest arrival per transaction is a group head.

| Column | Type | Notes |
|---|---|---|
| `txid` | string | |
| `observer_id` | string | Which observer saw the announcement. Null only in a hand-fed sealed directory that lacks it. |
| `peer_ip` | string | The announcing peer. |
| `seen_us` | int64 | When this observer saw it. |

---

## 5 · `graph/`, written by JAAL

| Column | Type | Notes |
|---|---|---|
| `node_id` | string | `addr:<address>`, `tx:<txid>`, `peer:<ip>`, `cluster:<n>`, `asn:<n>` |
| `kind` | string | `address`, `transaction`, `peer`, `cluster`, `asn` |
| `label` | string | Display label, already truncated for safety. |
| `first_us`, `last_us` | int64 | |
| `peel_chain_id` | string | The traced peel chain this transaction is a hop of, or null. Null on every other node kind. |
| `coinjoin` | bool | True when this transaction is a mixer. False on every other node kind. |

The last two columns are the JAAL v2 delta, appended so every reader that selects columns by
name keeps working. Both describe a *transaction* and neither describes any other node kind, so
they are null and false everywhere else rather than repeated per kind: a `false` that could have
been a `null` would make "not a mixer" and "never asked" the same cell.

`coinjoin` is `has_equal_outputs` **and** `n_out >= 3` **and** `n_in >= 2`. Three equal outputs is
a mixing round rather than a payments-plus-change coincidence, and the plural inputs are what make
the inputs strangers — a one-input transaction with equal outputs is one party splitting their own
coin, and their addresses do share an owner. A mixer is **set aside with the reason
`coinjoin_mixer`**: `common_input_edges` and `change_edges` are not applied across it, because
neither heuristic's premise survives a transaction several unrelated parties signed together
(Möser & Narayanan 2019). The counts are recorded, not asserted: `_meta.json` carries
`params.mixer` with the number of transactions set aside and how many candidate edges that
suppressed, computed by running the same heuristics over the excluded rows with the same code.

`graph/edges.parquet`

| Column | Type | Notes |
|---|---|---|
| `src`, `dst` | string | `node_id` values. |
| `kind` | string | `SPENDS`, `RECEIVES`, `ANNOUNCED_BY`, `SAME_OWNER`, `HOSTED_IN`, `MEMBER_OF` |
| `ts_us` | int64 | Null for structural edges such as `MEMBER_OF`. |
| `sats` | int64 | Null where not a value transfer. |
| `confidence` | float64 | 1.0 for facts read off the chain. Below 1.0 for anything inferred. |
| `evidence` | string | Which heuristic produced it: `multi_input`, `change_addr`, `observed`, `geoip`. |

**`SAME_OWNER` never merges nodes.** It is an edge with a confidence and a named heuristic,
and the console lets an analyst move the threshold and watch clusters change shape. The
multi-input heuristic measures 0.36 precision and 0.44 recall on full clusters in law
enforcement settings, so a hard merge would be wrong roughly two times in three.

`graph/clusters.parquet`

| Column | Type | Notes |
|---|---|---|
| `cluster_id` | string | |
| `addresses` | list[string] | |
| `n_addresses` | int32 | |
| `min_edge_confidence` | float64 | The weakest link holding this cluster together. |
| `heuristics_used` | list[string] | |
| `threshold` | float64 | The confidence threshold this clustering was cut at. |

`graph/peel_chains.parquet`, the JAAL v2 delta: one row per traced peel chain, the subgraph the
tracer found rather than a tally of peel-shaped transactions.

| Column | Type | Notes |
|---|---|---|
| `peel_chain_id` | string | `peel:<n>`, numbered in a fixed order so two runs agree. |
| `transactions` | list[string] | The chain's txids in hop order, first to last. |
| `depth` | int32 | Number of hops. Two or more; a lone peel is not a chain. |
| `initial_sats` | int64 | The value that entered the first hop. |
| `peeled_sats` | int64 | Total paid away as thin slices across the chain. |
| `leak_frac` | float64 | `peeled_sats / initial_sats`; null when nothing entered. |
| `root_address` | string | The largest input address of the first hop. |
| `first_us`, `last_us` | int64 | Span of the chain's first-seen times. |
| `stop_reason` | string | Why the walk ended: `no_continuation`, `ambiguous_spend`, `chain_broken`, `cycle`. |

A hop is a transaction with two outputs whose smaller output is at most 0.35 of the value moved,
and a chain continues only through the change output (the larger one) that the next hop actually
spends. The tracer is deliberately sharper than `signals/typology_hits.parquet`'s `peel_chain`
hit, which counts peel-shaped transactions per subject: a count does not say which transaction
followed which, and two peels by one owner on unrelated coins are two hits and no chain.

The column is `transactions` and not `txids` on purpose. `txids` is a name `eval/validate.py`
treats as a quarantine tripwire, permitted in exactly one observable file; picking a different
name for a traced prediction is a smaller change than widening that gate.

`leak_frac` may exceed 1 when a later hop also spends coin from outside the chain. That is
reported rather than clamped: a chain that absorbed value is a fact about the chain.

No truth is read here. A chain is a shape in the transaction graph and the tracer can be wrong
about it, which is why a chain is a row with a depth and a stopping reason rather than a merge.

---

## 6 · `signals/`, written by SHASTRA

`signals/origin_estimates.parquet`, the centre of the project. One row per candidate peer
per txid, so a txid with nine announcing peers produces nine rows. This is the L0 host grain
(officer-only) and the L3 shortlist substrate; the L1 operator headline lives in its own file
below.

| Column | Type | Notes |
|---|---|---|
| `txid` | string | |
| `peer_ip` | string | |
| `p_origin` | float64 | Estimated probability this peer originated it. Sums to at most 1.0 per txid. |
| `rank` | int32 | 1 is the most likely originator. |
| `margin` | float64 | `p_origin` of rank 1 minus rank 2. Small margin means do not act. |
| `features` | struct | The named inputs to the estimate, so it can be explained and replayed. |
| `estimator` | string | `first_spy`, `timing_mle`, `ensemble` (see below) |
| `abstain` | bool | True when the estimator refuses to rank. Then no row for this txid has rank 1. |
| `abstain_reason` | string | `tor_present`, `single_observer`, `margin_below_floor`, `too_few_announcements` |

The `features` struct holds at minimum, in this order: `delta_first_us`, `rank_in_tx`,
`n_announcements`, `n_observers_seen`, `peer_frac_rank_one`, `peer_n_txids`, `net_class`,
`announce_spread_us`. It carries more after those eight, including `mle_logscore`, the
multi-observer source log-likelihood `timing_mle` ranks on and `ensemble` blends — persisted so a
reader can see the timing evidence behind a call and a replay can reproduce it (comparable within a
transaction, not across).

The estimator stack, each independently runnable so `make compare-estimators` prints them side by
side rather than us asserting the ensemble is better:

- `first_spy` — the first-seen baseline, kept.
- `timing_mle` — a multi-observer maximum-likelihood source estimate over the arrival matrix and
  the known relay-delay model. Degrades to first-seen ordering when no `arrival.parquet` exists.
- `ensemble` — a calibrated (Platt) blend across regimes; falls back to the strongest label-free
  rule when the answer key is absent, and says so in `_meta.json`.

`asn_rollup` is the fourth estimator name, but it produces the L1 headline below rather than a
per-candidate ranking, so it appears in `origin_l1.parquet`, never in this file.

Three rules that make this honest. Abstention is a first class outcome and never a low score in
disguise. `p_origin` values within one txid must not be renormalised to sum to exactly one, because
"none of these peers is the originator, we simply did not observe it" is a real state of the world
and the sum is how we express it. And every estimator named in the column must be independently
runnable.

`signals/origin_l1.parquet`, the L1 operator headline — the hero of the reframe. One row per
transaction: the network operator (ASN) the ensemble's candidate mass rolls up to, which is
recoverable on far more transactions than the exact host, because a sibling peer in the same ASN
carries the operator even when the precise host was never observed.

| Column | Type | Notes |
|---|---|---|
| `txid` | string | |
| `origin_asn` | int32 | The most likely originating operator's ASN. |
| `as_org` | string | Its organisation name. |
| `net_class` | string | `residential`, `hosting`, `mobile`, `tor_exit`, `vpn_suspect`, `unknown`. |
| `p_asn` | float64 | Probability mass on that operator. Capped, never renormalised, like `p_origin`. |
| `origin_country` | string | The L2 region attribution. May be null when no vendor list resolved it. |
| `p_country` | float64 | Probability mass on that country. |
| `margin` | float64 | `p_asn` of the top operator minus the runner-up. |
| `shortlist_size` | int32 | Candidate peers inside the confidence shell the L3 view draws. |
| `abstain` | bool | True when no single operator carries the transaction. |
| `abstain_reason` | string | The four per-candidate reasons plus `cross_asn_ambiguous` (mass split across operators). |
| `estimator` | string | Always `ensemble`: this is the operator view of the calibrated blend. |

Empty (zero rows, exact schema) when the run has no ASN substrate — a run with an empty `vendor/`
writes the header and nothing else, which `_meta.json` records.



`signals/typology_hits.parquet`

| Column | Type | Notes |
|---|---|---|
| `hit_id` | string | |
| `typology` | string | `peel_chain`, `structuring`, `fan_out`, `pass_through`, `coinjoin_like`, `rapid_hop` |
| `subject_id` | string | An address, cluster, or txid `node_id`. |
| `txids` | list[string] | The transactions that make up the pattern. |
| `strength` | float64 | How well it matches, zero to one. Not a probability of guilt. |
| `params` | struct | The thresholds that fired, recorded so a hit can be re-derived. |

`signals/entity_types.parquet`, runs before any scoring, by design.

| Column | Type | Notes |
|---|---|---|
| `subject_id` | string | Address or cluster. |
| `predicted_type` | string | Same vocabulary as ground truth `entity_type`. |
| `confidence` | float64 | |
| `basis` | list[string] | `coinbase_origination`, `payout_cadence`, `long_dwell`, `high_fanout`, `port_diversity`, `known_service_pattern` |
| `exempt_from_scoring` | bool | True for `mining_pool` and `exchange` unless a typology hit overrides. |

---

## 7 · `scores/`, written by BUDDHI

`scores/wallet_scores.parquet`

| Column | Type | Notes |
|---|---|---|
| `subject_id` | string | Address or cluster. |
| `risk_score` | float64 | Raw model output. Not shown to a user on its own. |
| `label` | string | `LIKELY_ILLICIT`, `UNCLEAR`, `LIKELY_LICIT`, `ABSTAIN` |
| `conf_low`, `conf_high` | float64 | Conformal interval. This is what the console displays. |
| `coverage_target` | float64 | The alpha the interval was built for, typically 0.9. |
| `model` | string | `gbm_v2` (the LightGBM risk model), `gbm_gnn_v2` (the same model with the label-free dual-graph embedding added as columns). Recorded per row so a mixed run stays auditable; a row may name `gbm_gnn_v2` only where `eval_report.json`'s `embedding_leg.available` is true. |
| `top_features` | list[struct] | Name and SHAP value, top five, ordered by absolute value. |
| `abstain` | bool | |

`scores/calibration.parquet`, one row per class per calibration split.

| Column | Type | Notes |
|---|---|---|
| `class` | string | |
| `method` | string | `plain_conformal`, `class_conditional` |
| `target_coverage` | float64 | |
| `empirical_coverage` | float64 | The number that goes on a slide. |
| `n_calibration`, `n_test` | int32 | |
| `imbalance_ratio` | string | For example `1:345`. |

`scores/eval_report.json`

Must contain, and a test asserts each key is present and non-null:

```json
{
  "split": {"mode": "time_ordered", "train_end_us": 0, "val_end_us": 0, "test_start_us": 0},
  "wallet_model": {"pr_auc": 0.0, "roc_auc": 0.0, "precision_at_20": 0.0, "recall_at_20": 0.0,
                   "tx_pr_auc": 0.0, "campaign_recall": 0.0},
  "origin_estimator": {
    "top1_accuracy": 0.0, "top3_accuracy": 0.0, "abstain_rate": 0.0,
    "by_observer_fraction": [{"fraction": 0.05, "top1": 0.0, "abstain": 0.0}],
    "by_traffic_type": [{"type": "clear", "top1": 0.0}, {"type": "vpn", "top1": 0.0},
                        {"type": "tor", "top1": 0.0}]
  },
  "clustering": {"precision": 0.0, "recall": 0.0, "threshold": 0.0},
  "baseline_beaten": false,
  "seed": 0, "run_id": "", "code_version": "",
  "protocol": "inductive_time_ordered",
  "elliptic_external": {"available": false, "reason": "not_run_for_this_run"},
  "embedding_leg": {"available": false, "reason": "embeddings_not_requested"}
}
```

### 7.1 · The three grains `wallet_model` reports

Risk is measured at three grains, and all three are reported because they can move apart: a
model can hold its actor-level ranking while losing the campaign it was supposed to catch.

| Key | Grain | Meaning |
|---|---|---|
| `pr_auc`, `roc_auc`, `precision_at_20`, `recall_at_20` | actor | One subject (cluster or singleton address) is one unit. |
| `tx_pr_auc` | transaction | One transaction is one unit, so a subject holding many transactions weighs accordingly. |
| `campaign_recall` | campaign | Share of labelled campaigns with at least one member whose subject is flagged illicit. A campaign is an `entity_id`; "flagged" is the subject's class-1 conformal verdict (equivalently the `LIKELY_ILICIT` label — the two were measured to agree, because a `UNCLEAR` subject has both classes in its set and so is not a flag). Recall is over the holdout members of illicit entities only, so it answers "of the campaigns still active after the boundary, how many do we touch at all" — reach, not accuracy, and it is deliberately easy: a campaign with many addresses is likely to be touched by at least one. |

### 7.2 · `protocol` — the only one reported

`protocol` must be the string `inductive_time_ordered`: train on the past
(`seen_us < boundary_us`), test on the future (`>=`). `chakravyuh.eval.split.PROTOCOL` holds the
name beside the boundary that implements it. `scripts/check_scores.py` compares the value, not
merely the presence of the key, because a randomly split run could carry the key with the wrong
word in it and pass every other structural check.

### 7.3 · `elliptic_external` — the two shapes

`elliptic_external` validates the shared recipe on the Elliptic dataset (§ external validation),
and it has exactly two shapes, which are different facts and are kept distinct:

```json
{"available": true, "dataset": "elliptic", "source_sha256": "", "source_name": "",
 "n_train": 0, "n_test": 0, "n_illicit": 0, "illicit_rate": 0.0,
 "pr_auc": 0.0, "roc_auc": 0.0, "f1": 0.0, "precision": 0.0, "recall": 0.0,
 "protocol": "inductive_time_ordered", "train_fraction": 0.7, "seed": 0, "caveat": ""}

{"available": false, "reason": "dataset_not_vendored" | "not_run_for_this_run"}
```

A test asserts only `available` is present, deliberately: requiring a figure here would force a
run to have run the external leg before it could report at all. When `available` is true the
figures come from `measurements/<run>/elliptic_external.json`, written by
`chakravyuh.eval.external` — never from the scoring pass, which quotes it. The `caveat` is part of
the contract, not decoration: it states that the shared thing is the procedure, not the feature
set.

### 7.4 · `embedding_leg` — the graph-embedding gate

The risk model's feature set has an optional second half: `buddhi.embed` computes a label-free
structural embedding of the JAAL dual graph (two-hop propagation, no labels anywhere in it,
reduced to eight columns), and `--gnn` trains a second booster over the baseline features plus
those eight. The gate decides whether those rows may ship, and it can only be decided on the
answer key, so it is decided here rather than in the stage:

```json
{"available": true, "reason": null, "embedding": "", "rows_by_model": {"gbm_v2": 0, "gbm_gnn_v2": 0},
 "n_rows_scored_by_gnn": 0, "n_rows_scored_by_baseline": 0,
 "shipped_model": {"pr_auc": 0.0, "roc_auc": 0.0, "precision_at_20": 0.0, "recall_at_20": 0.0,
                   "n_scored": 0},
 "baseline_model": {"pr_auc": 0.0, "roc_auc": 0.0, "precision_at_20": 0.0, "recall_at_20": 0.0,
                    "n_scored": 0},
 "delta_pr_auc": 0.0, "delta_precision_at_20": 0.0, "caveat": ""}

{"available": false, "reason": "embeddings_not_requested" | "no_row_scored_by_the_gnn_booster"
 | "no_counterfactual_measured" | "baseline_not_beaten" | "gnn_does_not_beat_baseline"
 | "not_scored_no_answer_key"}
```

`available` is true only when the run's own `baseline_beaten` is true **and** the shipped
ranking's holdout PR-AUC is at least the baseline booster's, measured on the identical subject
population with the identical time-ordered split — the two differ in the embedding columns and
nothing else. `baseline_model` is that counterfactual, filed only inside this block and never as
a `model_report.json`: one run, one shipped report. `reason` is a closed vocabulary rather than
prose, so a reader can tell "nobody asked for it" from "it was asked for and did not earn its
columns". A mixed run's headline figures are the mix's, not the GNN booster's alone, which is
what `rows_by_model` is for.

`scripts/check_scores.py` refuses any run where a row names `gbm_gnn_v2` while `available` is
false, and that refusal is the intended outcome rather than a bug to work around: such a run's
scores are the ones its own measurement rejected, so the run is regenerated without `--gnn` and
the embedding leg is recorded as the thing that did not beat the baseline. The plain invocation
(`gbm_v2` everywhere, `available: false, reason: "embeddings_not_requested"`) is unaffected and
is what every gate builds.

`baseline_beaten` is a boolean the timeline depends on. If the embedding leg does not beat the
plain GBM on a future time window, `baseline_beaten` (or `embedding_leg.available`) stays false
and we ship the plain model and say so on the slide.

`by_observer_fraction` is the block that makes the whole evaluation credible. A single
headline accuracy for origin estimation would be meaningless, because the number depends
almost entirely on how much of the network the observer sees. Published measurements of
originating IP inference range from 11% to 60% for exactly this reason. Reporting the curve
instead of a point is both more honest and more impressive.

`baseline_beaten` is a boolean the timeline depends on. If the GNN does not beat LightGBM on
a future time window, this stays false and we ship LightGBM and say so on the slide.

---

## 8 · `alerts/`, written by VAANI

`alerts/alerts.parquet`

| Column | Type | Notes |
|---|---|---|
| `alert_id` | string | Stable across runs with the same seed. |
| `subject_id` | string | |
| `rank` | int32 | 1 to 20 in the default queue. |
| `severity` | string | `high`, `medium`, `low` |
| `conf_low`, `conf_high` | float64 | Carried through from `scores/`. |
| `headline` | string | One sentence, under 100 characters, generated from the features rather than free text. |
| `origin_txid` | string | The transaction whose origin estimate anchors this alert. Null if none. |
| `origin_peer_ip` | string | |
| `origin_p` | float64 | |
| `attribution_ready` | bool | True only when a peer IP, a source port and a precise timestamp all exist. |

`alerts/evidence.parquet`, the reasons for. One row per reason per alert.

| Column | Type | Notes |
|---|---|---|
| `alert_id` | string | |
| `kind` | string | `typology`, `origin_estimate`, `cluster_edge`, `model_feature`, `network_context` |
| `statement` | string | Plain sentence a non-specialist can read. |
| `weight` | float64 | Contribution to the score. |
| `source_ref` | string | The artifact and row this came from, for replay. |

`alerts/counter.parquet`, the reasons against. Mandatory. A test asserts every alert has at
least one row here, and the pipeline fails if any alert has none.

| Column | Type | Notes |
|---|---|---|
| `alert_id` | string | |
| `kind` | string | `entity_type_conflict`, `shared_ip`, `weak_cluster_link`, `low_origin_margin`, `pool_payout_pattern`, `insufficient_observation` |
| `statement` | string | |
| `strength` | float64 | |
| `would_clear` | bool | True if this alone is sufficient to drop the lead. |

That last column is worth pausing on. A tool that lists doubts is nice. A tool that marks
which single doubt is sufficient to close the lead is one an investigator can actually use,
and it is the difference between an interface and a colleague.

---

## 9 · `packets/`, written by PRAMAAN

`packets/<case_id>/packet.json`

```json
{
  "case_id": "", "generated_at_us": 0, "tool_version": "", "code_version": "",
  "input": {"files": [{"path": "", "sha256": ""}], "rows_sealed": 0},
  "subject": {"subject_id": "", "addresses_redacted": ["bc1q4f…9f4d"], "cluster_id": ""},
  "attribution_ready": false,
  "attribution": {
    "asn": 0, "as_org": "", "net_class": "", "geo_country": "",
    "p_asn": 0.0, "margin": 0.0,
    "shortlist": [{"peer_ip_display": "103.x.x.x", "peer_port": 0, "p_origin": 0.0, "rank": 1}],
    "observed_at_utc": "",
    "peer_ip": "", "peer_port": 0
  },
  "findings": [{"statement": "", "kind": "", "source_ref": ""}],
  "counter_findings": [{"statement": "", "kind": "", "would_clear": false}],
  "confidence": {"low": 0.0, "high": 0.0, "coverage_target": 0.9, "method": "class_conditional"},
  "chain_of_custody": [{"stage": "", "at_us": 0, "inputs": [""], "outputs": [""], "sha256": ""}],
  "replay": {"seed": 0, "command": "", "expected_packet_sha256": ""},
  "legal": {"basis": "BNSS 2023 s.94", "hash_disclosure": "BSA 2023 s.63(4), Schedule Part A"}
}
```

The attribution block leads with **L1 (the network operator/ASN)**, the reframe's hero: `asn`,
`as_org`, `net_class`, `geo_country` and the capped `p_asn` come from `signals/origin_l1.parquet`
(the one ensemble row per transaction). `shortlist` is the ranked L3 candidate peers from
`signals/origin_estimates.parquet`, each redacted for display (`peer_ip_display`, its `peer_port`,
`p_origin`, `rank`). `observed_at_utc` is the anchor announcement's time. `peer_ip`/`peer_port` are
the **exact host, officer-only**: present in the JSON for an authorised officer, never rendered on a
screen or in the PDF. `attribution_ready` is a real top-level field (read from `alerts.parquet`), so
the frontend reads it rather than deriving it.

Also in that directory: `packet.pdf` from the same JSON, `notice.pdf` being the pre filled
production notice, `merkle.log` being the append only hash chain, and `packet.sig` being the
Ed25519 signature over `packet.json`.

Three requirements on this stage that are not negotiable.

**No complete identifiers in any rendered output.** IPs appear in `packet.json` because that
is a machine artifact served to an authorised officer, but every PDF, every screen and every
log line renders them redacted, `103.x.x.x`, and Bitcoin addresses truncated, `bc1q4f…9f4d`. A
test greps the generated PDFs for a full address pattern and fails on a hit.

**`replay.expected_packet_sha256` must actually verify.** `make verify-replay` re-runs from
the sealed inputs with the recorded seed and compares. If it does not match, the packet is
not evidence, it is a screenshot.

**The Merkle log is append only and its head is printed.** Every packet generation appends a
leaf and prints the new root. The root is what a second analyst checks.

---

## 10 · `_meta.json`, written by every stage

```json
{
  "stage": "setu", "run_id": "", "started_at_us": 0, "finished_at_us": 0,
  "code_version": "", "seed": 0,
  "params": {},
  "inputs": [{"path": "", "sha256": "", "rows": 0}],
  "outputs": [{"path": "", "sha256": "", "rows": 0}],
  "counts": {"in": 0, "out": 0, "dropped": 0, "drop_reasons": {}},
  "warnings": [],
  "optional_deps": {"geolite2": true, "kuzu": false, "gpu": false}
}
```

`counts.in` must equal `counts.out + counts.dropped` for every stage. This one equality,
enforced by a test at every stage, is how the whole pipeline stays accountable for every row
it was given. When someone asks at the finale where the other 900,000 rows went, the answer
is a table, not an explanation.

---

## 11 · Fixtures

`data/fixtures/` holds a committed miniature of every artifact above, generated once by
`make fixtures` with seed 42 and about 200 capture rows across about 25 transactions. Small
enough to read by eye, complete enough that every stage and the entire frontend can be built
and tested against it with no pipeline run.

Fixtures must include, deliberately, at least one of each awkward case, because a fixture set
of only well behaved rows is how a bug reaches a demo:

a coinbase transaction, a transaction announced by exactly one peer, a transaction announced
by more than fifteen, two peers announcing within the same microsecond, a Tor exit peer, two
different peers sharing one public IP on different ports, a transaction with equal value
outputs, a three hop peel chain, a mining pool with a regular payout cadence, a null ASN, a
malformed row that must be rejected, and an IPv6 peer.