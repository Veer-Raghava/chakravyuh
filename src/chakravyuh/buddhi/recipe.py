"""The dataset-agnostic risk recipe: one train + calibrate + score procedure, called by both
the BUDDHI stage (our morphological features) and eval/external (Elliptic's features). The sole
thing that varies between datasets is the (X, y, time_index) triple handed in; every LightGBM
param, the time-ordered split, and the conformal wrap are identical here.

`model.fit` shares this file's conformal core (`_mondrian_ok`, `_fit_calibrators`) so the two
callers cannot drift: the class-conditional wrapper is defined once. `model.fit` keeps its own
booster training and bundle assembly because it holds no test set — its input is already the
train window and it must return the fitted objects for `predict_sets` to score the world — and
so its byte-for-byte determinism gate is untouched by this extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from chakravyuh.buddhi import model
from chakravyuh.eval import split

if TYPE_CHECKING:
    import lightgbm as lgb


@dataclass(frozen=True)
class RecipeResult:
    scores: np.ndarray
    y_test: np.ndarray
    in_set_1: np.ndarray
    boundary: float
    n_train: int
    n_test: int
    n_positive_train: int
    calibrated: model.Calibrated


def _mondrian_ok(y_cal: np.ndarray) -> bool:
    """Both classes present in the calibration tail with >= MIN_CALIBRATION_PER_CLASS members.

    The numpy statement of the same decision `model.fit` makes over polars: a class with too few
    calibration members cannot support an honest class-conditional quantile, so the partition is
    refused.
    """
    y_cal = np.asarray(y_cal)
    if y_cal.size == 0:
        return False
    classes, counts = np.unique(y_cal, return_counts=True)
    return set(classes.tolist()) == {0, 1} and bool(
        (counts >= model.MIN_CALIBRATION_PER_CLASS).all()
    )


def _fit_calibrators(
    booster: lgb.Booster, X_cal: np.ndarray, y_cal: np.ndarray, *, mondrian_ok: bool
) -> tuple[Any, Any]:
    """Fit the prefit MAPIE plain (LAC) and, when `mondrian_ok`, class-conditional (MondrianCP)
    calibrators around an already-trained booster.

    The one place the conformal wrap is built, shared by `model.fit` and `train_and_score`. The
    calibration arrays are handed straight to MAPIE exactly as `model.fit` handed them, so the
    quantiles — and therefore the sets `predict_sets` reads back — are byte-identical. Returns
    `(plain, mondrian_or_None)`.
    """
    model._patch_mapie_tags()
    from mapie.classification import MapieClassifier
    from mapie.mondrian import MondrianCP

    classifier = model._BoosterClassifier(booster)
    plain = MapieClassifier(estimator=classifier, method="lac", cv="prefit")
    plain.fit(X_cal, y_cal)
    mondrian = None
    if mondrian_ok:
        mondrian = MondrianCP(
            mapie_estimator=MapieClassifier(estimator=classifier, method="lac", cv="prefit")
        )
        mondrian.fit(X_cal, y_cal, partition=y_cal)
    return plain, mondrian


def _conformal_illicit_flag(
    booster: lgb.Booster,
    X_cal: np.ndarray,
    y_cal: np.ndarray,
    X_te: np.ndarray,
    *,
    coverage_target: float,
    mondrian_ok: bool,
) -> tuple[np.ndarray | None, bool]:
    """The class-1 conformal membership for the test rows, mirroring `predict_sets`.

    MondrianCP's class-1 column when the calibration tail supports it, else plain LAC's. Returns
    `(None, False)` when the calibration slice is too small to fit any calibrator — the same floor
    `model.fit` refuses on — so the caller falls back to a 0.5 threshold. The second element says
    whether the class-conditional partition was used.
    """
    y_cal = np.asarray(y_cal)
    if y_cal.size < model.MIN_CALIBRATION_ROWS or np.unique(y_cal).size < 2:
        return None, False

    plain, mondrian = _fit_calibrators(booster, X_cal, y_cal, mondrian_ok=mondrian_ok)
    alpha = 1.0 - float(coverage_target)
    X_te = np.asarray(X_te, dtype="float64")
    n = X_te.shape[0]
    if mondrian is not None:
        if n == 0:
            return np.zeros(0, dtype=bool), True
        _, ps = mondrian.predict(X_te, partition=np.full(n, 1, dtype=np.int64), alpha=alpha)
        return np.asarray(ps[:, 1, 0], dtype=bool), True
    if n == 0:
        return np.zeros(0, dtype=bool), False
    _, ps = plain.predict(X_te, alpha=alpha)
    return np.asarray(ps[:, 1, 0], dtype=bool), False


def train_and_score(
    X: np.ndarray,
    y: np.ndarray,
    time_index: np.ndarray,
    *,
    train_fraction: float,
    seed: int,
    coverage_target: float,
) -> RecipeResult:
    """Train a booster, wrap it in class-conditional conformal, and score the holdout — the whole
    procedure on one `(X, y, time_index)` triple, split by time exactly as the BUDDHI stage is.

    Rows are stably sorted by `time_index` (ties keep input order) before the split, so two
    interpreters cannot disagree. `train_fraction` cuts train from test at `split.boundary_us`;
    within train, `model.CALIBRATION_SHARE` cuts the booster's fit rows from the calibrator's.
    """
    import lightgbm as lgb

    time_index = np.asarray(time_index)
    order = np.argsort(time_index, kind="stable")  # stable so ties keep input order
    X = np.asarray(X, dtype="float64")[order]
    y = np.asarray(y)[order]
    t = time_index[order]

    boundary = split.boundary_us(int(t.min()), int(t.max()), train_fraction)
    is_train = t < boundary
    X_tr, y_tr = X[is_train], y[is_train]
    X_te, y_te = X[~is_train], y[~is_train]

    # Fit/calibration sub-split inside train, by time, exactly as model.fit does.
    cut = int(X_tr.shape[0] * (1.0 - model.CALIBRATION_SHARE))
    X_fit, y_fit = X_tr[:cut], y_tr[:cut]
    X_cal, y_cal = X_tr[cut:], y_tr[cut:]

    params = dict(model.TREE_PARAMS)
    params["seed"] = seed
    booster = lgb.train(
        params,
        lgb.Dataset(X_fit, label=y_fit, params=params),
        num_boost_round=model.BOOST_ROUNDS,
    )
    scores = np.asarray(booster.predict(X_te), dtype="float64")

    mondrian_ok = _mondrian_ok(y_cal)
    flag, used_mondrian = _conformal_illicit_flag(
        booster, X_cal, y_cal, X_te, coverage_target=coverage_target, mondrian_ok=mondrian_ok
    )
    in_set_1 = flag if flag is not None else (scores >= 0.5)

    if flag is None:
        reason: str | None = "too_few_calibration_rows"
    elif used_mondrian:
        reason = None
    else:
        reason = "class_too_small_for_mondrian"
    calibrated = model.Calibrated(
        trained=True,
        mondrian=used_mondrian,
        n_train=int(X_tr.shape[0]),
        n_calibration=int(X_cal.shape[0]),
        n_positive=int(np.asarray(y_cal).sum()),
        reason=reason,
    )
    return RecipeResult(
        scores=scores,
        y_test=np.asarray(y_te, dtype="int64"),
        in_set_1=np.asarray(in_set_1, dtype=bool),
        boundary=float(boundary),
        n_train=int(X_tr.shape[0]),
        n_test=int(X_te.shape[0]),
        n_positive_train=int(np.asarray(y_tr).sum()),
        calibrated=calibrated,
    )
