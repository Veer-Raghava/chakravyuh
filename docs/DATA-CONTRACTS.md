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
| `true_origin_ip` | string | The peer that actually created and first sent it. |
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

---

## 5 · `graph/`, written by JAAL

`graph/nodes.parquet`

| Column | Type | Notes |
|---|---|---|
| `node_id` | string | `addr:<address>`, `tx:<txid>`, `peer:<ip>`, `cluster:<n>`, `asn:<n>` |
| `kind` | string | `address`, `transaction`, `peer`, `cluster`, `asn` |
| `label` | string | Display label, already truncated for safety. |
| `first_us`, `last_us` | int64 | |

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

---

## 6 · `signals/`, written by SHASTRA

`signals/origin_estimates.parquet`, the centre of the project. One row per candidate peer
per txid, so a txid with nine announcing peers produces nine rows.

| Column | Type | Notes |
|---|---|---|
| `txid` | string | |
| `peer_ip` | string | |
| `p_origin` | float64 | Estimated probability this peer originated it. Sums to at most 1.0 per txid. |
| `rank` | int32 | 1 is the most likely originator. |
| `margin` | float64 | `p_origin` of rank 1 minus rank 2. Small margin means do not act. |
| `features` | struct | The named inputs to the estimate, so it can be explained and replayed. |
| `estimator` | string | `first_spy`, `weighted_first_seen`, `bayes_peer_prior`, `ensemble` |
| `abstain` | bool | True when the estimator refuses to rank. Then no row for this txid has rank 1. |
| `abstain_reason` | string | `tor_present`, `single_observer`, `margin_below_floor`, `too_few_announcements` |

The `features` struct holds at minimum: `delta_first_us`, `rank_in_tx`, `n_announcements`,
`n_observers_seen`, `peer_frac_rank_one`, `peer_n_txids`, `net_class`, `announce_spread_us`.

Three rules that make this honest. Abstention is a first class outcome and never a low
score in disguise. `p_origin` values within one txid must not be renormalised to sum to
exactly one, because "none of these peers is the originator, we simply did not observe it"
is a real state of the world and the sum is how we express it. And every estimator named in
the column must be independently runnable, so `make compare-estimators` can print them side
by side rather than us asserting the ensemble is better.

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
| `model` | string | `lightgbm_v1`, `gnn_v1`. Recorded per row so a mixed run stays auditable. |
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
  "wallet_model": {"pr_auc": 0.0, "roc_auc": 0.0, "precision_at_20": 0.0, "recall_at_20": 0.0},
  "origin_estimator": {
    "top1_accuracy": 0.0, "top3_accuracy": 0.0, "abstain_rate": 0.0,
    "by_observer_fraction": [{"fraction": 0.05, "top1": 0.0, "abstain": 0.0}],
    "by_traffic_type": [{"type": "clear", "top1": 0.0}, {"type": "vpn", "top1": 0.0},
                        {"type": "tor", "top1": 0.0}]
  },
  "clustering": {"precision": 0.0, "recall": 0.0, "threshold": 0.0},
  "baseline_beaten": false,
  "seed": 0, "run_id": "", "code_version": ""
}
```

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
  "subject": {"subject_id": "", "addresses_redacted": ["bc1q…9f4d"], "cluster_id": ""},
  "attribution": {
    "peer_ip": "", "peer_port": 0, "observed_at_utc": "",
    "p_origin": 0.0, "margin": 0.0, "runner_up_peer_ip": "",
    "asn": 0, "as_org": "", "geo_country": "", "net_class": ""
  },
  "findings": [{"statement": "", "kind": "", "source_ref": ""}],
  "counter_findings": [{"statement": "", "kind": "", "would_clear": false}],
  "confidence": {"low": 0.0, "high": 0.0, "coverage_target": 0.9, "method": "class_conditional"},
  "chain_of_custody": [{"stage": "", "at_us": 0, "inputs": [""], "outputs": [""], "sha256": ""}],
  "replay": {"seed": 0, "command": "", "expected_packet_sha256": ""},
  "legal": {"basis": "BNSS 2023 s.94", "hash_disclosure": "BSA 2023 s.63(4), Schedule Part A"}
}
```

Also in that directory: `packet.pdf` from the same JSON, `notice.pdf` being the pre filled
production notice, `merkle.log` being the append only hash chain, and `packet.sig` being the
Ed25519 signature over `packet.json`.

Three requirements on this stage that are not negotiable.

**No complete identifiers in any rendered output.** IPs appear in `packet.json` because that
is a machine artifact served to an authorised officer, but every PDF, every screen and every
log line renders them redacted, `103.x.x.x`, and Bitcoin addresses truncated, `bc1q…9f4d`. A
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