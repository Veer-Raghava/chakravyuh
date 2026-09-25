# MAYAJAAL validation

**PASS** — 48 of 48 checks passed.

## Run

- capture rows: 8913
- transactions: 758
- coinbase transactions never gossiped: 144
- transactions broadcast: 614
- transactions announced: 609
- broadcast transactions no observer saw: 5
- blocks: 144
- announcing peers: 179
- observers: 16
- tor share: 0.030945
- vpn share: 0.078176
- unresolved asn share: 0.046898
- unresolved geo share: 0.026254
- entities: 120
- illicit entities: 4
- entities in a campaign: 0
- campaigns: 0

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
| ok | capture: counts.in == counts.out + counts.dropped | 8913 == 8913 + 0 | equal |  |
| ok | capture: names its outputs | 1 | >= 1 |  |
| ok | capture_json: counts.in == counts.out + counts.dropped | 8913 == 8913 + 0 | equal |  |
| ok | capture_json: names its outputs | 1 | >= 1 |  |
| ok | capture_xml: counts.in == counts.out + counts.dropped | 8913 == 500 + 8413 | equal |  |
| ok | capture_xml: names its outputs | 1 | >= 1 |  |
| ok | chain: counts.in == counts.out + counts.dropped | 600 == 600 + 0 | equal |  |
| ok | chain: names its outputs | 3 | >= 1 |  |
| ok | normalised: counts.in == counts.out + counts.dropped | 8913 == 8913 + 0 | equal |  |
| ok | normalised: names its outputs | 4 | >= 1 |  |
| ok | sealed: counts.in == counts.out + counts.dropped | 8913 == 8913 + 0 | equal |  |
| ok | sealed: names its outputs | 3 | >= 1 |  |

## Quarantine

| | check | measured | required | note |
|-|-|-|-|-|
| ok | no ground-truth column name appears in an observable header | none | none | 12 files checked |

## Distributions

| | check | measured | required | note |
|-|-|-|-|-|
| ok | value p99 / p50 | 195.640833 | >= 8.000000 |  |
| ok | value p999 / p50 | 540.568046 | >= 25.000000 |  |
| ok | multi-input rate | 0.382736 | 0.280000 to 0.420000 |  |
| ok | announcements per transaction | 14.516287 | 9.750000 to 20.250000 |  |
| ok | relay delay coefficient of variation | 0.623265 | >= 0.500000 |  |
| ok | block interval coefficient of variation | 1.064795 | 0.700000 to 1.300000 |  |

## Leakage

| | check | measured | required | note |
|-|-|-|-|-|
| ok | the originator is in the capture at all | 0.426710 | >= 0.250000 | the ceiling on every score below, and on S03's accuracy |
| ok | first announcement seen names the originator | 0.228013 | 0.150000 to 0.600000 | 0.534351 of the reachable share |
| ok | trivial rule: the peer announcing it most often | 0.221498 | <= 0.350000 |  |
| ok | trivial rule: the first full tx message rather than an inv | 0.084691 | <= 0.350000 |  |
| ok | trivial rule: the lowest source port | 0.024430 | <= 0.350000 |  |
| ok | trivial rule: the busiest peer in the whole capture | 0.000000 | <= 0.350000 |  |
| ok | trivial rule: the peer seen across most of that payer's transactions | 0.234528 | <= 0.350000 |  |
| ok | depth-2 decision tree over the observable columns | 0.228013 | <= 0.350000 | the same six features, combined instead of tried one at a time |
