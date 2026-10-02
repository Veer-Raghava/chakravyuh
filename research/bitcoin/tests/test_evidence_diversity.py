"""Selection uses observed evidence only; repeated evidence is not an identity claim."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_diversity import select  # noqa: E402


def test_repetitive_evidence_and_empty_support():
    candidates = [("a", 0.99), ("b", 0.98), ("empty", 0.97), ("c", 0.96)]
    supports = {"a": frozenset({1, 2}), "b": frozenset({1, 2}), "c": frozenset({3})}
    assert select(candidates, supports, k=2) == ["a", "b"]
    assert select(candidates, supports, k=2, overlap=0.5) == ["a", "c"]


def test_jaccard_boundary_and_nonidentity():
    candidates = [("a", 0.9), ("b", 0.8), ("c", 0.7)]
    supports = {"a": frozenset({1, 2}), "b": frozenset({2, 3}), "c": frozenset({4})}
    assert select(candidates, supports, k=3, overlap=1 / 3) == ["a", "b", "c"]
    assert select(candidates, supports, k=3, overlap=0.0) == ["a", "c"]
    # Distinct TX support cannot establish distinct controllers, nor ownership equality.
    assert select(candidates, supports, k=3, overlap=0.0) == ["a", "c"]
