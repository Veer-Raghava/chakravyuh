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

# `timing_mle` turns a per-candidate source log-likelihood into a probability by softmax against a
# phantom "none of these" candidate held one nat below the best. The escape keeps the per-txid sum
# strictly below one whatever the candidate count, which is the contract's shortfall = "maybe the
# source was a peer no observer heard": a stated modelling assumption exactly like BASELINE_P1, not
# a measured number. The ordering, which is what the accuracy is a property of, does not depend on
# it. `MLE_MIN_MEAN_US` floors the relay-delay mean so a hand-built fixture recording a zero mean
# cannot divide by zero; a real run's mean is seconds.
MLE_ESCAPE_LOG_GAP = 1.0
MLE_MIN_MEAN_US = 1.0
MLE_EPS = 1e-12

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


def _mle_scores(candidates: pl.DataFrame, arrival: pl.DataFrame, mean_us: float) -> pl.DataFrame:
    """Per-candidate source log-likelihood from the arrival matrix and the relay-delay mean.

    Returns `(txid, peer_ip, _mle)` where `_mle` is, up to a per-transaction constant, the log of
    the probability that the observed first-arrivals were produced by this peer being the source.
    The model is the one MAYAJAAL propagates under and this function does not alter: every hop is an
    independent exponential delay of mean `mean_us`, so an observer's first hearing of the source is
    its broadcast instant plus a shifted exponential.

    Three terms, each a piece of that likelihood, all in units of relay delays so `mean_us` is the
    only scale:

      earliness         `-lead / mean`, where `lead` is how far this peer's earliest observed
                        sighting sits behind the transaction's earliest sighting by anyone. The
                        true source is early; a peer first heard a full relay delay after the
                        front is one delay less likely to be it.
      consistency       `-mean_dispersion / mean`, the average spread of this peer's sightings
                        across the observers that heard it. A source relays once to each observer,
                        so its arrivals cluster; a peer whose sightings are scattered is being
                        relayed through, not originating. Averaged over observers so a well-heard
                        peer is not penalised for being heard more.
      network prior     `m * log(frac_rank_one)`, how often this peer is the earliest an observer
                        sees network-wide, weighted by how many observers back it here. This is the
                        ASN/peer earliness the brief asks the estimator to fuse in.

    Computed from `arrival` rather than from the candidate summary columns because the per-observer
    times are the matrix the likelihood is defined over; the summaries are lossy views of it.
    """
    mean = max(mean_us, MLE_MIN_MEAN_US)
    tx_first = arrival.group_by("txid").agg(pl.col("seen_us").min().alias("_tx_first"))
    per_peer = (
        arrival.group_by("txid", "peer_ip")
        .agg(
            pl.col("observer_id").n_unique().alias("_m"),
            pl.col("seen_us").min().alias("_peer_first"),
            pl.col("seen_us").sum().alias("_seen_sum"),
        )
        .join(tx_first, on="txid", how="left")
        .with_columns(
            (pl.col("_peer_first") - pl.col("_tx_first")).alias("_lead"),
            # Σ(t - min) = Σt - m*min, then averaged over the m observers that heard this peer.
            ((pl.col("_seen_sum") - pl.col("_m") * pl.col("_peer_first")) / pl.col("_m")).alias(
                "_mean_disp"
            ),
        )
    )
    priors = candidates.select("txid", "peer_ip", pl.col("peer_frac_rank_one").alias("_prior"))
    return (
        per_peer.join(priors, on=["txid", "peer_ip"], how="left")
        .with_columns(pl.col("_prior").fill_null(0.0))
        .with_columns(
            (
                pl.col("_m") * (pl.col("_prior") + MLE_EPS).log()
                - pl.col("_lead") / mean
                - pl.col("_mean_disp") / mean
            ).alias("_mle")
        )
        .select("txid", "peer_ip", "_mle")
    )


def _softmax_with_escape(scored: pl.DataFrame, score: str) -> pl.DataFrame:
    """Turn a per-candidate score into `p_origin`, softmax against a per-txid escape mass.

    The escape is a phantom candidate held `MLE_ESCAPE_LOG_GAP` below each transaction's best, so
    the probabilities sum strictly below one and the shortfall carries the "maybe none of these"
    the contract's un-renormalised sum is for. The subtraction of the per-txid max is numerical,
    not semantic: it cancels in the ratio, so the escape is always `exp(-gap)` relative to the
    leader.
    """
    escape = float(np.exp(-MLE_ESCAPE_LOG_GAP))
    return (
        scored.with_columns(pl.col(score).max().over("txid").alias("_smax"))
        .with_columns((pl.col(score) - pl.col("_smax")).exp().alias("_e"))
        .with_columns((pl.col("_e").sum().over("txid") + escape).alias("_denom"))
        .with_columns((pl.col("_e") / pl.col("_denom")).alias("p_origin"))
        .drop("_smax", "_e", "_denom")
    )


def attach_mle(
    candidates: pl.DataFrame, arrival: pl.DataFrame | None, *, relay_delay_us: float
) -> pl.DataFrame:
    """Add the `mle_logscore` column every downstream estimator reads, once.

    `arrival` is `chakravyuh.setu`'s `arrival.parquet`: `(txid, observer_id, peer_ip, seen_us)`,
    one row per observer per transaction. `relay_delay_us` is the mean of the exponential relay
    delay the world was propagated under, read from the run's config and never altered here. None
    or an empty matrix means the file was absent, and the column degrades to first-seen earliness
    so the two estimators that use it stay runnable on a hand-built fixture.

    Computed here and joined onto the candidate frame so `timing_mle` and `ensemble` share one score
    rather than each recomputing it, and so it lands in the `features` struct the contract persists.
    """
    if arrival is None or arrival.is_empty():
        mean = max(relay_delay_us, MLE_MIN_MEAN_US)
        return candidates.with_columns(
            (-pl.col("delta_first_us") / mean).cast(pl.Float64()).alias("mle_logscore")
        )
    mle = _mle_scores(candidates, arrival, relay_delay_us)
    return (
        candidates.join(mle, on=["txid", "peer_ip"], how="left")
        .with_columns(
            # A candidate with no arrival row is impossible for a matrix built from the same
            # announcements, but a left join keeps the set total if one ever is: the lowest score
            # in its transaction, so it ranks last rather than vanishing and tripping the coverage
            # check.
            pl.col("_mle")
            .fill_null(pl.col("_mle").min().over("txid"))
            .fill_null(0.0)
            .alias("mle_logscore")
        )
        .drop("_mle")
    )


def timing_mle(
    candidates: pl.DataFrame, *, margin_floor: float, min_announcements: int
) -> pl.DataFrame:
    """Multi-observer maximum-likelihood source estimate. Reads `mle_logscore` from `attach_mle`.

    The likelihood ranks candidates; `_softmax_with_escape` turns it into the contract's
    un-renormalised `p_origin`, and `_finalise` applies the shared cap, margin and abstention rules.
    Independently runnable: given a candidate frame carrying `mle_logscore`, it needs nothing else.
    """
    scored = _softmax_with_escape(candidates, "mle_logscore")
    return _finalise(
        scored,
        estimator="timing_mle",
        margin_floor=margin_floor,
        min_announcements=min_announcements,
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


def _top_two(scored: pl.DataFrame, key: str, score: str) -> pl.DataFrame:
    """Per-txid rank-1 and rank-2 of `key` by `score`, tie-broken on `key` for determinism.

    Returns one row per txid: the leader's key and score, and the runner-up's score (0.0 when the
    transaction has a single group). Shared by the ASN and country roll-ups so the two agree on how
    a leader and a margin are picked.
    """
    ranked = scored.sort(["txid", score, key], descending=[False, True, False]).with_columns(
        pl.int_range(pl.len()).over("txid").alias("_pos")
    )
    leader = ranked.filter(pl.col("_pos") == 0)
    runner = ranked.filter(pl.col("_pos") == 1).select("txid", pl.col(score).alias("_p2"))
    return leader.join(runner, on="txid", how="left").with_columns(pl.col("_p2").fill_null(0.0))


def asn_rollup(
    estimates: pl.DataFrame,
    peers: pl.DataFrame,
    asn_prior: pl.DataFrame,
    *,
    margin_floor: float,
    estimator: str = "ensemble",
) -> pl.DataFrame:
    """Lift a per-candidate estimate to the L1/L2 headline: one operator and region per transaction.

    `estimates` is a finalised per-candidate frame (`txid`, `peer_ip`, `p_origin`, `abstain`,
    `abstain_reason`), normally the ensemble's. `peers` carries each peer's observable `asn`,
    `as_org`, `net_class` and `geo_country`. `asn_prior` is SETU's `asn_rollup.parquet`, whose
    `frac_rank_one` is how often traffic on an ASN is the earliest an observer saw it network-wide.

    The reframe's core: candidate hosts collapse onto few operators, so summing candidate mass by
    ASN and weighting by the prior turns a guess no single host can carry into one an operator can.
    `p_asn` and `p_country` are capped by the same escape softmax `p_origin` uses, never
    renormalised, so the shortfall stays "maybe an operator no observer heard". A transaction the
    candidate estimate already refused for weak evidence (Tor, single observer, too few
    announcements) is refused at L1 for the same reason; one it answered can still be refused here,
    with `cross_asn_ambiguous`, when the shortlist mass splits across operators so no ASN stands
    alone.
    """
    tx_flags = estimates.group_by("txid", maintain_order=True).agg(
        pl.col("abstain").first().alias("_tx_abstain"),
        pl.col("abstain_reason").first().alias("_tx_reason"),
        pl.col("p_origin").max().alias("_leader_p"),
    )
    shortlist = (
        estimates.join(tx_flags.select("txid", "_leader_p"), on="txid", how="left")
        .filter(pl.col("p_origin") >= pl.col("_leader_p") * float(np.exp(-MLE_ESCAPE_LOG_GAP)))
        .group_by("txid", maintain_order=True)
        .agg(pl.len().cast(pl.Int32()).alias("shortlist_size"))
    )

    labelled = estimates.select("txid", "peer_ip", "p_origin").join(
        peers.select("peer_ip", "asn", "as_org", "net_class", "geo_country"),
        on="peer_ip",
        how="left",
    )
    prior = asn_prior.select("asn", pl.col("frac_rank_one").alias("_prior"))

    by_asn = (
        # maintain_order keeps the per-group float reduction single-threaded and so byte-identical
        # across interpreters, which `make verify-s06` compares; the per-transaction grain is small,
        # so the ordered path costs nothing that matters.
        labelled.group_by("txid", "asn", maintain_order=True)
        .agg(
            pl.col("p_origin").sum().alias("_mass"),
            pl.col("as_org").drop_nulls().first().alias("as_org"),
            pl.col("net_class").drop_nulls().first().alias("net_class"),
        )
        .join(prior, on="asn", how="left")
        .with_columns(
            (pl.col("_mass") * (pl.col("_prior").fill_null(0.0) + MLE_EPS)).alias("_score")
        )
    )
    by_asn = _softmax_with_escape(by_asn, "_score")
    asn_top = _top_two(by_asn, "asn", "p_origin").select(
        "txid",
        pl.col("asn").alias("origin_asn"),
        "as_org",
        "net_class",
        pl.col("p_origin").alias("p_asn"),
        "_p2",
    )

    by_country = labelled.group_by("txid", "geo_country", maintain_order=True).agg(
        pl.col("p_origin").sum().alias("_score")
    )
    by_country = _softmax_with_escape(by_country, "_score")
    country_top = _top_two(by_country, "geo_country", "p_origin").select(
        "txid",
        pl.col("geo_country").alias("origin_country"),
        pl.col("p_origin").alias("p_country"),
    )

    merged = (
        asn_top.join(country_top, on="txid", how="left")
        .join(shortlist, on="txid", how="left")
        .join(tx_flags, on="txid", how="left")
        .with_columns(
            (pl.col("p_asn") - pl.col("_p2")).alias("margin"),
            # Scale-free separation of the top two operators, the same shape the per-candidate
            # margin floor is applied to, so one configured number means one thing at both grains.
            pl.when((pl.col("p_asn") + pl.col("_p2")) > 0.0)
            .then((pl.col("p_asn") - pl.col("_p2")) / (pl.col("p_asn") + pl.col("_p2")))
            .otherwise(0.0)
            .alias("_sep"),
            pl.col("shortlist_size").fill_null(0),
        )
    )

    inherited = pl.col("_tx_abstain") & pl.col("_tx_reason").is_in(
        ["tor_present", "single_observer", "too_few_announcements"]
    )
    reason = (
        pl.when(inherited)
        .then(pl.col("_tx_reason"))
        .when(pl.col("_sep") < margin_floor)
        .then(pl.lit("cross_asn_ambiguous"))
        .otherwise(pl.lit(None, dtype=pl.String()))
        .alias("abstain_reason")
    )
    return (
        merged.with_columns(reason)
        .with_columns(
            pl.col("abstain_reason").is_not_null().alias("abstain"),
            pl.lit(estimator).alias("estimator"),
        )
        .drop("_p2", "_sep", "_tx_abstain", "_tx_reason", "_leader_p")
        .sort("txid")
    )


def to_contract(estimates: pl.DataFrame) -> pl.DataFrame:
    """Fold the flat feature columns into the `features` struct contract section 6 asks for."""
    return estimates.with_columns(
        pl.struct([pl.col(name) for name in FEATURES_SCHEMA]).alias("features")
    )
