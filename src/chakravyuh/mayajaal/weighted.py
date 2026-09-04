"""Weighted sampling with the cumulative table built once.

`random.Random.choices` rebuilds a cumulative-weight list on every call, which is O(n) per
draw. Entity selection happens once per transaction over twenty thousand candidates, so that
is the difference between a run that finishes and one that does not. The draw itself is one
`random()` call, which keeps the stream position per draw fixed and therefore keeps the run
reproducible from the seed alone.
"""

from __future__ import annotations

import bisect
import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class WeightedIndex(Generic[T]):
    items: tuple[T, ...]
    cumulative: tuple[float, ...]

    def pick(self, rng: random.Random) -> T:
        target = rng.random() * self.cumulative[-1]
        return self.items[bisect.bisect_right(self.cumulative, target)]

    def __len__(self) -> int:
        return len(self.items)


def build(pairs: Iterable[tuple[T, float]]) -> WeightedIndex[T]:
    """Zero and negative weights are dropped; an empty or all-zero input is a caller error."""
    items: list[T] = []
    cumulative: list[float] = []
    total = 0.0
    for item, weight in pairs:
        if weight <= 0.0:
            continue
        total += weight
        items.append(item)
        cumulative.append(total)
    if not items:
        raise ValueError("weighted index needs at least one positive weight")
    return WeightedIndex(items=tuple(items), cumulative=tuple(cumulative))
