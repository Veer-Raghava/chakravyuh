"""Ownership views must not learn a stronger claim from future transactions."""

from __future__ import annotations

import polars as pl
from polars.testing import assert_frame_equal

from chakravyuh.jaal import cluster, provenance


def _transactions() -> pl.DataFrame:
    # Early change links a-b weakly; a later common-input spend strengthens the same pair.
    return pl.DataFrame(
        {
            "txid": ["early", "late"],
            "first_seen_us": [100, 200],
            "is_coinbase": [False, False],
            "has_equal_outputs": [False, False],
            "n_in": [1, 2],
            "n_out": [2, 1],
            "input_addresses": [["a"], ["a", "b"]],
            "output_addresses": [["b", "c"], ["d"]],
            "output_values_sats": [[123, 456], [579]],
            "change_index": [0, -1],
        }
    )


def test_future_stronger_claim_is_not_backdated() -> None:
    ledger = provenance.ownership_evidence(_transactions())
    assert ledger.height == 2
    early = provenance.snapshot_edges(ledger, 150)
    late = provenance.snapshot_edges(ledger, 200)
    assert early["confidence"].to_list() == [0.25]
    assert early["ts_us"].to_list() == [100]
    assert late["confidence"].to_list() == [0.36]
    assert late["ts_us"].to_list() == [200]
    assert cluster.components(early, 0.3) == []
    assert cluster.components(late, 0.3) == [["addr:a", "addr:b"]]


def test_snapshot_equals_prefix_rebuild_and_future_append_is_invariant() -> None:
    transactions = _transactions()
    prefix = transactions.filter(pl.col("first_seen_us") <= 150)
    assert_frame_equal(
        provenance.snapshot_edges(provenance.ownership_evidence(transactions), 150),
        provenance.snapshot_edges(provenance.ownership_evidence(prefix), 150),
    )
    assert provenance.snapshot_edges(provenance.ownership_evidence(transactions), 99).is_empty()


def test_full_snapshot_matches_existing_edge_claims_and_partition() -> None:
    transactions = _transactions()
    old = cluster.same_owner_edges(transactions).drop("ts_us").sort("src", "dst")
    new = provenance.snapshot_edges(provenance.ownership_evidence(transactions), 200)
    assert_frame_equal(old, new.drop("ts_us").sort("src", "dst"))
    assert cluster.components(new, 0.2) == [["addr:a", "addr:b"]]
