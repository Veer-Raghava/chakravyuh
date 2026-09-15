"""Cluster scoring. The only module that opens the clustering answer key.

A stage passes its predicted clusters in and gets two numbers back. No frame crosses back, no
label crosses back, and no argument is a path: the run id is what locates both the answer key and
the measurements directory, exactly as `validate.py` does it, so there is deliberately no way to
point this at a different run's truth.

The number is pairwise, not full-cluster. Contract section 5 quotes 0.36 precision and 0.44
recall for the multi-input heuristic on *full* clusters, where a cluster counts only if it is
recovered exactly. That metric is discontinuous: one wrong edge destroys a 134-address cluster's
score entirely, so it moves in jumps as an analyst drags a threshold and tells them nothing about
whether the drag helped. Pairwise precision and recall move smoothly, which is what the console
needs. The JSON records `metric: "pairwise"` so nobody compares these two numbers to the
contract's two by accident.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import polars as pl

from chakravyuh.eval import split
from chakravyuh.mayajaal.writers import RUN_ID

GENERATED_ROOT = Path("data") / "generated"
GROUND_TRUTH_ROOT = Path("ground_truth")
MEASUREMENTS_ROOT = Path("measurements")
ENTITIES = "entities.parquet"
ORIGINS = "origins.parquet"


@dataclass(frozen=True)
class ClusterScore:
    """What a stage is allowed to learn about its own clustering. Numbers, never members."""

    pair_precision: float
    pair_recall: float
    pair_f1: float
    predicted_pairs: int
    true_pairs: int
    shared_pairs: int
    n_predicted_clusters: int
    n_universe_addresses: int


def _pairs(groups: Sequence[Sequence[str]], universe: set[str]) -> set[tuple[str, str]]:
    """Every unordered same-group pair, restricted to `universe`.

    The restriction is what makes recall a measurement of the heuristic rather than of capture
    coverage. An entity owning a thousand addresses of which this capture saw four has 499500 true
    pairs in the answer key and six that any clustering could possibly recover; scoring against
    the former would report a recall near zero no matter how good the heuristic was.
    """
    found: set[tuple[str, str]] = set()
    for group in groups:
        inside = sorted(set(group) & universe)
        found.update(combinations(inside, 2))
    return found


def score_clusters(
    run_id: str,
    predicted: Sequence[Sequence[str]],
    universe: Sequence[str],
    threshold: float,
    heuristics: Sequence[str],
) -> ClusterScore | None:
    """Score `predicted` against the run's answer key. Returns None when it is absent.

    `run_id` is a run id, never a path. `predicted` is a sequence of address groups, `universe`
    is every address the caller observed, and the remaining two are recorded in the report so a
    number can be traced to the cut that produced it.

    None rather than an exception when the answer key does not exist, because Law 2 rule 6 says
    inference must complete with it absent, and a caller that asked for a score it cannot have
    should warn and carry on rather than die.

    The two trees are resolved from the working directory rather than from the repository root,
    which is what `writers.run_roots` does and what makes a test's throwaway workspace behave
    exactly like the repository. The run name is validated with the same pattern, so `..` can
    never walk out of either tree.
    """
    if not RUN_ID.match(run_id):
        raise ValueError(f"run_id must match {RUN_ID.pattern}, got {run_id!r}")
    key = GROUND_TRUTH_ROOT / run_id / ENTITIES
    if not key.is_file():
        return None

    seen = set(universe)
    predicted_pairs = _pairs(predicted, seen)
    true_pairs = _pairs(
        pl.read_parquet(key, columns=["addresses"])["addresses"].to_list(),
        seen,
    )
    shared = predicted_pairs & true_pairs

    precision = len(shared) / len(predicted_pairs) if predicted_pairs else 0.0
    recall = len(shared) / len(true_pairs) if true_pairs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    score = ClusterScore(
        pair_precision=precision,
        pair_recall=recall,
        pair_f1=f1,
        predicted_pairs=len(predicted_pairs),
        true_pairs=len(true_pairs),
        shared_pairs=len(shared),
        n_predicted_clusters=len(predicted),
        n_universe_addresses=len(seen),
    )

    report = {
        "run_id": run_id,
        "metric": "pairwise",
        "metric_note": (
            "Same-cluster address pairs, restricted to the addresses the stage observed. Not "
            "comparable to the full-cluster 0.36/0.44 quoted in contract section 5."
        ),
        "threshold": threshold,
        "heuristics": sorted(heuristics),
        **asdict(score),
    }
    out = MEASUREMENTS_ROOT / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "cluster_metrics.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return score


# --- origin accuracy ---------------------------------------------------------------------------
#
# One report, three kinds of number, so the comparison a gate makes is auditable rather than
# asserted: the ceiling nothing can beat, the two trivial rules an investigator already has, and
# whatever SHASTRA shipped. All of them re-measured here, on this run, from the file SHASTRA
# actually wrote. Copying the numbers from `_s02-final` into a gate would compare an estimator
# against a different world's baseline, and every one of these moves when the generator moves.
#
# The denominator is every transaction that was broadcast, never the transactions some observer
# happened to record. That is the trap the brief names: an observer keeps only the earliest
# arrival, so for most transactions the true originator is not in the candidate set at all, and
# scoring over the observed subset silently drops exactly the transactions no method could get
# right. `recoverable_ceiling` is reported first because a number read without it looks like far
# more headroom than the capture has.

TRAFFIC = ("clear", "vpn", "tor")


@dataclass(frozen=True)
class OriginScore:
    """What one estimator, or one trivial rule, scored. Shares of all broadcast transactions.

    Two accuracies, because one number cannot answer both questions an investigator has.

    `top1` and `top3` measure the ranking and ignore abstention. That is what makes the gate's
    comparison mean something: the two trivial rules never abstain, so a metric that zeroed an
    abstaining estimator's numerator would compare refusal policies rather than estimator quality,
    and at low observer coverage a calibrated model is *right* to be unsure about almost everything.

    `top1_acted` and `precision_when_acted` measure what the estimator actually claimed. An
    estimator that abstains on everything scores zero on the first and is undefined on the second,
    so abstention is never free, it is just accounted for separately instead of hidden inside the
    headline. `coverage` is the share of broadcast transactions it was willing to answer at all.
    """

    top1: float
    top3: float
    n_correct: int
    n_ranked: int
    n_abstained: int
    top1_acted: float
    precision_when_acted: float
    coverage: float
    by_traffic: Mapping[str, float]
    by_window: Mapping[str, Any]


def _round(value: float) -> float:
    """Six decimals, so two runs of one seed produce byte-identical reports."""
    return round(value, 6)


def _traffic_expr() -> pl.Expr:
    """Tor beats VPN when a run sets both, so the harder class is never reported as the easier."""
    return (
        pl.when(pl.col("used_tor"))
        .then(pl.lit("tor"))
        .when(pl.col("used_vpn"))
        .then(pl.lit("vpn"))
        .otherwise(pl.lit("clear"))
        .alias("traffic")
    )


def _score_ranked(
    ranked: pl.DataFrame, truth: pl.DataFrame, broadcast: int, windows: pl.DataFrame
) -> OriginScore:
    """Score a ranked candidate table against the answer key.

    `ranked` is `txid`, `peer_ip`, `rank`, `abstain`, one row per candidate, and the caller
    guarantees the ranking is total and deterministic within a transaction. `truth` is `txid`,
    `true_origin_ip`, `traffic`, one row per broadcast transaction. `windows` is `txid`, `window`
    for every observed transaction.

    Ordinal position is derived from `rank` rather than read from it, because SHASTRA shifts an
    abstaining transaction's ranks to start at two so that no refusal can be mistaken for a rank 1
    accusation. The shift preserves the ordering, so position one is `rank.min()` and the ranking
    stays scoreable without the file having to lie about what it claims.
    """
    ordered = (
        ranked.sort(["txid", "rank"])
        .with_columns(pl.int_range(pl.len()).over("txid").add(1).alias("position"))
        .join(truth, on="txid", how="inner")
        .with_columns((pl.col("peer_ip") == pl.col("true_origin_ip")).alias("hit"))
    )
    at1 = ordered.filter(pl.col("position") == 1)
    at3 = ordered.filter(pl.col("position") <= 3).group_by("txid").agg(pl.col("hit").any())
    correct = int(at1["hit"].sum())
    acted = at1.filter(~pl.col("abstain"))
    acted_correct = int(acted["hit"].sum())

    by_traffic: dict[str, float] = {}
    for name in TRAFFIC:
        total = truth.filter(pl.col("traffic") == name).height
        got = at1.filter((pl.col("traffic") == name) & pl.col("hit")).height
        by_traffic[name] = _round(got / total) if total else 0.0

    # A different denominator, and labelled as one: a transaction no observer heard has no
    # first-seen time and so belongs to neither window. Reported with its own count rather than
    # folded into `top1`, whose denominator is every broadcast transaction.
    placed = at1.join(windows, on="txid", how="inner")
    scope = truth.join(windows, on="txid", how="inner")
    by_window: dict[str, Any] = {}
    for name in (split.TRAIN, split.HOLDOUT):
        total = scope.filter(pl.col("window") == name).height
        got = placed.filter((pl.col("window") == name) & pl.col("hit")).height
        by_window[name] = {
            "top1": _round(got / total) if total else 0.0,
            "n_transactions": total,
            "n_correct": got,
        }

    return OriginScore(
        top1=_round(correct / broadcast) if broadcast else 0.0,
        top3=_round(int(at3["hit"].sum()) / broadcast) if broadcast else 0.0,
        n_correct=correct,
        n_ranked=at1.height,
        n_abstained=int(at1.filter(pl.col("abstain")).height),
        top1_acted=_round(acted_correct / broadcast) if broadcast else 0.0,
        precision_when_acted=_round(acted_correct / acted.height) if acted.height else 0.0,
        coverage=_round(acted.height / broadcast) if broadcast else 0.0,
        by_traffic=by_traffic,
        by_window=by_window,
    )


def _rank_by(
    candidates: pl.DataFrame, by: Sequence[str], descending: Sequence[bool]
) -> pl.DataFrame:
    """Turn a sort rule into a ranked candidate table, so a trivial rule scores through one path.

    Ties break on `row_id`, the announcement's position in `normalised/`, which every caller
    appends: a rule whose ordering is ambiguous must still be deterministic or two runs of one seed
    disagree here. `abstain` is false throughout, because a one-line SQL rule never refuses.
    """
    return (
        candidates.sort(list(by), descending=list(descending))
        .with_columns(pl.int_range(pl.len()).over("txid").add(1).cast(pl.Int32).alias("rank"))
        .with_columns(pl.lit(False).alias("abstain"))
        .select("txid", "peer_ip", "rank", "abstain")
    )


def _candidates(observable: Path) -> pl.DataFrame:
    """One row per (txid, peer) an observer heard from, with the columns the trivial rules need.

    Grouped to the peer rather than left at the announcement, because "which peer originated this"
    is a question about peers: a peer that reached four observers is one candidate, not four, and
    leaving the rows ungrouped would let a well-observed relay outvote the originator.
    """
    announcements = pl.read_parquet(
        observable / "normalised" / "announcements.parquet",
        columns=["row_id", "txid", "peer_ip", "seen_us"],
    )
    return announcements.group_by("txid", "peer_ip").agg(
        pl.col("seen_us").min().alias("seen_us"),
        pl.col("row_id").min().alias("row_id"),
    )


def _payer_linkage(observable: Path, candidates: pl.DataFrame) -> pl.DataFrame:
    """The strongest trivial rule: the peer seen across most of that payer's transactions.

    Transactions are linked by their first input address, which is the strongest observable signal
    in the capture and the shape SHASTRA is supposed to discover, so it is the rule most worth
    knowing the score of. Identical in definition to `validate.py`'s leakage check of the same
    name, re-derived here from `normalised/` because a gate must compare against a number measured
    on the run it is gating.
    """
    payers = pl.read_parquet(
        observable / "normalised" / "transactions.parquet", columns=["txid", "input_addresses"]
    ).select("txid", pl.col("input_addresses").list.first().alias("payer"))
    linked = candidates.join(payers, on="txid", how="left")
    shared = linked.group_by("payer", "peer_ip").agg(pl.col("txid").n_unique().alias("shared"))
    return _rank_by(
        linked.join(shared, on=["payer", "peer_ip"], how="left").with_columns(
            pl.col("shared").fill_null(0)
        ),
        ["shared", "row_id"],
        [True, False],
    )


def _windows(observable: Path, train_fraction: float) -> tuple[pl.DataFrame, int]:
    """Each observed transaction's window, and the boundary. Derived, never hardcoded.

    The boundary comes from the capture's own observed time span through
    `chakravyuh.eval.split.boundary_us`, which is the same function SHASTRA's label door calls, so
    a report and the model that produced it can never disagree about where the training window
    ended. An absolute timestamp would be wrong in four of the five observer-fraction worlds, whose
    spans differ.
    """
    announcements = pl.read_parquet(
        observable / "normalised" / "announcements.parquet", columns=["txid", "seen_us"]
    )
    if announcements.is_empty():
        return pl.DataFrame(schema={"txid": pl.String(), "window": pl.String()}), 0
    first = int(announcements["seen_us"].min())  # type: ignore[arg-type]
    last = int(announcements["seen_us"].max())  # type: ignore[arg-type]
    boundary = split.boundary_us(first, last, train_fraction)
    placed = announcements.group_by("txid").agg(pl.col("seen_us").min().alias("first_seen_us"))
    return (
        placed.select(
            "txid",
            pl.when(pl.col("first_seen_us") < boundary)
            .then(pl.lit(split.TRAIN))
            .otherwise(pl.lit(split.HOLDOUT))
            .alias("window"),
        ),
        boundary,
    )


def score_origin(
    run_id: str,
    *,
    train_fraction: float,
    observer_fraction: float,
    params: Mapping[str, Any],
) -> dict[str, OriginScore] | None:
    """Score every estimator in this run's `signals/` and write `origin_accuracy.json`.

    `run_id` is a run id, never a path: the answer key, the observable tree and the measurements
    directory are all derived from it, exactly as `score_clusters` does it, so there is no way to
    point this at another run's truth. Returns one score per value of the `estimator` column, plus
    the two baselines under their own keys, or None when the answer key is absent.

    Nothing crosses back into the stage but numbers. The predictions are read from the Parquet
    SHASTRA already wrote rather than passed in as a frame, so what is scored is what shipped.
    """
    if not RUN_ID.match(run_id):
        raise ValueError(f"run_id must match {RUN_ID.pattern}, got {run_id!r}")
    observable = GENERATED_ROOT / run_id
    key = GROUND_TRUTH_ROOT / run_id / ORIGINS
    if not key.is_file():
        return None

    chain = pl.read_parquet(observable / "chain" / "transactions.parquet", columns=["is_coinbase"])
    broadcast = chain.height - int(chain["is_coinbase"].sum())
    truth = pl.read_parquet(
        key, columns=["txid", "true_origin_ip", "used_tor", "used_vpn"]
    ).with_columns(_traffic_expr())

    candidates = _candidates(observable)
    windows, boundary = _windows(observable, train_fraction)
    recoverable = (
        candidates.join(truth.select("txid", "true_origin_ip"), on="txid", how="inner")
        .filter(pl.col("peer_ip") == pl.col("true_origin_ip"))
        .select("txid")
        .unique()
    )
    reachable = recoverable.height

    # The ceiling per window as well as over the whole run, because the windows are not equally
    # winnable and a holdout number read against the run-wide ceiling looks like a failure when it
    # may be a harder half. Same denominator as `by_window`: transactions an observer heard.
    placed_ceiling = recoverable.join(windows, on="txid", how="inner")
    scope = truth.join(windows, on="txid", how="inner")
    ceiling_by_window: dict[str, Any] = {}
    for name in (split.TRAIN, split.HOLDOUT):
        total = scope.filter(pl.col("window") == name).height
        got = placed_ceiling.filter(pl.col("window") == name).height
        ceiling_by_window[name] = {
            "ceiling": _round(got / total) if total else 0.0,
            "n_transactions": total,
            "n_recoverable": got,
        }

    scores: dict[str, OriginScore] = {
        "first_seen": _score_ranked(
            _rank_by(candidates, ["seen_us", "row_id"], [False, False]), truth, broadcast, windows
        ),
        "payer_linkage": _score_ranked(
            _payer_linkage(observable, candidates), truth, broadcast, windows
        ),
    }
    baselines = tuple(scores)

    estimates = pl.read_parquet(
        observable / "signals" / "origin_estimates.parquet",
        columns=["txid", "peer_ip", "rank", "abstain", "estimator"],
    )
    for name in sorted(estimates["estimator"].unique().to_list()):
        if name in scores:
            raise ValueError(
                f"signals/ names an estimator {name!r}, which collides with a baseline key in "
                "origin_accuracy.json. Rename the estimator: the report has to keep the two "
                "apart or the gate compares a number against itself."
            )
        rows = estimates.filter(pl.col("estimator") == name).drop("estimator")
        scores[name] = _score_ranked(rows, truth, broadcast, windows)

    report: dict[str, Any] = {
        "run_id": run_id,
        "metric": "top-1 and top-3 over all broadcast transactions",
        "metric_note": (
            "The denominator is every transaction put on the wire, not the transactions an "
            "observer recorded. recoverable_ceiling is the most any estimator here can score. "
            "top1 scores the ranking and ignores abstention, so it means the same thing for an "
            "estimator that refuses and for a trivial rule that cannot; top1_acted, coverage and "
            "precision_when_acted are what the estimator actually claimed."
        ),
        "observer_fraction": observer_fraction,
        "transactions_broadcast": broadcast,
        "transactions_with_a_candidate": int(candidates["txid"].n_unique()),
        "recoverable_ceiling": _round(reachable / broadcast) if broadcast else 0.0,
        "recoverable_ceiling_by_window": ceiling_by_window,
        "split": {
            "train_fraction": train_fraction,
            "boundary_us": boundary,
            "policy": "first_seen_us < boundary trains",
            "by_window_note": (
                "by_window denominators count only transactions an observer heard, so they do not "
                "sum to transactions_broadcast."
            ),
        },
        "baselines": sorted(baselines),
        "params": dict(sorted(params.items())),
        "scores": {name: asdict(score) for name, score in sorted(scores.items())},
    }
    out = MEASUREMENTS_ROOT / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "origin_accuracy.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return scores
