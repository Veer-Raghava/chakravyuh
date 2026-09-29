"""Elliptic / Elliptic++ external validation: the same recipe, on somebody else's labels.

The credibility question this module exists to answer is "you scored well on a world you built
yourself, so what?" The answer is a second number, produced by the *same* function that produced
the first one, on a dataset nobody here generated: Elliptic's 203,769 Bitcoin transactions with
the labels the Elliptic authors gave them.

**What is shared, and what is not.** The shared thing is the procedure, not the feature matrix.
`buddhi.recipe.train_and_score` takes `(X, y, time_index)` and does the time-ordered split, the
booster, the calibration, the conformal wrap and the scoring. CHAKRAVYUH hands it named
morphology; Elliptic hands it whatever numeric columns follow the id and the time step — 182 of
them in the vendored export (93 `Local_feature_*`, 84 `Aggregate_feature_*`, 5 `out_BTC_*`) —
which are not our named features and cannot be mapped onto them without inventing semantics that
are not there. So the claim this block supports is exactly "one procedure, two datasets" — no
stronger, and the report says so in `caveat` rather than letting a reader assume the features are
the same too. The classic `f1..f165` export loads through the same path unchanged; the loader
reads column positions, never names.

**Vendored, never fetched.** The box is air-gapped. The files are side-loaded under
`vendor/elliptic/` (see that directory's README for provenance and the expected names); this
module reads them and nothing else. When they are absent it returns
`{"available": false, "reason": "dataset_not_vendored"}` — the same honest-absence shape
`score_wallets` uses when a run has no answer key, never a placeholder zero.

**Where the numbers go.** `run()` writes one file, `measurements/<run>/elliptic_external.json`,
keyed on the hash of the vendored CSV so a reader can tell which bytes produced the figures. It is
computed by its own command rather than inside every scoring pass: the features and the recipe are
identical either way, and a 700 MB read plus a 300-round fit does not belong in a gate that scores
the same run twice.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

import numpy as np
import polars as pl

from chakravyuh.buddhi import recipe
from chakravyuh.eval import metrics, split
from chakravyuh.mayajaal.writers import run_roots

# The classic Elliptic file names, and the names the same three files carry in the Elliptic++
# repository. Both are accepted so the operator does not have to rename what they downloaded.
FEATURES_NAMES: Final[tuple[str, ...]] = ("elliptic_txs_features.csv", "txs_features.csv")
CLASSES_NAMES: Final[tuple[str, ...]] = ("elliptic_txs_classes.csv", "txs_classes.csv")

# Elliptic's own class codes: 1 is illicit, 2 is licit, and anything else (the string "unknown",
# or the code 3) is an unlabelled transaction the authors did not commit to. Unlabelled rows are
# dropped rather than guessed at, and the count of what was dropped is reported.
ILLICIT_CODE: Final[int] = 1
LICIT_CODE: Final[int] = 2

ABSENT: Final[dict[str, Any]] = {"available": False, "reason": "dataset_not_vendored"}

# Where the leg's own measurement lands, so the writer and the reader of `eval_report.json` name
# the same file rather than each spelling it out.
FILENAME: Final[str] = "elliptic_external.json"

# What `eval_report.json` carries when the leg was never run for the run in question. Distinct
# from ABSENT on purpose: "nobody ran it" and "the dataset is not here" are different facts, and
# a reader deciding whether to trust the box needs to be able to tell them apart.
NOT_RUN: Final[dict[str, Any]] = {"available": False, "reason": "not_run_for_this_run"}

# The strongest claim this block is entitled to make, stated once so no reader has to infer it.
CAVEAT: Final[str] = (
    "Same training procedure as our own leg (time-ordered split, same booster params, same "
    "conformal wrap) on the Elliptic transactions and the labels its authors gave them; "
    "Elliptic's own columns are not our named morphology, so this replicates the method, not "
    "the feature set."
)


def _locate(vendor_dir: Path, names: tuple[str, ...]) -> Path | None:
    """The first of `names` that exists in `vendor_dir`, or None. Neither name is preferred."""
    for name in names:
        candidate = vendor_dir / name
        if candidate.is_file():
            return candidate
    return None


def _load(vendor_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, Path] | None:
    """The vendored CSVs as `(X, y, time_index, features_path)`, or None when not vendored.

    The first two columns of the features file are the transaction id and the ordinal time step;
    every column after them is a feature. Elliptic's time step is already an integer ordering, so
    it is the recipe's time index directly — monotone in real time by the dataset's construction,
    which is what the time-ordered split needs and all it needs.
    """
    features_path = _locate(vendor_dir, FEATURES_NAMES)
    classes_path = _locate(vendor_dir, CLASSES_NAMES)
    if features_path is None or classes_path is None:
        return None

    features = pl.read_csv(features_path)
    # Read the labels as text whatever they look like. Polars would otherwise infer an integer
    # column from the first rows and then fail on the literal "unknown" that the real file carries
    # further down — and a schema inferred from the head is exactly the guess this leg must not
    # make, because the rows it would drop are the unlabelled ones.
    classes = pl.read_csv(classes_path, infer_schema_length=0)
    id_col = features.columns[0]
    time_col = features.columns[1]
    feature_cols = features.columns[2:]

    label_col = classes.columns[1]
    # Join on the id as text at both ends: the features file infers an integer id and the classes
    # file is read as text, and a typed join between the two would fail on the one pair of columns
    # that is certainly present in both.
    joined = features.with_columns(pl.col(id_col).cast(pl.String)).join(
        classes.select(pl.col(classes.columns[0]).cast(pl.String).alias(id_col), pl.col(label_col)),
        on=id_col,
    )
    # Drop the unlabelled: their class is the string "unknown" in the classic file and the code 3
    # in some mirrors, so the test is on the numeric code after a strict cast, which fails loudly
    # on a string rather than silently coercing it to null and dropping the row as unlabelled.
    labels = joined[label_col].cast(pl.String).str.replace("unknown", "3").cast(pl.Int64)
    labelled = joined.with_columns(labels.alias("_code")).filter(
        pl.col("_code").is_in([ILLICIT_CODE, LICIT_CODE])
    )

    y = (labelled["_code"] == ILLICIT_CODE).cast(pl.Int64).to_numpy()
    X = labelled.select(feature_cols).to_numpy().astype("float64")
    time_index = labelled[time_col].cast(pl.Int64).to_numpy()
    return X, y, time_index, features_path


def _auc(y: Sequence[int], scores: Sequence[float], *, pr: bool) -> float:
    """The project's one AUC, so both legs are scored by the same arithmetic.

    Deliberately the *scoring* code and not a second copy of it: two implementations of average
    precision would be two chances to disagree, and the whole point of quoting an external number
    beside our own is that the two are comparable.
    """
    return metrics._auc(y, scores, pr)


def elliptic_block(
    vendor_dir: Path, *, train_fraction: float, seed: int, coverage_target: float
) -> dict[str, Any]:
    """Train and score the shared recipe on the vendored Elliptic data.

    Returns the honest-absence block when the dataset is not vendored. Otherwise every number
    below is computed from the files that are there: nothing in the returned object is a constant
    except the protocol name and the caveat.
    """
    loaded = _load(vendor_dir)
    if loaded is None:
        return dict(ABSENT)
    X, y, time_index, features_path = loaded

    result = recipe.train_and_score(
        X,
        y,
        time_index,
        train_fraction=train_fraction,
        seed=seed,
        coverage_target=coverage_target,
    )

    y_test = result.y_test.tolist()
    scores = result.scores.tolist()
    y_pred = [1 if s >= 0.5 else 0 for s in scores]
    tp = sum(1 for p, t in zip(y_pred, y_test, strict=True) if p and t)
    fp = sum(1 for p, t in zip(y_pred, y_test, strict=True) if p and not t)
    fn = sum(1 for p, t in zip(y_pred, y_test, strict=True) if not p and t)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "available": True,
        "dataset": "elliptic",
        "source_sha256": hashlib.sha256(features_path.read_bytes()).hexdigest(),
        "source_name": features_path.name,
        "n_train": result.n_train,
        "n_test": result.n_test,
        "n_illicit": int(np.sum(y)),
        "illicit_rate": round(float(np.mean(y)), 6),
        "pr_auc": round(_auc(y_test, scores, pr=True), 6),
        "roc_auc": round(_auc(y_test, scores, pr=False), 6),
        "f1": round(f1, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "protocol": split.PROTOCOL,
        "train_fraction": train_fraction,
        "seed": seed,
        "caveat": CAVEAT,
    }


def run(out: Path, *, vendor_dir: Path) -> dict[str, Any]:
    """Score the Elliptic leg for the run `out` names, and file it beside that run's reports.

    The split parameters are read from the run's own `config.effective.json`. That is the point of
    doing it here rather than taking them as arguments: "the same recipe" has to mean the same
    *numbers* too, and a leg that quietly trained on a different share of the data, or calibrated
    to a different coverage, would be a different experiment wearing the same name. Reading them
    from the run's config makes that agreement structural instead of a promise the caller keeps.
    """
    roots = run_roots(out)
    config_path = roots.observable / "config.effective.json"
    node = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    evaluation = node.get("eval", {})
    block = elliptic_block(
        vendor_dir,
        train_fraction=float(evaluation.get("train_fraction", 0.7)),
        seed=int(node.get("seed", 0)),
        coverage_target=float(evaluation.get("coverage_target", 0.9)),
    )
    roots.measurements.mkdir(parents=True, exist_ok=True)
    (roots.measurements / FILENAME).write_text(
        json.dumps(block, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return block


def main(argv: list[str] | None = None) -> int:
    """`python -m chakravyuh.eval.external --out <run-dir> [--vendor vendor/elliptic]`."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path, help="the run's data/generated/<id>")
    parser.add_argument("--vendor", type=Path, default=Path("vendor") / "elliptic")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    block = run(args.out, vendor_dir=args.vendor)
    if not block.get("available"):
        sys.stderr.write(
            f"external: {args.vendor} holds no Elliptic files, so the block reports "
            f"{block.get('reason')!r}. See vendor/elliptic/README.md for what to side-load.\n"
        )
        return 0
    sys.stderr.write(
        f"external: elliptic PR-AUC {block['pr_auc']:.4f} ROC-AUC {block['roc_auc']:.4f} "
        f"F1 {block['f1']:.4f} on {block['n_test']} holdout transactions "
        f"(train {block['n_train']}).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
