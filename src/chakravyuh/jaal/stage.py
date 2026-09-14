"""JAAL as a stage: read `normalised/`, write `graph/`, account for every candidate edge.

The path guards are KAVACH's and SETU's, restated rather than imported. No stage imports another
stage's internals, and the rule pays for itself here too: `--in` is allowlisted to `data/`, so a
JAAL invocation cannot be pointed at the answer key even by an operator who wants to, because the
answer key is a sibling tree and not under `data/`.

Nothing truth-derived is written here. `graph/_meta.json` carries no precision, no recall and no
path into a sibling tree, so the two determinism runs in `make verify-s05` agree byte for byte
whether or not scoring ran.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.jaal import build, cluster, view

INPUT_ROOT: Final[str] = "data"
OUTPUT_ROOT: Final[str] = "data/generated"
OUT_DIR: Final[str] = "graph"
REQUIRED_TABLES: Final[tuple[str, ...]] = (
    "announcements.parquet",
    "transactions.parquet",
    "addresses.parquet",
    "peers.parquet",
)


class InputPathError(ValueError):
    """A path JAAL will not read from, or will not write to."""


def _relative_to_cwd(path: Path, root: str) -> Path:
    """`path` resolved, refused unless it sits inside `<cwd>/<root>`."""
    base = (Path.cwd() / root).resolve()
    resolved = path.resolve()
    if resolved != base and base not in resolved.parents:
        raise InputPathError(
            f"{path} resolves outside {base}. JAAL only reads and writes inside that directory, "
            f"which is how a stage input can never reach a sibling tree it has no business in."
        )
    return resolved


def resolve_in(target: Path) -> Path:
    """The `normalised/` directory to build a graph from."""
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    missing = [name for name in REQUIRED_TABLES if not (resolved / name).is_file()]
    if missing:
        raise InputPathError(
            f"{target} is missing {', '.join(missing)}. JAAL reads a normalised/ directory "
            f"written by SETU: run `python -m chakravyuh.setu --in <run>/sealed --out <run>` first."
        )
    return resolved


def resolve_out(target: Path) -> Path:
    """The run directory to write `graph/` into."""
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


def _upstream_meta(normalised: Path) -> tuple[str | None, str | None, bool]:
    """The staleness link plus upstream's `geolite2` flag: path, hash, whether a lookup ran.

    Recorded so `scripts/check_stage.py` can fail when the upstream moves after this ran. The
    path and hash are null for a normalised directory with no `_meta.json`, which only happens
    in a hand-built fixture; `geolite2` is False there, which is the honest reading — nothing
    told us a vendored lookup ran, so the ASNs are treated as capture-carried.
    """
    candidate = normalised / "_meta.json"
    if not candidate.is_file():
        return None, None, False
    raw = candidate.read_bytes()
    upstream = json.loads(raw.decode("utf-8"))
    from_lookup = bool(upstream.get("optional_deps", {}).get("geolite2", False))
    return _repo_relative(candidate), hashlib.sha256(raw).hexdigest(), from_lookup


def build_run(normalised: Path, out: Path, threshold: float = cluster.DEFAULT_THRESHOLD) -> Path:
    """Build `<out>/graph/` from `normalised/`. Returns the path to `_meta.json`.

    `normalised` and `out` are already resolved and guarded by the caller. `threshold` is the
    confidence cut the derived cluster view is taken at, and is recorded in every row of
    clusters.parquet as well as in `params`.
    """
    started_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    tables = {name: pl.read_parquet(normalised / name) for name in REQUIRED_TABLES}
    announcements = tables["announcements.parquet"]
    transactions = tables["transactions.parquet"]
    addresses = tables["addresses.parquet"]
    peers = tables["peers.parquet"]
    upstream_path, upstream_hash, from_lookup = _upstream_meta(normalised)

    same_owner = cluster.same_owner_edges(transactions)
    cluster_frame, member_edges = cluster.clusters(same_owner, threshold)
    kept = same_owner.filter(pl.col("confidence") >= threshold)

    node_frame = pl.concat(
        [
            build.address_nodes(addresses),
            build.transaction_nodes(transactions),
            build.peer_nodes(peers),
            build.asn_nodes(peers),
            cluster.cluster_nodes(cluster_frame),
        ]
    )
    edge_frame = pl.concat(
        [
            build.chain_edges(transactions),
            build.announcement_edges(announcements),
            build.hosting_edges(peers, from_lookup),
            kept,
            member_edges,
        ]
    )

    outputs = {
        "nodes.parquet": node_frame,
        "edges.parquet": edge_frame,
        "clusters.parquet": cluster_frame,
    }
    out_dir = out / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {name: _write_parquet(frame, out_dir / name) for name, frame in outputs.items()}

    warnings: list[str] = []
    kuzu_available = view.available()
    if not kuzu_available:
        warnings.append("kuzu_absent_cypher_view_unavailable")
    if peers["asn"].null_count() == peers.height:
        # The no-vendor path, made visible: without an ASN there is no asn layer and no
        # HOSTED_IN edge, so a reader who expected five node kinds gets four.
        warnings.append("no_asn_resolved_graph_has_no_asn_layer")
    if cluster_frame.height == 0:
        warnings.append("no_clusters_at_this_threshold")
    if upstream_hash is None:
        warnings.append("upstream_meta_absent_no_staleness_link")

    # Section 10's grain is rows, and the equality is what makes the pipeline accountable for
    # every row it was handed rather than for some quantity internal to this stage. So `in` is
    # every row of every normalised table this stage read.
    #
    # Three of those tables are one row per entity and each row becomes exactly one node, so
    # nothing can go missing there. announcements/ is the only table with a coarser output than
    # its input: several rows can describe one (txid, peer_ip) pair, and only one ANNOUNCED_BY
    # edge is written for them, so peer degree counts transactions rather than packets. Those
    # collapsed rows are the stage's one real drop and they are named as such.
    #
    # An earlier version counted candidate SAME_OWNER edges here. The arithmetic held, but the
    # 11014 rows the stage was handed were unaccounted, which is exactly the question section 10
    # exists to answer. That accounting is still recorded, under params.same_owner_candidates.
    rows_in = sum(frame.height for frame in tables.values())
    distinct_pairs = announcements.select("txid", "peer_ip").n_unique()
    collapsed = announcements.height - distinct_pairs
    rows_out = rows_in - collapsed

    proposed = (
        cluster.common_input_edges(transactions).height + cluster.change_edges(transactions).height
    )
    duplicates = proposed - same_owner.height
    below = same_owner.height - kept.height

    finished_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    meta = {
        "stage": build.STAGE,
        "run_id": out.name,
        "started_at_us": started_at_us,
        "finished_at_us": finished_at_us,
        "code_version": buildinfo.code_version(),
        "seed": 0,
        "params": {
            "input": _repo_relative(normalised),
            "upstream_meta": {"path": upstream_path, "sha256": upstream_hash},
            "threshold": threshold,
            "heuristics": {
                "multi_input": {
                    "confidence": cluster.MULTI_INPUT_CONFIDENCE,
                    "source": "contract section 5, published full-cluster precision",
                    "excludes": "has_equal_outputs, which is where this heuristic is known wrong",
                },
                "change_addr": {
                    "confidence": cluster.CHANGE_ADDR_CONFIDENCE,
                    "source": "unmeasured in this project, set below multi_input deliberately",
                    "rule": "setu change_index, sole non-round output not paying an input address",
                },
            },
            # The stage's own accounting, beside the row accounting rather than instead of it.
            "same_owner_candidates": {
                "proposed": proposed,
                "kept": kept.height,
                "duplicate_pair": duplicates,
                "below_threshold": below,
            },
            "hosting_evidence": "geoip" if from_lookup else "observed",
            "counts_grain": "normalised rows",
            "edge_shape": "star per transaction, anchored on the smallest address",
        },
        "inputs": [
            {
                "path": _repo_relative(normalised / name),
                "sha256": hashlib.sha256((normalised / name).read_bytes()).hexdigest(),
                "rows": tables[name].height,
            }
            for name in REQUIRED_TABLES
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
        "optional_deps": {"geolite2": from_lookup, "kuzu": kuzu_available, "gpu": False},
    }
    meta_path = out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    address_nodes = node_frame.filter(pl.col("kind") == "address").height
    if address_nodes != addresses.height:
        raise AssertionError(
            f"read {addresses.height} addresses and wrote {address_nodes} address nodes. "
            "SAME_OWNER never merges nodes, so these two counts are the same number always."
        )
    return meta_path
