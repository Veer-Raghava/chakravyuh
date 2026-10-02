"""Observable-evidence diversity; selection never consumes ownership truth or labels."""

from __future__ import annotations


def select(candidates, supports, *, k=20, overlap=None):
    """Greedy score order; cap pairwise TX-set Jaccard, never infer common ownership.

    candidates is already sorted [(subject_id, score), ...]. Empty support is excluded.
    overlap=None gives the matched score-only control. Equality is allowed.
    """
    if k < 1 or (overlap is not None and not 0 <= overlap <= 1):
        raise ValueError("invalid selection parameters")
    chosen = []
    selected_sets = []
    for subject, _score in candidates:
        evidence = supports.get(subject, frozenset())
        if not evidence:
            continue
        if overlap is not None and any(
            len(evidence & prior) / len(evidence | prior) > overlap for prior in selected_sets
        ):
            continue
        chosen.append(subject)
        selected_sets.append(evidence)
        if len(chosen) == k:
            break
    return chosen
