"""The LightGBM risk model and the class-conditional conformal wrapper around it.

Two version facts shaped this file, both found the hard way in S06 and here:

LightGBM's sklearn wrapper is unusable — its `fit` calls a keyword sklearn 1.9 removed — so the
booster is trained through the native API exactly as SHASTRA does it, then handed to the conformal
layer behind a thin adapter that speaks the sklearn protocol (`classes_`, `predict_proba`).

MAPIE 0.9.1 predates sklearn's estimator-tags protocol: its internal `EnsembleClassifier` has no
`__sklearn_tags__`, and sklearn 1.9's `check_is_fitted` demands one, so any prefit `MapieClassifier`
raises `AttributeError` before doing any work. `_patch_mapie_tags` adds the missing method at
runtime, guarded so it is a no-op the day MAPIE ships its own tags. It is the same shape of
compromise as Kùzu's absence path: narrow, loud in the source, and removable.

Determinism is not a preference here. `make verify-s07` runs this stage in two separate
interpreters and compares bytes, so every random and threading knob is pinned, and the Mondrian
predict loop runs per class in a fixed order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import polars as pl

from chakravyuh.buddhi.features import MODEL_FEATURES

if TYPE_CHECKING:
    import lightgbm as lgb
    from sklearn.utils._tags import Tags

# Fixed so a model trained in one process scores identically in another. The same values SHASTRA
# uses: `num_threads=1` and `deterministic` remove scheduler-order from split choice, and
# `force_row_wise` pins the histogram build.
BOOST_ROUNDS: Final[int] = 300
TREE_PARAMS: Final[dict[str, Any]] = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 40,
    "lambda_l2": 1.0,
    "feature_fraction": 1.0,
    "bagging_fraction": 1.0,
    "num_threads": 1,
    "deterministic": True,
    "force_row_wise": True,
    "verbose": -1,
    "seed": 0,
}

# The model is fitted on the early part of the training window; the calibrator sees only rows
# later than that. A calibrator fitted on rows interleaved with the model's own training rows
# measures how well the model memorised, not how well it is calibrated.
CALIBRATION_SHARE: Final[float] = 0.25
MIN_CALIBRATION_ROWS: Final[int] = 50

# A class with fewer calibration members than this cannot support a class-conditional quantile
# with any honesty; the Mondrian wrapper refuses the partition and the run records why.
MIN_CALIBRATION_PER_CLASS: Final[int] = 10

TOP_FEATURES: Final[int] = 5


@dataclass(frozen=True)
class Calibrated:
    """What training produced. `reason` says what did not happen, for `_meta.json`."""

    trained: bool
    mondrian: bool
    n_train: int
    n_calibration: int
    n_positive: int
    reason: str | None


def _patch_mapie_tags() -> None:
    """Give MAPIE's internal estimator the sklearn-1.9 tags protocol, once, if it still lacks it.

    MAPIE 0.9.1's `EnsembleClassifier` was written before `__sklearn_tags__` existed; sklearn 1.9
    calls it unconditionally inside `check_is_fitted`, so every prefit `MapieClassifier` dies with
    `AttributeError` before fitting anything. Adding a classifier-tagged method restores exactly
    the behaviour MAPIE's own code assumes. Guarded by `hasattr` so a future MAPIE that ships its
    own tags is left alone.
    """
    from mapie.estimator.classifier import EnsembleClassifier
    from sklearn.utils._tags import ClassifierTags, InputTags, Tags, TargetTags

    if hasattr(EnsembleClassifier, "__sklearn_tags__"):
        return

    def _tags(self: EnsembleClassifier) -> Tags:
        return Tags(
            estimator_type="classifier",
            target_tags=TargetTags(required=True),
            classifier_tags=ClassifierTags(),
            input_tags=InputTags(),
        )

    EnsembleClassifier.__sklearn_tags__ = _tags


class _BoosterClassifier:
    """The native-API booster behind the sklearn protocol MAPIE's prefit path checks for.

    Not a `BaseEstimator` subclass on purpose: subclassing pulls sklearn's default `__init__`
    contract (parameters saved as constructor arguments, no mutable defaults), which a fitted
    booster violates by existing. The attributes MAPIE's `check_estimator_classification` reads —
    `classes_` and `n_features_in_` — are set eagerly in `__init__`, and `check_is_fitted` sees
    them and passes. `X` is typed loosely because MAPIE hands whatever it was given.
    """

    def __init__(self, booster: lgb.Booster) -> None:
        self.booster = booster
        self.classes_ = np.array([0, 1])
        self.n_features_in_ = int(booster.num_feature())

    # sklearn 1.9's `check_is_fitted` and `is_classifier` both read the tags protocol. Inheriting
    # BaseEstimator for it would pull in the constructor contract a fitted booster violates, so
    # the method is stated directly, exactly as BaseEstimator's own is.
    def __sklearn_tags__(self) -> Tags:
        from sklearn.utils._tags import ClassifierTags, InputTags, Tags, TargetTags

        return Tags(
            estimator_type="classifier",
            target_tags=TargetTags(required=True),
            classifier_tags=ClassifierTags(),
            input_tags=InputTags(),
        )

    def get_params(self, deep: bool = True) -> dict[str, Any]:
        # sklearn's `clone` and several validation paths call `get_params`; the adapter's only
        # constructor argument is the booster itself.
        return {"booster": self.booster}

    def fit(self, X: np.ndarray, y: np.ndarray) -> _BoosterClassifier:
        # Present but deliberately unusable: MAPIE's prefit path checks `hasattr(est, "fit")`
        # to decide the object is an estimator at all, and calling it would overwrite a booster
        # that is already trained. The estimator is fitted by construction.
        raise RuntimeError(
            "_BoosterClassifier wraps a booster that is already trained; it cannot be fitted. "
            "Use cv='prefit' and call predict/predict_proba."
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(np.int64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p = np.asarray(self.booster.predict(np.asarray(X, dtype="float64")), dtype="float64")
        return np.column_stack([1.0 - p, p])


def fit(
    subject_frame: pl.DataFrame, seed: int, coverage_target: float
) -> tuple[dict[str, Any], Calibrated]:
    """Train the risk model and wrap it in class-conditional conformal prediction.

    `subject_frame` is train-window subjects only, with `MODEL_FEATURES` and a `y` column. The
    fit/calibration split is by time (`_order`, the subject's first activity), never at random.
    Returns the fitted bundle and a `Calibrated` record for `_meta.json`.

    The Mondrian partition is the class itself. Plain (unpartitioned) conformal under-covers the
    minority class exactly when the classes are imbalanced, which is the one failure this project
    cannot afford: the interval is the thing an investigator is shown, and an interval that holds
    for the licit class 95% of the time while holding for the illicit class 60% of the time is
    worse than no interval, because it looks like a guarantee.
    """
    import lightgbm as lgb

    ordered = subject_frame.sort("_order")
    cut = int(ordered.height * (1.0 - CALIBRATION_SHARE))
    fit_rows, cal_rows = ordered.head(cut), ordered.tail(ordered.height - cut)

    if fit_rows["y"].n_unique() < 2:
        return {}, Calibrated(
            False,
            False,
            fit_rows.height,
            cal_rows.height,
            int(fit_rows["y"].sum()),
            "one_class_in_training_window",
        )

    params = dict(TREE_PARAMS)
    params["seed"] = seed
    booster = lgb.train(
        params,
        lgb.Dataset(
            fit_rows.select(MODEL_FEATURES).to_numpy(),
            label=fit_rows["y"].to_numpy(),
            feature_name=list(MODEL_FEATURES),
            params=params,
        ),
        num_boost_round=BOOST_ROUNDS,
    )

    bundle: dict[str, Any] = {
        "booster": booster,
        "model_features": list(MODEL_FEATURES),
        "coverage_target": coverage_target,
        "seed": seed,
        "mondrian": None,
        "plain": None,
        "calibration_rows": cal_rows,
        "n_fit_rows": fit_rows.height,
    }

    if cal_rows.height < MIN_CALIBRATION_ROWS or cal_rows["y"].n_unique() < 2:
        return bundle, Calibrated(
            True,
            False,
            fit_rows.height,
            cal_rows.height,
            int(cal_rows["y"].sum()),
            "too_few_calibration_rows",
        )

    _patch_mapie_tags()
    from mapie.classification import MapieClassifier
    from mapie.mondrian import MondrianCP

    classifier = _BoosterClassifier(booster)
    counts = cal_rows.group_by("y").len()
    mondrian_ok = (
        counts.filter(
            (pl.col("y").is_in([0, 1])) & (pl.col("len") >= MIN_CALIBRATION_PER_CLASS)
        ).height
        == counts.height
        and counts.height == 2
    )

    X = cal_rows.select(MODEL_FEATURES).to_numpy()
    y_cal = cal_rows["y"].to_numpy()

    plain = MapieClassifier(estimator=classifier, method="lac", cv="prefit")
    plain.fit(X, y_cal)
    bundle["plain"] = plain

    if mondrian_ok:
        mondrian = MondrianCP(
            mapie_estimator=MapieClassifier(estimator=classifier, method="lac", cv="prefit")
        )
        mondrian.fit(X, y_cal, partition=y_cal)
        bundle["mondrian"] = mondrian
        return bundle, Calibrated(
            True, True, fit_rows.height, cal_rows.height, int(cal_rows["y"].sum()), None
        )
    return bundle, Calibrated(
        True,
        False,
        fit_rows.height,
        cal_rows.height,
        int(cal_rows["y"].sum()),
        "class_too_small_for_mondrian",
    )


def predict_sets(bundle: dict[str, Any], frame: pl.DataFrame) -> pl.DataFrame:
    """Which classes each subject's conformal set contains, per method, class-conditional first.

    Returns `in_set_0` and `in_set_1` from the Mondrian wrapper when present — the columns the
    contract's coverage claim is measured on — plus `_plain_set0`/`_plain_set1` so
    `calibration.parquet` can show why the class-conditional method exists. An empty set is a real
    outcome, not an error: it means this subject looks like neither class, and it is what the
    abstain rate counts.
    """
    X = frame.select(MODEL_FEATURES).to_numpy()
    alpha = 1.0 - float(bundle["coverage_target"])
    n = X.shape[0]

    if bundle.get("mondrian") is not None:
        mondrian: Any = bundle["mondrian"]
        sets = np.zeros((n, 2), dtype=bool)
        for k in (0, 1):
            if n:
                _, ps = mondrian.predict(X, partition=np.full(n, k, dtype=np.int64), alpha=alpha)
                sets[:, k] = ps[:, k, 0]
    else:
        # Without the Mondrian wrapper the plain sets are the only ones there are, and reporting
        # them under both names says so honestly: the report's coverage table then shows one
        # method, not a comparison that never ran.
        sets = _plain_sets(bundle, X, alpha)

    plain = _plain_sets(bundle, X, alpha)
    return pl.DataFrame(
        {
            "in_set_0": sets[:, 0],
            "in_set_1": sets[:, 1],
            "_plain_set0": plain[:, 0],
            "_plain_set1": plain[:, 1],
        }
    )


def _plain_sets(bundle: dict[str, Any], X: np.ndarray, alpha: float) -> np.ndarray:
    """The unpartitioned LAC sets. Returns all-true when no calibrator was fitted."""
    plain: Any = bundle.get("plain")
    n = X.shape[0]
    if plain is None or n == 0:
        return np.ones((n, 2), dtype=bool)
    _, ps = plain.predict(X, alpha=alpha)
    return np.asarray(ps[:, :, 0], dtype=bool)


def risk_scores(bundle: dict[str, Any], frame: pl.DataFrame) -> np.ndarray:
    """The booster's P(illicit), one per subject. The raw model output, before any set logic."""
    booster: Any = bundle["booster"]
    return np.asarray(booster.predict(frame.select(MODEL_FEATURES).to_numpy()), dtype="float64")


def top_shap(bundle: dict[str, Any], frame: pl.DataFrame) -> list[list[dict[str, Any]]]:
    """Top-`TOP_FEATURES` SHAP pairs per subject, ordered by absolute value.

    `TreeExplainer` on a native binary booster returns one value matrix (marginal contribution to
    the log-odds of class 1) with a deprecation warning about lists; indexing element `[0]` handles
    both shapes, because 0.46 returns a length-1 list and a plain array behaves identically under
    that index. Struct field names are `name`/`value` per contract section 7.
    """
    import shap

    booster: Any = bundle["booster"]
    X = frame.select(MODEL_FEATURES).to_numpy()
    values = np.asarray(shap.TreeExplainer(booster).shap_values(X))
    if values.ndim == 3:
        values = values[0]
    if values.ndim == 1:
        values = values.reshape(1, -1)

    names = list(MODEL_FEATURES)
    out: list[list[dict[str, Any]]] = []
    for row in values:
        order = sorted(range(len(names)), key=lambda i: (-abs(float(row[i])), names[i]))
        out.append(
            [{"name": names[i], "value": round(float(row[i]), 6)} for i in order[:TOP_FEATURES]]
        )
    return out
