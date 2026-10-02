"""Distribution summaries must preserve dispersion and leave empty targets explicit."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from relational_summary_controls import summaries  # noqa: E402


def test_large_offset_variance_and_no_reverse_messages() -> None:
    context = torch.tensor([[1_000_000.0], [1_000_001.0], [-99.0]])
    edges = torch.tensor([[0, 1], [1, 1]])
    actual = summaries(context, edges, 3)
    # Columns: log(degree+1), mean, population std, min, max.
    np.testing.assert_allclose(actual[1], [np.log(3), 1_000_000.5, 0.5, 1_000_000, 1_000_001])
    np.testing.assert_array_equal(actual[0], np.zeros(5))
    np.testing.assert_array_equal(actual[2], np.zeros(5))
    reordered = summaries(context, edges[:, [1, 0]], 3)
    np.testing.assert_array_equal(actual, reordered)


def test_empty_edges_produce_finite_zero_summaries() -> None:
    actual = summaries(torch.ones(2, 3), torch.empty((2, 0), dtype=torch.long), 4)
    assert actual.shape == (4, 13)
    assert np.isfinite(actual).all()
    np.testing.assert_array_equal(actual, np.zeros_like(actual))
