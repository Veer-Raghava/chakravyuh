"""Lead packets preserve observation boundaries and transaction amount semantics."""

from __future__ import annotations

import polars as pl

from chakravyuh.buddhi import relational_inference, snapshot
from chakravyuh.vaani.investigation import packet, select


def test_evidence_diversity_has_no_ownership_input() -> None:
    supports = {"a": {"tx1"}, "b": {"tx1"}, "c": {"tx2"}}
    assert select(["a", "b", "c"], supports, k=2, overlap=None) == ["a", "b"]
    assert select(["a", "b", "c"], supports, k=2, overlap=0.25) == ["a", "c"]


def test_packet_keeps_money_edges_and_excludes_future_evidence() -> None:
    a, b = "sameAA-address-one-ZZZZ", "sameAA-address-two-ZZZZ"
    subject = "addr:" + a
    table = pl.DataFrame({"subject_id": [subject]})
    members = pl.DataFrame({"subject_id": [subject], "address": [a]})
    view = snapshot.Snapshot(table, members, pl.DataFrame(), 0, 100, "address")
    scores = pl.DataFrame(
        {
            "subject_id": [subject],
            "risk_score": [0.8],
            "raw_score": [0.7],
            **{
                f"shap_{n}": [0.1 if n == "n_tx_sent" else 0.0]
                for n in relational_inference.FEATURES
            },
        }
    )
    tx = pl.DataFrame(
        {
            "txid": ["txnow", "txfuture"],
            "first_seen_us": [50, 101],
            "input_addresses": [[a], [a]],
            "output_addresses": [[b], [b]],
            "input_amounts": [[123456789], [1]],
            "output_amounts": [[123456788], [1]],
            "fee_sats": [1, 0],
        }
    )
    ann = pl.DataFrame(
        {
            "txid": ["txnow", "txnow"],
            "seen_us": [60, 101],
            "row_id": [1, 2],
            "peer_ip": ["192.0.2.1", "198.51.100.1"],
        }
    )
    peers = pl.DataFrame(
        {
            "peer_ip": ["192.0.2.1", "198.51.100.1"],
            "asn": [65001, 65002],
            "net_class": ["hosting", "residential"],
        }
    )
    result = packet(scores, view, tx, ann, peers, k=1)
    lead = result["leads"][0]
    assert lead["supporting_transaction_count"] == 1
    edges = lead["evidence_graph"]["edges"]
    assert [(e["relation"], e["amount_sats"]) for e in edges if "amount_sats" in e] == [
        ("funds", 123456789),
        ("receives", 123456788),
    ]
    assert [e["row_id"] for e in edges if e["relation"] == "announced"] == [1]
    nodes = lead["evidence_graph"]["nodes"]
    address_nodes = [n for n in nodes if n["kind"] == "address"]
    assert len(address_nodes) == 2
    assert address_nodes[0]["label"] == address_nodes[1]["label"]
    assert address_nodes[0]["id"] != address_nodes[1]["id"]
    assert all(
        e["source"] in {n["id"] for n in nodes} and e["target"] in {n["id"] for n in nodes}
        for e in edges
    )
    # Mutating an unused answer column cannot change observable evidence packets.
    assert (
        packet(scores, view, tx.with_columns(pl.lit("secret").alias("truth")), ann, peers, k=1)
        == result
    )
