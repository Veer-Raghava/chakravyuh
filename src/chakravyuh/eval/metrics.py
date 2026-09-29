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


# --- per-granularity origin accuracy -----------------------------------------------------------
#
# The reframe's arithmetic. L0 above scores the exact host, which most observers never heard; the
# hero is L1, the operator, and it is winnable on transactions L0 cannot touch, because a sibling
# peer in the same ASN carries the operator even when the precise host is absent. So the ceiling
# and the accuracy are re-measured at each granularity, from the same per-candidate p_origin the
# ranking estimators shipped, rolled up here the way SHASTRA's asn_rollup rolls it up: mass summed
# per key, the ASN prior applied at L1 (never at L2, matching the stage), ranked with the same
# key-ascending tie-break so the ensemble's L1 top-1 here equals the operator it actually shipped.
#
# Truth for L1/L2 is `true_origin_asn` and `true_origin_country`, which only ground truth written
# at or after P0-b carries. When they are absent the granularity block is omitted with a note
# rather than scored against nulls, because a fabricated denominator is worse than a missing one.

GRAIN_K = 3


@dataclass(frozen=True)
class GranularityScore:
    """One estimator scored at one granularity. Shares of all broadcast transactions.

    `top1` is the rank-1 key hitting truth; `topk` is truth landing anywhere in the top `k`. Both
    ignore abstention for the same reason `OriginScore` does: the comparison is of ranking, and the
    baselines never refuse. `abstain_rate` is the share of scored transactions whose rank-1 key
    abstained, reported alongside rather than folded in.
    """

    top1: float
    topk: float
    abstain_rate: float
    n_correct: int
    n_scored: int
    by_traffic: Mapping[str, float]


def _rollup(
    ranked: pl.DataFrame, peers: pl.DataFrame, key: str, prior: pl.DataFrame | None
) -> pl.DataFrame:
    """Lift a per-candidate ranking to a per-key ranking, the way `asn_rollup` lifts it.

    `ranked` is `txid`, `peer_ip`, `rank`, `abstain`, and optionally `p_origin`. When `p_origin`
    is present the key's score is its summed candidate mass, times `prior` at L1; when it is absent
    (a trivial rule that carries no probability) the key inherits its best member's rank, so a rule
    that puts the originator's host first also puts its operator first. Ties break on the key
    ascending, the same order `_top_two` uses in the stage, so the ensemble's rank-1 key here is
    the operator it shipped. `abstain` at the key is whether its best-ranked member abstained.
    """
    labelled = ranked.join(peers.select("peer_ip", key), on="peer_ip", how="inner").filter(
        pl.col(key).is_not_null()
    )
    if "p_origin" in ranked.columns:
        grouped = labelled.group_by("txid", key, maintain_order=True).agg(
            pl.col("p_origin").sum().alias("_mass"),
            pl.col("rank").min().alias("_best"),
        )
        scored = grouped.with_columns(pl.col("_mass").alias("_score"))
        if prior is not None:
            scored = (
                scored.join(prior, on=key, how="left")
                .with_columns(
                    (pl.col("_mass") * (pl.col("_prior").fill_null(0.0) + 1e-12)).alias("_score")
                )
                .drop("_prior")
            )
    else:
        grouped = labelled.group_by("txid", key, maintain_order=True).agg(
            pl.col("rank").min().alias("_best")
        )
        # A trivial rule has no probability, so the key that owns the earliest-ranked host wins.
        # Negated so "smaller rank" becomes "larger score" and the sort below is one rule.
        scored = grouped.with_columns((-pl.col("_best")).cast(pl.Float64).alias("_score"))

    # The abstain flag each key inherits from its best-ranked member.
    best_member = (
        labelled.sort("rank")
        .group_by("txid", key, maintain_order=True)
        .agg(pl.col("abstain").first().alias("abstain"))
    )
    return (
        scored.join(best_member, on=["txid", key], how="left")
        .sort(["txid", "_score", key], descending=[False, True, False])
        .with_columns(pl.int_range(pl.len()).over("txid").add(1).alias("position"))
        .select("txid", key, "position", "abstain")
    )


def _score_grain(
    ranked: pl.DataFrame, truth: pl.DataFrame, key: str, truth_key: str, broadcast: int
) -> GranularityScore:
    """Score a per-key ranking against the answer key. `ranked` has `txid`, `key`, `position`."""
    joined = ranked.join(truth, on="txid", how="inner").with_columns(
        (pl.col(key) == pl.col(truth_key)).alias("hit")
    )
    at1 = joined.filter(pl.col("position") == 1)
    atk = joined.filter(pl.col("position") <= GRAIN_K).group_by("txid").agg(pl.col("hit").any())
    correct = int(at1["hit"].sum())
    abstained = int(at1.filter(pl.col("abstain")).height)
    by_traffic: dict[str, float] = {}
    for name in TRAFFIC:
        total = truth.filter(pl.col("traffic") == name).height
        got = at1.filter((pl.col("traffic") == name) & pl.col("hit")).height
        by_traffic[name] = _round(got / total) if total else 0.0
    return GranularityScore(
        top1=_round(correct / broadcast) if broadcast else 0.0,
        topk=_round(int(atk["hit"].sum()) / broadcast) if broadcast else 0.0,
        abstain_rate=_round(abstained / at1.height) if at1.height else 0.0,
        n_correct=correct,
        n_scored=at1.height,
        by_traffic=by_traffic,
    )


def _positioned(ranked: pl.DataFrame, key: str) -> pl.DataFrame:
    """A per-candidate ranking as `txid`, `key`, `position`, `abstain`, position from `rank`.

    Position is derived rather than read for the reason `_score_ranked` derives it: an abstaining
    transaction's ranks start at two, so `rank` is not an ordinal, but its order is intact.
    """
    return (
        ranked.sort(["txid", "rank"])
        .with_columns(pl.int_range(pl.len()).over("txid").add(1).alias("position"))
        .select("txid", key, "position", "abstain")
    )


def _l1_headline(observable: Path, truth: pl.DataFrame, broadcast: int) -> dict[str, Any] | None:
    """Score the operator SHASTRA actually shipped in `origin_l1.parquet`, not a re-derivation.

    `by_granularity.l1_asn` rolls every estimator up the same way for comparison; this scores the
    one row per transaction the stage committed to, including its abstention, so the report carries
    what the console will show as the hero. None when the headline is empty (no ASN substrate).
    """
    path = observable / "signals" / "origin_l1.parquet"
    if not path.is_file():
        return None
    l1 = pl.read_parquet(path, columns=["txid", "origin_asn", "abstain", "abstain_reason"])
    if l1.is_empty():
        return None
    joined = l1.join(truth.select("txid", "true_origin_asn", "traffic"), on="txid", how="inner")
    joined = joined.with_columns((pl.col("origin_asn") == pl.col("true_origin_asn")).alias("hit"))
    correct = int(joined["hit"].sum())
    acted = joined.filter(~pl.col("abstain"))
    acted_correct = int(acted["hit"].sum())
    by_traffic: dict[str, float] = {}
    for name in TRAFFIC:
        total = truth.filter(pl.col("traffic") == name).height
        got = joined.filter((pl.col("traffic") == name) & pl.col("hit")).height
        by_traffic[name] = _round(got / total) if total else 0.0
    return {
        "top1": _round(correct / broadcast) if broadcast else 0.0,
        "top1_acted": _round(acted_correct / broadcast) if broadcast else 0.0,
        "precision_when_acted": _round(acted_correct / acted.height) if acted.height else 0.0,
        "coverage": _round(acted.height / broadcast) if broadcast else 0.0,
        "abstain_rate": _round(float(l1["abstain"].mean())),  # type: ignore[arg-type]
        "cross_asn_ambiguous": int(
            l1.filter(pl.col("abstain_reason") == "cross_asn_ambiguous").height
        ),
        "n_transactions": l1.height,
        "by_traffic": by_traffic,
    }


def _by_granularity(
    ranked_l0: Mapping[str, pl.DataFrame],
    truth: pl.DataFrame,
    observable: Path,
    broadcast: int,
    candidates: pl.DataFrame,
    *,
    has_l1: bool,
    has_l2: bool,
) -> dict[str, Any]:
    """The reframe's four granularities, each with its own ceiling and per-estimator accuracy.

    L0 and L3 read the shipped per-candidate ranking directly; L1 and L2 roll it up to the operator
    and the country the way `asn_rollup` does, applying the ASN prior at L1 only. L1/L2 are omitted
    with a note when the answer key predates the columns they need, rather than scored against null.
    """
    peers = pl.read_parquet(
        observable / "normalised" / "peers.parquet", columns=["peer_ip", "asn", "geo_country"]
    )
    prior_path = observable / "normalised" / "asn_rollup.parquet"
    asn_prior = (
        pl.read_parquet(prior_path, columns=["asn", "frac_rank_one"]).rename(
            {"frac_rank_one": "_prior"}
        )
        if prior_path.is_file()
        else None
    )
    cand_keys = candidates.select("txid", "peer_ip").join(peers, on="peer_ip", how="inner")

    def _ceiling(key: str, truth_key: str) -> float:
        reach = (
            cand_keys.join(truth.select("txid", truth_key), on="txid", how="inner")
            .filter(pl.col(key) == pl.col(truth_key))
            .select("txid")
            .unique()
            .height
        )
        return _round(reach / broadcast) if broadcast else 0.0

    grain: dict[str, Any] = {}

    l0 = {
        name: _score_grain(
            _positioned(fr, "peer_ip"), truth, "peer_ip", "true_origin_ip", broadcast
        )
        for name, fr in ranked_l0.items()
    }
    l0_reach = (
        candidates.join(truth.select("txid", "true_origin_ip"), on="txid", how="inner")
        .filter(pl.col("peer_ip") == pl.col("true_origin_ip"))
        .select("txid")
        .unique()
        .height
    )
    grain["l0_host"] = {
        "note": "Exact announcing host. Officer-only; most observers never heard it.",
        "k": GRAIN_K,
        "recoverable_ceiling": _round(l0_reach / broadcast) if broadcast else 0.0,
        "scores": {name: asdict(score) for name, score in sorted(l0.items())},
    }

    # L3 is the shortlist: the same per-candidate ranking read as "is the host anywhere in the top
    # k", the number the console leads with, plus the mean shell size the ensemble committed to.
    shortlist_size = 0.0
    l1_path = observable / "signals" / "origin_l1.parquet"
    if l1_path.is_file():
        l1_sizes = pl.read_parquet(l1_path, columns=["shortlist_size"])
        if not l1_sizes.is_empty():
            shortlist_size = _round(float(l1_sizes["shortlist_size"].mean()))  # type: ignore[arg-type]
    grain["l3_shortlist_topk"] = {
        "note": "The host inside the top-k shortlist, the confidence set the console draws.",
        "k": GRAIN_K,
        "recoverable_ceiling": grain["l0_host"]["recoverable_ceiling"],
        "mean_shortlist_size": shortlist_size,
        "scores": {
            name: {"topk": asdict(score)["topk"], "by_traffic": asdict(score)["by_traffic"]}
            for name, score in sorted(l0.items())
        },
    }

    if has_l1:
        l1 = {
            name: _score_grain(
                _rollup(fr, peers, "asn", asn_prior), truth, "asn", "true_origin_asn", broadcast
            )
            for name, fr in ranked_l0.items()
        }
        grain["l1_asn"] = {
            "note": "The network operator (ASN). The hero: winnable where the exact host is not.",
            "k": GRAIN_K,
            "recoverable_ceiling": _ceiling("asn", "true_origin_asn"),
            "scores": {name: asdict(score) for name, score in sorted(l1.items())},
        }
        headline = _l1_headline(observable, truth, broadcast)
        if headline is not None:
            grain["l1_headline"] = {
                "note": "The one operator per transaction origin_l1.parquet shipped, with its "
                "abstention. This is what the console shows, not a re-derivation.",
                **headline,
            }
    else:
        grain["l1_asn"] = {
            "note": "Omitted: this run's ground truth predates true_origin_asn, so L1 cannot be "
            "scored without fabricating a denominator. Regenerate ground truth to score it."
        }

    if has_l2:
        l2 = {
            name: _score_grain(
                _rollup(fr, peers, "geo_country", None),
                truth,
                "geo_country",
                "true_origin_country",
                broadcast,
            )
            for name, fr in ranked_l0.items()
        }
        grain["l2_region"] = {
            "note": "The country. Coarsest granularity, so the highest ceiling of the four.",
            "k": GRAIN_K,
            "recoverable_ceiling": _ceiling("geo_country", "true_origin_country"),
            "scores": {name: asdict(score) for name, score in sorted(l2.items())},
        }
    else:
        grain["l2_region"] = {
            "note": "Omitted: this run's ground truth predates true_origin_country."
        }

    return grain


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
    truth_all = pl.read_parquet(key)
    has_l1 = "true_origin_asn" in truth_all.columns
    has_l2 = "true_origin_country" in truth_all.columns
    truth = truth_all.with_columns(_traffic_expr())

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

    ranked_l0: dict[str, pl.DataFrame] = {
        "first_seen": _rank_by(candidates, ["seen_us", "row_id"], [False, False]),
        "payer_linkage": _payer_linkage(observable, candidates),
    }
    baselines = tuple(ranked_l0)
    scores: dict[str, OriginScore] = {
        name: _score_ranked(frame, truth, broadcast, windows) for name, frame in ranked_l0.items()
    }

    estimates = pl.read_parquet(
        observable / "signals" / "origin_estimates.parquet",
        columns=["txid", "peer_ip", "p_origin", "rank", "abstain", "estimator"],
    )
    for name in sorted(estimates["estimator"].unique().to_list()):
        if name in scores:
            raise ValueError(
                f"signals/ names an estimator {name!r}, which collides with a baseline key in "
                "origin_accuracy.json. Rename the estimator: the report has to keep the two "
                "apart or the gate compares a number against itself."
            )
        rows = estimates.filter(pl.col("estimator") == name).drop("estimator")
        ranked_l0[name] = rows
        scores[name] = _score_ranked(rows, truth, broadcast, windows)

    by_granularity = _by_granularity(
        ranked_l0, truth, observable, broadcast, candidates, has_l1=has_l1, has_l2=has_l2
    )

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
        "by_granularity": by_granularity,
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


# --- wallet risk scoring ------------------------------------------------------------------------
#
# BUDDHI's side of the label door. A stage passes its predictions in — subject, member addresses,
# a score, and which side of its own conformal sets each class fell on — and gets figures back.
# The labels those figures were computed from never cross back, which is what lets
# `scores/eval_report.json` sit exactly where the frozen contract puts it while BUDDHI holds no
# evaluation-window label of any kind.
#
# Everything measured here is measured on the holdout window alone. The training window's
# addresses were the model's own fitting data, so a number that included them would measure
# memorisation, and the report marks the denominator so it cannot be read as run-wide.


@dataclass(frozen=True)
class WalletScore:
    """What a wallet risk model scored, on holdout subjects only. Numbers, never labels."""

    n_subjects: int
    n_illicit: int
    n_labelled: int
    pr_auc: float
    roc_auc: float
    precision_at_20: float
    recall_at_20: float
    abstain_rate: float
    coverage_by_class: dict[str, float]
    baseline: dict[str, Any]
    baseline_beaten: bool
    n_unlabelled: int


def _auc(y_true: Sequence[int], scores: Sequence[float], pr: bool) -> float:
    """PR-AUC by average precision, ROC-AUC by rank sum. Small data, no sklearn dependency.

    Implemented here rather than imported for one reason: the evaluation is the answer key's side
    of the door, and its arithmetic should be readable by the same person who audits the door.
    """
    pairs = sorted(zip(scores, y_true, strict=True), key=lambda p: (-p[0], p[1]))
    n_pos = sum(y_true)
    if n_pos == 0 or n_pos == len(y_true):
        return 0.0
    if pr:
        tp = 0.0
        fp = 0.0
        ap = 0.0
        prev_recall = 0.0
        for _, label in pairs:
            if label:
                tp += 1
            else:
                fp += 1
            recall = tp / n_pos
            precision = tp / (tp + fp)
            ap += (recall - prev_recall) * precision
            prev_recall = recall
        return ap
    # ROC-AUC = Mann-Whitney U, so ranks run low-score-first (rank 1 = lowest score) and
    # tied scores share the midrank. `pairs` above is sorted high-score-first for PR; ranking
    # off it directly would compute 1 - AUC (a perfect model would score 0.0), so re-sort here.
    asc = sorted(zip(scores, y_true, strict=True), key=lambda p: p[0])
    n_neg = len(y_true) - n_pos
    rank_sum_pos = 0.0
    i = 0
    while i < len(asc):
        j = i
        while j < len(asc) and asc[j][0] == asc[i][0]:
            j += 1
        midrank = (i + 1 + j) / 2  # average of the 1-based ranks i+1..j in this tie block
        rank_sum_pos += midrank * sum(label for _, label in asc[i:j])
        i = j
    return (rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def _true_label_of_subject(addresses: Sequence[str], truth: pl.DataFrame) -> tuple[int, int]:
    """A subject's label: majority `is_illicit` over its member addresses' true owners.

    A tie is licit, on the same reasoning SHASTRA's rank 1 needs a strict winner: an accusation
    must not rest on a coin toss. Returns `(label, n_labelled)`; zero labelled means the subject
    cannot be scored and is excluded from every numerator and denominator here.
    """
    if not addresses:
        return 0, 0
    members = pl.DataFrame({"address": list(addresses)}).join(truth, on="address", how="inner")
    if members.is_empty():
        return 0, 0
    illicit = int(members["is_illicit"].sum())
    return (1 if illicit * 2 > members.height else 0), members.height


def _campaign_recall(
    predictions: pl.DataFrame, truth_illicit: pl.DataFrame
) -> tuple[int, int, float]:
    """Campaign = illicit entity_id. Caught = >=1 of its addresses is in a flagged subject.

    `truth_illicit` is address-grain rows (entity_id, is_illicit, address) already restricted to
    holdout addresses of illicit entities by the caller. Recall is over illicit entities only.
    """
    addr_flag = (
        predictions.explode("addresses")
        .rename({"addresses": "address"})
        .select("address", pl.col("in_set_1").alias("flagged"))
    )
    joined = truth_illicit.join(addr_flag, on="address", how="left").with_columns(
        pl.col("flagged").fill_null(False)
    )
    per_entity = joined.group_by("entity_id").agg(pl.col("flagged").any().alias("caught"))
    total = per_entity.height
    caught = int(per_entity["caught"].sum())
    return caught, total, (caught / total if total else 0.0)


def score_wallets(
    run_id: str,
    *,
    predictions: pl.DataFrame,
    boundary_us: int,
    coverage_target: float,
    params: Mapping[str, Any],
    write: bool = True,
) -> dict[str, Any] | None:
    """Score BUDDHI's wallet predictions against the run's answer key; write `model_report.json`.

    `run_id` is a run id, never a path: the answer key, the observable tree and the measurements
    directory are all derived from it, exactly as `score_origin` does it. Returns None when the
    answer key is absent, because Law 2 rule 6 says inference must complete without it.

    `predictions` carries `subject_id`, `addresses` (list[string]), `risk_score` (float), and the
    per-class conformal verdicts `in_set_0` and `in_set_1` (bool). The per-class sets, not a
    thresholded score, are what coverage means here: a class is covered when the true label's
    column is in the set. Holdout is decided here, from the observable `addresses.parquet`, so a
    stage cannot select its own evaluation rows.

    `write=False` scores a second ranking of the same subjects — BUDDHI's GNN leg calls it with the
    baseline booster's scores to measure the counterfactual — and returns the report without
    filing it. The file `model_report.json` is always the shipped model's, so the one thing a
    mis-ordered call cannot do is leave a comparison standing where the result should be.
    """
    if not RUN_ID.match(run_id):
        raise ValueError(f"run_id must match {RUN_ID.pattern}, got {run_id!r}")
    observable = GENERATED_ROOT / run_id
    key = GROUND_TRUTH_ROOT / run_id / ENTITIES
    if not key.is_file():
        return None

    truth = (
        pl.read_parquet(key, columns=["is_illicit", "addresses"])
        .explode("addresses")
        .rename({"addresses": "address"})
        .drop_nulls("address")
        .unique(subset=["address"])
    )

    first_seen = pl.read_parquet(
        observable / "normalised" / "addresses.parquet", columns=["address", "first_seen_us"]
    )
    truth = truth.join(first_seen, on="address", how="inner")
    holdout_addresses = set(
        truth.filter(pl.col("first_seen_us") >= boundary_us)["address"].to_list()
    )

    rows: list[dict[str, Any]] = []
    for row in predictions.iter_rows(named=True):
        members = [a for a in row["addresses"] if a in holdout_addresses]
        if not members:
            continue
        label, _ = _true_label_of_subject(members, truth)
        rows.append(
            {
                "subject_id": row["subject_id"],
                "risk_score": float(row["risk_score"]),
                "in_set_0": bool(row["in_set_0"]),
                "in_set_1": bool(row["in_set_1"]),
                "abstain": bool(row["abstain"]),
                "label": label,
            }
        )
    if not rows:
        return None
    frame = pl.DataFrame(rows)

    y = frame["label"].to_list()
    s = frame["risk_score"].to_list()
    n_illicit = sum(y)
    n_labelled = len(y)

    # Tie-break on subject_id, so two runs of one seed rank equal scores identically: a metric
    # whose top-20 depends on dict iteration order is not a measurement.
    order = sorted(range(n_labelled), key=lambda i: (-s[i], frame["subject_id"][i]))
    top = order[:20]
    n_top = len(top)
    hits = sum(y[i] for i in top)
    precision_at_20 = hits / n_top if n_top else 0.0
    total_illicit = n_illicit
    recall_at_20 = hits / total_illicit if total_illicit else 0.0

    abstain_rate = float(frame["abstain"].mean())  # type: ignore[arg-type]

    coverage: dict[str, float] = {}
    for k, col in ((0, "in_set_0"), (1, "in_set_1")):
        mask = frame.filter(pl.col("label") == k)
        coverage[str(k)] = _round(float(mask[col].mean())) if mask.height else 0.0  # type: ignore[arg-type]

    n_unlabelled = int(
        predictions.filter(~pl.col("subject_id").is_in(frame["subject_id"].to_list())).height
    )

    # Three grains, all under the inductive time-ordered split. The guard makes a transductive
    # (or None) boundary unable to emit a grain number at all: the whole point of these figures
    # is that the holdout was decided by first-activity time, not chosen after the fact.
    assert boundary_us is not None, "eval must run under the inductive time-ordered split"

    # Campaign grain: an illicit entity is caught when >=1 of its holdout addresses lands in a
    # flagged subject. Recall is over illicit entities only.
    entities = (
        pl.read_parquet(key, columns=["entity_id", "is_illicit", "addresses"])
        .explode("addresses")
        .rename({"addresses": "address"})
        .drop_nulls("address")
        .unique(subset=["address"])
    )
    truth_illicit = entities.filter(
        pl.col("is_illicit") & pl.col("address").is_in(holdout_addresses)
    ).select("entity_id", "is_illicit", "address")
    n_caught, n_campaigns, campaign_recall = _campaign_recall(predictions, truth_illicit)

    # Tx grain: label a holdout tx illicit when any input address is owned by an illicit entity;
    # score it by the max risk_score of any subject holding one of its input addresses (0 if none).
    illicit_addresses = set(truth.filter(pl.col("is_illicit"))["address"].to_list())
    addr_score = (
        predictions.explode("addresses")
        .rename({"addresses": "address"})
        .drop_nulls("address")
        .group_by("address")
        .agg(pl.col("risk_score").max().alias("addr_score"))
    )
    tx = pl.read_parquet(
        observable / "normalised" / "transactions.parquet",
        columns=["txid", "input_addresses", "first_seen_us"],
    ).filter(pl.col("first_seen_us") >= boundary_us)
    per_tx = (
        tx.select("txid", "input_addresses")
        .explode("input_addresses")
        .rename({"input_addresses": "address"})
        .join(addr_score, on="address", how="left")
        .with_columns(
            pl.col("addr_score").fill_null(0.0),
            pl.col("address").is_in(illicit_addresses).fill_null(False).alias("addr_illicit"),
        )
        .group_by("txid")
        .agg(
            pl.col("addr_score").max().alias("score"),
            pl.col("addr_illicit").any().alias("label_bool"),
        )
    )
    tx_y = [int(v) for v in per_tx["label_bool"].to_list()]
    tx_s = per_tx["score"].to_list()
    tx_ids = per_tx["txid"].to_list()
    # Tie-break on txid, same reasoning as the actor top-20: a metric that reads dict order is not
    # a measurement.
    tx_order = sorted(range(per_tx.height), key=lambda i: (-tx_s[i], tx_ids[i]))
    tx_top = tx_order[:20]
    tx_precision_at_20 = sum(tx_y[i] for i in tx_top) / len(tx_top) if tx_top else 0.0

    return _write_wallet_report(
        run_id,
        y=y,
        s=s,
        subject_ids=frame["subject_id"].to_list(),
        precision_at_20=precision_at_20,
        recall_at_20=recall_at_20,
        abstain_rate=abstain_rate,
        coverage=coverage,
        n_unlabelled=n_unlabelled,
        boundary_us=boundary_us,
        coverage_target=coverage_target,
        params=params,
        write=write,
        tx_pr_auc=_auc(tx_y, tx_s, pr=True),
        tx_roc_auc=_auc(tx_y, tx_s, pr=False),
        tx_precision_at_20=tx_precision_at_20,
        tx_n_scored=per_tx.height,
        campaign_recall=campaign_recall,
        n_campaigns=n_campaigns,
        n_caught=n_caught,
    )


def _write_wallet_report(
    run_id: str,
    *,
    y: list[int],
    s: list[float],
    subject_ids: list[str],
    precision_at_20: float,
    recall_at_20: float,
    abstain_rate: float,
    coverage: dict[str, float],
    n_unlabelled: int,
    boundary_us: int,
    coverage_target: float,
    params: Mapping[str, Any],
    write: bool = True,
    tx_pr_auc: float = 0.0,
    tx_roc_auc: float = 0.0,
    tx_precision_at_20: float = 0.0,
    tx_n_scored: int = 0,
    campaign_recall: float = 0.0,
    n_campaigns: int = 0,
    n_caught: int = 0,
) -> dict[str, Any] | None:
    """Assemble and write `model_report.json`, reading the baseline file if one exists.

    Split out from `score_wallets` so the baseline measurement can pass through the same
    assembly: it is scored here as an ordinary prediction table, its `wallet_model` numbers are
    written to `baseline_wallet.json` where the model's own report reads them, and the file
    `score_wallets` writes is restored afterwards — one scoring pass, one report.
    """
    n_illicit = sum(y)
    n_labelled = len(y)
    actor_pr_auc = _round(_auc(y, s, pr=True))
    actor_roc_auc = _round(_auc(y, s, pr=False))
    baseline_report = MEASUREMENTS_ROOT / run_id / "baseline_wallet.json"
    baseline = json.loads(baseline_report.read_text()) if baseline_report.is_file() else None
    baseline_beaten = bool(
        baseline and precision_at_20 > float(baseline.get("precision_at_20", 0.0))
    )
    report: dict[str, Any] = {
        "run_id": run_id,
        "metric": "wallet risk, holdout subjects only",
        "metric_note": (
            "Every figure below is computed over subjects whose earliest activity is at or after "
            "the split boundary. A subject's label is the majority is_illicit of its members' "
            "true owners, ties licit; subjects with no holdout member are excluded. Coverage is "
            "class-conditional: the fraction of class-k subjects whose class-k conformal flag is "
            "in the set."
        ),
        "split": {
            "boundary_us": boundary_us,
            "policy": "subject first activity >= boundary is holdout",
            "coverage_target": coverage_target,
        },
        "wallet_model": {
            "pr_auc": actor_pr_auc,
            "roc_auc": actor_roc_auc,
            "precision_at_20": _round(precision_at_20),
            "recall_at_20": _round(recall_at_20),
            "n_scored": n_labelled,
            "n_top": min(20, n_labelled),
            "abstain_rate": _round(abstain_rate),
            "actor_level": {
                "pr_auc": actor_pr_auc,
                "roc_auc": actor_roc_auc,
                "precision_at_20": _round(precision_at_20),
                "recall_at_20": _round(recall_at_20),
                "n_scored": n_labelled,
            },
            "tx_level": {
                "pr_auc": _round(tx_pr_auc),
                "roc_auc": _round(tx_roc_auc),
                "precision_at_20": _round(tx_precision_at_20),
                "n_scored": tx_n_scored,
            },
            "campaign_level": {
                "campaign_recall": _round(campaign_recall),
                "n_campaigns": n_campaigns,
                "n_caught": n_caught,
            },
        },
        "protocol": split.PROTOCOL,
        "coverage_by_class": coverage,
        "imbalance_ratio": f"1:{max(1, round((n_labelled - n_illicit) / max(1, n_illicit)))}",
        "baseline": baseline,
        "baseline_beaten": baseline_beaten,
        "n_subjects_excluded_unlabelled": n_unlabelled,
        "params": dict(sorted(params.items())),
    }
    out = MEASUREMENTS_ROOT / run_id
    out.mkdir(parents=True, exist_ok=True)
    if write:
        (out / "model_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return report


def write_baseline_wallet(
    run_id: str,
    *,
    predictions: pl.DataFrame,
    boundary_us: int,
    params: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Score the trivial baseline and file its bar at `measurements/<run>/baseline_wallet.json`.

    The baseline is scored through the same `score_wallets` arithmetic the model is, so the two
    numbers on the slide are comparable by construction rather than by trust. Its report is
    written to `baseline_wallet.json` — the file `score_wallets` reads `baseline_beaten` from —
    and `model_report.json`, which that pass overwrote, is restored to its previous content so
    a baseline measurement never replaces a model report.
    """
    model_report = MEASUREMENTS_ROOT / run_id / "model_report.json"
    saved = model_report.read_text(encoding="utf-8") if model_report.is_file() else None
    report = score_wallets(
        run_id,
        predictions=predictions,
        boundary_us=boundary_us,
        coverage_target=0.0,
        params=params,
    )
    if report is None:
        return None
    (MEASUREMENTS_ROOT / run_id / "baseline_wallet.json").write_text(
        json.dumps(
            {
                "rule": params.get("rule", "rank_by_total_value_received"),
                "precision_at_20": report["wallet_model"]["precision_at_20"],
                "recall_at_20": report["wallet_model"]["recall_at_20"],
                "n_scored": report["wallet_model"]["n_scored"],
                "split": report["split"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if saved is not None:
        model_report.write_text(saved, encoding="utf-8")
    return report
