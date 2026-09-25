# Origin accuracy over observer fraction

Top-1 accuracy as a share of **all broadcast transactions**, not of the transactions
an observer recorded. `ceiling` is the share whose true originator is in the candidate
set at all: no estimator here can exceed it, and an accuracy read without it looks like
far more headroom than the capture has. `coverage` is the share of transactions
`ensemble` was willing to answer; the rest it abstained on.

| observer_fraction | ceiling | first_seen | payer_linkage | first_spy | ensemble | coverage |
|---|---|---|---|---|---|---|
| 0.02 | 0.0225 | 0.0157 | 0.0172 | 0.0157 | 0.0193 | 0.318 |
| 0.05 | 0.0474 | 0.0286 | 0.0332 | 0.0286 | 0.0422 | 0.747 |
| 0.10 | 0.0918 | 0.0472 | 0.0598 | 0.0472 | 0.0740 | 0.912 |
| 0.25 | 0.1859 | 0.0975 | 0.1110 | 0.0975 | 0.1389 | 0.939 |
| 0.50 | 0.3323 | 0.1731 | 0.1934 | 0.1731 | 0.2246 | 0.943 |

## By traffic class, `ensemble`

Tor beats VPN where a transaction used both, so the harder class is never reported as the
easier one.

| observer_fraction | clear | vpn | tor |
|---|---|---|---|
| 0.02 | 0.0195 | 0.0115 | 0.0303 |
| 0.05 | 0.0433 | 0.0281 | 0.0460 |
| 0.10 | 0.0740 | 0.0611 | 0.1022 |
| 0.25 | 0.1414 | 0.1412 | 0.0767 |
| 0.50 | 0.2327 | 0.1718 | 0.1499 |

## Holdout only, `ensemble` against the best trivial rule

Transactions no label was available for. The denominator is transactions an observer
heard, so these do not compare to the table above. Reported because an estimator can beat
a trivial rule run-wide by memorising its own training window.

| observer_fraction | ensemble | best trivial rule |
|---|---|---|
| 0.02 | 0.0214 | 0.0235 |
| 0.05 | 0.0370 | 0.0355 |
| 0.10 | 0.0612 | 0.0572 |
| 0.25 | 0.1105 | 0.1047 |
| 0.50 | 0.2014 | 0.1971 |
