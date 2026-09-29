# Origin accuracy over observer fraction

Top-1 accuracy as a share of **all broadcast transactions**, not of the transactions
an observer recorded. `ceiling` is the share whose true originator is in the candidate
set at all: no estimator here can exceed it, and an accuracy read without it looks like
far more headroom than the capture has. `coverage` is the share of transactions
`ensemble` was willing to answer; the rest it abstained on.

| observer_fraction | ceiling | first_seen | payer_linkage | first_spy | ensemble | coverage |
|---|---|---|---|---|---|---|
| 0.02 | 0.0216 | 0.0170 | 0.0181 | 0.0170 | 0.0199 | 0.335 |
| 0.05 | 0.0391 | 0.0218 | 0.0241 | 0.0218 | 0.0320 | 0.569 |
| 0.10 | 0.0990 | 0.0468 | 0.0568 | 0.0468 | 0.0788 | 0.503 |
| 0.25 | 0.2311 | 0.0999 | 0.1188 | 0.0999 | 0.1542 | 0.458 |
| 0.50 | 0.4327 | 0.1760 | 0.2084 | 0.1760 | 0.2604 | 0.364 |
| 0.60 | 0.4948 | 0.2027 | 0.2365 | 0.2027 | 0.2868 | 0.330 |
| 0.70 | 0.5499 | 0.2219 | 0.2658 | 0.2219 | 0.3149 | 0.355 |

## Operator (L1 ASN) accuracy over observer fraction — the hero

The exact host most observers never heard is L0 above; the network operator is
recoverable on far more transactions, because a sibling peer in the same ASN carries
it. `l1_ceiling` is the share whose true operator is in the candidate set at all.

| observer_fraction | l1_ceiling | first_seen | payer_linkage | first_spy | ensemble |
|---|---|---|---|---|---|
| 0.02 | 0.2452 | 0.1736 | 0.1763 | 0.1736 | 0.1770 |
| 0.05 | 0.4089 | 0.1965 | 0.2020 | 0.1967 | 0.2012 |
| 0.10 | 0.6218 | 0.2381 | 0.2558 | 0.2382 | 0.2582 |
| 0.25 | 0.8395 | 0.3014 | 0.3296 | 0.3017 | 0.3559 |
| 0.50 | 0.9419 | 0.3791 | 0.4068 | 0.3806 | 0.4579 |
| 0.60 | 0.9529 | 0.3978 | 0.4271 | 0.3991 | 0.4808 |
| 0.70 | 0.9630 | 0.4251 | 0.4588 | 0.4276 | 0.5084 |

## By traffic class, `ensemble`

Tor beats VPN where a transaction used both, so the harder class is never reported as the
easier one.

| observer_fraction | clear | vpn | tor |
|---|---|---|---|
| 0.02 | 0.0198 | 0.0193 | 0.0221 |
| 0.05 | 0.0292 | 0.0255 | 0.1025 |
| 0.10 | 0.0758 | 0.0549 | 0.1953 |
| 0.25 | 0.1560 | 0.1169 | 0.1813 |
| 0.50 | 0.2688 | 0.1827 | 0.2343 |
| 0.60 | 0.2977 | 0.1904 | 0.2479 |
| 0.70 | 0.3255 | 0.2273 | 0.2624 |

## Holdout only, `ensemble` against the best trivial rule

Transactions no label was available for. The denominator is transactions an observer
heard, so these do not compare to the table above. Reported because an estimator can beat
a trivial rule run-wide by memorising its own training window.

| observer_fraction | ensemble | best trivial rule |
|---|---|---|
| 0.02 | 0.0214 | 0.0223 |
| 0.05 | 0.0264 | 0.0291 |
| 0.10 | 0.0530 | 0.0468 |
| 0.25 | 0.1112 | 0.1073 |
| 0.50 | 0.2267 | 0.2106 |
| 0.60 | 0.2652 | 0.2393 |
| 0.70 | 0.2899 | 0.2726 |
