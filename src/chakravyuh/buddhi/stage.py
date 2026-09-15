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
from chakravyuh.buddhi import features, model
from chakravyuh.buddhi.features import MODEL_FEATURES

INPUT_ROOT: Final[str] = "data"
OUTPUT_ROOT: Final[str] = "data/generated"
OUT_DIR: Final[str] = "scores"
REQUIRED_TABLES: Final[tuple[str, ...]] = ("transactions.parquet", "addresses.parquet")
SIGNALS_DIR: Final[str] = "signals"
SIGNALS_TABLE: Final[str] = "origin_estimates.parquet"
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

MODEL_NAME: Final[str] = "lightgbm_v1"
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


def build_run(
    run_dir: Path,
    out: Path,
    *,
    labels: pl.DataFrame | None,
    boundary_us: int | None,
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
    rows = {
        "transactions.parquet": transactions.height,
        "addresses.parquet": addresses.height,
        "clusters.parquet": clusters.height,
        "edges.parquet": edges.height,
        SIGNALS_TABLE: origin_estimates.height,
    }

    # No boundary means no window can be called train, which cannot leak because nothing trains.
    resolved_boundary = boundary_us if boundary_us is not None else 0
    subject_table = features.build(
        transactions, clusters, addresses, edges, origin_estimates, resolved_boundary
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
            "_order", "y", *MODEL_FEATURES
        )
    else:
        train_frame = (
            train_subjects.head(0)
            .with_columns(pl.lit(None, dtype=pl.Int64).alias("y"))
            .select("_order", "y", *MODEL_FEATURES)
        )

    bundle, calibrated = model.fit(
        train_frame, seed=config.seed, coverage_target=config.coverage_target
    )
    scored = subject_table.select("subject_id", "is_train", *MODEL_FEATURES)
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

    warnings: list[str] = []
    if not calibrated.trained:
        warnings.append(f"model_untrained_{calibrated.reason}")
    elif not calibrated.mondrian:
        warnings.append(f"conformal_plain_only_{calibrated.reason}")

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

    # What the eval side scores: holdout subjects only, with no `label` column anywhere in it.
    holdout_predictions = (
        out_frame.filter(~scored["is_train"])
        .select(
            "subject_id",
            "addresses",
            "risk_score",
            "in_set_0",
            "in_set_1",
        )
        .with_columns((~(pl.col("in_set_0") | pl.col("in_set_1"))).alias("abstain"))
    )

    wallet_output = pl.DataFrame(
        {
            "subject_id": out_frame["subject_id"],
            "risk_score": out_frame["risk_score"].to_list(),
            "label": [
                _row_label(s0, s1)
                for s0, s1 in zip(out_frame["in_set_0"], out_frame["in_set_1"], strict=True)
            ],
            "conf_low": [0.0 if s0 else 1.0 for s0 in out_frame["in_set_0"]],
            "conf_high": [1.0 if s1 else 0.0 for s1 in out_frame["in_set_1"]],
            "coverage_target": [config.coverage_target] * out_frame.height,
            "model": [MODEL_NAME] * out_frame.height,
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
