"""Turn the run's Parquet artifacts into the eight DRISHTI adapter payloads.

One serializer per adapter function, each a pure function of (run_dir, arguments) -> dict.
`app.py` serves them over HTTP, `scripts/export_ui_fixtures.py` writes the same dicts to
`data/fixtures/ui/`. Both call this module, which is what makes the API's response shape and
the committed fixtures agree field for field rather than by convention.

Every payload is derived at request time from the run's own artifacts. `origin_txid`,
`origin_peer_ip` and `subject_id` are contract join keys and stay whole; everything rendered
as prose is already truncated at write time by VAANI, and the few places this module emits an
identifier into a display field it truncates through `vaani.redact` here. Hashes are the
exception and print in full.

The run directory is resolved once by `app.py` from the environment. Nothing here accepts a
filesystem path from a caller outside the package, and nothing here names a quarantined tree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.vaani import redact

SEALED_DIR = "sealed"
NORMALISED_DIR = "normalised"
GRAPH_DIR = "graph"
SIGNALS_DIR = "signals"
SCORES_DIR = "scores"
ALERTS_DIR = "alerts"
PACKETS_DIR = "packets"

ENSEMBLE = "ensemble"
LABEL_QUEUE = ("LIKELY_ILICIT", "UNCLEAR")
DEFAULT_NODE_CAP = 2000

# L0..L6 in the fixed order the console lamps render. Each lamp is lit when the artifact
# that proves the stage ran is on disk, so a half-built run shows exactly how far it got
# rather than claiming completion it cannot back with a file.
STAGE_LAMPS: tuple[tuple[str, str, str], ...] = (
    ("L0", "kavach", f"{SEALED_DIR}/manifest.json"),
    ("L1", "setu", f"{NORMALISED_DIR}/_meta.json"),
    ("L2", "jaal", f"{GRAPH_DIR}/_meta.json"),
    ("L3", "shastra", f"{SIGNALS_DIR}/_meta.json"),
    ("L4", "buddhi", f"{SCORES_DIR}/_meta.json"),
    ("L5", "vaani", f"{ALERTS_DIR}/_meta.json"),
    ("L6", "pramaan", f"{PACKETS_DIR}/merkle.log"),
)

# The label the console badges an alert with, from the model's own class decision. The
# stored labels carry a historical misspelling ("ILICIT"); the console vocabulary is the
# corrected one, mapped here so one typo does not leak onto an investigator's screen.
LABEL_DISPLAY = {
    "LIKELY_ILICIT": "LIKELY_ILLICIT",
    "LIKELY_LICIT": "LIKELY_LICIT",
    "UNCLEAR": "UNCLEAR",
}

# The origin estimator's per-candidate features, in the order the fan panel reads them, each
# with the plain-english line the console shows beneath it. The values themselves come from
# the rank-1 peer's own feature struct in `origin_estimates.parquet`; this only names them.
ORIGIN_FEATURE_GLOSS: tuple[tuple[str, str, str], ...] = (
    (
        "delta_first_us",
        "first-announcement lead",
        "how long after the transaction was first seen this peer announced it; "
        "the origin is usually first",
    ),
    (
        "rank_in_tx",
        "announcement rank",
        "this peer's position in the order peers announced the transaction",
    ),
    (
        "n_candidates",
        "competing peers",
        "how many peers announced the transaction and could be its origin",
    ),
    (
        "peer_frac_rank_one",
        "first-seen habit",
        "the share of this peer's transactions on which it announced first",
    ),
    (
        "peer_n_txids",
        "peer activity",
        "how many distinct transactions this peer has been seen announcing",
    ),
    ("net_class", "network class", "the kind of network the peer's address sits in"),
    (
        "is_tor_exit",
        "Tor exit",
        "whether the peer is a known Tor exit, where origin cannot be attributed to a subscriber",
    ),
    (
        "is_hosting",
        "hosting network",
        "whether the peer sits in a datacentre rather than on a residential line",
    ),
    (
        "announce_spread_us",
        "announcement spread",
        "the time between the first and last announcement of the transaction",
    ),
    (
        "n_observers_seen",
        "monitors that saw it",
        "how many capture nodes recorded this peer's announcement",
    ),
)


def _meta(run_dir: Path, stage: str) -> dict[str, Any]:
    path = run_dir / stage / "_meta.json"
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing; the run is incomplete at stage {stage}")
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _redacted_ip(value: str | None) -> str:
    return redact.redact_ip(value) if value else ""


def _redacted_address(subject_id: str) -> str:
    """`addr:bc1q…` -> first six and last four of the address part."""
    if subject_id.startswith("addr:"):
        return redact.redact_address(subject_id[5:])
    return subject_id


def _stage_lamps(run_dir: Path) -> list[dict[str, Any]]:
    """L0..L6, each lit iff the file that proves the stage ran exists in the run."""
    return [
        {"id": lid, "stage": name, "complete": (run_dir / proof).is_file()}
        for lid, name, proof in STAGE_LAMPS
    ]


def _merkle_head(run_dir: Path) -> str:
    """The current Merkle root over every leaf in the run's log, in full.

    The log stores `index  leaf  prev_root`, so the head is not a column: it is the root of
    all leaves so far, which for the last entry is `root_of(leaves)`. Reading the last
    prev_root instead would report the root *before* the final packet — genesis zeros on a
    one-packet run — so the head is recomputed rather than scraped.
    """
    from chakravyuh.pramaan import merkle

    log_path = run_dir / PACKETS_DIR / "merkle.log"
    if not log_path.is_file():
        return ""
    leaves, _ = merkle.read(log_path)
    return merkle.root_of(leaves) if leaves else ""


def _n_transactions(run_dir: Path) -> int:
    """Gossiped transaction count, read without materialising the table."""
    path = run_dir / NORMALISED_DIR / "transactions.parquet"
    if not path.is_file():
        return 0
    return int(pl.scan_parquet(path).select(pl.len()).collect().item())


def _model_report(run_dir: Path) -> dict[str, Any]:
    """The eval report for this run, or `{}` before it was measured.

    Prevalence and empirical coverage are properties of the labelled truth, which only
    `chakravyuh.eval` may read; it writes them here. The API surfaces what eval already
    computed and never touches the quarantined labels itself.
    """
    path = Path("measurements") / run_dir.name / "model_report.json"
    if not path.is_file():
        return {}
    return dict(json.loads(path.read_text("utf-8")))


def _base_rate(report: dict[str, Any]) -> float:
    """Positive prevalence from the report's `1:N` imbalance ratio, 0.0 if unknown."""
    ratio = str(report.get("imbalance_ratio", ""))
    if ":" in ratio:
        _, _, tail = ratio.partition(":")
        try:
            n = float(tail)
        except ValueError:
            return 0.0
        return 1.0 / (1.0 + n) if n > 0 else 0.0
    return 0.0


# ---------------------------------------------------------------------------
# getManifest


def manifest(run_dir: Path) -> dict[str, Any]:
    """INTAKE payload: custody files, the seal arithmetic, the schema table, the rejects.

    The arithmetic line `rows_read == rows_sealed + rows_rejected` is computed here from the
    manifest's own fields, so the console renders the failure rather than hiding it whenever
    the numbers do not add up.
    """
    manifest_json = dict(json.loads((run_dir / SEALED_DIR / "manifest.json").read_text("utf-8")))
    chain = _meta(run_dir, "chain")
    files: list[dict[str, Any]] = []
    for path in sorted((run_dir / SEALED_DIR).glob("INPUT.sha256")):
        for line in path.read_text("utf-8").splitlines():
            digest, _, name = line.partition("  ")
            if digest and name:
                files.append({"name": name, "sha256": digest})
    for one in manifest_json["input_files"]:
        files.append(
            {"name": Path(one["path"]).name, "bytes": one["bytes"], "sha256": one["sha256"]}
        )

    status = manifest_json["column_status"]
    columns = [
        {
            "column": column,
            "type": "sats" if column in ("input_amounts", "output_amounts", "fee_sats") else "text",
            "status": tag,
            "null_count": 0,
        }
        for column, tag in status.items()
    ]

    rejected = pl.read_parquet(
        run_dir / SEALED_DIR / "rejected.parquet",
        columns=["row_id", "reject_reason"],
    )
    rejects = [
        {"row_id": int(row["row_id"]), "reason": str(row["reject_reason"])}
        for row in rejected.sort("row_id").head(200).iter_rows(named=True)
    ]

    rows_read = int(manifest_json["rows_read"])
    rows_sealed = int(manifest_json["rows_sealed"])
    rows_rejected = int(manifest_json["rows_rejected"])
    missing_optional = [column for column, tag in status.items() if str(tag).upper() == "MISSING"]
    return {
        "run_id": str(chain.get("run_id", run_dir.name)),
        "input_sha256": files[0]["sha256"] if files else "",
        "rows_read": rows_read,
        "rows_sealed": rows_sealed,
        "rows_rejected": rows_rejected,
        "n_transactions": _n_transactions(run_dir),
        "stages": _stage_lamps(run_dir),
        "merkle_head": _merkle_head(run_dir),
        "air_gapped": True,
        "columns_missing_optional": missing_optional,
        "tool_version": "0.1.0",
        "arithmetic_ok": rows_read == rows_sealed + rows_rejected,
        "amount_unit_detected": str(manifest_json["amount_unit_detected"]),
        "timestamp_format_detected": str(manifest_json["timestamp_format_detected"]),
        "code_version": str(chain.get("code_version", buildinfo.code_version())),
        "seed": int(chain.get("seed", 0)),
        "files": files,
        "columns": columns,
        "rejects": rejects,
        "reject_reasons": dict(manifest_json["reject_reasons"]),
        "warnings": list(manifest_json["warnings"]),
    }


# ---------------------------------------------------------------------------
# getCollapseStats


def collapse(run_dir: Path) -> dict[str, Any]:
    """COLLAPSE payload: the one-million-rows-is-not-one-million-events screen.

    The announcements-per-transaction mean is computed from the run's own tables and the
    console renders whatever it measures. The histogram, the per-second series and the
    per-block series are downsampled here, upstream, so no chart is ever fed more points
    than it can draw.
    """
    txs = pl.read_parquet(
        run_dir / NORMALISED_DIR / "transactions.parquet",
        columns=["txid", "first_seen_us", "n_announcements", "is_coinbase"],
    )
    gossiped = txs.filter(~pl.col("is_coinbase"))
    announcements = txs["n_announcements"].sum() or 0
    mean = announcements / gossiped.height if gossiped.height else 0.0

    histogram = (
        gossiped.group_by("n_announcements").agg(pl.len().alias("count")).sort("n_announcements")
    )

    cap = pl.read_parquet(run_dir / "chain" / "transactions.parquet", columns=["block_height"])
    blocks = cap.group_by("block_height").agg(pl.len().alias("n")).sort("block_height")
    # Cap the sparkline at 2000 points; a series longer than the screen is noise either way.
    step = max(1, blocks.height // 2000)

    return {
        "rows_read": int(
            json.loads((run_dir / SEALED_DIR / "manifest.json").read_text("utf-8"))["rows_read"]
        ),
        "announcements": int(announcements),
        "transactions": int(gossiped.height),
        "echo": int(announcements - gossiped.height)
        if False
        else int(announcements - gossiped.height),
        "mean_announcements_per_tx": round(mean, 4),
        "histogram": [
            {"n": int(row["n_announcements"]), "count": int(row["count"])}
            for row in histogram.iter_rows(named=True)
        ],
        "blocks": {
            "heights": blocks["block_height"].to_list()[::step],
            "txs_per_block": blocks["n"].to_list()[::step],
        },
    }


# ---------------------------------------------------------------------------
# listTransactions


def transactions(run_dir: Path, limit: int, offset: int) -> dict[str, Any]:
    """A paged, txid-ordered transaction list. `offset`/`limit` are ints, never paths.

    `abstained` marks the txids whose ensemble origin estimate declined to name a peer, so
    the list can badge them; it is read once from the signals table and joined in, never
    recomputed per row.
    """
    txs = pl.read_parquet(
        run_dir / NORMALISED_DIR / "transactions.parquet",
        columns=[
            "txid",
            "first_seen_us",
            "n_announcements",
            "n_distinct_peers",
            "announce_spread_us",
            "total_out_sats",
            "fee_sats",
            "is_coinbase",
            "has_equal_outputs",
        ],
    ).sort("txid")
    total = txs.height
    page = txs.slice(offset, limit)
    estimates = pl.read_parquet(
        run_dir / SIGNALS_DIR / "origin_estimates.parquet",
        columns=["txid", "estimator", "abstain"],
    ).filter((pl.col("estimator") == ENSEMBLE) & pl.col("abstain"))
    abstained = set(estimates["txid"].unique().to_list())
    return {
        "total": int(total),
        "offset": offset,
        "limit": limit,
        "transactions": [
            {
                "txid": row["txid"],
                "txid_display": redact.redact_txid(str(row["txid"])),
                "first_seen_us": int(row["first_seen_us"]),
                "n_announcements": int(row["n_announcements"]),
                "n_distinct_peers": int(row["n_distinct_peers"]),
                "announce_spread_us": int(row["announce_spread_us"]),
                "total_out_sats": int(row["total_out_sats"]),
                "fee_sats": int(row["fee_sats"]),
                "is_coinbase": bool(row["is_coinbase"]),
                "has_equal_outputs": bool(row["has_equal_outputs"]),
                "abstained": row["txid"] in abstained,
            }
            for row in page.iter_rows(named=True)
        ],
    }


# ---------------------------------------------------------------------------
# getOriginEstimate


def origin_estimate(run_dir: Path, txid: str) -> dict[str, Any]:
    """The timeline fan's payload: one lane per announcing peer, ordered by first seen.

    `abstain` is computed from the ensemble rows: an abstaining transaction has no rank-1
    ensemble row by SHASTRA's rule, so absence is the abstain. The abstain reason names what
    the estimator refused on; a Tor exit peer is the case the console demo leans on.
    """
    announcements = pl.read_parquet(run_dir / NORMALISED_DIR / "announcements.parquet")
    rows = announcements.filter(pl.col("txid") == txid).sort("seen_us")
    if rows.height == 0:
        raise KeyError(txid)

    peers = pl.read_parquet(
        run_dir / NORMALISED_DIR / "peers.parquet",
        columns=["peer_ip", "asn", "as_org", "geo_country", "net_class"],
    )
    estimates = pl.read_parquet(
        run_dir / SIGNALS_DIR / "origin_estimates.parquet",
        columns=[
            "txid",
            "peer_ip",
            "p_origin",
            "rank",
            "margin",
            "abstain",
            "abstain_reason",
            "estimator",
            "features",
        ],
    )
    estimates = estimates.filter((pl.col("txid") == txid) & (pl.col("estimator") == ENSEMBLE))

    ranks = estimates.filter(pl.col("rank") == 1)
    abstain = ranks.height == 0
    reason = ""
    if abstain:
        abstained = estimates.filter(pl.col("abstain"))
        reason = str(abstained["abstain_reason"][0]) if abstained.height else "abstained"

    lane_info = peers.filter(pl.col("peer_ip").is_in(rows["peer_ip"].unique().to_list()))
    lane_map = {row["peer_ip"]: row for row in lane_info.iter_rows(named=True)}

    first_seen = int(rows["seen_us"][0])
    lane_first: dict[str, int] = {}
    lanes: list[dict[str, Any]] = []
    by_peer: dict[str, list[int]] = {}
    for row in rows.iter_rows(named=True):
        peer = str(row["peer_ip"])
        by_peer.setdefault(peer, []).append(int(row["seen_us"]) - first_seen)
        lane_first.setdefault(peer, int(row["seen_us"]))
    # Order lanes by each peer's own first announcement, which is the fan's reading order.
    order = sorted(by_peer, key=lambda peer: min(by_peer[peer]))
    for peer_ip in order:
        info = lane_map.get(peer_ip, {})
        estimate = estimates.filter(pl.col("peer_ip") == peer_ip).sort("rank")
        p = float(estimate["p_origin"][0]) if estimate.height else 0.0
        rank = int(estimate["rank"][0]) if estimate.height else 0
        lanes.append(
            {
                "peer_ip": peer_ip,
                "peer_ip_display": _redacted_ip(peer_ip),
                "peer_port": int(rows.filter(pl.col("peer_ip") == peer_ip)["peer_port"][0]),
                "asn": info.get("asn"),
                "as_org": info.get("as_org") or "",
                "geo_country": info.get("geo_country") or "",
                "net_class": info.get("net_class") or "",
                "first_seen_us": lane_first[peer_ip],
                "announcements_ms": by_peer[peer_ip],
                "p_origin": p,
                "rank": rank,
            }
        )

    leader = lanes[0] if not abstain and lanes else None
    runner = lanes[1] if not abstain and len(lanes) > 1 else None
    margin = 0.0
    if leader and runner and leader["rank"] and runner["rank"]:
        values = estimates.filter(pl.col("rank") <= 2).sort("rank")["p_origin"].to_list()
        margin = float(values[0]) - float(values[1]) if len(values) == 2 else 0.0

    # The feature panel reads the rank-1 candidate's own feature struct; empty on abstain.
    struct = ranks.sort("p_origin", descending=True)["features"][0] if ranks.height else {}
    window_ms = max((max(v) for v in by_peer.values() if v), default=0)
    return {
        "txid": txid,
        "txid_display": redact.redact_txid(txid),
        "estimator": ENSEMBLE,
        "abstain": abstain,
        "abstain_reason": reason,
        "first_seen_us": first_seen,
        "window_ms": window_ms,
        "features": _origin_features(struct),
        "p_origin": leader["p_origin"] if leader else 0.0,
        "origin_peer_display": leader["peer_ip_display"] if leader else "",
        "runner_up_display": runner["peer_ip_display"] if runner else "",
        "runner_up_p": runner["p_origin"] if runner else 0.0,
        "margin": margin,
        "lanes": lanes,
    }


def _origin_features(struct: dict[str, Any] | None) -> list[dict[str, str]]:
    """The rank-1 candidate's features as label/value/gloss rows, in reading order."""
    if not struct:
        return []
    out: list[dict[str, str]] = []
    for key, label, gloss in ORIGIN_FEATURE_GLOSS:
        if key not in struct:
            continue
        raw = struct[key]
        if isinstance(raw, bool):
            value = "yes" if raw else "no"
        elif key.endswith("_us"):
            value = f"{int(raw) / 1000:.1f} ms"
        elif isinstance(raw, float):
            value = f"{raw:.3f}"
        else:
            value = str(raw)
        out.append({"label": label, "value": value, "gloss": gloss})
    return out


# ---------------------------------------------------------------------------
# getGraph


def graph(run_dir: Path, detail: str, focus: str | None, cap: int) -> dict[str, Any]:
    """The fused graph, cluster-aggregated by default.

    `detail=cluster` aggregates addresses into their cluster nodes and says so in the
    `aggregated` block, which is the DRISHTI rule: never silently show a subset. `detail=address`
    returns the address-level subgraph up to `cap` nodes, ordered by degree so the cap keeps the
    connected core rather than a random fringe. `focus` is a node id (`addr:…`, `cluster:…`),
    and the response carries the edges incident to it one hop out.
    """
    nodes = pl.read_parquet(run_dir / GRAPH_DIR / "nodes.parquet")
    edges = pl.read_parquet(run_dir / GRAPH_DIR / "edges.parquet")

    if detail == "address":
        degrees = (
            edges.group_by("src")
            .agg(pl.len().alias("d"))
            .rename({"src": "node_id"})
            .vstack(
                edges.group_by("dst").agg(pl.len().alias("d")).rename({"dst": "node_id"}),
            )
            .group_by("node_id")
            .agg(pl.col("d").sum())
            .sort("d", descending=True)
        )
        kept = degrees.head(cap)["node_id"].to_list()
        if focus and focus not in kept:
            kept = kept[: max(cap - 1, 0)] + [focus]
        kept_set = set(kept)
        node_rows = nodes.filter(pl.col("node_id").is_in(kept))
        edge_rows = edges.filter(pl.col("src").is_in(kept_set) & pl.col("dst").is_in(kept_set))
        if focus:
            edge_rows = edge_rows.filter((pl.col("src") == focus) | (pl.col("dst") == focus))
            neighbours = set(edge_rows["src"].to_list()) | set(edge_rows["dst"].to_list())
            node_rows = nodes.filter(pl.col("node_id").is_in(neighbours))
            edge_rows = edges.filter(
                pl.col("src").is_in(neighbours) & pl.col("dst").is_in(neighbours)
            )
        aggregated = None
    else:
        clusters = pl.read_parquet(
            run_dir / GRAPH_DIR / "clusters.parquet",
            columns=["cluster_id", "n_addresses"],
        )
        # Cluster-level view: every cluster node, with transaction and peer nodes filling the
        # remaining budget. All clusters survive the cap so the aggregate claim stays true.
        cluster_rows = nodes.filter(pl.col("kind") == "cluster")
        remaining = max(cap - cluster_rows.height, 0)
        filler = (
            nodes.filter(pl.col("kind").is_in(["peer", "asn"])).head(remaining // 2)
            if remaining
            else nodes.head(0)
        )
        remaining -= filler.height
        tx_rows = (
            nodes.filter(pl.col("kind") == "transaction").head(remaining)
            if remaining
            else nodes.head(0)
        )
        node_rows = pl.concat([cluster_rows, filler, tx_rows])
        kept_set = set(node_rows["node_id"].to_list())
        edge_rows = edges.filter(pl.col("src").is_in(kept_set) & pl.col("dst").is_in(kept_set))
        addresses_in = int(clusters["n_addresses"].sum())
        aggregated = {
            "addresses": addresses_in,
            "clusters": clusters.height,
            "note": "AGGREGATED",
        }

    def node_kind(node_id: str) -> str:
        if node_id.startswith("addr:"):
            return "address"
        if node_id.startswith("cluster:"):
            return "cluster"
        if node_id.startswith("tx:"):
            return "transaction"
        if node_id.startswith("asn:"):
            return "asn"
        return "peer"

    return {
        "detail": detail,
        "node_cap": cap,
        "aggregated": aggregated,
        "nodes": [
            {
                "node_id": row["node_id"],
                "kind": node_kind(str(row["node_id"])),
                "label": _redacted_address(str(row["label"]))
                if str(row["node_id"]).startswith(("addr:", "cluster:"))
                else str(row["label"]),
                "first_us": row["first_us"],
                "last_us": row["last_us"],
            }
            for row in node_rows.iter_rows(named=True)
        ],
        "edges": [
            {
                "src": row["src"],
                "dst": row["dst"],
                "kind": str(row["kind"]),
                "ts_us": row["ts_us"],
                "sats": row["sats"],
                "confidence": float(row["confidence"]),
                "evidence": str(row["evidence"]),
            }
            for row in edge_rows.iter_rows(named=True)
        ],
    }


# ---------------------------------------------------------------------------
# listAlerts


def alerts(run_dir: Path, limit: int, offset: int, severity: str | None) -> dict[str, Any]:
    """The QUEUE table. Rank order is the pipeline's rank; nothing reorders here."""
    frame = pl.read_parquet(run_dir / ALERTS_DIR / "alerts.parquet")
    clusters = pl.read_parquet(
        run_dir / GRAPH_DIR / "clusters.parquet",
        columns=["cluster_id", "n_addresses"],
    )
    cluster_size = {row["cluster_id"]: row for row in clusters.iter_rows(named=True)}
    peers = pl.read_parquet(
        run_dir / NORMALISED_DIR / "peers.parquet",
        columns=["peer_ip", "asn", "geo_country"],
    )
    peer_map = {row["peer_ip"]: row for row in peers.iter_rows(named=True)}
    scores = pl.read_parquet(
        run_dir / SCORES_DIR / "wallet_scores.parquet",
        columns=["subject_id", "risk_score", "label"],
    )
    score_map = {row["subject_id"]: row for row in scores.iter_rows(named=True)}

    # The typologies each subject carries, collapsed to one sorted list per subject so the
    # queue can chip them. Read from the signals table SHASTRA wrote, not recomputed here.
    typ_path = run_dir / SIGNALS_DIR / "typology_hits.parquet"
    typ_map: dict[str, list[str]] = {}
    if typ_path.is_file():
        typ = pl.read_parquet(typ_path, columns=["subject_id", "typology"])
        grouped = typ.group_by("subject_id").agg(pl.col("typology").unique().sort())
        typ_map = {
            row["subject_id"]: list(row["typology"]) for row in grouped.iter_rows(named=True)
        }

    if severity:
        frame = frame.filter(pl.col("severity") == severity)
    total = frame.height
    page = frame.sort("rank").slice(offset, limit)

    items: list[dict[str, Any]] = []
    for row in page.iter_rows(named=True):
        subject_id = str(row["subject_id"])
        score = score_map.get(subject_id, {})
        origin_ip = row["origin_peer_ip"]
        origin_peer = peer_map.get(str(origin_ip), {}) if origin_ip is not None else {}
        size = 1
        cluster_row = cluster_size.get(subject_id) if subject_id.startswith("cluster:") else None
        if cluster_row is not None:
            size = int(cluster_row["n_addresses"])
        items.append(
            {
                "alert_id": str(row["alert_id"]),
                "rank": int(row["rank"]),
                "severity": str(row["severity"]),
                "risk_score": float(score.get("risk_score", 0.0)),
                "conf_low": float(row["conf_low"]),
                "conf_high": float(row["conf_high"]),
                "headline": str(row["headline"]),
                "subject_display": _redacted_address(subject_id),
                "cluster_size": size,
                "typologies": typ_map.get(subject_id, []),
                "origin_asn": origin_peer.get("asn"),
                "origin_country": origin_peer.get("geo_country") or "",
                "attribution_ready": bool(row["attribution_ready"]),
            }
        )
    return {"total": int(total), "offset": offset, "limit": limit, "alerts": items}


# ---------------------------------------------------------------------------
# getAlert


def alert(run_dir: Path, alert_id: str) -> dict[str, Any]:
    """The inspector: SHAP features, evidence, mandatory counter-evidence, confidence.

    Counter-evidence is mandatory by VAANI's rule, so an empty list here is a visible defect.
    The payload says so with `counters_ok` rather than letting the console infer it.
    """
    alerts = pl.read_parquet(run_dir / ALERTS_DIR / "alerts.parquet")
    row_frame = alerts.filter(pl.col("alert_id") == alert_id)
    if row_frame.height == 0:
        raise KeyError(alert_id)
    row = row_frame.iter_rows(named=True).__next__()

    evidence = pl.read_parquet(run_dir / ALERTS_DIR / "evidence.parquet").filter(
        pl.col("alert_id") == alert_id
    )
    counters = pl.read_parquet(run_dir / ALERTS_DIR / "counter.parquet").filter(
        pl.col("alert_id") == alert_id
    )

    features = [
        {
            "name": str(one["kind"]),
            "statement": str(one["statement"]),
            "weight": float(one["weight"]),
        }
        for one in evidence.filter(pl.col("kind") == "model_feature")
        .sort("weight", descending=True)
        .iter_rows(named=True)
    ]
    evidence_rows = [
        {
            "kind": str(one["kind"]),
            "statement": str(one["statement"]),
            "source_ref": str(one["source_ref"]),
        }
        for one in evidence.filter(pl.col("kind") != "model_feature").iter_rows(named=True)
    ]
    counter_rows = [
        {
            "kind": str(one["kind"]),
            "statement": str(one["statement"]),
            "strength": float(one["strength"]),
            "would_clear": bool(one["would_clear"]),
        }
        for one in counters.iter_rows(named=True)
    ]

    txid = row["origin_txid"]
    estimates = None
    if txid is not None:
        estimates = origin_estimate(run_dir, str(txid))

    subject_id = str(row["subject_id"])
    scores = pl.read_parquet(
        run_dir / SCORES_DIR / "wallet_scores.parquet",
        columns=["subject_id", "risk_score", "label", "coverage_target", "abstain"],
    ).filter(pl.col("subject_id") == subject_id)
    score = scores.iter_rows(named=True).__next__() if scores.height else {}
    report = _model_report(run_dir)
    coverage_by_class = report.get("coverage_by_class", {}) or {}
    # empirical_coverage and base_rate are eval-side statistics of the labelled truth. On an
    # air-gapped serve (measurements/ absent) they are genuinely not present in this copy, so
    # they degrade to null rather than a misleading 0.0. The per-subject conformal interval and
    # coverage_target below are read from the run itself and always render.
    empirical = coverage_by_class.get("1")
    base_rate = _base_rate(report) if report else None
    label = str(score.get("label", "UNCLEAR"))
    abstained = bool(score.get("abstain", False))
    confidence = {
        "score": float(score.get("risk_score", 0.0)),
        "low": float(row["conf_low"]),
        "high": float(row["conf_high"]),
        "coverage_target": float(score.get("coverage_target", 0.9)),
        "empirical_coverage": None if empirical is None else float(empirical),
        "label": "ABSTAIN · insufficient evidence"
        if abstained
        else LABEL_DISPLAY.get(label, label),
    }

    return {
        "alert_id": alert_id,
        "severity": str(row["severity"]),
        "conf_low": float(row["conf_low"]),
        "conf_high": float(row["conf_high"]),
        "headline": str(row["headline"]),
        "subject_display": _redacted_address(str(row["subject_id"])),
        "attribution_ready": bool(row["attribution_ready"]),
        "base_rate": base_rate,
        "confidence": confidence,
        "features": features,
        "evidence": evidence_rows,
        "counters": counter_rows,
        "counters_ok": bool(counter_rows),
        "origin": estimates,
    }


# ---------------------------------------------------------------------------
# getPacket


def packet(run_dir: Path, alert_id: str) -> dict[str, Any]:
    """The filed packet as JSON. Identifiers whole in machine fields, PDFs truncated.

    The signature, the three verification bits and the structured production notice are
    added here from the case's own signed artifacts: the console renders evidence the
    packet can prove, not claims it merely asserts.
    """
    from chakravyuh.pramaan import packet as pramaan_packet
    from chakravyuh.pramaan import stage as pramaan_stage

    case_dir = run_dir / PACKETS_DIR / alert_id
    path = case_dir / "packet.json"
    if not path.is_file():
        raise KeyError(alert_id)
    payload = dict(json.loads(path.read_text(encoding="utf-8")))
    # Compute the digest check on the pristine packet, before the display-only keys below
    # are added: verify_replay_field re-serializes the whole dict, so an extra key would
    # change the canonical bytes and fail a packet that is in fact intact.
    hash_verified = pramaan_packet.verify_replay_field(payload)
    payload["merkle_head"] = _merkle_head(run_dir)
    payload["replay_command"] = str(payload.get("replay", {}).get("command", ""))

    sig_path = case_dir / "packet.sig"
    payload["ed25519_signature"] = sig_path.read_bytes().hex() if sig_path.is_file() else ""

    keys_dir = Path("keys")
    signature_valid = False
    if sig_path.is_file() and (keys_dir / "ed25519.pub").is_file():
        try:
            signature_valid = pramaan_stage.verify_signature(case_dir, keys_dir)
        except Exception:  # noqa: BLE001 — a verification that errors is a failed verification
            signature_valid = False
    replay_matched = False
    try:
        replay_matched = pramaan_stage.verify_replay(run_dir, run_dir, alert_id, Path.cwd())
    except Exception:  # noqa: BLE001 — same: an errored replay is a replay that did not match
        replay_matched = False
    payload["verification"] = {
        "hash_verified": hash_verified,
        "signature_valid": signature_valid,
        "replay_matched": replay_matched,
    }
    payload["notice"] = _notice(payload)
    return payload


def _notice(payload: dict[str, Any]) -> dict[str, Any]:
    """The production notice as structured fields, mirroring `notice.pdf`.

    `exchange` is the operator the notice is served on — the network provider the origin
    attribution resolves to — not a crypto exchange. Identifiers stay in the redacted form
    the packet already carries.
    """
    legal = payload.get("legal", {})
    attribution = payload.get("attribution", {})
    peer = attribution.get("as_org") or "the network operator of record"
    return {
        "statute": str(legal.get("basis", "")),
        "exchange": str(peer),
        "requested_records": [
            "Subscriber and session records for the attributed network address at the "
            "observed time.",
            "RADIUS/DHCP assignment logs identifying the subscriber behind that address.",
            "Know-your-customer records and transaction statements for the attributed "
            "Bitcoin subject.",
        ],
    }
