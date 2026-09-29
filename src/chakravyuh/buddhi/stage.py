"""BUDDHI as a stage: read `signals/` and `graph/`, write `scores/`, account for every row.

The path guards are SHASTRA's, restated rather than imported, for the reason that rule exists:
`--in` is allowlisted to `data/`, so a BUDDHI invocation cannot be pointed at the answer key even
by an operator who wants to, because the answer key is a sibling tree and not under `data/`.

This module never imports `chakravyuh.eval` and never receives an evaluation-window label.
`__main__.py` hands it train-window `y` values as an ordinary column and takes the holdout
predictions back out; where those `y` came from is none of this file's business, which is what
keeps the stage a pure read of directories under `data/` and lets the two determinism runs agree
byte for byte whether or not scoring ran.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np
import polars as pl

from chakravyuh import buildinfo
from chakravyuh.buddhi import embed, features, model
from chakravyuh.buddhi.features import ALL_FEATURES, EMBEDDING_FEATURES, MODEL_FEATURES

INPUT_ROOT: Final[str] = "data"
OUTPUT_ROOT: Final[str] = "data/generated"
OUT_DIR: Final[str] = "scores"
REQUIRED_TABLES: Final[tuple[str, ...]] = ("transactions.parquet", "addresses.parquet")
SIGNALS_DIR: Final[str] = "signals"
SIGNALS_TABLE: Final[str] = "origin_estimates.parquet"
# The operator-grain headline SHASTRA ships beside the host-grain one. Absent in a world with no
# ASN substrate, which is why every read of it is a file-exists check rather than an assumption.
L1_TABLE: Final[str] = "origin_l1.parquet"
GRAPH_DIR: Final[str] = "graph"
GRAPH_TABLES: Final[tuple[str, ...]] = ("clusters.parquet", "edges.parquet")
CONFIG_NAME: Final[str] = "config.effective.json"

# Used only when the run directory has no `config.effective.json`, which happens in a hand-built
# fixture and nowhere else. A run made by MAYAJAAL always carries the world it was given.
DEFAULT_TRAIN_FRACTION: Final[float] = 0.7
DEFAULT_COVERAGE_TARGET: Final[float] = 0.9

# Subject-level risk vocabulary of contract section 7, decided here from observable quantities
# only: the conformal set and the raw score.
LABEL_LIKELY_ILICIT: Final[str] = "LIKELY_ILICIT"
LABEL_UNCLEAR: Final[str] = "UNCLEAR"
LABEL_LIKELY_LICIT: Final[str] = "LIKELY_LICIT"
LABEL_ABSTAIN: Final[str] = "ABSTAIN"

# The half-width of the displayed score interval, as a fraction of the score itself.
CONFORMAL_BAND: Final[float] = 0.15

MODEL_NAME: Final[str] = "gbm_v2"
# The booster that also sees the label-free graph embedding. `wallet_scores.parquet` records which
# of the two scored each row, so a run where only some subjects have a graph position says so in
# the data rather than in a footnote.
MODEL_NAME_GNN: Final[str] = "gbm_gnn_v2"
STAGE: Final[str] = "buddhi"


class InputPathError(ValueError):
    """A path BUDDHI will not read from, or will not write to."""


@dataclass(frozen=True)
class Settings:
    """The eval knobs this run was generated with, read back from the run rather than the repo."""

    train_fraction: float
    coverage_target: float
    seed: int
    from_config: bool


def settings(run_dir: Path) -> Settings:
    """The run's eval settings, falling back to the module defaults when it records none."""
    path = run_dir / CONFIG_NAME
    if not path.is_file():
        return Settings(DEFAULT_TRAIN_FRACTION, DEFAULT_COVERAGE_TARGET, 0, False)
    node = json.loads(path.read_text(encoding="utf-8"))
    block = node.get("eval", {})
    return Settings(
        train_fraction=float(block.get("train_fraction", DEFAULT_TRAIN_FRACTION)),
        coverage_target=float(block.get("coverage_target", DEFAULT_COVERAGE_TARGET)),
        seed=int(node.get("seed", 0)),
        from_config="eval" in node,
    )


def _relative_to_cwd(path: Path, root: str) -> Path:
    """`path` resolved, refused unless it sits inside `<cwd>/<root>`."""
    base = (Path.cwd() / root).resolve()
    resolved = path.resolve()
    if resolved != base and base not in resolved.parents:
        raise InputPathError(
            f"{path} resolves outside {base}. BUDDHI only reads and writes inside that "
            f"directory, which is how a stage input can never reach a sibling tree it has no "
            f"business in."
        )
    return resolved


def resolve_in(target: Path) -> Path:
    """The run directory whose `signals/`, `graph/` and `normalised/` BUDDHI reads."""
    resolved = _relative_to_cwd(target, OUTPUT_ROOT)
    missing_graph = [name for name in GRAPH_TABLES if not (resolved / GRAPH_DIR / name).is_file()]
    missing_signals = not (resolved / SIGNALS_DIR / SIGNALS_TABLE).is_file()
    if missing_graph or missing_signals:
        raise InputPathError(
            f"{target} is missing {', '.join(missing_graph)} or {SIGNALS_DIR}/{SIGNALS_TABLE}. "
            f"BUDDHI reads a run written by JAAL and SHASTRA: run `python -m chakravyuh.jaal` "
            f"and `python -m chakravyuh.shastra` first."
        )
    if not all((resolved / "normalised" / name).is_file() for name in REQUIRED_TABLES):
        raise InputPathError(
            f"{target}/normalised is missing {', '.join(REQUIRED_TABLES)}. BUDDHI reads the "
            f"capture SETU normalised: run `python -m chakravyuh.setu` first."
        )
    return resolved


def resolve_out(target: Path) -> Path:
    """The run directory to write `scores/` into."""
    resolved = _relative_to_cwd(target, OUTPUT_ROOT)
    if resolved == (Path.cwd() / OUTPUT_ROOT).resolve():
        raise InputPathError(
            f"--out must name a run directory inside {OUTPUT_ROOT}/, not {OUTPUT_ROOT}/ itself"
        )
    return resolved


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _write_parquet(frame: pl.DataFrame, path: Path) -> str:
    """Write, then hash what was written. Compression is pinned so two runs agree byte for byte."""
    frame.write_parquet(path, compression="zstd", compression_level=3, statistics=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _meta_link(directory: Path) -> tuple[str | None, str | None]:
    """Path and hash of a stage directory's `_meta.json`, for the staleness check."""
    candidate = directory / "_meta.json"
    if not candidate.is_file():
        return None, None
    return _repo_relative(candidate), hashlib.sha256(candidate.read_bytes()).hexdigest()


def _conf_bounds(risk_score: float, in_set_0: bool, in_set_1: bool) -> tuple[float, float]:
    """The `conf_low` / `conf_high` the console prints for one subject.

    A conformal set is a set of labels, not a probability range, so it cannot be read back as an
    interval: every alert's set is the single element `{1}`, which the old mapping turned into
    `(1.0, 1.0)` — a band that claims the calibration pinned the risk at certainty. The interval is
    therefore taken from the score, widened by `CONFORMAL_BAND`, and clamped to [0, 1]. The one
    case the score cannot speak to is the genuinely ambiguous set, which keeps the full interval.
    """
    if in_set_0 and in_set_1:
        return 0.0, 1.0
    score = min(max(float(risk_score), 0.0), 1.0)
    return max(0.0, score * (1.0 - CONFORMAL_BAND)), min(1.0, score * (1.0 + CONFORMAL_BAND))


def _row_label(in_set_0: bool, in_set_1: bool) -> str:
    """Section 7's `label`, from the conformal set alone.

    Both classes in the set is genuinely uncertain (`UNCLEAR`), neither is `ABSTAIN`, exactly one
    names the class. A high raw score outside the illicit set is still licit as far as the
    interval is concerned: the interval, not the score, is what the console displays.
    """
    if in_set_0 and in_set_1:
        return LABEL_UNCLEAR
    if not in_set_0 and not in_set_1:
        return LABEL_ABSTAIN
    return LABEL_LIKELY_ILICIT if in_set_1 else LABEL_LIKELY_LICIT


def _calibration_frame(
    bundle: dict[str, Any], scored: pl.DataFrame, coverage_target: float
) -> pl.DataFrame:
    """One row per class per calibration method, with the coverage the console quotes.

    Plain and class-conditional coverage are both measured on the calibration rows themselves,
    class by class, because that is what a conformal guarantee is a statement about: the same
    distribution the quantile was read from. The two methods' differing per-class numbers are
    why the Mondrian wrapper exists; where they agree, the wrapper was unnecessary but honest.
    `n_test` counts the subjects scored beyond the fit rows, so nobody mistakes this table for
    a holdout measurement — the holdout number lives in the eval side's model_report.
    """
    schema = {
        "class": pl.String(),
        "method": pl.String(),
        "target_coverage": pl.Float64(),
        "empirical_coverage": pl.Float64(),
        "n_calibration": pl.Int32(),
        "n_test": pl.Int32(),
        "imbalance_ratio": pl.String(),
    }
    if not bundle or bundle.get("plain") is None:
        return pl.DataFrame(schema=schema)

    cal: pl.DataFrame = bundle["calibration_rows"]
    cal_sets = model.predict_sets(bundle, cal)
    n_test = max(0, scored.height - bundle["n_fit_rows"])
    n_pos = int(cal["y"].sum())
    ratio = f"1:{max(1, round((cal.height - n_pos) / max(1, n_pos)))}"

    rows: list[dict[str, Any]] = []
    for class_name in ("0", "1"):
        k = int(class_name)
        mask = cal["y"] == k
        for method, column in (
            ("plain_conformal", "_plain_set0" if k == 0 else "_plain_set1"),
            ("class_conditional", "in_set_0" if k == 0 else "in_set_1"),
        ):
            member_rows = cal_sets.filter(mask)
            coverage = (
                float(member_rows[column].mean())  # type: ignore[arg-type]
                if member_rows.height
                else 0.0
            )
            rows.append(
                {
                    "class": class_name,
                    "method": method,
                    "target_coverage": coverage_target,
                    "empirical_coverage": round(coverage, 6),
                    "n_calibration": int(mask.sum()),
                    "n_test": n_test,
                    "imbalance_ratio": ratio,
                }
            )
    return pl.DataFrame(rows, schema=schema)


def _embedding_complete(frame: pl.DataFrame) -> pl.Series:
    """One bool per row: this subject has every embedding column, so the GNN booster can score it.

    Read from the columns rather than from a flag column, because the columns are what the booster
    actually consumes: a row with a null in one direction cannot be scored by a model trained on
    eight, and a flag that said otherwise would be a flag that lies.
    """
    mask = pl.all_horizontal(pl.col(name).is_not_null() for name in EMBEDDING_FEATURES)
    return frame.select(mask.alias("_embedded"))["_embedded"]


def build_run(
    run_dir: Path,
    out: Path,
    *,
    labels: pl.DataFrame | None,
    boundary_us: int | None,
    use_embeddings: bool = False,
) -> tuple[Path, pl.DataFrame | None]:
    """Build `<out>/scores/` from the run's `normalised/`, `graph/` and `signals/`.

    `run_dir` and `out` are already resolved and guarded by the caller, and are the same
    directory in every normal invocation: BUDDHI reads a run's observable trees and writes its
    scores back into it, because `scores/` sits beside `signals/` in the contract's layout.
    `labels` is train-window `(address, y)` handed over by `__main__.py`, or None when the
    answer key is absent, in which case inference still completes and every subject is scored
    by the best model the observable data allows. `boundary_us` is the window boundary in
    microseconds; None means no boundary was derived and nothing can be called train.

    Returns the `_meta.json` path and the holdout subjects' predictions (`subject_id`,
    `addresses`, `risk_score`, `in_set_0`, `in_set_1`, `abstain`) for `__main__.py` to hand to
    `chakravyuh.eval.metrics`. The stage never sees what that call made of them.

    `use_embeddings` switches on the GNN leg: `features.build` then also produces the dual-graph
    embedding, and a second booster is trained over the subjects that have one. Rows the second
    booster cannot score keep the baseline model's verdict and say so in their `model` column. The
    leg's *credibility* is not decided here — the stage has no holdout labels to decide it with —
    so the predictions also carry the baseline booster's score for the same rows, and the eval side
    (which owns the labels) makes that call in `_eval_report`.
    """
    started_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    config = settings(run_dir)

    transactions = pl.read_parquet(
        run_dir / "normalised" / "transactions.parquet",
        columns=list(features.TRANSACTION_COLUMNS),
    )
    addresses = pl.read_parquet(
        run_dir / "normalised" / "addresses.parquet",
        columns=list(features.ADDRESS_COLUMNS) + ["first_seen_us"],
    )
    clusters = pl.read_parquet(
        run_dir / GRAPH_DIR / "clusters.parquet", columns=list(features.CLUSTER_COLUMNS)
    )
    edges = pl.read_parquet(
        run_dir / GRAPH_DIR / "edges.parquet", columns=list(features.EDGE_COLUMNS)
    )
    origin_estimates = pl.read_parquet(
        run_dir / SIGNALS_DIR / SIGNALS_TABLE,
        columns=list(features.ORIGIN_ESTIMATE_COLUMNS) + ["estimator"],
    )
    typology_hits = pl.read_parquet(
        run_dir / SIGNALS_DIR / "typology_hits.parquet",
        columns=["subject_id", "typology", "txids"],
    )
    # The operator-grain headline, when this run shipped one: a world with no ASN substrate writes
    # the file empty, and an empty frame is a null feature rather than a missing column.
    l1_path = run_dir / SIGNALS_DIR / L1_TABLE
    origin_l1 = (
        pl.read_parquet(l1_path, columns=list(features.ORIGIN_L1_COLUMNS))
        if l1_path.is_file()
        else None
    )
    rows = {
        "transactions.parquet": transactions.height,
        "addresses.parquet": addresses.height,
        "clusters.parquet": clusters.height,
        "edges.parquet": edges.height,
        SIGNALS_TABLE: origin_estimates.height,
        L1_TABLE: origin_l1.height if origin_l1 is not None else 0,
    }

    # No boundary means no window can be called train, which cannot leak because nothing trains.
    resolved_boundary = boundary_us if boundary_us is not None else 0
    feature_columns = MODEL_FEATURES + (EMBEDDING_FEATURES if use_embeddings else ())
    subject_table = features.build(
        transactions,
        clusters,
        addresses,
        edges,
        origin_estimates,
        resolved_boundary,
        typology_hits=typology_hits,
        origin_l1=origin_l1,
        use_embeddings=use_embeddings,
    )
    members = features.subjects(clusters, addresses)
    subject_addresses = members.group_by("subject_id", maintain_order=True).agg(
        pl.col("address").sort().alias("addresses")
    )
    # The model's time order, from the same first-activity quantity features.build windowed by.
    order_map = (
        members.join(addresses.select("address", "first_seen_us"), on="address", how="inner")
        .group_by("subject_id")
        .agg(pl.col("first_seen_us").min().alias("_order"))
    )

    y_by_address: dict[str, int] = {}
    if labels is not None and labels.height:
        y_by_address = dict(zip(labels["address"].to_list(), labels["y"].to_list(), strict=True))

    # The model sees only train-window subjects that carry at least one label, each with a
    # majority `y` over its labelled members — ties to zero, the same definition the eval side
    # scores holdout subjects with, so train and evaluation cannot disagree about what a label
    # means. `y` comes from the column handed in, and from nothing observable.
    train_subjects = (
        subject_table.filter(pl.col("is_train"))
        .join(order_map, on="subject_id", how="left")
        .with_columns(pl.col("_order").fill_null(0))
    )
    if y_by_address:
        labelled_members = members.join(
            pl.DataFrame({"address": list(y_by_address), "y": list(y_by_address.values())}),
            on="address",
            how="inner",
        )
        y_by_subject = labelled_members.group_by("subject_id", maintain_order=True).agg(
            (2 * pl.col("y").sum() > pl.len()).cast(pl.Int64).alias("y")
        )
        train_frame = train_subjects.join(y_by_subject, on="subject_id", how="inner").select(
            "_order", "y", *feature_columns
        )
    else:
        train_frame = (
            train_subjects.head(0)
            .with_columns(pl.lit(None, dtype=pl.Int64).alias("y"))
            .select("_order", "y", *feature_columns)
        )

    bundle, calibrated = model.fit(
        train_frame, seed=config.seed, coverage_target=config.coverage_target
    )
    # The GNN booster, over the train subjects the embedding actually covers. A subject with no
    # node in its window's graph is not a row with zeros — it is a row this model has no opinion
    # about, so it is excluded rather than imputed, and the baseline model answers for it below.
    gnn_bundle: dict[str, Any] = {}
    gnn_calibrated = model.Calibrated(False, False, 0, 0, 0, "embeddings_not_requested")
    n_train_with_embedding = 0
    if use_embeddings:
        covered = train_frame.filter(_embedding_complete(train_frame))
        n_train_with_embedding = covered.height
        gnn_bundle, gnn_calibrated = model.fit(
            covered,
            seed=config.seed,
            coverage_target=config.coverage_target,
            features=ALL_FEATURES,
        )

    scored = subject_table.select("subject_id", "is_train", *feature_columns)
    scores: list[float] | np.ndarray
    shap_values: list[list[dict[str, Any]]]
    if bundle:
        sets = model.predict_sets(bundle, scored)
        scores = model.risk_scores(bundle, scored)
        shap_values = model.top_shap(bundle, scored)
    else:
        # No trained model: section 7's rows must still exist with the exact schema, so every
        # subject gets the full interval and ABSTAIN — the honest statement "this run had
        # nothing to say", rather than a schema violation or a fabricated score.
        n = scored.height
        sets = pl.DataFrame(
            {
                "in_set_0": [True] * n,
                "in_set_1": [True] * n,
                "_plain_set0": [True] * n,
                "_plain_set1": [True] * n,
            }
        )
        scores = [0.5] * n
        shap_values = [[] for _ in range(n)]

    # The baseline booster's score for every subject, captured before the GNN overlay replaces any
    # of them. This is the counterfactual the eval side needs in order to say whether the embedding
    # leg earned its columns; the stage itself has no holdout label to judge that with.
    baseline_scores = np.asarray(scores, dtype="float64")

    warnings: list[str] = []
    if not calibrated.trained:
        warnings.append(f"model_untrained_{calibrated.reason}")
    elif not calibrated.mondrian:
        warnings.append(f"conformal_plain_only_{calibrated.reason}")

    # Which booster answered for each row, decided by the embeddings that row actually has.
    model_of_row = np.array([MODEL_NAME] * scored.height, dtype=object)
    if gnn_bundle:
        on_gnn = _embedding_complete(scored).to_numpy()
        if on_gnn.any():
            subset = scored.filter(pl.Series(on_gnn))
            gnn_sets = model.predict_sets(gnn_bundle, subset)
            gnn_scores = model.risk_scores(gnn_bundle, subset)
            gnn_shap = model.top_shap(gnn_bundle, subset)
            sets = sets.with_columns(
                [
                    pl.when(pl.Series(on_gnn)).then(gnn_sets[column]).otherwise(pl.col(column))
                    for column in ("in_set_0", "in_set_1", "_plain_set0", "_plain_set1")
                ]
            )
            scores = np.where(on_gnn, gnn_scores, scores)
            answered = iter(gnn_shap)
            shap_values = [
                next(answered) if on else row for on, row in zip(on_gnn, shap_values, strict=True)
            ]
            model_of_row[on_gnn] = MODEL_NAME_GNN
        else:
            warnings.append("no_subject_has_a_graph_embedding_gnn_booster_unused")
        if not gnn_calibrated.trained:
            warnings.append(f"gnn_model_untrained_{gnn_calibrated.reason}")
    elif use_embeddings:
        warnings.append("gnn_booster_not_trained_rows_fall_back_to_the_baseline_model")

    n_gnn_rows = int((model_of_row == MODEL_NAME_GNN).sum())
    if use_embeddings and n_gnn_rows == 0:
        warnings.append("gnn_requested_and_no_row_was_scored_by_it")

    out_frame = pl.DataFrame(
        {
            "subject_id": scored["subject_id"],
            "risk_score": scores,
            "in_set_0": sets["in_set_0"].to_list(),
            "in_set_1": sets["in_set_1"].to_list(),
            "_plain_set0": sets["_plain_set0"].to_list(),
            "_plain_set1": sets["_plain_set1"].to_list(),
        }
    ).join(subject_addresses, on="subject_id", how="left")
    if use_embeddings:
        out_frame = out_frame.with_columns(pl.Series("risk_score_baseline", baseline_scores))

    # What the eval side scores: holdout subjects only, with no `label` column anywhere in it.
    # `risk_score_baseline` travels with them so the eval side can score the same subjects by the
    # booster the run shipped without — it is not part of section 7 and never reaches
    # `wallet_scores.parquet`, which is built from `wallet_output` below.
    holdout_predictions = (
        out_frame.filter(~scored["is_train"])
        .select(
            "subject_id",
            "addresses",
            "risk_score",
            *(["risk_score_baseline"] if use_embeddings else []),
            "in_set_0",
            "in_set_1",
        )
        .with_columns((~(pl.col("in_set_0") | pl.col("in_set_1"))).alias("abstain"))
    )

    bounds = [
        _conf_bounds(score, s0, s1)
        for score, s0, s1 in zip(
            out_frame["risk_score"], out_frame["in_set_0"], out_frame["in_set_1"], strict=True
        )
    ]
    wallet_output = pl.DataFrame(
        {
            "subject_id": out_frame["subject_id"],
            "risk_score": out_frame["risk_score"].to_list(),
            "label": [
                _row_label(s0, s1)
                for s0, s1 in zip(out_frame["in_set_0"], out_frame["in_set_1"], strict=True)
            ],
            "conf_low": [low for low, _ in bounds],
            "conf_high": [high for _, high in bounds],
            "coverage_target": [config.coverage_target] * out_frame.height,
            "model": model_of_row.tolist(),
            "top_features": shap_values,
            "abstain": (~(out_frame["in_set_0"] | out_frame["in_set_1"])).to_list(),
        }
    )

    outputs = {
        "wallet_scores.parquet": wallet_output,
        "calibration.parquet": _calibration_frame(bundle, scored, config.coverage_target),
    }
    out_dir = out / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {name: _write_parquet(frame, out_dir / name) for name, frame in outputs.items()}

    signals_path, signals_hash = _meta_link(run_dir / SIGNALS_DIR)
    graph_path, graph_hash = _meta_link(run_dir / GRAPH_DIR)

    if not config.from_config:
        warnings.append("run_records_no_eval_block_stage_defaults_used")
    if signals_hash is None or graph_hash is None:
        warnings.append("upstream_meta_absent_no_staleness_link")
    if wallet_output.height != subject_table.height:
        warnings.append("subject_count_mismatch_between_feature_table_and_scores")
    if boundary_us is None:
        warnings.append("no_boundary_derived_nothing_trained")

    finished_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    meta: dict[str, Any] = {
        "stage": STAGE,
        "run_id": out.name,
        "started_at_us": started_at_us,
        "finished_at_us": finished_at_us,
        "code_version": buildinfo.code_version(),
        "seed": config.seed,
        "params": {
            "input": _repo_relative(run_dir),
            "upstream_meta": {"path": signals_path, "sha256": signals_hash},
            "graph_meta": {"path": graph_path, "sha256": graph_hash},
            "train_fraction": config.train_fraction,
            "coverage_target": config.coverage_target,
            "boundary_us": boundary_us,
            "model": (
                {
                    "kind": "lightgbm_binary_native_api",
                    "num_boost_round": model.BOOST_ROUNDS,
                    **model.TREE_PARAMS,
                    # The run's seed, not the module default, because that is what was fitted.
                    "seed": config.seed,
                }
                if calibrated.trained
                else None
            ),
            "calibration": "mondrian class-conditional conformal (LAC), plain LAC alongside",
            "fit": asdict(calibrated),
            # The GNN leg's own record, absent unless the leg ran. A reader asking "which model
            # produced this row" gets the answer twice: per row in `wallet_scores.parquet`'s
            # `model` column, and in aggregate here.
            "model_gnn": (
                {
                    "kind": "lightgbm_binary_native_api",
                    "features": list(ALL_FEATURES),
                    "embedding": {
                        "source": "buddhi.embed.label_free_dual_graph",
                        "dim": embed.DIM,
                        "hops": embed.HOPS,
                    },
                    "n_train_with_embedding": n_train_with_embedding,
                    "n_rows_scored": n_gnn_rows,
                    "num_boost_round": model.BOOST_ROUNDS,
                    **model.TREE_PARAMS,
                    "seed": config.seed,
                }
                if gnn_bundle
                else None
            ),
            "fit_gnn": asdict(gnn_calibrated) if use_embeddings else None,
            "label_policy": (
                "UNCLEAR when both conformal classes are in the set, ABSTAIN when neither, "
                "otherwise the class the set names"
            ),
            "window_policy": (
                "a train subject's features come from pre-boundary transactions, a holdout "
                "subject's from post-boundary only; cluster shape is windowed the same way"
            ),
            "counts_grain": "subjects, one row per predicted cluster or singleton address",
        },
        "inputs": [
            {
                "path": _repo_relative(run_dir / "normalised" / name),
                "sha256": hashlib.sha256((run_dir / "normalised" / name).read_bytes()).hexdigest(),
                "rows": rows[name],
            }
            for name in sorted(REQUIRED_TABLES)
        ]
        + [
            {
                "path": _repo_relative(run_dir / GRAPH_DIR / name),
                "sha256": hashlib.sha256((run_dir / GRAPH_DIR / name).read_bytes()).hexdigest(),
                "rows": rows[name],
            }
            for name in sorted(GRAPH_TABLES)
        ]
        + [
            {
                "path": _repo_relative(run_dir / SIGNALS_DIR / SIGNALS_TABLE),
                "sha256": hashlib.sha256(
                    (run_dir / SIGNALS_DIR / SIGNALS_TABLE).read_bytes()
                ).hexdigest(),
                "rows": rows[SIGNALS_TABLE],
            }
        ],
        "outputs": [
            {"path": f"{OUT_DIR}/{name}", "sha256": hashes[name], "rows": outputs[name].height}
            for name in sorted(outputs)
        ],
        # The subject grain is one-to-one: every subject features.build produced is scored, so
        # nothing is dropped and the arithmetic is an identity worth asserting rather than a
        # reconciliation to explain.
        "counts": {
            "in": subject_table.height,
            "out": wallet_output.height,
            "dropped": 0,
            "drop_reasons": {},
        },
        "warnings": sorted(set(warnings)),
        "optional_deps": {"geolite2": False, "kuzu": False, "gpu": False},
    }
    meta_path = out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if calibrated.trained and wallet_output["abstain"].all():
        raise AssertionError(
            "a trained model abstained on every subject, which means the conformal sets "
            "collapsed; a run that says nothing about everything is a defect to investigate, "
            "not an output to publish."
        )
    return meta_path, holdout_predictions
