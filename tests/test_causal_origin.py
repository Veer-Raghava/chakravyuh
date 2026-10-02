"""Causal extraction must ignore appended future traffic and its own historical counts."""

import polars as pl
from polars.testing import assert_frame_equal

from chakravyuh.shastra.causal import candidates


def _frames() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    announcements = pl.DataFrame(
        {
            "row_id": [0, 1, 2, 3],
            "txid": ["old", "old", "next", "next"],
            "peer_ip": ["A", "B", "A", "B"],
            "observer_ip": ["O1", "O2", "O1", "O2"],
            "seen_us": [100, 110, 1000, 1020],
        }
    )
    peers = pl.DataFrame(
        {"peer_ip": ["A", "B"], "asn": [1, 2], "net_class": ["residential", "hosting"]}
    )
    txs = pl.DataFrame({"txid": ["old", "next"], "input_addresses": [["payer"], ["payer"]]})
    return announcements, peers, txs


def test_history_excludes_current_transaction_and_later_events() -> None:
    ann, peers, txs = _frames()
    result = candidates(ann, peers, txs, n_observers=3, horizon_us=30)
    old = result.filter(pl.col("txid") == "old")
    assert old["peer_n_txids"].to_list() == [0, 0]
    assert old["payer_shared"].to_list() == [0, 0]
    assert old["max_history_us"].null_count() == 2
    later = result.filter(pl.col("txid") == "next")
    assert later["peer_n_txids"].to_list() == [1, 1]
    assert later["payer_shared"].to_list() == [1, 1]
    assert later["peer_frac_rank_one"].to_list() == [1.0, 0.0]
    assert later.filter(pl.col("max_history_us") >= pl.col("first_seen_us")).is_empty()
    assert result["n_observers_blind"].to_list() == [2, 2, 2, 2]


def test_appending_future_transactions_preserves_every_old_feature() -> None:
    ann, peers, txs = _frames()
    before = candidates(ann, peers, txs, n_observers=3, horizon_us=30)
    future = pl.DataFrame(
        {
            "row_id": [4, 5],
            "txid": ["future", "future"],
            "peer_ip": ["B", "A"],
            "observer_ip": ["O2", "O3"],
            "seen_us": [2000, 2001],
        }
    )
    txs = pl.concat([txs, pl.DataFrame({"txid": ["future"], "input_addresses": [["payer"]]})])
    after = candidates(pl.concat([ann, future]), peers, txs, n_observers=3, horizon_us=30)
    assert_frame_equal(before, after.filter(pl.col("txid") != "future"))


def test_late_announcements_outside_decision_horizon_do_not_change_old_features() -> None:
    ann, peers, txs = _frames()
    before = candidates(ann, peers, txs, n_observers=3, horizon_us=30)
    late = pl.DataFrame(
        {"row_id": [4], "txid": ["old"], "peer_ip": ["B"], "observer_ip": ["O3"], "seen_us": [1500]}
    )
    after = candidates(pl.concat([ann, late]), peers, txs, n_observers=3, horizon_us=30)
    assert_frame_equal(before, after)
