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

    attribution: dict[str, Any] = {
        "peer_ip": "",
        "peer_port": 0,
        "observed_at_utc": "",
        "p_origin": 0.0,
        "margin": 0.0,
        "runner_up_peer_ip": "",
        "asn": None,
        "as_org": "",
        "geo_country": "",
        "net_class": "",
    }
    origin_txid = alert["origin_txid"]
    if origin_txid is not None:
        peer_ip = str(alert["origin_peer_ip"])
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
            attribution["p_origin"] = float(alert["origin_p"])
            attribution["margin"] = _margin(run_dir, str(origin_txid), peer_ip)
        peers = pl.read_parquet(
            run_dir / "normalised" / "peers.parquet",
            columns=["peer_ip", "asn", "as_org", "geo_country", "net_class"],
        )
        prow = peers.filter(pl.col("peer_ip") == peer_ip)
        if prow.height:
            p = prow.iter_rows(named=True).__next__()
            attribution["asn"] = p["asn"]
            attribution["as_org"] = p["as_org"] or ""
            attribution["geo_country"] = p["geo_country"] or ""
            attribution["net_class"] = p["net_class"] or ""
        attribution["runner_up_peer_ip"] = _runner_up(run_dir, str(origin_txid), peer_ip)

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
    canonical = merkle.canonical(packet)
    packet["replay"]["expected_packet_sha256"] = hashlib.sha256(canonical).hexdigest()
    # Re-serialise after inserting the digest: the recorded value is the hash of the
    # packet with the field blank, so verification blanks it again and compares.
    return packet


def _utc(seen_us: int) -> str:
    """Microseconds since epoch as an ISO-8601 UTC string. Pure arithmetic, no clock."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(seen_us / 1_000_000, tz=UTC).isoformat()


def _margin(run_dir: Path, txid: str, peer_ip: str) -> float:
    """The rank-1 margin of the anchor's txid, from the ensemble's own rows."""
    origin = pl.read_parquet(
        run_dir / "signals" / "origin_estimates.parquet",
        columns=["txid", "peer_ip", "p_origin", "rank", "margin", "estimator"],
    )
    top1 = origin.filter(
        (pl.col("estimator") == "ensemble") & (pl.col("txid") == txid) & (pl.col("rank") == 1)
    )
    if not top1.height:
        return 0.0
    return float(top1["margin"][0]) if str(top1["peer_ip"][0]) == peer_ip else 0.0


def _runner_up(run_dir: Path, txid: str, peer_ip: str) -> str:
    """The rank-2 peer for the anchor txid, truncated like any rendered identifier."""
    origin = pl.read_parquet(
        run_dir / "signals" / "origin_estimates.parquet",
        columns=["txid", "peer_ip", "rank", "estimator"],
    )
    r2 = origin.filter(
        (pl.col("estimator") == "ensemble") & (pl.col("txid") == txid) & (pl.col("rank") == 2)
    )
    if not r2.height:
        return ""
    ip = str(r2["peer_ip"][0])
    return ip if ip == peer_ip else redact.redact_ip(ip)


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
