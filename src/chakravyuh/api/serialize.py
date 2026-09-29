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
from typing import Any, Final

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


def _l1_row(run_dir: Path, txid: str) -> dict[str, Any]:
    """The ensemble L1 row for one origin transaction, or `{}` when absent.

    The operator-level attribution `asn_rollup` lifted off the ensemble's candidate mass,
    one row per transaction. Both the origin fan and the alert queue read it through here so
    the ASN/org/class/probability an investigator sees agree field for field.
    """
    path = run_dir / SIGNALS_DIR / "origin_l1.parquet"
    if not path.is_file():
        return {}
    l1 = pl.read_parquet(
        path,
        columns=[
            "txid",
            "origin_asn",
            "as_org",
            "net_class",
            "p_asn",
            "origin_country",
            "p_country",
            "margin",
            "shortlist_size",
            "estimator",
        ],
    ).filter((pl.col("txid") == txid) & (pl.col("estimator") == ENSEMBLE))
    return l1.iter_rows(named=True).__next__() if l1.height else {}


def _attribution(l1: dict[str, Any]) -> dict[str, Any]:
    """The L1-leading attribution block the origin and packet screens both render."""
    return {
        "asn": None if l1.get("origin_asn") is None else int(l1["origin_asn"]),
        "as_org": l1.get("as_org") or "",
        "net_class": l1.get("net_class") or "",
        "geo_country": l1.get("origin_country") or "",
        "p_asn": float(l1.get("p_asn", 0.0) or 0.0),
        "p_country": float(l1.get("p_country", 0.0) or 0.0),
        "margin": float(l1.get("margin", 0.0) or 0.0),
    }


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
    shortlist: list[dict[str, Any]] = []
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
        shortlist.append(
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

    leader = shortlist[0] if not abstain and shortlist else None
    runner = shortlist[1] if not abstain and len(shortlist) > 1 else None
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
        "attribution": _attribution(_l1_row(run_dir, txid)),
        "p_origin": leader["p_origin"] if leader else 0.0,
        "origin_peer_display": leader["peer_ip_display"] if leader else "",
        "runner_up_display": runner["peer_ip_display"] if runner else "",
        "runner_up_p": runner["p_origin"] if runner else 0.0,
        "margin": margin,
        "shortlist": shortlist,
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


# The actor floor's whole vocabulary. Money and announcements are on the other floor, and the
# point of this view is that it holds none of them: an analyst reading it is reading who owns
# what, not what moved.
ACTOR_NODE_KINDS: Final[tuple[str, ...]] = ("address", "cluster")
ACTOR_EDGE_KINDS: Final[tuple[str, ...]] = ("SAME_OWNER", "MEMBER_OF")
GRAPH_NODE_KINDS: Final[tuple[str, ...]] = ("address", "transaction", "peer", "cluster", "asn")
GRAPH_EDGE_KINDS: Final[tuple[str, ...]] = (
    "SPENDS",
    "RECEIVES",
    "ANNOUNCED_BY",
    "SAME_OWNER",
    "HOSTED_IN",
    "MEMBER_OF",
)


def _node_kind(node_id: str) -> str:
    """The kind of a node id, from its prefix. The graph's ids are the contract's."""
    if node_id.startswith("addr:"):
        return "address"
    if node_id.startswith("cluster:"):
        return "cluster"
    if node_id.startswith("tx:"):
        return "transaction"
    if node_id.startswith("asn:"):
        return "asn"
    return "peer"


# The shape an actor the graph never scored returns. Named rather than written inline twice,
# because both branches of `_actor_node_scores` must return the same keys: a console that
# destructures them should not have to know which branch produced the dict.
EMPTY_ACTOR_SCORES: Final[dict[str, Any]] = {
    "degree": 0,
    "weakest_confidence": None,
    "strongest_confidence": None,
    "cluster_id": None,
    "n_transactions": None,
    "n_coinjoin": None,
    "n_peel_hops": None,
    "peel_chains": [],
}


def _touched(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    """One row per (address, transaction) pair the money edges put together, with the two marks.

    The pairwise form, before anything is counted. Two callers group it two different ways — by
    address for the address scores, by cluster for the cluster scores — and both must count the
    same pairs, so the pairing is written once here rather than twice with a chance of drifting.
    """
    return (
        edges.filter(pl.col("kind").is_in(["SPENDS", "RECEIVES"]))
        .select(
            pl.when(pl.col("kind") == "SPENDS")
            .then(pl.col("src"))
            .otherwise(pl.col("dst"))
            .alias("node_id"),
            pl.when(pl.col("kind") == "SPENDS")
            .then(pl.col("dst"))
            .otherwise(pl.col("src"))
            .alias("tx_node"),
        )
        .join(
            nodes.filter(pl.col("kind") == "transaction").select(
                pl.col("node_id").alias("tx_node"), "coinjoin", "peel_chain_id"
            ),
            on="tx_node",
            how="inner",
        )
    )


def _activity(frame: pl.DataFrame, key: str) -> pl.DataFrame:
    """`frame` counted by `key`: transactions, and how many of them carry each mark.

    Counts of transactions, not of pairs: an address paid twice by one collaborative transaction
    counts once, and two addresses of one owner paying each other is one transaction for the
    owner. `n_unique` is what makes that true rather than a row count that happens to agree.
    """
    return frame.group_by(key).agg(
        pl.col("tx_node").n_unique().alias("n_transactions"),
        pl.col("tx_node").filter(pl.col("coinjoin")).n_unique().alias("n_coinjoin"),
        pl.col("tx_node")
        .filter(pl.col("peel_chain_id").is_not_null())
        .n_unique()
        .alias("n_peel_hops"),
        pl.col("peel_chain_id").drop_nulls().unique().sort().alias("peel_chains"),
    )


def _actor_scores(
    run_dir: Path, nodes: pl.DataFrame, edges: pl.DataFrame
) -> dict[str, dict[str, Any]]:
    """Per-actor scores, keyed by node id, for both actor kinds.

    An address's headline number is the confidence of the strongest `SAME_OWNER` edge it carries,
    and its degree counts those edges alone: counting the `MEMBER_OF` edge as well would count the
    same claim twice, once as a link and once as the cluster it puts the address in.

    Both ends of the confidence range are reported. The strongest edge says how well attested the
    address is at best; the weakest says what actually holds it in its cluster, and an address
    held by one confident edge and one coin-flip edge is not well attested at all.

    A cluster's degree is its member count, because its `MEMBER_OF` edges are exactly its members.
    Its activity is the sum over those members, deduplicated by transaction.
    """
    address_nodes = nodes.filter(pl.col("kind") == "address")
    cluster_nodes = nodes.filter(pl.col("kind") == "cluster")

    same_owner = edges.filter(pl.col("kind") == "SAME_OWNER")
    incident = pl.concat(
        [
            same_owner.select(pl.col("src").alias("node_id"), "confidence"),
            same_owner.select(pl.col("dst").alias("node_id"), "confidence"),
        ]
    )
    footing = incident.group_by("node_id").agg(
        pl.len().alias("degree"),
        pl.col("confidence").min().alias("weakest_confidence"),
        pl.col("confidence").max().alias("strongest_confidence"),
    )
    membership = (
        edges.filter(pl.col("kind") == "MEMBER_OF")
        .select(
            pl.col("src").alias("node_id"),
            pl.col("dst").alias("cluster_id"),
            pl.col("confidence").alias("membership_confidence"),
        )
        .unique(subset=["node_id"], keep="first")
    )
    touched = _touched(nodes, edges)

    addresses = (
        address_nodes.select(pl.col("node_id"))
        .join(footing, on="node_id", how="left")
        .join(membership, on="node_id", how="left")
        .join(_activity(touched, "node_id"), on="node_id", how="left")
        .with_columns(pl.col("degree").fill_null(0).cast(pl.Int32))
    )

    # A cluster's own facts come from `clusters.parquet`, which is where the derived view lives.
    # Reading them back off the `MEMBER_OF` edges instead would be a second implementation of the
    # aggregation, free to disagree with the file the console shows.
    cluster_facts = pl.read_parquet(
        run_dir / GRAPH_DIR / "clusters.parquet",
        columns=["cluster_id", "n_addresses", "min_edge_confidence"],
    )
    by_cluster = _activity(
        touched.join(membership.select("node_id", "cluster_id"), on="node_id", how="inner"),
        "cluster_id",
    )
    clusters = (
        # Keyed as `cluster_id` throughout and renamed at the end, because a join with
        # `left_on`/`right_on` keeps only the left key: naming the left side `node_id` would drop
        # the column the activity frame is about to be joined on.
        cluster_nodes.select(pl.col("node_id").alias("cluster_id"))
        .join(cluster_facts, on="cluster_id", how="left")
        .join(by_cluster, on="cluster_id", how="left")
        .with_columns(
            # A cluster's degree is its membership, and its confidence footing is the weakest
            # edge holding it together — the same number `clusters.parquet` reports, not a second
            # reading of it.
            pl.col("n_addresses").fill_null(0).cast(pl.Int32).alias("degree"),
            pl.col("min_edge_confidence").alias("weakest_confidence"),
            pl.col("min_edge_confidence").alias("strongest_confidence"),
        )
        .rename({"cluster_id": "node_id"})
    )

    combined = pl.concat([addresses, clusters], how="diagonal_relaxed")
    return {str(row["node_id"]): row for row in combined.iter_rows(named=True)}


def _actor_graph(
    run_dir: Path, nodes: pl.DataFrame, edges: pl.DataFrame, focus: str | None, cap: int
) -> dict[str, Any]:
    """The ownership floor: addresses, the clusters they sit in, and the edges between them.

    Two node kinds and two edge kinds, and the response names what it left out rather than leaving
    the caller to notice. The cluster view already aggregates addresses away and the address view
    already carries the money; this is the view where an owner is the unit, so a `SPENDS` edge from
    an address to a transaction has no place in it.

    The cap is split between the two kinds, because spending it on one would make the view useless
    in exactly the case it is most needed. A large run holds more clusters than the console has
    budget for nodes, and a cluster list with no addresses in it answers no question an analyst
    has. So the biggest clusters take at most half, by member count, and addresses take the rest by
    degree. Both totals and both shown-counts are in the `aggregated` block: this view is a subset
    and says so in numbers.

    Within each kind the order is total, with the node id breaking ties, so two runs of one seed
    keep the same nodes and the cap is not a source of drift.
    """
    scores = _actor_scores(run_dir, nodes, edges)
    actor_edges = edges.filter(pl.col("kind").is_in(ACTOR_EDGE_KINDS))
    cluster_nodes = nodes.filter(pl.col("kind") == "cluster")
    address_nodes = nodes.filter(pl.col("kind") == "address")

    def by_degree(node_ids: list[str]) -> list[str]:
        return sorted(
            node_ids,
            key=lambda node_id: (-int(scores.get(node_id, {}).get("degree") or 0), node_id),
        )

    kept_clusters = by_degree(cluster_nodes["node_id"].to_list())[: max(cap // 2, 0)]
    # A kept cluster whose members are not also kept is a claim with nothing under it, and a
    # console reading this view would draw a cluster of one. So the members of the clusters that
    # were kept are ranked first for the address budget, and only what is left goes to the most
    # connected addresses elsewhere in the graph.
    kept_cluster_set = set(kept_clusters)
    members = sorted(
        set(
            actor_edges.filter(
                (pl.col("kind") == "MEMBER_OF") & pl.col("dst").is_in(kept_cluster_set)
            )["src"].to_list()
        )
    )
    address_budget = max(cap - len(kept_clusters), 0)
    kept_addresses = by_degree(members)[:address_budget]
    if len(kept_addresses) < address_budget:
        already = set(kept_addresses)
        kept_addresses += [
            node_id
            for node_id in by_degree(address_nodes["node_id"].to_list())
            if node_id not in already
        ][: address_budget - len(kept_addresses)]
    kept = kept_clusters + kept_addresses

    if focus:
        # One hop out over the actor edges, and the neighbourhood is *shown* rather than
        # intersected with the capped set: a caller who named a node is asking what it is attached
        # to, and answering with the one node it named says nothing. The neighbourhood is bounded
        # by the focus's own degree, so this cannot run away, and the `aggregated` counts below
        # report what was returned either way.
        incident = actor_edges.filter((pl.col("src") == focus) | (pl.col("dst") == focus))
        neighbourhood = set(incident["src"].to_list()) | set(incident["dst"].to_list())
        actor_ids = set(address_nodes["node_id"].to_list()) | set(
            cluster_nodes["node_id"].to_list()
        )
        kept = sorted((neighbourhood & actor_ids) | {focus})

    kept_set = set(kept)
    node_rows = nodes.filter(pl.col("node_id").is_in(kept_set))
    edge_rows = actor_edges.filter(pl.col("src").is_in(kept_set) & pl.col("dst").is_in(kept_set))

    return {
        "detail": "actor",
        "node_cap": cap,
        "focus": focus,
        "aggregated": {
            "addresses": sum(1 for node_id in kept if node_id.startswith("addr:")),
            "total_addresses": address_nodes.height,
            "clusters": sum(1 for node_id in kept if node_id.startswith("cluster:")),
            "total_clusters": cluster_nodes.height,
            "note": "AGGREGATED",
            "node_kinds": list(ACTOR_NODE_KINDS),
            "omitted_node_kinds": sorted(set(GRAPH_NODE_KINDS) - set(ACTOR_NODE_KINDS)),
            "edge_kinds": list(ACTOR_EDGE_KINDS),
            "omitted_edge_kinds": sorted(set(GRAPH_EDGE_KINDS) - set(ACTOR_EDGE_KINDS)),
        },
        "nodes": [
            {
                "node_id": row["node_id"],
                "kind": _node_kind(str(row["node_id"])),
                "label": _redacted_address(str(row["label"])),
                "first_us": row["first_us"],
                "last_us": row["last_us"],
                "scores": _actor_node_scores(str(row["node_id"]), scores),
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


def _actor_node_scores(node_id: str, scores: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """One actor's scores, with a null wherever the graph has nothing to say.

    `null` and `0` are different answers and are kept apart: an address with no transactions in
    this capture has an unknown transaction count, not a count of zero, and an address no
    `SAME_OWNER` edge touches has no confidence rather than a confidence of nothing.
    """
    found = scores.get(node_id)
    if found is None:
        return dict(EMPTY_ACTOR_SCORES)
    return {
        "degree": int(found["degree"] or 0),
        "weakest_confidence": found["weakest_confidence"],
        "strongest_confidence": found["strongest_confidence"],
        "cluster_id": found["cluster_id"],
        "n_transactions": found["n_transactions"],
        "n_coinjoin": found["n_coinjoin"],
        "n_peel_hops": found["n_peel_hops"],
        "peel_chains": found["peel_chains"] or [],
    }


def graph(run_dir: Path, detail: str, focus: str | None, cap: int) -> dict[str, Any]:
    """The fused graph, cluster-aggregated by default.

    `detail=cluster` aggregates addresses into their cluster nodes and says so in the
    `aggregated` block, which is the DRISHTI rule: never silently show a subset. `detail=address`
    returns the address-level subgraph up to `cap` nodes, seeded on the transactions by degree and
    grown to their addresses and to the peers that announced them, so the cap keeps a connected
    core rather than a random fringe. `detail=actor` is the second floor: the ownership
    graph on its own — addresses and the clusters the heuristics place them in, and nothing else.
    `focus` is a node id (`addr:…`, `cluster:…`), and the response carries the edges incident to
    it one hop out.
    """
    nodes = pl.read_parquet(run_dir / GRAPH_DIR / "nodes.parquet")
    edges = pl.read_parquet(run_dir / GRAPH_DIR / "edges.parquet")

    if detail == "actor":
        return _actor_graph(run_dir, nodes, edges, focus, cap)

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
            # Node id breaks the ties, and not for tidiness: a bare sort by degree leaves nodes of
            # equal degree in whatever order the group-by happened to produce, which differs between
            # two calls in one process, so the same view answered twice would pick different nodes.
            .sort(["d", "node_id"], descending=[True, False])
        )
        # Degree, most to least, and the kind of each node. Everything below is chosen from these
        # two, so the cap keeps the connected core rather than a fringe.
        order = degrees["node_id"].to_list()
        rank = {node_id: i for i, node_id in enumerate(order)}
        kind_of = dict(zip(nodes["node_id"], nodes["kind"], strict=True))

        def ranked(kind: str) -> list[str]:
            return [node_id for node_id in order if kind_of.get(node_id) == kind]

        # The cap is spent from the middle out, because no single ranking by degree serves this
        # view. A peer carries one edge per announcement — around three hundred apiece in this
        # world — against an address's couple of payments, so the top five hundred nodes here are
        # 497 peers, 3 operators and not one address. The view is the two-floor graph, so it is
        # assembled the way the floors are drawn: the money, then the wire that announced it, then
        # the operators and the hulls those two sit in.
        # Tag-alongs are allowed a tenth of the budget each, so a fifth between them: an operator in
        # the peer panel, a hull around the addresses that are on screen. A quarter goes to the
        # announcers, whose edges are the only ones that cross floors. The money takes the rest,
        # which is what is left to say after the arithmetic rather than a share of its own, because
        # it is the one thing the view must not run out of.
        tag_budget = max(cap // 10, 0)
        peer_budget = max(cap // 4, 0)
        money_budget = max(cap - 2 * tag_budget - peer_budget, 0)

        # Money. A transaction moves the value and the addresses only appear because of one, so the
        # seeds are transactions by degree and each brings a couple of its addresses with it — the
        # one that paid it and the one it paid. Ranking the two kinds independently is what leaves
        # this floor disconnected: hundreds of transactions and hundreds of addresses, no edge
        # between any of them, because a well-connected transaction and a well-connected address
        # are almost never each other's.
        money = (
            edges.filter(pl.col("kind").is_in(["SPENDS", "RECEIVES"]))
            .select(
                pl.when(pl.col("kind") == "SPENDS")
                .then(pl.col("dst"))
                .otherwise(pl.col("src"))
                .alias("tx"),
                pl.when(pl.col("kind") == "SPENDS")
                .then(pl.col("src"))
                .otherwise(pl.col("dst"))
                .alias("addr"),
            )
            .unique()
        )
        paid_by = {
            tx: sorted(addrs, key=lambda addr: rank.get(addr, len(order)))
            for tx, addrs in money.group_by("tx").agg(pl.col("addr")).iter_rows()
        }
        per_tx = 2
        kept: list[str] = []
        addresses: list[str] = []
        money_left = money_budget
        for tx in ranked("transaction"):
            if money_left <= 0:
                break
            kept.append(tx)
            money_left -= 1
            for addr in paid_by.get(tx, ())[:per_tx]:
                if money_left <= 0:
                    break
                kept.append(addr)
                addresses.append(addr)
                money_left -= 1

        # Wire. The peers that announced the transactions just chosen, not the peers that announced
        # the most: this edge is the fusion the two floors exist to show, so it has to land on the
        # money actually on screen. The announcers of a few hundred transactions are still a
        # handful of relays apiece — the 93% echo, made visible.
        announcers = (
            edges.filter((pl.col("kind") == "ANNOUNCED_BY") & pl.col("src").is_in(set(kept)))
            .select(pl.col("dst").alias("node_id"))
            .unique()
        )
        peers = sorted(announcers["node_id"].to_list(), key=lambda p: rank.get(p, len(order)))[
            :peer_budget
        ]

        # Operators and hulls, in that order of need: an ASN rides in the peer panel, and a cluster
        # is a hull drawn around addresses, so both are chosen by what is already on screen rather
        # than by size — a hull around nothing is a circle.
        hosted = (
            edges.filter((pl.col("kind") == "HOSTED_IN") & pl.col("src").is_in(set(peers)))
            .select(pl.col("dst").alias("node_id"))
            .unique()["node_id"]
            .to_list()
        )
        asns = sorted(hosted, key=lambda a: rank.get(a, len(order)))[:tag_budget]

        joined = (
            edges.filter((pl.col("kind") == "MEMBER_OF") & pl.col("src").is_in(set(addresses)))
            .select(pl.col("dst").alias("node_id"))
            .unique()["node_id"]
            .to_list()
        )
        clusters = sorted(joined, key=lambda c: rank.get(c, len(order)))[:tag_budget]

        kept += peers + asns + clusters
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
        cluster_facts = pl.read_parquet(
            run_dir / GRAPH_DIR / "clusters.parquet",
            columns=["cluster_id", "n_addresses"],
        )
        # Cluster-level view: the largest clusters, with transaction and peer nodes filling the
        # rest of the budget. Letting every cluster through was fine while a run held fewer
        # clusters than the cap; at this run's scale it evicts every other node kind and leaves
        # the console a field of isolated dots, because nothing on this floor draws an edge
        # between two clusters — they attach to addresses, which are aggregated away here. So the
        # clusters are ranked by membership and take at most half the budget, the same split the
        # actor view uses for the same reason.
        by_size = cluster_facts.sort(["n_addresses", "cluster_id"], descending=[True, False])
        shown = by_size.head(max(cap // 2, 0))
        cluster_rows = nodes.filter(pl.col("node_id").is_in(shown["cluster_id"]))
        remaining = max(cap - cluster_rows.height, 0)
        # Operators before peers: the network kinds are written in file order and the ASNs are last,
        # so one `head` over both of them drops all ten and with them every HOSTED_IN edge — the
        # layer the operator attribution rides on. There are only ever a handful, so they are taken
        # first and the peers fill what is left.
        asn_rows = nodes.filter(pl.col("kind") == "asn").head(remaining)
        remaining -= asn_rows.height
        filler = (
            nodes.filter(pl.col("kind") == "peer").head(remaining // 2)
            if remaining
            else nodes.head(0)
        )
        remaining -= filler.height
        tx_rows = (
            nodes.filter(pl.col("kind") == "transaction").head(remaining)
            if remaining
            else nodes.head(0)
        )
        node_rows = pl.concat([cluster_rows, asn_rows, filler, tx_rows])
        kept_set = set(node_rows["node_id"].to_list())
        edge_rows = edges.filter(pl.col("src").is_in(kept_set) & pl.col("dst").is_in(kept_set))
        addresses_in = int(shown["n_addresses"].sum())
        aggregated = {
            # The convention the actor view uses, for the same reason: what is on screen, and the
            # totals it is a subset of. `clusters` was the total back when every cluster survived
            # the cap, and on a run with more clusters than nodes that number would be a lie told
            # by omission — the console would print 6,532 over a picture of 1,000.
            "addresses": addresses_in,
            "total_addresses": int(by_size["n_addresses"].sum()),
            "clusters": cluster_rows.height,
            "total_clusters": by_size.height,
            "note": "AGGREGATED",
        }

    return {
        "detail": detail,
        "node_cap": cap,
        "aggregated": aggregated,
        "nodes": [
            {
                "node_id": row["node_id"],
                "kind": _node_kind(str(row["node_id"])),
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
    # The operator-level attribution per origin transaction, read once and joined by txid.
    # The alert queue leads with L1 (the network operator), so the exact host IP is not read
    # here at all — it lives only inside the officer packet.
    l1_path = run_dir / SIGNALS_DIR / "origin_l1.parquet"
    l1_map: dict[str, dict[str, Any]] = {}
    if l1_path.is_file():
        l1_frame = pl.read_parquet(
            l1_path,
            columns=[
                "txid",
                "origin_asn",
                "as_org",
                "net_class",
                "p_asn",
                "origin_country",
                "shortlist_size",
                "estimator",
            ],
        ).filter(pl.col("estimator") == ENSEMBLE)
        l1_map = {str(row["txid"]): row for row in l1_frame.iter_rows(named=True)}
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
        origin_txid = row["origin_txid"]
        l1 = l1_map.get(str(origin_txid), {}) if origin_txid is not None else {}
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
                "origin_asn": None if l1.get("origin_asn") is None else int(l1["origin_asn"]),
                "origin_as_org": l1.get("as_org") or "",
                "origin_net_class": l1.get("net_class") or "",
                "origin_country": l1.get("origin_country") or "",
                "p_asn": float(l1.get("p_asn", 0.0) or 0.0),
                "shortlist_k": int(l1.get("shortlist_size", 0) or 0),
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


# ---------------------------------------------------------------------------
# getWorld

# Cited, documented constants — not measured results of this run. The literature band is the
# 11–60% observer-fraction range the deanonymisation literature sweeps; the defences name the
# four honesty checks the project stands on. They describe the method, so they live in code,
# not in a measurement file, and the run's own numbers below are read, never hand-typed.
LITERATURE_BAND: tuple[float, float] = (0.11, 0.60)
DEFENCES: tuple[str, ...] = (
    "observer curve",
    "elliptic replication",
    "real-slice",
    "parameter holdout",
)

# The phase-3 graph-embedding leg as the audit recorded it. This run did NOT run the leg —
# `eval_report.embedding_leg` says `reason: embeddings_not_requested` — so there is no file to
# read them from and no honest way to recompute them here. The two numbers are the recorded
# result of that one throwaway run, published in docs/REMODEL-AUDIT-P0-P3.md §3.1, and they are
# stated as a citation rather than dressed up as this run's measurement. `gate` is the word the
# pipeline's own checker wrote: the leg scored every subject and still lost, so the columns are
# wired off and a checker turns red if anyone ships them.
REJECTED_LEG: dict[str, Any] = {
    "with_embeddings_pr_auc": 0.0357,
    "without_embeddings_pr_auc": 0.0373,
    "gate": "baseline_not_beaten",
}
# Published Elliptic F1 ranges for the two alternatives, cited and never measured by us
# (Grinsztajn et al., NeurIPS 2022; Weber et al., 2019). The console draws our own 0.766 against
# these, so the payload has to keep them apart from `ours` — a band we did not produce is not a
# number we get to own.
PUBLISHED_BANDS: dict[str, list[float]] = {"gnn_f1": [0.70, 0.82], "rf_f1": [0.60, 0.70]}

# The pipeline, one row per landing layer, each count read from the artifact that proves the
# stage ran. `label` is the plain word the console prints; the story's round 1,000,000 is never
# faked — these are the run's real counts, so a small demo run reads as a small run, honestly.
# This is a PIPELINE, not a shrinking funnel: it branches at BUDDHI, where one transaction can
# leave several owner groups scored, so a later row can honestly outnumber an earlier one.
FUNNEL_STAGES: tuple[tuple[str, str, str], ...] = (
    ("globe", "signals", "MAYAJAAL"),
    ("intake", "sealed", "KAVACH"),
    ("untangle", "announcements", "SETU"),
    ("map", "transactions", "JAAL"),
    ("origin", "with a candidate", "SHASTRA"),
    ("buddhi", "owner groups scored", "BUDDHI"),
    ("leads", "ranked leads", "VAANI"),
    ("proof", "court-ready proofs", "PRAMAAN"),
)


def _origin_report(run_dir: Path) -> dict[str, Any]:
    """This run's origin accuracy report, or `{}` before it was measured."""
    path = Path("measurements") / run_dir.name / "origin_accuracy.json"
    if not path.is_file():
        return {}
    return dict(json.loads(path.read_text("utf-8")))


def _pair_precision(run_dir: Path) -> float | None:
    """The measured same-owner pair precision over the addresses the stage observed.

    Read from `cluster_metrics.pair_precision`, whose own `metric_note` warns it is NOT the
    full-cluster 0.36/0.44 the contract quotes. The console labels it for what it is, so the field
    is named `pair_precision` too — the name `cluster_confidence` would collide with §11's 0.36
    anchor, which is a different quantity.
    """
    path = Path("measurements") / run_dir.name / "cluster_metrics.json"
    if not path.is_file():
        return None
    metrics = json.loads(path.read_text("utf-8"))
    value = metrics.get("pair_precision")
    return None if value is None else float(value)


def _run_eval_report(run_dir: Path) -> dict[str, Any]:
    """The stage's own rolled-up eval report, or `{}` before BUDDHI wrote one.

    `scores/eval_report.json` is the pipeline's artifact (written by the stage, travels with
    the run); `measurements/<run>/model_report.json` is eval's external copy of the same
    measurement. Prefer the stage's, fall back to eval's, so a run that was scored but not
    re-measured still reports its numbers rather than a wall of nulls.
    """
    path = run_dir / SCORES_DIR / "eval_report.json"
    if path.is_file():
        return dict(json.loads(path.read_text("utf-8")))
    return _model_report(run_dir)


def _recoverable_ceiling(run_dir: Path) -> float | None:
    """The fraction of transactions the observed world even contains the answer for.

    This is the honesty ceiling, not an accuracy: a run whose observers never heard the true
    announcer cannot name it however good the model is. None when not measured (null ≠ 0).
    """
    value = _origin_report(run_dir).get("recoverable_ceiling")
    return None if value is None else float(value)


def _n_scored(run_dir: Path) -> int:
    """Owner groups BUDDHI scored, read without materialising the table."""
    path = run_dir / SCORES_DIR / "wallet_scores.parquet"
    if not path.is_file():
        return 0
    return int(pl.scan_parquet(path).select(pl.len()).collect().item())


def _elliptic_metric(run_dir: Path, key: str) -> float | None:
    """One score from the external-replication block, or None when that leg did not run.

    `elliptic_external` has two shapes (§7.3): when `available` is false the block carries
    only a `reason`. An absent external validation and a model that scored zero on it are
    opposite claims, so this returns None and the console drops the defence instead of
    printing a zero it cannot stand behind.
    """
    block = _run_eval_report(run_dir).get("elliptic_external")
    if not isinstance(block, dict) or not block.get("available"):
        return None
    value = block.get(key)
    return None if value is None else float(value)


def _elliptic_f1(run_dir: Path) -> float | None:
    """The external-replication F1 — the headline of the Elliptic leg."""
    return _elliptic_metric(run_dir, "f1")


def _ceiling_by_granularity(run_dir: Path) -> dict[str, float | None]:
    """The honesty ceiling at each granularity, keyed as the origin report keys them.

    One scalar ceiling is not enough to state the reframe: the exact host is capped far
    below the operator (most observers never heard the announcing host at all), and the
    operator is what the console actually claims. The gauge that divides our accuracy by
    "the most any estimator could score" must divide it by the ceiling of the SAME grain,
    or it flatters itself. Absent grains report None, never 0.0 (null ≠ 0).
    """
    by_grain = _origin_report(run_dir).get("by_granularity", {})
    ceilings: dict[str, float | None] = {}
    for grain in ("l0_host", "l1_asn", "l2_region", "l3_shortlist_topk"):
        node = by_grain.get(grain) or {}
        value = node.get("recoverable_ceiling")
        ceilings[grain] = None if value is None else float(value)
    return ceilings


def _campaign_recall(run_dir: Path) -> float | None:
    """Held-out campaign recall, the headline of the wallet model, or None when unmeasured."""
    wallet = _run_eval_report(run_dir).get("wallet_model")
    if not isinstance(wallet, dict):
        return None
    value = wallet.get("campaign_recall")
    return None if value is None else float(value)


def _curve_point(report: dict[str, Any], grain: str, kind: str) -> dict[str, Any] | None:
    """One observer-fraction point for a granularity, from a single origin report.

    `kind` picks the shape the frontend curve expects: the host/operator lines carry
    top1+abstain, the shortlist line carries topk+k. None when the grain is absent, so the
    caller drops it rather than plotting a zero it never measured.
    """
    node = report.get("by_granularity", {}).get(grain)
    if not node:
        return None
    fraction = float(report.get("observer_fraction", 0.0))
    ensemble = node.get("scores", {}).get(ENSEMBLE, {})
    if kind == "shortlist":
        return {
            "fraction": fraction,
            "topk": float(ensemble.get("topk", 0.0)),
            "k": int(node.get("k", 0)),
        }
    return {
        "fraction": fraction,
        "top1": float(ensemble.get("top1", 0.0)),
        "abstain": float(ensemble.get("abstain_rate", 0.0)),
    }


def _origin_curve(run_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """The observer-fraction curve per granularity, one point per measured run.

    This run's own report is always a point; any sibling `measurements/*sweep*` reports are
    folded in and sorted by fraction, so a real sweep draws a curve and a single run draws a
    single honest dot. Every point is measured — nothing is interpolated or invented.
    """
    reports = [_origin_report(run_dir)]
    for path in sorted(Path("measurements").glob("*sweep*/origin_accuracy.json")):
        reports.append(dict(json.loads(path.read_text("utf-8"))))
    curve: dict[str, list[dict[str, Any]]] = {"l0_host": [], "l1_asn": [], "l3_shortlist": []}
    seen: dict[str, set[float]] = {key: set() for key in curve}
    for report in reports:
        if not report:
            continue
        for key, grain, kind in (
            ("l0_host", "l0_host", "top1"),
            ("l1_asn", "l1_asn", "top1"),
            ("l3_shortlist", "l3_shortlist_topk", "shortlist"),
        ):
            point = _curve_point(report, grain, kind)
            if point and point["fraction"] not in seen[key]:
                curve[key].append(point)
                seen[key].add(point["fraction"])
    for key in curve:
        curve[key].sort(key=lambda p: p["fraction"])
    return curve


def _funnel(run_dir: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    """The run's real stage counts, each read from the artifact that proves the stage ran."""
    manifest_json = dict(json.loads((run_dir / SEALED_DIR / "manifest.json").read_text("utf-8")))
    announcements = 0
    ann_path = run_dir / NORMALISED_DIR / "announcements.parquet"
    if ann_path.is_file():
        announcements = int(pl.scan_parquet(ann_path).select(pl.len()).collect().item())
    alerts_count = 0
    alerts_path = run_dir / ALERTS_DIR / "alerts.parquet"
    if alerts_path.is_file():
        alerts_count = int(pl.scan_parquet(alerts_path).select(pl.len()).collect().item())
    proof = 0
    log_path = run_dir / PACKETS_DIR / "merkle.log"
    if log_path.is_file():
        from chakravyuh.pramaan import merkle

        leaves, _ = merkle.read(log_path)
        proof = len(leaves)
    counts = {
        "globe": int(manifest_json.get("rows_read", 0)),
        "intake": int(manifest_json.get("rows_sealed", 0)),
        "untangle": announcements,
        "map": _n_transactions(run_dir),
        "origin": int(report.get("transactions_with_a_candidate", _n_transactions(run_dir))),
        "buddhi": _n_scored(run_dir),
        "leads": alerts_count,
        "proof": proof,
    }
    return [
        {"stage": stage, "label": label, "layer": layer, "count": counts[stage]}
        for stage, label, layer in FUNNEL_STAGES
    ]


def _shipped_model(run_dir: Path) -> str:
    """The model tag that actually scored this run's rows, or "" when nothing recorded one.

    Read from eval's external copy, which is the artifact that carries `params`; the stage's own
    `scores/eval_report.json` does not. The panel names what shipped from here rather than from a
    string typed into the frontend, so a run scored by a different booster cannot be mislabelled
    by a stale component.
    """
    params = _model_report(run_dir).get("params", {})
    return str(params.get("model", "")) if isinstance(params, dict) else ""


def _model_intelligence(run_dir: Path) -> dict[str, Any]:
    """The model-comparison panel's numbers, each one labelled by where it came from.

    Four different kinds of claim sit on one panel and the console must not blur them, so the
    payload keeps them under separate keys rather than flattening them into one scoreboard:

    `ours` — this run's own measurements (the external Elliptic replication and the wallet
    model's precision@20), read from the eval report like every other number here. Null when the
    leg that produces one did not run: an absent measurement is not a zero.

    `shipped_model` — the model tag the report recorded, so the panel names what actually ships
    instead of a name typed into the frontend.

    `rejected_leg` / `published_bands` — a recorded result and cited literature, both constants
    above. They are here so the frontend holds no numbers of its own; a figure the console prints
    is traceable to this file or to an artifact, never to a component.
    """
    report = _run_eval_report(run_dir)
    model = report.get("wallet_model", {})
    precision_at_20 = model.get("precision_at_20") if isinstance(model, dict) else None
    return {
        "ours": {
            "elliptic_f1": _elliptic_f1(run_dir),
            "elliptic_pr_auc": _elliptic_metric(run_dir, "pr_auc"),
            "elliptic_roc_auc": _elliptic_metric(run_dir, "roc_auc"),
            "precision_at_20": None if precision_at_20 is None else float(precision_at_20),
        },
        "shipped_model": _shipped_model(run_dir),
        "rejected_leg": dict(REJECTED_LEG),
        "published_bands": {key: list(band) for key, band in PUBLISHED_BANDS.items()},
    }


def world(run_dir: Path) -> dict[str, Any]:
    """WORLD/ceiling payload: the run's pipeline, origin curve and headline numbers.

    Every number is this run's own measurement — the World station and the Origin ceiling
    gauge read here instead of hardcoding the ceiling / naive baseline / accuracy band.
    `campaign_recall` and `elliptic_f1` come from the run's eval report, and stay null only when
    the leg that measures them did not run (null ≠ 0); the console then renders not-measured
    rather than a zero it can't stand behind. `pair_precision` is the measured same-owner pair
    precision — not the 0.36 cluster-confidence anchor, which is a different quantity.

    `recoverable_ceiling` is the honesty ceiling — the fraction of transactions the observed
    world even contains the answer for — and is read at THIS run's observer fraction, so a
    less-observed world honestly reports a lower ceiling.
    """
    report = _origin_report(run_dir)
    by_grain = report.get("by_granularity", {})
    l1 = by_grain.get("l1_asn", {}).get("scores", {}).get(ENSEMBLE, {})
    l0 = by_grain.get("l0_host", {}).get("scores", {}).get(ENSEMBLE, {})
    naive = report.get("scores", {}).get("first_seen", {})
    fraction = float(report.get("observer_fraction", 0.0))
    regime = "agency" if fraction >= 0.5 else "sparse"
    return {
        "run_id": str(report.get("run_id", run_dir.name)),
        "observer_regime": regime,
        "observer_fraction": fraction,
        "protocol": str(_run_eval_report(run_dir).get("protocol", "")),
        "funnel": _funnel(run_dir, report),
        "recoverable_ceiling": _recoverable_ceiling(run_dir),
        "ceilings": _ceiling_by_granularity(run_dir),
        "origin_curve": _origin_curve(run_dir),
        "naive_first_seen_top1": float(naive.get("top1", 0.0)),
        "literature_band": list(LITERATURE_BAND),
        "headline": {
            "l1_top1": float(l1.get("top1", 0.0)),
            "l0_top1": float(l0.get("top1", 0.0)),
            "campaign_recall": _campaign_recall(run_dir),
            "elliptic_f1": _elliptic_f1(run_dir),
            "elliptic_roc_auc": _elliptic_metric(run_dir, "roc_auc"),
            "elliptic_precision": _elliptic_metric(run_dir, "precision"),
            "pair_precision": _pair_precision(run_dir),
        },
        "defences": list(DEFENCES),
        "model_intelligence": _model_intelligence(run_dir),
    }
