# MAYAJAAL validation

**PASS** — 36 of 36 checks passed.

## Run

- capture rows: 11694
- transactions: 776
- transactions announced: 776
- transactions no observer saw: 0
- blocks: 144
- announcing peers: 308
- observers: 16
- tor share: 0.029639
- vpn share: 0.060567
- unresolved asn share: 0.037968
- unresolved geo share: 0.028647
- entities: 300
- illicit entities: 9
- entities in a campaign: 0
- campaigns: 0

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
| ok | capture: counts.in == counts.out + counts.dropped | 11694 == 11694 + 0 | equal |
| ok | capture: names its outputs | 1 | >= 1 |
| ok | capture_json: counts.in == counts.out + counts.dropped | 11694 == 11694 + 0 | equal |
| ok | capture_json: names its outputs | 1 | >= 1 |
| ok | capture_xml: counts.in == counts.out + counts.dropped | 11694 == 500 + 11194 | equal |
| ok | capture_xml: names its outputs | 1 | >= 1 |
| ok | chain: counts.in == counts.out + counts.dropped | 600 == 600 + 0 | equal |
| ok | chain: names its outputs | 3 | >= 1 |

## Quarantine

| | check | measured | required |
|-|-|-|-|
| ok | no ground-truth column name appears in an observable header | none | none |

## Distributions

| | check | measured | required |
|-|-|-|-|
| ok | value p99 / p50 | 196.327014 | >= 8.000000 |
| ok | value p999 / p50 | 406.414556 | >= 25.000000 |
| ok | multi-input rate | 0.387658 | 0.280000 to 0.420000 |
| ok | announcements per transaction | 15.069588 | 9.750000 to 20.250000 |
| ok | relay delay coefficient of variation | 0.605408 | >= 0.600000 |
| ok | block interval coefficient of variation | 0.961923 | 0.700000 to 1.300000 |

## Leakage

| | check | measured | required |
|-|-|-|-|
| ok | first announcement seen names the originator | 0.253866 | 0.150000 to 0.600000 |
| ok | trivial rule: the peer announcing it most often | 0.250000 | <= 0.350000 |
| ok | trivial rule: the first full tx message rather than an inv | 0.092784 | <= 0.350000 |
| ok | trivial rule: the lowest source port | 0.057990 | <= 0.350000 |
| ok | trivial rule: the busiest peer in the whole capture | 0.000000 | <= 0.350000 |
| ok | depth-2 decision tree over the observable columns | 0.255155 | <= 0.700000 |
