"""Snapshot AML features must conserve gross address flows and exclude future evidence."""

from __future__ import annotations

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from chakravyuh.buddhi import features, snapshot
from chakravyuh.jaal import cluster, provenance


def _data() -> tuple[pl.DataFrame, pl.DataFrame]:
    tx = pl.DataFrame(
        {
            "txid": ["early", "future"],
            "first_seen_us": [100, 300],
            "input_addresses": [["a", "b"], ["c", "d"]],
            "input_amounts": [[100, 200], [250, 50]],
            "output_addresses": [["c", "a"], ["e"]],
            "output_amounts": [[250, 40], [290]],
            "total_out_sats": [290, 290],
            "fee_sats": [10, 10],
            "fee_rate_sat_vb": [1.0, 1.0],
            "n_in": [2, 2],
            "n_out": [2, 1],
            "change_index": [1, -1],
            "is_coinbase": [False, False],
            "has_equal_outputs": [False, False],
        }
    )
    addresses = pl.DataFrame(
        {
            "address": ["a", "b", "c", "d", "e"],
            "script_type": ["p2wpkh"] * 5,
            "first_seen_us": [100, 100, 100, 300, 300],
        }
    )
    return tx, addresses


def test_flows_are_not_repeated_per_member_or_paid_to_every_output() -> None:
    tx, addresses = _data()
    s = snapshot.build(tx, addresses, provenance.ownership_evidence(tx), start_us=0, end_us=200)
    source_id = s.members.filter(pl.col("address") == "a")["subject_id"].item()
    source = s.table.filter(pl.col("subject_id") == source_id).row(0, named=True)
    recipient_id = s.members.filter(pl.col("address") == "c")["subject_id"].item()
    recipient = s.table.filter(pl.col("subject_id") == recipient_id).row(0, named=True)
    assert source["total_sent_sats"] == 300
    assert source["total_received_sats"] == 40
    assert source["balance_sats"] == -260
    assert source["n_tx_sent"] == 1
    assert source["n_counterparties"] == 1
    assert recipient["total_received_sats"] == 250
    assert recipient["n_counterparties"] == 1


def test_future_append_does_not_change_previous_snapshot() -> None:
    tx, addresses = _data()
    past = tx.filter(pl.col("first_seen_us") <= 200)
    old_addresses = addresses.filter(pl.col("first_seen_us") <= 200)
    original = snapshot.build(
        past, old_addresses, provenance.ownership_evidence(past), start_us=0, end_us=200
    )
    appended = snapshot.build(
        tx, addresses, provenance.ownership_evidence(tx), start_us=0, end_us=200
    )
    assert_frame_equal(original.table.sort("subject_id"), appended.table.sort("subject_id"))
    assert_frame_equal(
        original.members.sort("subject_id", "address"),
        appended.members.sort("subject_id", "address"),
    )


def test_cluster_shape_uses_actual_edges_for_large_subject() -> None:
    # The previous Cartesian membership join would construct 100 million pairs.
    addresses = [f"a{i}" for i in range(10_000)]
    members = pl.DataFrame({"subject_id": ["large"] * len(addresses), "address": addresses})
    active = members.select("address")
    edges = pl.DataFrame(
        {
            "src": ["addr:a0", "addr:a1"],
            "dst": ["addr:a1", "addr:a2"],
            "kind": ["SAME_OWNER"] * 2,
            "confidence": [0.36, 0.25],
            "evidence": ["multi_input", "change_addr"],
        }
    )
    result = features.cluster_shape(pl.DataFrame(), edges, members, active).row(0, named=True)
    assert result["n_addresses"] == 10_000
    assert result["min_edge_confidence"] == 0.25
    assert result["n_heuristics"] == 2


def test_address_mode_ignores_even_adversarial_ownership_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tx, addresses = _data()
    ledger = provenance.ownership_evidence(tx)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("address mode invoked ownership inference")

    monkeypatch.setattr(provenance, "snapshot_edges", forbidden)
    monkeypatch.setattr(cluster, "clusters", forbidden)
    original = snapshot.build(
        tx, addresses, ledger, start_us=0, end_us=200, partition_mode="address"
    )
    # Claim that every observed address has the same owner with maximal weight.
    poisoned = pl.DataFrame(
        {
            "src": ["addr:a", "addr:a"],
            "dst": ["addr:b", "addr:c"],
            "txid": ["early", "early"],
            "available_us": [100, 100],
            "confidence": [1.0, 1.0],
            "evidence": ["false_merge", "false_merge"],
        },
        schema=provenance.LEDGER_SCHEMA,
    )
    corrupted = snapshot.build(
        tx, addresses, poisoned, start_us=0, end_us=200, partition_mode="address"
    )
    assert_frame_equal(original.table, corrupted.table)
    assert_frame_equal(original.members, corrupted.members)
    assert original.edges.height == corrupted.edges.height == 0
    assert original.members.group_by("subject_id").len()["len"].max() == 1
    assert original.partition_mode == "address"
