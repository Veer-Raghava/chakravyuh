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
from chakravyuh.shastra import estimate, features, schema, typology

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
# The outbound relay-delay mean MAYAJAAL propagates under, in microseconds, used only when a
# hand-built fixture records no config. A real run carries `network.relay_delay_outbound_mean_s`
# and this default is never consulted; `run_config.json` ships 2.0s.
DEFAULT_RELAY_DELAY_US: Final[float] = 2_000_000.0
# Peer columns the L1 roll-up needs beyond the estimator features: the operator label and region
# each candidate host sits under. Read from `peers.parquet`, not derived, so the attribution is the
# same operator string SETU wrote and `asn_rollup.parquet` is keyed on.
L1_PEER_COLUMNS: Final[tuple[str, ...]] = ("peer_ip", "asn", "as_org", "net_class", "geo_country")


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
    relay_delay_us: float
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
            DEFAULT_RELAY_DELAY_US,
            0,
            False,
        )
    node = json.loads(path.read_text(encoding="utf-8"))
    block = node.get("eval", {})
    network = node.get("network", {})
    return Settings(
        train_fraction=float(block.get("train_fraction", DEFAULT_TRAIN_FRACTION)),
        margin_floor=float(block.get("margin_floor", DEFAULT_MARGIN_FLOOR)),
        min_announcements=int(block.get("min_announcements", DEFAULT_MIN_ANNOUNCEMENTS)),
        observer_fraction=float(network.get("observer_fraction", 0.0)),
        # The relay-delay model is not altered here; its mean is only read, so `timing_mle`
        # measures arrivals in the same units MAYAJAAL propagated them in. Seconds in config,
        # microseconds here.
        relay_delay_us=float(
            network.get("relay_delay_outbound_mean_s", DEFAULT_RELAY_DELAY_US / 1_000_000.0)
        )
        * 1_000_000.0,
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
    # Read wide enough for both consumers in one pass: the estimator features SETU keyed on and the
    # operator/region columns the L1 roll-up attributes with. `dict.fromkeys` unions the two tuples
    # without repeating a column.
    peer_columns = list(dict.fromkeys((*features.PEER_COLUMNS, *L1_PEER_COLUMNS)))
    peers = pl.read_parquet(normalised / "peers.parquet", columns=peer_columns)
    transactions = pl.read_parquet(
        normalised / "transactions.parquet", columns=list(features.TRANSACTION_COLUMNS)
    )
    # The arrival matrix and ASN substrate are SETU outputs too, but a run captured before P0-b,
    # or a hand-built fixture, may not carry them. Absent arrival degrades `mle_logscore` to
    # first-seen earliness inside `attach_mle`; absent `asn_rollup` leaves the L1 headline empty
    # and warns.
    arrival_path = normalised / "arrival.parquet"
    arrival = pl.read_parquet(arrival_path) if arrival_path.is_file() else None
    asn_prior_path = normalised / "asn_rollup.parquet"
    asn_prior = pl.read_parquet(asn_prior_path) if asn_prior_path.is_file() else None
    edges = pl.read_parquet(run_dir / GRAPH_DIR / GRAPH_TABLE, columns=["src", "dst"])
    clusters = pl.read_parquet(
        run_dir / GRAPH_DIR / "clusters.parquet", columns=["cluster_id", "addresses"]
    )
    addresses = pl.read_parquet(normalised / "addresses.parquet", columns=["address"])
    morphology = pl.read_parquet(
        normalised / "transactions.parquet", columns=list(typology.TRANSACTION_COLUMNS)
    )
    # A column subset does not change the row count, so these are the input row counts section 10
    # asks for without reading any table twice.
    rows = {
        "announcements.parquet": announcements.height,
        "transactions.parquet": transactions.height,
        "peers.parquet": peers.height,
    }

    candidates = features.candidates(announcements, peers, transactions, edges)
    # Compute the multi-observer source log-likelihood once, so `timing_mle` ranks on it, `ensemble`
    # blends it as a feature, and it lands in the persisted `features` struct. The relay-delay mean
    # is read from the run, never altered.
    candidates = estimate.attach_mle(candidates, arrival, relay_delay_us=config.relay_delay_us)
    baseline = estimate.first_spy(
        candidates,
        margin_floor=config.margin_floor,
        min_announcements=config.min_announcements,
    )
    timing = estimate.timing_mle(
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
        estimate.to_contract(pl.concat([baseline, timing, learned])).sort(
            "estimator", "txid", "rank"
        ),
        schema.ORIGIN_ESTIMATES_SCHEMA,
    )

    # The L1/L2 headline the reframe makes the hero: the ensemble's candidate mass lifted onto one
    # operator and region per transaction. Ensemble-only on disk — a by-estimator L1 comparison is
    # eval's job, computed on the fly rather than stored four times. Empty with the exact schema
    # when the run predates the ASN substrate, so the file always exists for the contract auditor.
    if asn_prior is not None:
        origin_l1 = schema.conform(
            estimate.asn_rollup(learned, peers, asn_prior, margin_floor=config.margin_floor),
            schema.ORIGIN_L1_SCHEMA,
        )
    else:
        origin_l1 = schema.empty(schema.ORIGIN_L1_SCHEMA)

    # Typology hits are read straight off the transaction morphology, no labels: a hit is a shape
    # (fan-out, coinjoin-like, peel chain, structuring) an analyst can point at in the capture. The
    # `entity_types.parquet` classifier stays deferred — predicting a subject's *kind* is a separate
    # model, and an empty file with the exact schema is the honest shape of "not built yet".
    hits = typology.detect(morphology, clusters, addresses)
    outputs = {
        "origin_estimates.parquet": estimates,
        "origin_l1.parquet": origin_l1,
        "typology_hits.parquet": hits,
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
    if asn_prior is None:
        # No ASN substrate upstream, so the L1 headline the reframe leads with is empty. Said out
        # loud: an empty origin_l1 from a missing input reads the same on disk as one where every
        # transaction abstained, and only the first is a warning.
        warnings.append("asn_rollup_absent_l1_headline_is_empty")
    if arrival is None:
        # No arrival matrix, so `timing_mle` and the `mle_logscore` feature fell back to first-seen
        # earliness. The two estimators still ran; they just saw less than a real capture offers.
        warnings.append("arrival_absent_mle_degraded_to_first_seen")

    # Section 10's grain is rows, and the equality accounts for every row this stage was handed.
    # announcements/ is the input; the output grain is the candidate (txid, peer_ip) pair, so the
    # rows a group collapsed are this stage's one real drop, exactly as in JAAL. The three ranking
    # estimators each write one row per pair, so the file is three times `out` and says so in
    # outputs[].rows; origin_l1 is a separate per-transaction file at its own grain.
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
            # The relay-delay mean `timing_mle` measures arrivals against, read from the run's
            # config and not altered. Recorded so a reader knows which world's units the score is
            # in.
            "relay_delay_outbound_us": config.relay_delay_us,
            "mle": {
                "escape_log_gap": estimate.MLE_ESCAPE_LOG_GAP,
                "min_mean_us": estimate.MLE_MIN_MEAN_US,
                "arrival_present": arrival is not None,
            },
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
            "l1_policy": (
                "origin_l1 is the ensemble's candidate mass summed by ASN, weighted by the "
                "asn_rollup frac_rank_one prior; p_asn and p_country are capped, never "
                "renormalised; a txid whose top two operators are within margin_floor separation "
                "abstains with cross_asn_ambiguous, and weak-evidence refusals are inherited"
            ),
            "deferred_outputs": {
                "entity_types.parquet": (
                    "empty, subject-type classifier not built; typology_hits is live"
                ),
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
