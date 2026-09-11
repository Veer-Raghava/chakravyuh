## S06 · SHASTRA origin estimator

**Goal.** Per transaction, a calibrated `P(originator)` for each announcing peer, with a runner-up,
a margin, and an explicit abstain. Plus typology heuristics and entity typing.

**Reads.** `normalised/`, `graph/`. Ground truth only inside `src/chakravyuh/eval/`.

**Writes.** `signals/origin_estimates.parquet` one row per candidate peer per txid,
`signals/typology_hits.parquet`, `signals/entity_types.parquet`, `_meta.json`, the recorded
baseline accuracies. `tests/test_shastra.py`.

**Definition of done.** `make verify-s06`, which asserts the real estimator beats the strongest
trivial rule on top-1 accuracy at `observer_fraction` 0.10 — not first-seen.

Beating first-seen is not a real bar. The numbers below come from run `_s02-final`, the
remediated S02 reference run at `--txs 20000 --entities 4000`, and every one of them is a share
of all broadcast transactions, which is the denominator S06 must report on:

| quantity | value |
|-|-|
| recoverable-origin ceiling | 0.415376 |
| first-seen baseline | 0.220919 |
| strongest trivial rule: the peer seen across most of that payer's transactions | 0.263241 |
| depth-2 tree over the observable columns | 0.220919 |
| depth-12 tree over the same columns | 0.233983 |

The ceiling is what makes the rest readable. An observer keeps only the earliest arrival and each
monitored node dials exactly one observer, so for most transactions the originator is not in the
candidate set at all and no method can ever be right about them. 0.415376 is the most any
estimator can score, and 0.263241 is what one line of SQL already gets. An estimator scoring 0.27
has learned essentially nothing; measured against first-seen it would look like a 22% improvement.

Record both baselines in `_meta.json`, and re-measure them on whatever run S06 actually scores
against rather than copying these. They move when the generator moves: all three fell slightly
when S02 stopped gossiping coinbase transactions, because the denominator grew.

**Known traps.** Renormalising `p_origin` to sum to one, which destroys the ability to express
"none of these peers is the originator". Building abstention later, which means never. Scoring
against first-seen instead of the strongest trivial rule, which passes the gate without beating
anything. Scoring over the transactions an observer happened to see instead of over all broadcast
transactions, which silently drops the ones no rule could ever get right and flatters every
number. Reporting a single accuracy number instead of a curve over `observer_fraction` split by
traffic type. Touching ground truth outside `eval/`.

---
