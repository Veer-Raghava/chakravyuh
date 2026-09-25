# MAYAJAAL validation

**PASS** — 44 of 44 checks passed.

## Run

- capture rows: 354023
- transactions: 24626
- coinbase transactions never gossiped: 667
- transactions broadcast: 23959
- transactions announced: 23784
- broadcast transactions no observer saw: 175
- blocks: 667
- announcing peers: 2571
- observers: 16
- tor share: 0.040861
- vpn share: 0.078008
- unresolved asn share: 0.018236
- unresolved geo share: 0.00916
- entities: 4000
- illicit entities: 120
- entities in a campaign: 37
- campaigns: 5

## Invariants

| | check | measured | required | note |
|-|-|-|-|-|
| ok | txid is 64 lowercase hex | 0 rows | 0 rows |  |
| ok | timestamp is ISO 8601 with six fractional digits and an explicit offset | 0 rows | 0 rows |  |
| ok | input addresses and input amounts are the same length | 0 rows | 0 rows |  |
| ok | output addresses and output amounts are the same length | 0 rows | 0 rows |  |
| ok | script types name every output | 0 rows | 0 rows |  |
| ok | every announced transaction has an output | 0 rows | 0 rows |  |
| ok | inputs cover outputs on a payment | 0 rows | 0 rows |  |
| ok | vsize is positive and fee is not negative | 0 rows | 0 rows |  |
| ok | ports are inside the 16-bit range | 0 rows | 0 rows |  |
| ok | msg_type is inv or tx | 0 rows | 0 rows |  |
| ok | the capture never goes backwards in time | 0 rows | 0 rows |  |
| ok | rows sharing a txid agree on the chain columns | 0 txids | 0 txids |  |
| ok | every announced txid exists on the chain | 0 txids | 0 txids |  |
| ok | no coinbase transaction is announced | 0 rows | 0 rows |  |
| ok | no announcement lands at or after its confirming block | 0 rows | 0 rows |  |
| ok | exactly one true originator per announced txid | 0 txids | 0 txids |  |
| ok | observer id and dst_ip are one to one | 0 surplus pairings | 0 surplus pairings |  |
| ok | no address is owned by two entities | 0 addresses | 0 addresses |  |
| ok | no coinbase output address is also an endowment address | 0 addresses | 0 addresses |  |
| ok | observed_by_n equals the observers that recorded the transaction | 0 txids | 0 txids |  |
| ok | no announcement predates its broadcast | 0 rows | 0 rows |  |

## Manifests

| | check | measured | required | note |
|-|-|-|-|-|
| ok | capture: counts.in == counts.out + counts.dropped | 354023 == 354023 + 0 | equal |  |
| ok | capture: names its outputs | 2 | >= 1 |  |
| ok | capture_json: counts.in == counts.out + counts.dropped | 354023 == 354023 + 0 | equal |  |
| ok | capture_json: names its outputs | 2 | >= 1 |  |
| ok | capture_xml: counts.in == counts.out + counts.dropped | 354023 == 500 + 353523 | equal |  |
| ok | capture_xml: names its outputs | 1 | >= 1 |  |
| ok | chain: counts.in == counts.out + counts.dropped | 20000 == 20000 + 0 | equal |  |
| ok | chain: names its outputs | 3 | >= 1 |  |

## Quarantine

| | check | measured | required | note |
|-|-|-|-|-|
| ok | no ground-truth column name appears in an observable header | none | none | 8 files checked |

## Distributions

| | check | measured | required | note |
|-|-|-|-|-|
| ok | value p99 / p50 | 396.413758 | >= 8.000000 |  |
| ok | value p999 / p50 | 2276.569895 | >= 25.000000 |  |
| ok | multi-input rate | 0.371593 | 0.280000 to 0.420000 |  |
| ok | announcements per transaction | 14.776201 | 9.750000 to 20.250000 |  |
| ok | relay delay coefficient of variation | 0.618320 | >= 0.500000 |  |
| ok | block interval coefficient of variation | 0.988811 | 0.700000 to 1.300000 |  |

## Leakage

| | check | measured | required | note |
|-|-|-|-|-|
| ok | the originator is in the capture at all | 0.415376 | >= 0.250000 | the ceiling on every score below, and on S03's accuracy |
| ok | first announcement seen names the originator | 0.220919 | 0.150000 to 0.600000 | 0.531853 of the reachable share |
| ok | trivial rule: the peer announcing it most often | 0.215702 | <= 0.350000 |  |
| ok | trivial rule: the first full tx message rather than an inv | 0.084728 | <= 0.350000 |  |
| ok | trivial rule: the lowest source port | 0.027130 | <= 0.350000 |  |
| ok | trivial rule: the busiest peer in the whole capture | 0.000459 | <= 0.350000 |  |
| ok | trivial rule: the peer seen across most of that payer's transactions | 0.263241 | <= 0.350000 |  |
| ok | depth-2 decision tree over the observable columns | 0.220919 | <= 0.350000 | the same six features, combined instead of tried one at a time |
