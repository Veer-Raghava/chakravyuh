"""Causal graph-context inference contracts, independent of fitting or research code."""

from __future__ import annotations

from typing import Literal

import numpy as np
import polars as pl
import pytest
from test_buddhi_snapshot import _data

from chakravyuh.buddhi import relational_inference as engine


def test_feature_schema_and_directed_mean() -> None:
    assert len(engine.FEATURES) == 329
    assert len(set(engine.FEATURES)) == 329
    values = np.array([[10.0], [20.0]], dtype=np.float32)
    edges = np.array([[0, 1], [1, 1]], dtype=np.int64)
    np.testing.assert_array_equal(engine._pool(values, edges, 3), [[0.0], [15.0], [0.0]])


@pytest.mark.parametrize("mode", ["address", "heuristic"])
def test_future_money_and_network_events_cannot_change_past_context(mode: str) -> None:
    tx, addresses = _data()
    ann = pl.DataFrame(
        {
            "row_id": [0, 1],
            "txid": ["early", "future"],
            "peer_ip": ["192.0.2.1", "198.51.100.1"],
            "observer_ip": ["203.0.113.1", "203.0.113.2"],
            "seen_us": [101, 301],
        }
    )
    peers = pl.DataFrame(
        {"peer_ip": ["192.0.2.1", "198.51.100.1"], "net_class": ["hosting", "residential"]}
    )
    scalers = {
        name: {"mean": [0.0] * width, "scale": [1.0] * width}
        for name, width in [("subject", 23), ("transaction", 6), ("ip", 9)]
    }
    assert mode in ("address", "heuristic")
    # Explicit branches preserve Literal typing and make each representation's contract clear.
    partition: Literal["address", "heuristic"] = "address" if mode == "address" else "heuristic"
    earlier, view = engine.build(
        tx.filter(pl.col("first_seen_us") < 200),
        addresses,
        ann.filter(pl.col("seen_us") < 200),
        peers,
        scalers,
        start_us=0,
        end_us=200,
        partition_mode=partition,
    )
    appended, new = engine.build(
        tx.with_columns(pl.lit("unused answer").alias("truth")),
        addresses,
        ann,
        peers,
        scalers,
        start_us=0,
        end_us=200,
        partition_mode=partition,
    )
    assert view.table["subject_id"].equals(new.table["subject_id"])
    np.testing.assert_array_equal(earlier, appended)
