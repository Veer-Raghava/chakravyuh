# MAYAJAAL validation

**PASS** — 58 of 58 checks passed.

## Run

- capture rows: 906560
- transactions: 33849
- coinbase transactions never gossiped: 800
- transactions broadcast: 33049
- transactions announced: 32787
- broadcast transactions no observer saw: 262
- blocks: 800
- announcing peers: 2954
- observers: 48
- tor share: 0.041454
- vpn share: 0.077945
- unresolved asn share: 0.022482
- unresolved geo share: 0.007583
- entities: 20000
- illicit entities: 272
- entities in a campaign: 272
- campaigns: 34

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
| ok | alerts: counts.in == counts.out + counts.dropped | 87896 == 66957 + 20939 | equal |  |
| ok | alerts: names its outputs | 3 | >= 1 |  |
| ok | capture: counts.in == counts.out + counts.dropped | 906560 == 906560 + 0 | equal |  |
| ok | capture: names its outputs | 4 | >= 1 |  |
| ok | capture_json: counts.in == counts.out + counts.dropped | 906560 == 906560 + 0 | equal |  |
| ok | capture_json: names its outputs | 4 | >= 1 |  |
| ok | capture_xml: counts.in == counts.out + counts.dropped | 906560 == 500 + 906060 | equal |  |
| ok | capture_xml: names its outputs | 1 | >= 1 |  |
| ok | chain: counts.in == counts.out + counts.dropped | 24000 == 24000 + 0 | equal |  |
| ok | chain: names its outputs | 3 | >= 1 |  |
| ok | graph: counts.in == counts.out + counts.dropped | 1063595 == 1062417 + 1178 | equal |  |
| ok | graph: names its outputs | 4 | >= 1 |  |
| ok | normalised: counts.in == counts.out + counts.dropped | 906560 == 906560 + 0 | equal |  |
| ok | normalised: names its outputs | 6 | >= 1 |  |
| ok | packets: counts.in == counts.out + counts.dropped | 1 == 1 + 0 | equal |  |
| ok | packets: names its outputs | 4 | >= 1 |  |
| ok | scores: counts.in == counts.out + counts.dropped | 87896 == 87896 + 0 | equal |  |
| ok | scores: names its outputs | 2 | >= 1 |  |
| ok | sealed: counts.in == counts.out + counts.dropped | 906560 == 906560 + 0 | equal |  |
| ok | sealed: names its outputs | 3 | >= 1 |  |
| ok | signals: counts.in == counts.out + counts.dropped | 906560 == 905382 + 1178 | equal |  |
| ok | signals: names its outputs | 4 | >= 1 |  |

## Quarantine

| | check | measured | required | note |
|-|-|-|-|-|
| ok | no ground-truth column name appears in an observable header | none | none | 33 files checked |

## Distributions

| | check | measured | required | note |
|-|-|-|-|-|
| ok | value p99 / p50 | 232.865827 | >= 8.000000 |  |
| ok | value p999 / p50 | 1643.401644 | >= 25.000000 |  |
| ok | multi-input rate | 0.341886 | 0.280000 to 0.420000 |  |
| ok | announcements per transaction | 27.430785 | 17.550000 to 36.450000 |  |
| ok | relay delay coefficient of variation | 0.660403 | >= 0.500000 |  |
| ok | block interval coefficient of variation | 1.005179 | 0.700000 to 1.300000 |  |

## Leakage

| | check | measured | required | note |
|-|-|-|-|-|
| ok | the originator is in the capture at all | 0.482405 | >= 0.250000 | the ceiling on every score below, and on S03's accuracy |
| ok | first announcement seen names the originator | 0.186753 | 0.150000 to 0.600000 | 0.387129 of the reachable share |
| ok | trivial rule: the peer announcing it most often | 0.180883 | <= 0.350000 |  |
| ok | trivial rule: the first full tx message rather than an inv | 0.042694 | <= 0.350000 |  |
| ok | trivial rule: the lowest source port | 0.018185 | <= 0.350000 |  |
| ok | trivial rule: the busiest peer in the whole capture | 0.000242 | <= 0.350000 |  |
| ok | trivial rule: the peer seen across most of that payer's transactions | 0.253472 | <= 0.350000 |  |
| ok | depth-2 decision tree over the observable columns | 0.186753 | <= 0.350000 | the same six features, combined instead of tried one at a time |
