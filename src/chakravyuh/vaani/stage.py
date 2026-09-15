"""VAANI as a stage: read `scores/`, `signals/` and `graph/`, write `alerts/`.

The path guards are BUDDHI's, restated rather than imported, for the reason that rule
exists: `--in` is allowlisted to `data/generated/`, so a VAANI invocation cannot be pointed
at the answer key even by an operator who wants to, because the answer key is a sibling tree
and not under `data/`.

This module never imports `chakravyuh.eval` and never opens anything outside the run's
observable directories. Every counter row is built in the same pass that builds its alert,
so an alert cannot exist without counter-evidence — the brief's "technically present and
always empty" trap is a raise here, not a warning.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.vaani import counters, evidence, gloss

INPUT_ROOT: Final[str] = "data/generated"
OUT_DIR: Final[str] = "alerts"
SCORES_DIR: Final[str] = "scores"
SIGNALS_DIR: Final[str] = "signals"
GRAPH_DIR: Final[str] = "graph"
NORMALISED_DIR: Final[str] = "normalised"

WALLET_SCORES: Final[str] = "wallet_scores.parquet"
ORIGIN_ESTIMATES: Final[str] = "origin_estimates.parquet"
ENTITY_TYPES: Final[str] = "entity_types.parquet"
TYPOLOGY_HITS: Final[str] = "typology_hits.parquet"
CLUSTERS: Final[str] = "clusters.parquet"
EDGES: Final[str] = "edges.parquet"
ANNOUNCEMENTS: Final[str] = "announcements.parquet"
ENSEMBLE: Final[str] = "ensemble"
DEFAULT_MARGIN_FLOOR: Final[float] = 0.04


class InputPathError(ValueError):
    """A path VAANI will not read from, or will not write to."""


def _relative_to_cwd(path: Path, root: str) -> Path:
    """`path` resolved, refused unless it sits inside `<cwd>/<root>`."""
    base = (Path.cwd() / root).resolve()
    resolved = path.resolve()
    if resolved != base and base not in resolved.parents:
        raise InputPathError(
            f"{path} resolves outside {base}. VAANI only reads and writes inside that "
            f"directory, which is how a stage input can never reach a sibling tree it has "
            f"no business in."
        )
    return resolved


def resolve_in(target: Path) -> Path:
    """The run directory whose `scores/`, `signals/` and `graph/` VAANI reads."""
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    missing = [
        name
        for name, subdir in (
            (WALLET_SCORES, SCORES_DIR),
            (ORIGIN_ESTIMATES, SIGNALS_DIR),
            (CLUSTERS, GRAPH_DIR),
            (EDGES, GRAPH_DIR),
            (ANNOUNCEMENTS, NORMALISED_DIR),
        )
        if not (resolved / subdir / name).is_file()
    ]
    if missing:
        raise InputPathError(
            f"{target} is missing {', '.join(missing)}. VAANI reads a run written by BUDDHI, "
            f"SHASTRA, JAAL and SETU: run those stages first."
        )
    return resolved


def resolve_out(target: Path) -> Path:
    """The run directory to write `alerts/` into."""
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    if resolved == (Path.cwd() / INPUT_ROOT).resolve():
        raise InputPathError(
            f"--out must name a run directory inside {INPUT_ROOT}/, not {INPUT_ROOT}/ itself"
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


def _margin_floor(run_dir: Path) -> float:
    """The estimator's own abstention threshold, read from the run it was estimated under."""
    path = run_dir / "config.effective.json"
    if not path.is_file():
        return DEFAULT_MARGIN_FLOOR
    node = json.loads(path.read_text(encoding="utf-8"))
    return float(node.get("eval", {}).get("margin_floor", DEFAULT_MARGIN_FLOOR))


def build_run(run_dir: Path, out: Path) -> Path:
    """Build `<out>/alerts/` from the run's `scores/`, `signals/`, `graph/` and `normalised/`.

    `run_dir` and `out` are already resolved and guarded by the caller and are the same
    directory in every normal invocation: `alerts/` sits beside `scores/` in the contract's
    layout. Returns the `_meta.json` path.
    """
    started_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)

    scores = pl.read_parquet(run_dir / SCORES_DIR / WALLET_SCORES)
    origin = pl.read_parquet(
        run_dir / SIGNALS_DIR / ORIGIN_ESTIMATES,
        columns=["txid", "peer_ip", "p_origin", "rank", "margin", "abstain", "estimator"],
    )
    entity_types = pl.read_parquet(
        run_dir / SIGNALS_DIR / ENTITY_TYPES,
        columns=["subject_id", "predicted_type", "confidence", "basis", "exempt_from_scoring"],
    )
    typology_hits = pl.read_parquet(
        run_dir / SIGNALS_DIR / TYPOLOGY_HITS, columns=["subject_id", "typology", "strength"]
    )
    clusters = pl.read_parquet(
        run_dir / GRAPH_DIR / CLUSTERS, columns=["cluster_id", "addresses", "min_edge_confidence"]
    )
    edges = pl.read_parquet(
        run_dir / GRAPH_DIR / EDGES, columns=["src", "dst", "kind", "confidence"]
    )
    announcements = pl.read_parquet(
        run_dir / NORMALISED_DIR / ANNOUNCEMENTS, columns=["row_id", "txid", "peer_ip", "seen_us"]
    )
    rows_in = {
        "wallet_scores.parquet": scores.height,
        "origin_estimates.parquet": origin.height,
        "entity_types.parquet": entity_types.height,
        "typology_hits.parquet": typology_hits.height,
        "clusters.parquet": clusters.height,
        "edges.parquet": edges.height,
        "announcements.parquet": announcements.height,
    }

    glosses = gloss.load_glosses(gloss.default_path())

    # The ensemble's rank-1 rows are the only attribution this stage states. An abstaining
    # transaction has no rank-1 row by SHASTRA's rule, so absence here is the abstain.
    top1 = origin.filter((pl.col("estimator") == ENSEMBLE) & (pl.col("rank") == 1)).select(
        "txid", "peer_ip", "p_origin", "margin"
    )
    receives = edges.filter(pl.col("kind") == "RECEIVES").select(
        pl.col("dst").str.strip_prefix("addr:").alias("address"),
        pl.col("src").str.strip_prefix("tx:").alias("txid"),
    )

    # Which subjects' sends the estimator refused, as a share, for the abstain counter.
    sent_pairs = (
        edges.filter(pl.col("kind") == "SPENDS")
        .select(
            pl.col("dst").str.strip_prefix("addr:").alias("address"),
            pl.col("src").str.strip_prefix("tx:").alias("txid"),
        )
        .join(
            clusters.select("cluster_id", "addresses").explode("addresses"),
            left_on="address",
            right_on="addresses",
            how="inner",
        )
        .rename({"cluster_id": "subject_id"})
        .select("subject_id", "txid")
        .unique()
    )
    answered = sent_pairs.join(top1.select("txid"), on="txid", how="semi")
    abstain_frac = (
        sent_pairs.group_by("subject_id", maintain_order=True)
        .agg(pl.len().alias("n"))
        .join(
            answered.group_by("subject_id", maintain_order=True).agg(pl.len().alias("k")),
            on="subject_id",
            how="left",
        )
        .with_columns(((pl.col("n") - pl.col("k").fill_null(0)) / pl.col("n")).alias("frac"))
        .select("subject_id", "frac")
    )

    # One peer often announces for several subjects; that sharing is counter-evidence.
    announced_addresses = edges.filter(pl.col("kind") == "ANNOUNCED_BY").select(
        pl.col("dst").str.strip_prefix("peer:").alias("peer_ip"),
        pl.col("src").str.strip_prefix("tx:").alias("txid"),
    )
    peer_subjects = (
        announced_addresses.join(sent_pairs, on="txid", how="inner")
        .select("peer_ip", "subject_id")
        .unique()
        .group_by("peer_ip", maintain_order=True)
        .agg(pl.len().alias("n_subjects"))
    )

    internal = evidence.alerts_frame(scores, clusters, receives, top1, glosses)
    internal = internal.with_columns(
        pl.struct("subject_id", "risk_score")
        .map_elements(
            lambda s: "alw-"
            + hashlib.sha256(f"{s['subject_id']}:{_seed(run_dir)}".encode()).hexdigest()[:12],
            return_dtype=pl.String(),
        )
        .alias("alert_id")
    )

    origin_mass = (
        origin.filter(pl.col("estimator") == ENSEMBLE)
        .group_by("txid", maintain_order=True)
        .agg(pl.col("p_origin").sum().alias("mass"))
    )
    counter_frame = counters.build(
        internal,
        top1,
        entity_types,
        typology_hits,
        clusters,
        peer_subjects,
        abstain_frac,
        _margin_floor(run_dir),
        origin_mass,
    )
    alert_frame = internal.select(list(evidence.ALERTS_SCHEMA))
    evidence_frame = evidence.evidence_rows(internal, glosses, announcements, clusters)

    outputs = {
        "alerts.parquet": alert_frame,
        "evidence.parquet": evidence_frame,
        "counter.parquet": counter_frame,
    }
    out_dir = out / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {name: _write_parquet(frame, out_dir / name) for name, frame in outputs.items()}

    scores_path, scores_hash = _meta_link(run_dir / SCORES_DIR)
    signals_path, signals_hash = _meta_link(run_dir / SIGNALS_DIR)

    warnings: list[str] = []
    if scores_hash is None or signals_hash is None:
        warnings.append("upstream_meta_absent_no_staleness_link")
    if entity_types.height == 0:
        warnings.append("entity_types_zero_row_entity_counters_dormant")
    if typology_hits.height == 0:
        warnings.append("typology_hits_zero_row_benign_explanations_dormant")
    licit = rows_in[WALLET_SCORES] - scores.filter(pl.col("label") != "LIKELY_LICIT").height
    if scores.height and alert_frame.height == 0:
        warnings.append("every_subject_licit_no_alerts_written")

    finished_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    meta: dict[str, Any] = {
        "stage": "vaani",
        "run_id": out.name,
        "started_at_us": started_at_us,
        "finished_at_us": finished_at_us,
        "code_version": buildinfo.code_version(),
        "seed": _seed(run_dir),
        "params": {
            "input": _repo_relative(run_dir),
            "upstream_meta": {"path": scores_path, "sha256": scores_hash},
            "signals_meta": {"path": signals_path, "sha256": signals_hash},
            "margin_floor": _margin_floor(run_dir),
            "identifier_policy": (
                "alerts.parquet carries contract fields whole (section 9's packet quotes "
                "them); prose in evidence and counter is truncated at write time"
            ),
            "counts_grain": "scored subjects, LIKELY_LICIT excluded as the drop",
        },
        "inputs": [
            {
                "path": _repo_relative(run_dir / subdir / name),
                "sha256": hashlib.sha256((run_dir / subdir / name).read_bytes()).hexdigest(),
                "rows": rows_in[name],
            }
            for name, subdir in sorted(
                {
                    WALLET_SCORES: SCORES_DIR,
                    ORIGIN_ESTIMATES: SIGNALS_DIR,
                    ENTITY_TYPES: SIGNALS_DIR,
                    TYPOLOGY_HITS: SIGNALS_DIR,
                    CLUSTERS: GRAPH_DIR,
                    EDGES: GRAPH_DIR,
                    ANNOUNCEMENTS: NORMALISED_DIR,
                }.items(),
                key=lambda item: (item[1], item[0]),
            )
        ],
        "outputs": [
            {"path": f"{OUT_DIR}/{name}", "sha256": hashes[name], "rows": outputs[name].height}
            for name in sorted(outputs)
        ],
        "counts": {
            "in": rows_in[WALLET_SCORES],
            "out": alert_frame.height,
            "dropped": licit,
            "drop_reasons": {"likely_licit_not_alerted": licit},
        },
        "warnings": sorted(set(warnings)),
        "optional_deps": {"geolite2": False, "kuzu": False, "gpu": False},
    }
    meta_path = out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta_path


def _seed(run_dir: Path) -> int:
    """The run's seed, from `config.effective.json`; 0 when the run records none."""
    path = run_dir / "config.effective.json"
    if not path.is_file():
        return 0
    node = json.loads(path.read_text(encoding="utf-8"))
    return int(node.get("seed", 0))
