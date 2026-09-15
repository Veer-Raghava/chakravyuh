"""The estimators. Two are built: `first_spy` for pass one, `ensemble` for pass two.

Pass one exists to be beaten. It ranks candidates by first-seen time and nothing else, which is
what an investigator gets for free, and its accuracy is recorded before any better model exists so
that every later version has a number to clear rather than a feeling to appeal to.

Pass two is a gradient-boosted model over the observable features, calibrated by isotonic
regression on a slice of the training window that the model never saw, with abstention inside it
rather than bolted on afterwards. Labels arrive already restricted to the training window by
`chakravyuh.eval.labels`; this module takes them as an ordinary frame and has no idea where they
came from, which is the point of the door.

The three honesty rules of contract section 6 are enforced in `_finalise`, once, for every
estimator, so a new estimator cannot forget one:

  p_origin is capped, never renormalised. A transaction whose candidate probabilities sum to 0.31
  keeps 0.31. Only a sum above one is scaled, and only down to one, because the contract's ceiling
  is a ceiling and the shortfall below it is the file saying "probably none of these".
  An abstaining transaction has no rank one row. Ranks are shifted to start at two, which keeps
  the ordering legible without ever letting a refusal look like an accusation.
  Ties break on `row_id`, so two interpreters agree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl

from chakravyuh.shastra.schema import FEATURES_SCHEMA, MODEL_FEATURES

# `first_spy` has no information to calibrate with, so its probabilities are a stated assumption
# rather than a measurement: belief halves with each step down the first-seen ordering. The series
# 0.5, 0.25, 0.125 ... sums below one for any number of candidates, so the contract's ceiling holds
# without a cap ever firing. Nothing about pass one's accuracy depends on these two constants: the
# accuracy is a property of the ordering, and the numbers exist so the column is populated and the
# margin is defined.
BASELINE_P1 = 0.5
BASELINE_DECAY = 0.5

# Below this many labelled candidate rows, or with only one class present, there is nothing to
# learn and the model would be fitting noise. The stage falls back to the strongest observable rule
# and records a warning, which is also the path taken when the answer key has been moved away.
MIN_TRAIN_ROWS = 200

# Below this many calibration rows Platt scaling is fitting a two-parameter curve to noise, so the
# booster's own sigmoid is shipped uncalibrated and `_meta.json` says so.
MIN_CALIBRATION_ROWS = 50

# LightGBM's native parameter names, and its native `train` entry point rather than the
# scikit-learn wrapper. The wrapper in LightGBM 4.5.0 calls `sklearn.utils.check_X_y` with
# `force_all_finite`, a keyword scikit-learn 1.9 removed, so `LGBMClassifier.fit` raises on this
# machine. The native API does not touch scikit-learn at all, which is also one fewer version
# coupling in an offline tool that must still build in a year.
BOOST_ROUNDS = 300
TREE_PARAMS: dict[str, Any] = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 40,
    "lambda_l2": 1.0,
    "feature_fraction": 1.0,
    "bagging_fraction": 1.0,
    # Determinism, not speed. `make verify-s06` runs the stage in two separate interpreters and
    # compares the bytes, so a model whose split choices depend on thread scheduling would fail
    # that gate rather than quietly produce two different answers in the field.
    "num_threads": 1,
    "deterministic": True,
    "force_row_wise": True,
    "verbose": -1,
    "seed": 0,
}

# Share of the training window kept back from the model and used to fit the calibrator. Split by
# time rather than at random, so the calibrator is fitted on transactions later than the ones the
# model saw, which is the situation it will be used in.
CALIBRATION_SHARE = 0.25


@dataclass(frozen=True)
class Fit:
    """What pass two did, so `_meta.json` can record it and a warning can name the fallback."""

    trained: bool
    n_train_rows: int
    n_train_txids: int
    n_positive: int
    n_calibration_rows: int
    calibrated: bool
    reason: str | None


def _decay_scores(order: pl.Expr) -> pl.Expr:
    """`BASELINE_P1 * BASELINE_DECAY ** position`, `position` zero-based within the transaction."""
    return pl.lit(BASELINE_P1) * pl.lit(BASELINE_DECAY) ** order


def _finalise(
    scored: pl.DataFrame,
    *,
    estimator: str,
    margin_floor: float,
    min_announcements: int,
) -> pl.DataFrame:
    """Rank, cap, measure the margin, decide abstention. The only place those four happen.

    `scored` carries the feature columns, `row_id`, `n_observers_in_tx` and a `p_origin` column
    that has not yet been capped. Returns the same rows plus `rank`, `margin`, `abstain` and
    `abstain_reason`, ordered by txid then rank so the written file is order-independent.

    The margin of a transaction with one candidate is that candidate's `p_origin`, because there is
    no rank two and zero is the honest value for a probability nobody assigned.

    `margin_floor` is applied to the *separation* of the top two, `(p1 - p2) / (p1 + p2)`, not to
    the absolute margin the contract's column carries. A calibrated probability is on the scale of
    the base rate, and the base rate here is the share of transactions whose originator is even in
    the candidate set: 0.049 at observer_fraction 0.10 against 0.415 at 0.70. An absolute floor of
    0.04 therefore abstains on every transaction in one world and on none in another, which is a
    threshold measuring the world rather than the evidence. The separation is scale-free, is zero
    exactly when the top two are tied and one when the leader stands alone, so one configured number
    means the same thing in all five sweep worlds.
    """
    ranked = scored.with_columns(
        pl.col("p_origin").sum().over("txid").alias("_sum"),
    ).with_columns(
        # A cap, not a normalisation. Sums at or below one are untouched, which is where the
        # "none of these peers is the originator" information lives.
        pl.when(pl.col("_sum") > 1.0)
        .then(pl.col("p_origin") / pl.col("_sum"))
        .otherwise(pl.col("p_origin"))
        .alias("p_origin")
    )
    runner_up = (
        pl.when(pl.col("n_candidates") > 1)
        .then(pl.col("p_origin").shift(-1).first().over("txid"))
        .otherwise(0.0)
    )
    ranked = (
        ranked.sort(["txid", "p_origin", "row_id"], descending=[False, True, False])
        .with_columns(pl.int_range(pl.len()).over("txid").alias("_position"))
        .with_columns(
            (pl.col("p_origin").first().over("txid") - runner_up).alias("margin"),
            (pl.col("p_origin").first().over("txid") + runner_up).alias("_pair"),
        )
        .with_columns(
            # Zero when the model gave the whole transaction no probability at all, which is a
            # refusal and not a tie for first place.
            pl.when(pl.col("_pair") > 0.0)
            .then(pl.col("margin") / pl.col("_pair"))
            .otherwise(0.0)
            .alias("_separation")
        )
    )

    tor = pl.col("is_tor_exit").any().over("txid")
    announcements = pl.col("n_announcements").sum().over("txid")
    reason = (
        # Priority, most specific first. A transaction one observer heard once trips three of
        # these; the reason recorded is the one that tells an analyst the most.
        pl.when(tor)
        .then(pl.lit("tor_present"))
        .when(pl.col("n_observers_in_tx") <= 1)
        .then(pl.lit("single_observer"))
        .when(announcements < min_announcements)
        .then(pl.lit("too_few_announcements"))
        .when(pl.col("_separation") < margin_floor)
        .then(pl.lit("margin_below_floor"))
        .otherwise(pl.lit(None, dtype=pl.String()))
        .alias("abstain_reason")
    )
    return (
        ranked.with_columns(reason)
        .with_columns(pl.col("abstain_reason").is_not_null().alias("abstain"))
        .with_columns(
            # Contract section 6: an abstaining transaction has no rank 1 row. Shifted rather than
            # zeroed so the ordering survives for a consumer who wants to see what was considered.
            (pl.col("_position") + 1 + pl.col("abstain").cast(pl.Int32()))
            .cast(pl.Int32())
            .alias("rank"),
            pl.lit(estimator).alias("estimator"),
        )
        .drop("_sum", "_position", "_pair", "_separation")
        .sort("txid", "rank")
    )


def first_spy(
    candidates: pl.DataFrame, *, margin_floor: float, min_announcements: int
) -> pl.DataFrame:
    """Pass one. Rank by first-seen time, tie-break on capture position, and nothing else.

    This is the number every later version must beat, and it is deliberately not clever: no peer
    prior, no payer linkage, no model. `delta_first_us` ascending is the whole rule.
    """
    scored = (
        candidates.sort(["txid", "delta_first_us", "row_id"])
        .with_columns(pl.int_range(pl.len()).over("txid").alias("_order"))
        .with_columns(_decay_scores(pl.col("_order")).alias("p_origin"))
        .drop("_order")
    )
    return _finalise(
        scored,
        estimator="first_spy",
        margin_floor=margin_floor,
        min_announcements=min_announcements,
    )


def _heuristic(candidates: pl.DataFrame) -> pl.DataFrame:
    """The fallback ordering when there is nothing to learn from: payer linkage, then first-seen.

    Not a guess at what the model would have done. It is the strongest rule available without
    labels, which is the honest thing to ship when the answer key has been moved away, and Law 2
    rule 6 requires inference to complete in that state rather than fail.
    """
    return (
        candidates.sort(
            ["txid", "payer_shared", "delta_first_us", "row_id"],
            descending=[False, True, False, False],
        )
        .with_columns(pl.int_range(pl.len()).over("txid").alias("_order"))
        .with_columns(_decay_scores(pl.col("_order")).alias("p_origin"))
        .drop("_order")
    )


def _train(train_rows: pl.DataFrame, seed: int) -> tuple[Any, Any, int]:
    """Fit the tree on the early part of the training window and the calibrator on the late part.

    Returns the fitted booster, the fitted calibrator or None, and the number of calibration rows.
    Split by transaction time, never at random: a calibrator fitted on rows interleaved with the
    model's own training rows measures how well the model memorised, not how well it is calibrated.

    Platt scaling, a logistic regression on the booster's log-odds, rather than isotonic regression.
    Isotonic was tried first and is the better calibrator with plenty of positives, but there are
    not plenty here: a capture at observer_fraction 0.10 yields around seventy positive rows in the
    training window and a quarter of that in the calibration slice, and isotonic's step function
    then collapses the whole score range onto a handful of levels. Two candidates of one transaction
    land on the same level, the ranking inside the transaction is destroyed, and every transaction
    looks like a tie for first place. Platt is strictly monotone, so it changes what the numbers
    mean without touching the order they are in.
    """
    import lightgbm as lgb
    from sklearn.linear_model import LogisticRegression

    ordered = train_rows.sort(["seen_us", "row_id"])
    cut = int(ordered.height * (1.0 - CALIBRATION_SHARE))
    fit_rows, cal_rows = ordered.head(cut), ordered.tail(ordered.height - cut)

    params = dict(TREE_PARAMS)
    params["seed"] = seed
    dataset = lgb.Dataset(
        fit_rows.select(MODEL_FEATURES).to_numpy(),
        label=fit_rows["y"].to_numpy(),
        feature_name=list(MODEL_FEATURES),
        params=params,
    )
    model = lgb.train(params, dataset, num_boost_round=BOOST_ROUNDS)

    if cal_rows.height < MIN_CALIBRATION_ROWS or cal_rows["y"].n_unique() < 2:
        return model, None, cal_rows.height
    raw = model.predict(cal_rows.select(MODEL_FEATURES).to_numpy(), raw_score=True)
    calibrator = LogisticRegression(solver="lbfgs", max_iter=1000)
    calibrator.fit(np.asarray(raw, dtype="float64").reshape(-1, 1), cal_rows["y"].to_numpy())
    return model, calibrator, cal_rows.height


def ensemble(
    candidates: pl.DataFrame,
    labels: pl.DataFrame | None,
    *,
    boundary_us: int | None,
    margin_floor: float,
    min_announcements: int,
    seed: int,
) -> tuple[pl.DataFrame, Fit]:
    """Pass two. A calibrated probability per candidate peer, with abstention built in.

    `labels` is `(txid, origin_peer_ip)` from `chakravyuh.eval.labels` and is already restricted to
    the training window; None means the answer key was absent. `boundary_us` is the same door's
    boundary and is re-applied here as a belt-and-braces mask over `seen_us`: if the door and this
    stage ever disagreed about where the window ends, the intersection is what gets trained on,
    which fails safe rather than training on the holdout.

    Returns the estimates and a `Fit` describing what actually happened, because "the model was
    trained" and "the fallback ran" produce the same shaped file and only the second is a warning.
    """
    if labels is None or labels.is_empty() or boundary_us is None:
        reason = "answer_key_absent" if labels is None else "no_labels_in_training_window"
        scored = _heuristic(candidates)
        fit = Fit(False, 0, 0, 0, 0, False, reason)
        return (
            _finalise(
                scored,
                estimator="ensemble",
                margin_floor=margin_floor,
                min_announcements=min_announcements,
            ),
            fit,
        )

    labelled = candidates.join(labels, on="txid", how="inner").with_columns(
        (pl.col("peer_ip") == pl.col("origin_peer_ip")).cast(pl.Int8()).alias("y")
    )
    train_rows = labelled.filter(pl.col("seen_us") < boundary_us)
    n_positive = int(train_rows["y"].sum()) if train_rows.height else 0
    n_txids = train_rows["txid"].n_unique() if train_rows.height else 0

    if train_rows.height < MIN_TRAIN_ROWS or n_positive == 0 or n_positive == train_rows.height:
        scored = _heuristic(candidates)
        fit = Fit(False, train_rows.height, n_txids, n_positive, 0, False, "too_few_labels")
        return (
            _finalise(
                scored,
                estimator="ensemble",
                margin_floor=margin_floor,
                min_announcements=min_announcements,
            ),
            fit,
        )

    model, calibrator, n_cal = _train(train_rows, seed)
    matrix = candidates.select(MODEL_FEATURES).to_numpy()
    if calibrator is None:
        probability = np.asarray(model.predict(matrix), dtype="float64")
    else:
        raw = np.asarray(model.predict(matrix, raw_score=True), dtype="float64")
        probability = calibrator.predict_proba(raw.reshape(-1, 1))[:, 1]
    scored = candidates.with_columns(
        pl.Series("p_origin", np.asarray(probability, dtype="float64"), dtype=pl.Float64())
    )
    fit = Fit(
        trained=True,
        n_train_rows=train_rows.height,
        n_train_txids=int(n_txids),
        n_positive=n_positive,
        n_calibration_rows=n_cal,
        calibrated=calibrator is not None,
        reason=None,
    )
    return (
        _finalise(
            scored,
            estimator="ensemble",
            margin_floor=margin_floor,
            min_announcements=min_announcements,
        ),
        fit,
    )


def to_contract(estimates: pl.DataFrame) -> pl.DataFrame:
    """Fold the flat feature columns into the `features` struct contract section 6 asks for."""
    return estimates.with_columns(
        pl.struct([pl.col(name) for name in FEATURES_SCHEMA]).alias("features")
    )
