"""Frozen preprocessing must keep feature identity/order and signed monetary values."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from chakravyuh.buddhi import causal_inference, snapshot


def test_signed_balance_nulls_and_column_order() -> None:
    values = {name: [0.0] for name in reversed(snapshot.SNAPSHOT_FEATURES)}
    values["balance_sats"] = [-99.0]
    frame = pl.DataFrame(values).with_columns(pl.lit(None, dtype=pl.Float64).alias("burstiness"))
    width = len(snapshot.SNAPSHOT_FEATURES)
    result = causal_inference.transform(frame, np.zeros(width), np.ones(width))
    assert result.shape == (1, width)
    assert result.dtype == np.float32
    balance = snapshot.SNAPSHOT_FEATURES.index("balance_sats")
    np.testing.assert_allclose(result[0, balance], -np.log(100), rtol=1e-6)
    assert np.isfinite(result).all()
    assert result[0, snapshot.SNAPSHOT_FEATURES.index("burstiness")] == 0


@pytest.mark.parametrize("invalid", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_scaling_is_rejected(invalid: float) -> None:
    width = len(snapshot.SNAPSHOT_FEATURES)
    scales = np.ones(width)
    scales[0] = invalid
    with pytest.raises(ValueError, match="finite with positive scales"):
        causal_inference.transform(pl.DataFrame(), np.zeros(width), scales)


def test_scaler_schema_mismatch_is_rejected_before_feature_selection() -> None:
    with pytest.raises(ValueError, match="width differs"):
        causal_inference.transform(pl.DataFrame(), np.zeros(1), np.ones(1))
