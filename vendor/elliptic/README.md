# vendor/elliptic — the external-validation dataset

The box is air-gapped, so this dataset is **side-loaded by hand and never fetched by the code**.
`chakravyuh.eval.external` reads whatever is in this directory and nothing else. When the CSVs are
absent it reports `{"available": false, "reason": "dataset_not_vendored"}` — an honest absence,
never a placeholder zero — and `make elliptic-eval` exits 0 having said so.

Everything here is gitignored (the whole of `vendor/` is) and must never reach a commit. The
dataset is redistributed by its authors under their own terms, which are not ours to relicense;
obtain it from the distributor you have access to and check those terms before passing the bytes
on.

## What the leg is for

The credibility question is "you scored well on a world you built yourself, so what?". The answer
is a second number produced by the *same* function that produced the first one — the same
time-ordered split, the same boosted-tree parameters, the same conformal wrap — on a dataset
nobody in this repository generated. See the module docstring in
`src/chakravyuh/eval/external.py` for what that does and does not establish.

## Files

| File | Size | Read by the leg |
|---|---|---|
| `elliptic_txs_features.csv` | 663 MB | **yes** — the feature matrix |
| `elliptic_txs_classes.csv` | 3 MB | **yes** — the labels |
| `elliptic_txs_edgelist.csv` | 5 MB | no — the transaction graph, unused here |

The same three files are published under shorter names in some mirrors
(`txs_features.csv`, `txs_classes.csv`). Both namings are accepted; do not rename what you
downloaded on our account.

The loader takes column *positions*, not names: the first column is the transaction id, the second
is the ordinal time step, and every column after them is a feature. So both published exports work
unchanged — the classic `f1..f165` set and the named one (93 `Local_feature_*`, 84
`Aggregate_feature_*`, 5 `out_BTC_*`, 184 columns including the two leading ones, 203,769 rows).

Labels are Elliptic's own: `1` illicit, `2` licit, and `3` (or the literal `unknown`, which some
mirrors use for the same rows) for a transaction the authors did not commit to. Unlabelled rows are
**dropped, never guessed at**. In the export measured here that leaves 46,564 labelled transactions,
4,545 of them illicit.

## Verifying what you side-loaded

The leg records the SHA-256 of the features file it actually read in the report's
`source_sha256`, so a figure can always be traced to the bytes behind it. To confirm you have the
same export this repository was measured on:

```sh
sha256sum vendor/elliptic/elliptic_txs_features.csv
# 2db326ec8ddb68f1d810c1834e1ff62e0a8300378f0984a1e3b2ca82a439821b
```

A different hash is not a failure — it is a different export, and the run will report its own hash.
Check the row and column counts above match before comparing any number to a previously published
one.

## Running it

```sh
make elliptic-eval                      # the canonical run, data/generated/agency-v2
python -m chakravyuh.eval.external --out data/generated/<run> --vendor vendor/elliptic
```

The split parameters are read from the run's own `config.effective.json` rather than passed on the
command line, because "the same recipe" has to mean the same *numbers* — a leg that silently
trained on a different share of the data would be a different experiment wearing the same name.
