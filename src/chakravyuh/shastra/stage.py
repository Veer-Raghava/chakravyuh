"""SHASTRA as a stage: read `normalised/` and `graph/`, write `signals/`, account for every row.

The path guards are JAAL's, restated rather than imported, for the reason that rule exists: `--in`
is allowlisted to `data/`, so a SHASTRA invocation cannot be pointed at the answer key even by an
operator who wants to, because the answer key is a sibling tree and not under `data/`.

This module never imports `chakravyuh.eval`. Labels arrive as an ordinary frame from `__main__.py`,
which is not itself part of the pipeline, so `build_run` is a pure read of two directories under
`data/`. Nothing truth-derived is written: `signals/` carries no truth column and no accuracy
figure, which is what lets the two determinism runs in `make verify-s06` agree byte for byte
whether or not scoring ran.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.shastra import estimate, features, schema

INPUT_ROOT: Final[str] = "data"
OUTPUT_ROOT: Final[str] = "data/generated"
OUT_DIR: Final[str] = schema.OUT_DIR
REQUIRED_TABLES: Final[tuple[str, ...]] = (
    "announcements.parquet",
    "transactions.parquet",
    "peers.parquet",
)
GRAPH_DIR: Final[str] = "graph"
GRAPH_TABLE: Final[str] = "edges.parquet"
CONFIG_NAME: Final[str] = "config.effective.json"

# Used only when the run directory has no `config.effective.json`, which happens in a hand-built
# fixture and nowhere else. A run made by MAYAJAAL always carries the world it was given, so these
# are a fixture convenience rather than a policy: the real values live in `run_config.json`.
DEFAULT_TRAIN_FRACTION: Final[float] = 0.7
DEFAULT_MARGIN_FLOOR: Final[float] = 0.04
DEFAULT_MIN_ANNOUNCEMENTS: Final[int] = 2


class InputPathError(ValueError):
    """A path SHASTRA will not read from, or will not write to."""


@dataclass(frozen=True)
class Settings:
    """The eval knobs this run was generated with, read back from the run rather than the repo.

    Read from `<run>/config.effective.json` so a stage re-run months later uses the thresholds the
    capture was made under, not whatever `run_config.json` says today. `observer_fraction` is
    carried for the report only; nothing in the estimator branches on it.
    """

    train_fraction: float
    margin_floor: float
    min_announcements: int
    observer_fraction: float
    seed: int
    from_config: bool


def settings(run_dir: Path) -> Settings:
    """The run's eval settings, falling back to the module defaults when it records none."""
    path = run_dir / CONFIG_NAME
    if not path.is_file():
        return Settings(
            DEFAULT_TRAIN_FRACTION,
            DEFAULT_MARGIN_FLOOR,
            DEFAULT_MIN_ANNOUNCEMENTS,
            0.0,
            0,
            False,
        )
    node = json.loads(path.read_text(encoding="utf-8"))
    block = node.get("eval", {})
    return Settings(
        train_fraction=float(block.get("train_fraction", DEFAULT_TRAIN_FRACTION)),
        margin_floor=float(block.get("margin_floor", DEFAULT_MARGIN_FLOOR)),
        min_announcements=int(block.get("min_announcements", DEFAULT_MIN_ANNOUNCEMENTS)),
        observer_fraction=float(node.get("network", {}).get("observer_fraction", 0.0)),
        seed=int(node.get("seed", 0)),
        from_config="eval" in node,
    )


def _relative_to_cwd(path: Path, root: str) -> Path:
    """`path` resolved, refused unless it sits inside `<cwd>/<root>`."""
    base = (Path.cwd() / root).resolve()
    resolved = path.resolve()
    if resolved != base and base not in resolved.parents:
        raise InputPathError(
            f"{path} resolves outside {base}. SHASTRA only reads and writes inside that directory, "
            f"which is how a stage input can never reach a sibling tree it has no business in."
        )
    return resolved


def resolve_in(target: Path) -> Path:
    """The `normalised/` directory to estimate from. Its sibling `graph/` must exist too."""
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    missing = [name for name in REQUIRED_TABLES if not (resolved / name).is_file()]
    if missing:
        raise InputPathError(
            f"{target} is missing {', '.join(missing)}. SHASTRA reads a normalised/ directory "
            f"written by SETU: run `python -m chakravyuh.setu --in <run>/sealed --out <run>` first."
        )
    if not (resolved.parent / GRAPH_DIR / GRAPH_TABLE).is_file():
        raise InputPathError(
            f"{target.parent / GRAPH_DIR / GRAPH_TABLE} does not exist. SHASTRA needs the fused "
            f"graph for peer degree: run `python -m chakravyuh.jaal --in {target} "
            f"--out {target.parent}` first."
        )
    return resolved


def resolve_out(target: Path) -> Path:
    """The run directory to write `signals/` into."""
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


def _upstream_geolite2(normalised: Path) -> bool:
    """Whether a vendored lookup ran upstream, read back rather than assumed.

    Two features the estimator uses, `is_tor_exit` and `is_hosting`, exist only when SETU had
    `vendor/` to resolve `net_class` from. Hardcoding False here would report an estimator that
    never saw them in a run where it did, which is the one thing `optional_deps` is for. JAAL reads
    the same flag the same way; False for a fixture with no upstream meta is the honest reading.
    """
    candidate = normalised / "_meta.json"
    if not candidate.is_file():
        return False
    upstream = json.loads(candidate.read_text(encoding="utf-8"))
    return bool(upstream.get("optional_deps", {}).get("geolite2", False))


def build_run(
    normalised: Path,
    out: Path,
    *,
    labels: pl.DataFrame | None = None,
    boundary_us: int | None = None,
) -> Path:
    """Build `<out>/signals/` from `normalised/` and its sibling `graph/`. Returns `_meta.json`.

    `normalised` and `out` are already resolved and guarded by the caller. `labels` is
    `(txid, origin_peer_ip)` restricted to the training window, or None when the answer key is
    absent; `boundary_us` is the window boundary in microseconds and is re-applied here over
    `seen_us` as a second mask. Both come from `chakravyuh.eval.labels` via `__main__.py`, and this
    function does not know or care which door they came through.

    Two estimators are written into one file, distinguished by the `estimator` column, because the
    gate has to compare pass one against pass two on the same run and a reader has to be able to
    see both without re-running anything.
    """
    started_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    run_dir = normalised.parent
    config = settings(run_dir)

    announcements = pl.read_parquet(
        normalised / "announcements.parquet", columns=list(features.ANNOUNCEMENT_COLUMNS)
    )
    peers = pl.read_parquet(normalised / "peers.parquet", columns=list(features.PEER_COLUMNS))
    transactions = pl.read_parquet(
        normalised / "transactions.parquet", columns=list(features.TRANSACTION_COLUMNS)
    )
    edges = pl.read_parquet(run_dir / GRAPH_DIR / GRAPH_TABLE, columns=["src", "dst"])
    # A column subset does not change the row count, so these are the input row counts section 10
    # asks for without reading any table twice.
    rows = {
        "announcements.parquet": announcements.height,
        "transactions.parquet": transactions.height,
        "peers.parquet": peers.height,
    }

    candidates = features.candidates(announcements, peers, transactions, edges)
    baseline = estimate.first_spy(
        candidates,
        margin_floor=config.margin_floor,
        min_announcements=config.min_announcements,
    )
    learned, fit = estimate.ensemble(
        candidates,
        labels,
        boundary_us=boundary_us,
        margin_floor=config.margin_floor,
        min_announcements=config.min_announcements,
        seed=config.seed,
    )
    estimates = schema.conform(
        estimate.to_contract(pl.concat([baseline, learned])).sort("estimator", "txid", "rank"),
        schema.ORIGIN_ESTIMATES_SCHEMA,
    )

    # Deferred, not forgotten. Contract section 6 states no nullability for either table, so a row
    # with placeholder columns would be a row an auditor must reject; a zero-row file with the exact
    # schema is the honest shape of "this stage does not do typologies yet" and is what the console
    # can read without special-casing an absent file. The deferral is recorded in STATE.md.
    outputs = {
        "origin_estimates.parquet": estimates,
        "typology_hits.parquet": schema.empty(schema.TYPOLOGY_HITS_SCHEMA),
        "entity_types.parquet": schema.empty(schema.ENTITY_TYPES_SCHEMA),
    }
    out_dir = out / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {name: _write_parquet(frame, out_dir / name) for name, frame in outputs.items()}

    upstream_path, upstream_hash = _meta_link(normalised)
    graph_path, graph_hash = _meta_link(run_dir / GRAPH_DIR)

    warnings: list[str] = []
    if not fit.trained:
        warnings.append(f"ensemble_is_heuristic_{fit.reason}")
    if not fit.calibrated and fit.trained:
        warnings.append("model_uncalibrated_too_few_calibration_rows")
    if announcements["net_class"].null_count() == announcements.height:
        # Without `vendor/`, no peer has a network class, so `tor_present` can never fire and
        # `net_class_code` is a constant zero. Said out loud, because an abstention rule that
        # cannot trigger looks the same in the output as one that had no reason to.
        warnings.append("no_net_class_resolved_tor_abstention_cannot_fire")
    if not config.from_config:
        warnings.append("run_records_no_eval_block_stage_defaults_used")
    if upstream_hash is None:
        warnings.append("upstream_meta_absent_no_staleness_link")
    if not estimates.height:
        warnings.append("no_candidates_signals_is_empty")

    # Section 10's grain is rows, and the equality accounts for every row this stage was handed.
    # announcements/ is the input; the output grain is the candidate (txid, peer_ip) pair, so the
    # rows a group collapsed are this stage's one real drop, exactly as in JAAL. The two estimators
    # each write one row per pair, so the file is twice `out` and says so in outputs[].rows.
    rows_in = announcements.height
    rows_out = candidates.height
    collapsed = rows_in - rows_out

    finished_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    meta: dict[str, Any] = {
        "stage": schema.STAGE,
        "run_id": out.name,
        "started_at_us": started_at_us,
        "finished_at_us": finished_at_us,
        "code_version": buildinfo.code_version(),
        "seed": config.seed,
        "params": {
            "input": _repo_relative(normalised),
            "upstream_meta": {"path": upstream_path, "sha256": upstream_hash},
            "graph_meta": {"path": graph_path, "sha256": graph_hash},
            "estimators": sorted(estimates["estimator"].unique().to_list()),
            "margin_floor": config.margin_floor,
            "min_announcements": config.min_announcements,
            "train_fraction": config.train_fraction,
            "boundary_us": boundary_us,
            "model": (
                {
                    "kind": "lightgbm_binary_native_api",
                    "num_boost_round": estimate.BOOST_ROUNDS,
                    **estimate.TREE_PARAMS,
                    # The run's seed, not the module default, because that is what was fitted.
                    "seed": config.seed,
                }
                if fit.trained
                else None
            ),
            "calibration": "platt on a time-ordered tail of the training window",
            "fit": asdict(fit),
            "p_origin_policy": "capped at 1.0 per txid, never renormalised to 1.0",
            "margin_policy": (
                "the margin column is the contract's absolute p1 minus p2; margin_floor is applied "
                "to the scale-free separation (p1 - p2) / (p1 + p2)"
            ),
            "abstain_policy": "an abstaining txid has no rank 1 row; ranks start at 2",
            "deferred_outputs": {
                "typology_hits.parquet": "empty, S06 ships the origin estimator only",
                "entity_types.parquet": "empty, S06 ships the origin estimator only",
            },
            "counts_grain": "announcement rows, grouped to candidate (txid, peer_ip) pairs",
        },
        "inputs": [
            {
                "path": _repo_relative(normalised / name),
                "sha256": hashlib.sha256((normalised / name).read_bytes()).hexdigest(),
                "rows": rows[name],
            }
            for name in REQUIRED_TABLES
        ]
        + [
            {
                "path": _repo_relative(run_dir / GRAPH_DIR / GRAPH_TABLE),
                "sha256": hashlib.sha256(
                    (run_dir / GRAPH_DIR / GRAPH_TABLE).read_bytes()
                ).hexdigest(),
                "rows": edges.height,
            }
        ],
        "outputs": [
            {"path": f"{OUT_DIR}/{name}", "sha256": hashes[name], "rows": outputs[name].height}
            for name in sorted(outputs)
        ],
        "counts": {
            "in": rows_in,
            "out": rows_out,
            "dropped": collapsed,
            "drop_reasons": {"duplicate_announcement_of_one_txid_by_one_peer": collapsed},
        },
        "warnings": warnings,
        "optional_deps": {
            "geolite2": _upstream_geolite2(normalised),
            "kuzu": False,
            "gpu": False,
        },
    }
    meta_path = out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if estimates.filter(pl.col("abstain") & (pl.col("rank") == 1)).height:
        raise AssertionError(
            "an abstaining transaction was written with a rank 1 row. Contract section 6 forbids "
            "it and a consumer would read the refusal as an accusation."
        )
    return meta_path
