"""Adversarial checks on research inference, directed edges and absence diagnostics."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np
import polars as pl
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_sufficiency_gate import metrics  # noqa: E402
from temporal_hetero_benchmark import WIDTH, Model, pool, rollout  # noqa: E402


def _graph(memory: bool = False) -> dict:
    return {
        "subject": torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
        "transaction": torch.tensor([[5.0, 6.0]]),
        "ip": torch.tensor([[7.0, 8.0]]),
        "edges": {
            "funds": torch.tensor([[0], [0]]),
            "receives": torch.tensor([[0], [1]]),
            "announces": torch.tensor([[0], [0]]),
        },
        "memory_edges": torch.tensor([[0, 1], [0, 1]])
        if memory
        else torch.empty((2, 0), dtype=torch.long),
        "y": torch.tensor([0.0, 1.0]),
    }


def test_directed_mean_does_not_create_reverse_or_nonexistent_links() -> None:
    values = torch.tensor([[2.0], [6.0], [100.0]])
    edges = torch.tensor([[0, 1], [1, 1]])
    torch.testing.assert_close(pool(values, edges, 3), torch.tensor([[0.0], [4.0], [0.0]]))
    torch.testing.assert_close(
        pool(values, torch.empty((2, 0), dtype=torch.long), 2), torch.zeros(2, 1)
    )


def test_future_graph_and_label_mutation_cannot_change_past_scores() -> None:
    torch.manual_seed(31)
    net = Model({"subject": 2, "transaction": 2, "ip": 2}, temporal=True).eval()
    early, future = _graph(), _graph(memory=True)
    with torch.no_grad():
        expected, _ = rollout(net, [early])
        before, _ = rollout(net, [early, future])
        altered = copy.deepcopy([early, future])
        for graph in altered:
            graph["y"] = 1 - graph["y"]
        altered[1]["subject"] *= 10000
        altered[1]["ip"] *= -10000
        altered[1]["edges"]["funds"] = torch.tensor([[1], [0]])
        after, _ = rollout(net, altered)
    np.testing.assert_array_equal(before[:2], expected)
    np.testing.assert_array_equal(after[:2], expected)


def test_previous_observed_memory_can_influence_current_predictions() -> None:
    torch.manual_seed(31)
    net = Model({"subject": 2, "transaction": 2, "ip": 2}, temporal=True).eval()
    with torch.no_grad():
        empty, _ = net(_graph(memory=True), torch.zeros(2, WIDTH))
        prior, _ = net(_graph(memory=True), torch.ones(2, WIDTH))
    assert not torch.allclose(empty, prior)


def test_integer_source_presence_is_a_boolean_mask_not_row_indices() -> None:
    frame = pl.DataFrame(
        {
            "n_observers_in_tx": [2, 2, 2, 2],
            "any_tor": [False, False, False, False],
            "weighted_hit": [1, 0, 1, 0],
            "source_present": pl.Series([1, 0, 0, 1], dtype=pl.Int8),
        }
    )
    result = metrics(frame, np.array([0.9, 0.9, 0.9, 0.1]), 0.5)
    assert result["answered"] == 3
    assert result["correct"] == 2
    assert result["source_absent_answered"] == 2
    assert result["source_absent_correct"] == 1
