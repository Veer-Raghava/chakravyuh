"""Ranked offline lead packets: model reasons, exact money edges and observed network support."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from chakravyuh.buddhi import relational_inference, snapshot
from chakravyuh.vaani.redact import redact_address, redact_ip, redact_txid


def select(
    ranked: list[str],
    supports: dict[str, set[str]],
    *,
    k: int,
    overlap: float | None,
) -> list[str]:
    """Select evidence-diverse leads without labels or assumptions about ownership."""
    if k < 1 or (overlap is not None and not 0 <= overlap <= 1):
        raise ValueError("invalid lead selection parameters")
    chosen: list[str] = []
    used: list[set[str]] = []
    for subject in ranked:
        current = supports.get(subject, set())
        if not current:
            continue
        if overlap is not None and any(
            len(current & old) / len(current | old) > overlap for old in used
        ):
            continue
        chosen.append(subject)
        used.append(current)
        if len(chosen) == k:
            break
    return chosen


def packet(
    scores: pl.DataFrame,
    view: snapshot.Snapshot,
    transactions: pl.DataFrame,
    announcements: pl.DataFrame,
    peers: pl.DataFrame,
    *,
    k: int = 20,
    overlap: float | None = 0.25,
    max_transactions: int = 16,
) -> dict[str, Any]:
    """Structured evidence plus redacted display strings; no answer-key dependencies.

    IDs are content-derived references, not truncated labels used as keys. Graphs retain
    all money endpoints for included TXs, so in/out amounts are not fictional pair flows.
    """
    if max_transactions < 1:
        raise ValueError("positive evidence transaction cap required")
    window = transactions.filter(pl.col("first_seen_us").is_between(view.start_us, view.end_us))
    lookup = dict(view.members.select("address", "subject_id").iter_rows())
    supports: dict[str, set[str]] = {}
    tx_rows: dict[str, dict[str, Any]] = {}
    for row in window.iter_rows(named=True):
        tx_rows[row["txid"]] = row
        for address in (*row["input_addresses"], *row["output_addresses"]):
            subject = lookup.get(address)
            if subject is not None:
                supports.setdefault(subject, set()).add(row["txid"])
    ranked = scores.sort(["risk_score", "subject_id"], descending=[True, False]).head(2000)
    selected = select(ranked["subject_id"].to_list(), supports, k=k, overlap=overlap)
    ann = announcements.filter(pl.col("seen_us").is_between(view.start_us, view.end_us))
    # Only retain bounded context for this queue, never export the entire capture.
    chosen_tx = {t for s in selected for t in supports[s]}
    network = ann.filter(pl.col("txid").is_in(chosen_tx)).sort("seen_us", "row_id")
    peer_facts = {r["peer_ip"]: r for r in peers.iter_rows(named=True)}
    observation_map: dict[str, list[dict[str, Any]]] = {}
    for row in network.iter_rows(named=True):
        observation_map.setdefault(row["txid"], []).append(row)
    rows = {r["subject_id"]: r for r in ranked.iter_rows(named=True)}
    raw_features = {r["subject_id"]: r for r in view.table.iter_rows(named=True)}
    members: dict[str, list[str]] = {}
    for address, subject in lookup.items():
        members.setdefault(subject, []).append(address)

    def ref(kind: str, value: str) -> str:
        return kind + ":" + hashlib.sha256(value.encode()).hexdigest()[:24]

    leads: list[dict[str, Any]] = []
    for subject in selected:
        row = rows[subject]
        relevant = sorted(supports[subject], key=lambda t: (tx_rows[t]["first_seen_us"], t))
        included = relevant[-max_transactions:]
        nodes: dict[str, dict[str, Any]] = {}
        edges = []
        observations = []
        for txid in included:
            tx = tx_rows[txid]
            tid = ref("tx", txid)
            nodes[tid] = dict(
                id=tid,
                kind="transaction",
                label=redact_txid(txid),
                time_us=tx["first_seen_us"],
                fee_sats=tx["fee_sats"],
            )
            for field, amount_field, relation in [
                ("input_addresses", "input_amounts", "funds"),
                ("output_addresses", "output_amounts", "receives"),
            ]:
                for address, value in zip(tx[field], tx[amount_field], strict=True):
                    aid = ref("address", address)
                    nodes[aid] = dict(
                        id=aid,
                        kind="address",
                        label=redact_address(address),
                        focus=address in members[subject],
                    )
                    source, target = (aid, tid) if relation == "funds" else (tid, aid)
                    edges.append(
                        dict(
                            source=source, target=target, relation=relation, amount_sats=int(value)
                        )
                    )
            seen_peers = set()
            for capture in observation_map.get(txid, []):
                ip = capture["peer_ip"]
                if ip in seen_peers:
                    continue
                seen_peers.add(ip)
                facts = peer_facts.get(ip, {})
                pid = ref("ip", ip)
                nodes[pid] = dict(
                    id=pid,
                    kind="ip",
                    label=redact_ip(ip),
                    asn=facts.get("asn"),
                    net_class=facts.get("net_class"),
                )
                evidence = dict(
                    source=pid,
                    target=tid,
                    relation="announced",
                    seen_us=capture["seen_us"],
                    row_id=capture["row_id"],
                    peer_port=capture.get("peer_port"),
                    observer_port=capture.get("observer_port"),
                )
                edges.append(evidence)
                observations.append(evidence)
                if len(seen_peers) >= 4:
                    break
        contribution = [
            (name, float(row[f"shap_{name}"])) for name in relational_inference.FEATURES
        ]
        positive = sorted([v for v in contribution if v[1] > 0], key=lambda v: (-v[1], v[0]))[:5]
        negative = sorted([v for v in contribution if v[1] < 0], key=lambda v: (v[1], v[0]))[:3]
        reasons = [
            dict(feature=name, description=name.replace("_", " "), shap_margin=value)
            for name, value in positive
        ]
        leads.append(
            dict(
                id=ref("lead", subject),
                subject_ref=ref("subject", subject),
                rank=len(leads) + 1,
                risk_score=float(row["risk_score"]),
                raw_score=float(row["raw_score"]),
                address_count=len(members[subject]),
                addresses=[redact_address(a) for a in sorted(members[subject])[:8]],
                facts=raw_features[subject] | {"subject_id": ref("subject", subject)},
                supporting_transaction_count=len(relevant),
                displayed_transaction_count=len(included),
                graph_truncated=len(relevant) > len(included),
                reasons=reasons,
                mitigating_contributions=[dict(feature=n, shap_margin=v) for n, v in negative],
                evidence_graph=dict(nodes=list(nodes.values()), edges=edges),
                next_actions=[
                    "Trace the displayed transaction inputs and outputs.",
                    "Compare repeated announcing peers and ASNs across supporting transactions.",
                    "Review ownership evidence before combining addresses into an entity.",
                ],
                network_observation_count=len(observations),
            )
        )
    return dict(
        schema_version=1,
        window=dict(start_us=view.start_us, end_us=view.end_us),
        partition_mode=view.partition_mode,
        lead_count=len(leads),
        leads=leads,
        selection=dict(k=k, overlap=overlap, candidate_pool=2000, unit="observed evidence lead"),
        score_meaning="model ranking score calibrated on synthetic history",
        explanation_meaning="signed TreeSHAP contributions to raw model log-odds",
        graph_meaning="observed fund flows and announcements; IP origin unresolved",
        identifier_display="redacted; content-derived references preserve graph joins",
    )


def run(
    normalised: Path,
    model: Path,
    output: Path,
    *,
    start_us: int,
    end_us: int,
    k: int = 20,
    overlap: float | None = 0.25,
) -> dict[str, Any]:
    """Produce a reusable JSON queue, scores and provenance on unlabeled input files."""
    if output.exists():
        raise ValueError("output directory already exists")
    scores, view, metadata = relational_inference.score(
        normalised, model, start_us=start_us, end_us=end_us
    )
    result = packet(
        scores,
        view,
        pl.read_parquet(normalised / "transactions.parquet"),
        pl.read_parquet(normalised / "announcements.parquet"),
        pl.read_parquet(normalised / "peers.parquet"),
        k=k,
        overlap=overlap,
    )
    output.mkdir(parents=True)
    scores.write_parquet(output / "scores.parquet")
    (output / "leads.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    metadata.update(
        queue_sha256=hashlib.sha256((output / "leads.json").read_bytes()).hexdigest(),
        queue_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalised", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-us", type=int, required=True)
    parser.add_argument("--end-us", type=int, required=True)
    parser.add_argument("--leads", type=int, default=20)
    parser.add_argument("--overlap", type=float, default=0.25)
    args = parser.parse_args()
    run(
        args.normalised,
        args.model,
        args.output,
        start_us=args.start_us,
        end_us=args.end_us,
        k=args.leads,
        overlap=args.overlap,
    )


if __name__ == "__main__":
    main()
