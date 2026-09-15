"""Where the training window ends. One definition, called by every stage that trains.

This module holds no I/O and opens nothing. It is in `chakravyuh.eval` because the split is part
of how a run is measured rather than part of how it is generated, and because the label doors in
`labels.py` enforce it: a door filters on the boundary this function returns, so a stage that
disagreed with it about where the window ends would be handed labels it thought were holdout.

The boundary is derived from the capture's own observed time span rather than written down as a
timestamp. That is not tidiness. The five worlds behind the S06 accuracy curve differ in
`observer_fraction`, which changes how many announcements reach an observer at all and therefore
where the first and last observed microseconds fall; an absolute boundary tuned on one of them
would put a different share of a different world on each side, and the five accuracies would no
longer be comparable. A fraction of each world's own span puts the same share on each side of all
five.

Half-open on purpose. `seen_us < boundary_us` trains, `seen_us >= boundary_us` is holdout, so a
row exactly on the boundary is holdout. A closed interval would let the single most recent
training row be the one the split exists to hide.
"""

from __future__ import annotations

TRAIN = "train"
HOLDOUT = "holdout"


def boundary_us(first_us: int, last_us: int, train_fraction: float) -> int:
    """The first microsecond that is *not* in the training window.

    `first_us` and `last_us` are the earliest and latest observed microseconds of the capture the
    split is being taken over, inclusive, and the caller must guarantee they came from the
    observable tree. `train_fraction` is the share of that span the training window covers, from
    `run_config.json`'s `eval.train_fraction`.

    Floored rather than rounded, so the arithmetic is integer throughout and two interpreters
    cannot disagree about a half microsecond. Returns `last_us + 1` for a zero-length span, which
    is the only honest answer when every row shares one timestamp: there is nothing to hold out,
    and a caller that then finds an empty holdout should say so rather than train on it silently.
    """
    if not 0.0 < train_fraction < 1.0:
        raise ValueError(f"train_fraction must be strictly between 0 and 1, got {train_fraction}")
    if last_us < first_us:
        raise ValueError(f"span is inverted: first_us={first_us}, last_us={last_us}")
    span = last_us - first_us
    if span == 0:
        return last_us + 1
    return first_us + int(span * train_fraction)


def window_of(seen_us: int, boundary: int) -> str:
    """Which side of `boundary` a microsecond falls on. The one place the comparison is written."""
    return TRAIN if seen_us < boundary else HOLDOUT
