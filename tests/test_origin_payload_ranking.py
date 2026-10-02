"""Origin timeline order must never substitute for model probability order."""

from pathlib import Path

import polars as pl
import pytest

from chakravyuh.api import serialize

RUN = Path("data/generated/agency-v2")


@pytest.mark.skipif(
    not (RUN / "signals/origin_estimates.parquet").exists(),
    reason="Requires generated Agency capture",
)
def test_probability_leaders_are_independent_of_announcement_order() -> None:
    estimates = pl.read_parquet(RUN / "signals/origin_estimates.parquet")
    txids = (
        estimates.filter((pl.col("estimator") == serialize.ENSEMBLE) & (pl.col("rank") == 1))[
            "txid"
        ]
        .unique()
        .sort()
        .head(8)
    )
    announcements = pl.read_parquet(RUN / "normalised/announcements.parquet")
    witnessed_different_order = False
    for txid in txids:
        payload = serialize.origin_estimate(RUN, txid)
        timeline = payload["shortlist"]
        times = [lane["first_seen_us"] for lane in timeline]
        assert times == sorted(times)
        probabilities = sorted(timeline, key=lambda lane: lane["p_origin"], reverse=True)
        assert payload["origin_peer_display"] == probabilities[0]["peer_ip_display"]
        assert payload["p_origin"] == probabilities[0]["p_origin"]
        if len(probabilities) > 1:
            assert payload["runner_up_display"] == probabilities[1]["peer_ip_display"]
            assert payload["runner_up_p"] == probabilities[1]["p_origin"]
            assert payload["margin"] == pytest.approx(
                probabilities[0]["p_origin"] - probabilities[1]["p_origin"]
            )
            witnessed_different_order |= timeline[1]["peer_ip"] != probabilities[1]["peer_ip"]
        assert (
            timeline[0]["first_seen_us"]
            == announcements.filter(pl.col("txid") == txid)["seen_us"].min()
        )
    assert (
        witnessed_different_order
    ), "Regression capture must distinguish arrival order from likelihood order"
