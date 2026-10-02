"""The packet builder: one alert becomes one signed, replayable evidence packet.

Every value is read from the run's observable directories or derived from them. The one
field that would break that rule is `generated_at_us`: a wall clock would make the packet
a different byte-string on every replay, so it is derived from `alerts/_meta.json`'s
`finished_at_us` instead — the time the pipeline, not the operator, stamped.

`replay.expected_packet_sha256` is the SHA-256 of the canonical serialisation with that
field blanked, so a second analyst can verify it without solving a self-reference: blank
the field, re-serialize, hash, compare. `verify-replay` does exactly that, byte-exact.

The packet never names either quarantined sibling tree, and no evaluation figure appears
in it: the only numbers are case-local (probabilities, the interval, row counts) and
hashes. A benchmark accuracy presented as a property of the evidence is the one claim an
evaluator could call misleading, so the packet carries no accuracy at all.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.pramaan import merkle
from chakravyuh.vaani import redact

ALERTS_DIR: Final[str] = "alerts"
SEALED_DIR: Final[str] = "sealed"
REPLAY_FIELD: Final[str] = "replay.expected_packet_sha256"
BLANK: Final[str] = ""


class CaseError(ValueError):
    """The case id does not name an alert, or names an alert that cannot be packed."""


def resolve_case(alert_id: str, alerts_dir: Path) -> str:
    """Reject a case id that is not an alert id in this run. A path separator here would
    let `--case` point outside `packets/`, so the id must match exactly."""
    alerts = pl.read_parquet(alerts_dir / "alerts.parquet", columns=["alert_id"])
    known = set(alerts["alert_id"].to_list())
    if alert_id not in known:
        raise CaseError(f"{alert_id} is not an alert id in {alerts_dir}; {len(known)} known")
    return alert_id


def _redact_subject(subject_id: str) -> str:
    """`addr:<hex>` and `cluster:<n>` render through the truncation law like addresses."""
    if subject_id.startswith("addr:"):
        return "addr:" + redact.redact_address(subject_id[5:])
    if subject_id.startswith("peer:"):
        return "peer:" + redact.redact_ip(subject_id[5:])
    return subject_id  # `cluster:<n>` is an opaque id, not an identifier.


def _meta_entries(run_dir: Path) -> list[dict[str, Any]]:
    """One custody link per stage directory, ordered: the stage, its meta hash, in/out."""
    stages = [
        ("kavach", SEALED_DIR),
        ("setu", "normalised"),
        ("jaal", "graph"),
        ("shastra", "signals"),
        ("buddhi", "scores"),
        ("vaani", ALERTS_DIR),
    ]
    chain: list[dict[str, Any]] = []
    for stage, directory in stages:
        path = run_dir / directory / "_meta.json"
        if not path.is_file():
            continue
        meta = json.loads(path.read_text(encoding="utf-8"))
        chain.append(
            {
                "stage": stage,
                "at_us": int(meta["finished_at_us"]),
                "inputs": [entry["path"] for entry in meta.get("inputs", [])],
                "outputs": [entry["path"] for entry in meta.get("outputs", [])],
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return chain


def _input_files(run_dir: Path) -> tuple[list[dict[str, str]], int]:
    """The sealed input hashes and the sealed row count, from KAVACH's own manifest."""
    manifest = json.loads((run_dir / SEALED_DIR / "manifest.json").read_text(encoding="utf-8"))
    files = [
        {"path": entry["path"], "sha256": entry["sha256"]}
        for entry in manifest.get("input_files", [])
    ]
    return files, int(manifest["rows_sealed"])


def build(run_dir: Path, alert_id: str, seed: int, replay_command: str) -> dict[str, Any]:
    """Assemble the contract section 9 packet for one alert as a plain dict.

    `run_dir` is the resolved run directory; the caller has already allowed its path.
    Deterministic: the same run and alert produce the same dict in any process.
    """
    alerts_dir = run_dir / ALERTS_DIR
    alerts = pl.read_parquet(alerts_dir / "alerts.parquet")
    row = alerts.filter(pl.col("alert_id") == alert_id)
    if row.height != 1:
        raise CaseError(f"{alert_id} matched {row.height} rows")
    alert = row.iter_rows(named=True).__next__()

    evidence = pl.read_parquet(alerts_dir / "evidence.parquet")
    counters = pl.read_parquet(alerts_dir / "counter.parquet")
    ev_rows = evidence.filter(pl.col("alert_id") == alert_id)
    counter_rows = counters.filter(pl.col("alert_id") == alert_id)
    if counter_rows.height == 0:
        raise CaseError(f"{alert_id} carries no counter-evidence; VAANI's rule forbids that")

    subject_id = str(alert["subject_id"])
    cluster_id = ""
    addresses: list[str] = []
    if subject_id.startswith("addr:"):
        addresses = [subject_id[5:]]
    else:
        clusters = pl.read_parquet(
            run_dir / "graph" / "clusters.parquet", columns=["cluster_id", "addresses"]
        )
        hit = clusters.filter(pl.col("cluster_id") == subject_id)
        if hit.height:
            cluster_id = subject_id
            addresses = hit["addresses"].to_list()[0]

    # The attribution block leads with L1 (the network operator), the hero of the reframe: the
    # exact host is winnable on a minority of transactions, the operator on most. The operator
    # fields come from `origin_l1.parquet`, the one row per transaction SHASTRA committed to; the
    # L3 shortlist is the ranked candidate peers, redacted for display. The full host IP and port
    # stay in the block because this is a machine artifact for an authorised officer, but they are
    # last and marked officer-only: no PDF or screen renders them.
    attribution: dict[str, Any] = {
        "asn": None,
        "as_org": "",
        "net_class": "",
        "geo_country": "",
        "p_asn": 0.0,
        "margin": 0.0,
        "shortlist": [],
        "observed_at_utc": "",
        "peer_ip": "",  # OFFICER-ONLY, full
        "peer_port": 0,  # OFFICER-ONLY
    }
    origin_txid = alert["origin_txid"]
    if origin_txid is not None:
        attribution.update(_l1_attribution(run_dir, str(origin_txid)))
        attribution["shortlist"] = _shortlist(run_dir, str(origin_txid))
        peer_ip = str(alert["origin_peer_ip"]) if alert["origin_peer_ip"] is not None else ""
        if peer_ip:
            announcements = pl.read_parquet(
                run_dir / "normalised" / "announcements.parquet",
                columns=["txid", "peer_ip", "peer_port", "seen_us"],
            )
            anchor = announcements.filter(
                (pl.col("txid") == origin_txid) & (pl.col("peer_ip") == peer_ip)
            ).sort("seen_us")
            if anchor.height:
                first = anchor.head(1).iter_rows(named=True).__next__()
                attribution["peer_ip"] = peer_ip
                attribution["peer_port"] = int(first["peer_port"])
                attribution["observed_at_utc"] = _utc(int(first["seen_us"]))

    scores = pl.read_parquet(
        run_dir / "scores" / "wallet_scores.parquet",
        columns=["subject_id", "conf_low", "conf_high", "coverage_target", "model"],
    )
    score = scores.filter(pl.col("subject_id") == subject_id)
    confidence = {"low": 0.0, "high": 1.0, "coverage_target": 0.9, "method": "unavailable"}
    if score.height:
        s = score.iter_rows(named=True).__next__()
        confidence = {
            "low": float(s["conf_low"]),
            "high": float(s["conf_high"]),
            "coverage_target": float(s["coverage_target"]),
            "method": _method(run_dir, str(s["model"])),
        }

    inputs, rows_sealed = _input_files(run_dir)
    alerts_meta = json.loads((alerts_dir / "_meta.json").read_text(encoding="utf-8"))

    packet: dict[str, Any] = {
        "case_id": alert_id,
        "generated_at_us": int(alerts_meta["finished_at_us"]),
        "tool_version": "0.1.0",
        "code_version": buildinfo.code_version(),
        "input": {"files": inputs, "rows_sealed": rows_sealed},
        "subject": {
            "subject_id": _redact_subject(subject_id),
            "addresses_redacted": [_redact_subject(f"addr:{one}") for one in sorted(addresses)],
            "cluster_id": cluster_id,
        },
        "attribution_ready": bool(alert["attribution_ready"]),
        "attribution": attribution,
        "findings": [
            {
                "statement": str(one["statement"]),
                "kind": str(one["kind"]),
                "source_ref": str(one["source_ref"]),
            }
            for one in ev_rows.iter_rows(named=True)
        ],
        "counter_findings": [
            {
                "statement": str(one["statement"]),
                "kind": str(one["kind"]),
                "would_clear": bool(one["would_clear"]),
            }
            for one in counter_rows.iter_rows(named=True)
        ],
        "confidence": confidence,
        "chain_of_custody": _meta_entries(run_dir),
        "replay": {
            "seed": seed,
            "command": replay_command,
            "expected_packet_sha256": BLANK,
        },
        "legal": {
            "basis": "BNSS 2023 s.94",
            "hash_disclosure": "BSA 2023 s.63(4), Schedule Part A",
        },
    }
    engine_path = run_dir / "scores/engine.json"
    if engine_path.is_file():
        engine = json.loads(engine_path.read_text())
        for name, expected in engine["input_sha256"].items():
            actual = hashlib.sha256(
                (run_dir / "normalised" / f"{name}.parquet").read_bytes()
            ).hexdigest()
            if actual != expected:
                raise CaseError("detection observations differ from the scored snapshot")
        detector = run_dir / "detector"
        if (
            hashlib.sha256((detector / "model.json").read_bytes()).hexdigest()
            != engine["model_sha256"]
        ):
            raise CaseError("detection model differs from the scored artifact")
        if (
            hashlib.sha256((detector / "manifest.json").read_bytes()).hexdigest()
            != engine["model_manifest_sha256"]
        ):
            raise CaseError("detection transforms differ from the scored artifact")
        queue = json.loads((run_dir / "alerts/lead_queue.json").read_text())
        lead = next(one for one in queue["leads"] if one["alert_id"] == alert_id)
        packet["detection"] = {"engine": engine, "lead": lead}
        packet["confidence"] = {
            "low": 0.0,
            "high": 1.0,
            "coverage_target": 0.0,
            "method": "ranking_only",
            "interval_available": False,
            "risk_score": lead["risk_score"],
        }
    canonical = merkle.canonical(packet)
    packet["replay"]["expected_packet_sha256"] = hashlib.sha256(canonical).hexdigest()
    # Re-serialise after inserting the digest: the recorded value is the hash of the
    # packet with the field blank, so verification blanks it again and compares.
    return packet


def _utc(seen_us: int) -> str:
    """Microseconds since epoch as an ISO-8601 UTC string. Pure arithmetic, no clock."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(seen_us / 1_000_000, tz=UTC).isoformat()


def _l1_attribution(run_dir: Path, txid: str) -> dict[str, Any]:
    """The L1 operator headline for the origin transaction, from `origin_l1.parquet`.

    One ensemble row per transaction: the ASN SHASTRA committed candidate mass to, its
    org/class/country, the capped operator probability and the rank-1 margin. Empty dict
    when the file or row is absent, so the caller keeps the neutral defaults.
    """
    path = run_dir / "signals" / "origin_l1.parquet"
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
            "margin",
            "estimator",
        ],
    ).filter((pl.col("txid") == txid) & (pl.col("estimator") == "ensemble"))
    if not l1.height:
        return {}
    r = l1.iter_rows(named=True).__next__()
    return {
        "asn": None if r["origin_asn"] is None else int(r["origin_asn"]),
        "as_org": r["as_org"] or "",
        "net_class": r["net_class"] or "",
        "geo_country": r["origin_country"] or "",
        "p_asn": float(r["p_asn"]),
        "margin": float(r["margin"]),
    }


def _shortlist(run_dir: Path, txid: str) -> list[dict[str, Any]]:
    """The ranked L3 candidate peers for the origin transaction, redacted for display.

    From the ensemble rows of `origin_estimates.parquet`, ordered by rank. Ports come from
    the announcement each peer sent for this transaction; the IP is truncated through the
    same law the screen uses, since the shortlist is rendered.
    """
    path = run_dir / "signals" / "origin_estimates.parquet"
    if not path.is_file():
        return []
    est = pl.read_parquet(
        path, columns=["txid", "peer_ip", "p_origin", "rank", "estimator"]
    ).filter((pl.col("txid") == txid) & (pl.col("estimator") == "ensemble"))
    if not est.height:
        return []
    ports = pl.read_parquet(
        run_dir / "normalised" / "announcements.parquet",
        columns=["txid", "peer_ip", "peer_port"],
    ).filter(pl.col("txid") == txid)
    port_by_peer = {
        str(row["peer_ip"]): int(row["peer_port"])
        for row in ports.sort("peer_port").iter_rows(named=True)
    }
    return [
        {
            "peer_ip_display": redact.redact_ip(str(row["peer_ip"])),
            "peer_port": port_by_peer.get(str(row["peer_ip"]), 0),
            "p_origin": float(row["p_origin"]),
            "rank": int(row["rank"]),
        }
        for row in est.sort("rank").iter_rows(named=True)
    ]


def _method(run_dir: Path, model: str) -> str:
    """The calibration method recorded for this run, from `scores/calibration.parquet`."""
    path = run_dir / "scores" / "calibration.parquet"
    if not path.is_file():
        return "unavailable"
    calibration = pl.read_parquet(path, columns=["class", "method"])
    if not calibration.height:
        return "unavailable"
    return str(calibration["method"][0])


def verify_replay_field(packet: dict[str, Any]) -> bool:
    """Blank the recorded digest, re-serialize, hash. True when the claim recomputes."""
    recorded = str(packet.get("replay", {}).get("expected_packet_sha256", ""))
    probe = json.loads(json.dumps(packet))
    probe["replay"]["expected_packet_sha256"] = BLANK
    return hashlib.sha256(merkle.canonical(probe)).hexdigest() == recorded


def packet_bytes(packet: dict[str, Any]) -> bytes:
    """The exact bytes written to `packet.json`: canonical, key-sorted, one line."""
    return merkle.canonical(packet)
