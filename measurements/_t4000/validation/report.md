# MAYAJAAL validation

**PASS** — 36 of 36 checks passed.

## Run

- capture rows: 63868
- transactions: 4270
- transactions announced: 4270
- transactions no observer saw: 0
- blocks: 144
- announcing peers: 641
- observers: 16
- tor share: 0.035129
- vpn share: 0.078689
- unresolved asn share: 0.014248
- unresolved geo share: 0.009989
- entities: 800
- illicit entities: 24
- entities in a campaign: 8
- campaigns: 1

## Invariants

| | check | measured | required |
|-|-|-|-|
| ok | txid is 64 lowercase hex | 0 rows | 0 rows |
| ok | timestamp is ISO 8601 with six fractional digits and an explicit offset | 0 rows | 0 rows |
| ok | input addresses and input amounts are the same length | 0 rows | 0 rows |
| ok | output addresses and output amounts are the same length | 0 rows | 0 rows |
| ok | script types name every output | 0 rows | 0 rows |
| ok | every announced transaction has an output | 0 rows | 0 rows |
| ok | inputs cover outputs on a payment | 0 rows | 0 rows |
| ok | vsize is positive and fee is not negative | 0 rows | 0 rows |
| ok | ports are inside the 16-bit range | 0 rows | 0 rows |
| ok | msg_type is inv or tx | 0 rows | 0 rows |
| ok | the capture never goes backwards in time | 0 rows | 0 rows |
| ok | rows sharing a txid agree on the chain columns | 0 txids | 0 txids |
| ok | every announced txid exists on the chain | 0 txids | 0 txids |
| ok | every transaction has exactly one true originator | 0 txids | 0 txids |
| ok | observed_by_n equals the observers that recorded the transaction | 0 txids | 0 txids |

## Manifests

| | check | measured | required |
|-|-|-|-|
| ok | capture: counts.in == counts.out + counts.dropped | 63868 == 63868 + 0 | equal |
| ok | capture: names its outputs | 1 | >= 1 |
| ok | capture_json: counts.in == counts.out + counts.dropped | 63868 == 63868 + 0 | equal |
| ok | capture_json: names its outputs | 1 | >= 1 |
| ok | capture_xml: counts.in == counts.out + counts.dropped | 63868 == 500 + 63368 | equal |
| ok | capture_xml: names its outputs | 1 | >= 1 |
| ok | chain: counts.in == counts.out + counts.dropped | 4000 == 3999 + 1 | equal |
| ok | chain: names its outputs | 3 | >= 1 |

## Quarantine

| | check | measured | required |
|-|-|-|-|
| ok | no ground-truth column name appears in an observable header | none | none |

## Distributions

| | check | measured | required |
|-|-|-|-|
| ok | value p99 / p50 | 123.726803 | >= 8.000000 |
| ok | value p999 / p50 | 516.164239 | >= 25.000000 |
| ok | multi-input rate | 0.376878 | 0.280000 to 0.420000 |
| ok | announcements per transaction | 14.957377 | 9.750000 to 20.250000 |
| ok | relay delay coefficient of variation | 0.616985 | >= 0.500000 |
| ok | block interval coefficient of variation | 1.053810 | 0.700000 to 1.300000 |

## Leakage

| | check | measured | required |
|-|-|-|-|
| ok | first announcement seen names the originator | 0.225293 | 0.150000 to 0.600000 |
| ok | trivial rule: the peer announcing it most often | 0.220843 | <= 0.350000 |
| ok | trivial rule: the first full tx message rather than an inv | 0.080562 | <= 0.350000 |
| ok | trivial rule: the lowest source port | 0.028806 | <= 0.350000 |
| ok | trivial rule: the busiest peer in the whole capture | 0.000234 | <= 0.350000 |
| ok | depth-2 decision tree over the observable columns | 0.225293 | <= 0.700000 |
