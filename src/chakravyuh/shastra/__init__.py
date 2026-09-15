"""SHASTRA: which announcing peer originated a transaction, rather than merely relayed it.

`normalised/` and `graph/` in, `signals/` out. The estimate is the centre of the project and the
one number an investigator acts on, so the package is arranged around three refusals.

It refuses to renormalise. `p_origin` within one transaction sums to at most one and usually to
much less, because "none of these peers is the originator, we simply never saw it announce" is the
common case and the sum is how the file says so. An observer keeps only the earliest arrival per
transaction, so for most transactions the originator is not a candidate at all.

It refuses to rank when ranking would be a guess. Abstention is built into the estimator rather
than layered on afterwards, and it is a first class outcome: an abstaining transaction has no rank
one row at all, so a consumer cannot mistake a refusal for a weak accusation.

It refuses to see a label. Labels reach this stage through `chakravyuh.eval.labels` and are
training-window only, and the only module that imports that door is `__main__.py`, which is not
itself part of the pipeline. `stage.py` is a pure read of two directories under `data/`.
"""
