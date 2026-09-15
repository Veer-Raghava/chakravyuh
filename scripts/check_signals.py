"""Check `signals/` against contract section 6, from outside the code that wrote it.

`check_stage.py` checks the manifest's arithmetic. This checks the file itself, and in particular
the three rules section 6 calls the ones that make it honest, none of which a schema check can see:

  p_origin is not renormalised. Sums at or below one per txid, and a real share of transactions
  strictly below one, because a file whose every transaction sums to exactly one has thrown away
  the "none of these peers is the originator" information the contract says the sum carries.
  An abstaining transaction has no rank 1 row, and a transaction that did not abstain has exactly
  one.
  Every estimator in the column is independently runnable, checked here as: each one ranks the same
  candidate set, so two of them can be printed side by side without one having scored fewer
  transactions than the other.

Transcribed from the contract by hand, never imported from `chakravyuh.shastra.schema`. A checker
that imports the writer's constants asserts only that a module equals itself.

Writes file names, field names and counts to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

# Contract section 6, column order and dtype. The struct's interior is checked separately, because
# the contract fixes eight field names and explicitly permits more. `pl.Struct` appears as the
# class rather than an instance here; `_schema` handles both, and typing the tuple as
# `type[pl.DataType] | pl.DataType` is what the union costs.
ORIGIN_ESTIMATES: tuple[tuple[str, pl.DataType | type[pl.DataType]], ...] = (
    ("txid", pl.String()),
    ("peer_ip", pl.String()),
    ("p_origin", pl.Float64()),
    ("rank", pl.Int32()),
    ("margin", pl.Float64()),
    ("features", pl.Struct),  # interior checked by _features
    ("estimator", pl.String()),
    ("abstain", pl.Boolean()),
    ("abstain_reason", pl.String()),
)

# "The features struct holds at minimum", in the order section 6 lists them. The contract does not
# type these, so only their presence is checked.
REQUIRED_FEATURES: tuple[str, ...] = (
    "delta_first_us",
    "rank_in_tx",
    "n_announcements",
    "n_observers_seen",
    "peer_frac_rank_one",
    "peer_n_txids",
    "net_class",
    "announce_spread_us",
)

TYPOLOGY_HITS: tuple[tuple[str, pl.DataType], ...] = (
    ("hit_id", pl.String()),
    ("typology", pl.String()),
    ("subject_id", pl.String()),
    ("txids", pl.List(pl.String())),
    ("strength", pl.Float64()),
    ("params", pl.Struct({"threshold": pl.Float64(), "window_us": pl.Int64()})),
)

ENTITY_TYPES: tuple[tuple[str, pl.DataType], ...] = (
    ("subject_id", pl.String()),
    ("predicted_type", pl.String()),
    ("confidence", pl.Float64()),
    ("basis", pl.List(pl.String())),
    ("exempt_from_scoring", pl.Boolean()),
)

ESTIMATORS = {"first_spy", "weighted_first_seen", "bayes_peer_prior", "ensemble"}
ABSTAIN_REASONS = {"tor_present", "single_observer", "margin_below_floor", "too_few_announcements"}
TYPOLOGIES = {
    "peel_chain",
    "structuring",
    "fan_out",
    "pass_through",
    "coinjoin_like",
    "rapid_hop",
}
BASIS = {
    "coinbase_origination",
    "payout_cadence",
    "long_dwell",
    "high_fanout",
    "port_diversity",
    "known_service_pattern",
}

# Float slack. Probabilities are summed per transaction, so a handful of ulps can accumulate; a
# renormalised file misses by 0.5, not by 1e-9.
EPSILON = 1e-9

# The share of transactions that must sum strictly below one for the no-renormalisation rule to
# have been checked rather than merely stated. A file that renormalised has every transaction at
# exactly one, so any non-trivial share below one refutes it. Ten percent, because the recoverable
# ceiling is 0.42 even at observer_fraction 0.70: an estimator confident on nine transactions in
# ten would be claiming more than the capture contains.
MIN_SHARE_BELOW_ONE = 0.10


def _schema(
    frame: pl.DataFrame,
    expected: tuple[tuple[str, pl.DataType | type[pl.DataType]], ...],
    name: str,
) -> list[str]:
    """Column names in contract order, and each dtype, for one table."""
    problems: list[str] = []
    want = [column for column, _ in expected]
    got = list(frame.columns)
    if got != want:
        problems.append(f"{name}: columns are {got}, contract section 6 says {want}")
        return problems
    for column, dtype in expected:
        found = frame.schema[column]
        ok = isinstance(found, dtype) if isinstance(dtype, type) else found == dtype
        if not ok:
            problems.append(f"{name}: {column} is {found}, contract section 6 says {dtype}")
    return problems


def _features(frame: pl.DataFrame) -> list[str]:
    """The eight field names section 6 requires the struct to hold at minimum."""
    dtype = frame.schema["features"]
    if not isinstance(dtype, pl.Struct):
        return ["features is not a struct"]
    present = [field.name for field in dtype.fields]
    missing = [name for name in REQUIRED_FEATURES if name not in present]
    if missing:
        return [f"features struct is missing {missing}, which section 6 requires at minimum"]
    if present[: len(REQUIRED_FEATURES)] != list(REQUIRED_FEATURES):
        # Not a contract violation, a legibility one: the contract lists eight and a reader
        # diffing the file against it should find them first rather than scattered.
        return [
            "the eight required features are present but not first in the struct, so the file "
            "cannot be read against section 6 field by field"
        ]
    return []


def _vocabularies(estimates: pl.DataFrame) -> list[str]:
    """Closed vocabularies, and the agreement between `abstain` and `abstain_reason`."""
    problems: list[str] = []
    stray = set(estimates["estimator"].drop_nulls().to_list()) - ESTIMATORS
    if stray:
        problems.append(f"estimator values outside contract section 6: {sorted(stray)}")
    stray_reasons = set(estimates["abstain_reason"].drop_nulls().to_list()) - ABSTAIN_REASONS
    if stray_reasons:
        problems.append(
            f"abstain_reason values outside contract section 6: {sorted(stray_reasons)}"
        )

    disagree = estimates.filter(pl.col("abstain") != pl.col("abstain_reason").is_not_null()).height
    if disagree:
        problems.append(
            f"{disagree} rows where abstain and abstain_reason disagree. A refusal without a "
            "reason cannot be reviewed and a reason without a refusal is not one."
        )
    for column in ("txid", "peer_ip", "p_origin", "rank", "margin", "estimator", "abstain"):
        nulls = estimates[column].null_count()
        if nulls:
            problems.append(f"{nulls} null values in {column}, which section 6 does not permit")
    out_of_range = estimates.filter((pl.col("p_origin") < 0.0) | (pl.col("p_origin") > 1.0)).height
    if out_of_range:
        problems.append(f"{out_of_range} rows whose p_origin is outside 0 and 1")
    return problems


def _sums(estimates: pl.DataFrame) -> list[str]:
    """Rule one: `p_origin` sums to at most one per txid, and is not renormalised to exactly one."""
    problems: list[str] = []
    totals = estimates.group_by("estimator", "txid").agg(pl.col("p_origin").sum().alias("total"))
    over = totals.filter(pl.col("total") > 1.0 + EPSILON)
    if over.height:
        # Same `type: ignore` as tests/test_chain.py:136: a Polars Series max can be a date or
        # a list, and only the float branch is real over a `p_origin` column.
        worst = float(over["total"].max() or 0.0)  # type: ignore[arg-type]
        problems.append(
            f"{over.height} transactions whose p_origin sums above one, the worst at {worst:.6f}"
        )
    for name in sorted(totals["estimator"].unique().to_list()):
        rows = totals.filter(pl.col("estimator") == name)
        if not rows.height:
            continue
        below = rows.filter(pl.col("total") < 1.0 - EPSILON).height
        share = below / rows.height
        if share < MIN_SHARE_BELOW_ONE:
            problems.append(
                f"{name}: only {share:.3f} of transactions sum below one. Section 6 forbids "
                "renormalising to exactly one, because the shortfall is how the file says none of "
                "these peers was observed originating it."
            )
    return problems


def _ranking(estimates: pl.DataFrame) -> list[str]:
    """Rule two, plus the ranking being total: one row per rank, contiguous, from 1 or from 2."""
    problems: list[str] = []
    accused = estimates.filter(pl.col("abstain") & (pl.col("rank") == 1))
    if accused.height:
        problems.append(
            f"{accused.height} rows rank an abstaining transaction's peer at 1. Section 6 says no "
            "row of an abstaining txid has rank 1, and a consumer reads rank 1 as an accusation."
        )

    grouped = estimates.group_by("estimator", "txid").agg(
        pl.len().alias("n"),
        pl.col("rank").n_unique().alias("distinct"),
        pl.col("rank").min().alias("lowest"),
        pl.col("rank").max().alias("highest"),
        pl.col("abstain").any().alias("abstained"),
        pl.col("abstain").all().alias("all_abstained"),
    )
    ties = grouped.filter(pl.col("n") != pl.col("distinct")).height
    if ties:
        problems.append(f"{ties} transactions where two candidates share a rank")
    mixed = grouped.filter(pl.col("abstained") != pl.col("all_abstained")).height
    if mixed:
        problems.append(
            f"{mixed} transactions where some candidates abstain and others do not. Abstention is "
            "a decision about the transaction, so a partial one cannot be read."
        )
    expected_low = pl.col("abstained").cast(pl.Int32) + 1
    wrong_start = grouped.filter(pl.col("lowest") != expected_low).height
    if wrong_start:
        problems.append(
            f"{wrong_start} transactions whose best rank is neither 1 nor, when abstaining, 2"
        )
    gaps = grouped.filter(pl.col("highest") - pl.col("lowest") + 1 != pl.col("n")).height
    if gaps:
        problems.append(f"{gaps} transactions whose ranks have a gap, so the ordering is not total")
    return problems


def _margins(estimates: pl.DataFrame) -> list[str]:
    """`margin` is rank 1's `p_origin` minus rank 2's, per section 6, and constant per txid."""
    ordered = estimates.sort(["estimator", "txid", "rank"]).with_columns(
        pl.int_range(pl.len()).over("estimator", "txid").alias("position")
    )
    top = ordered.filter(pl.col("position") == 0).select(
        "estimator", "txid", pl.col("p_origin").alias("p1"), pl.col("margin").alias("recorded")
    )
    second = ordered.filter(pl.col("position") == 1).select(
        "estimator", "txid", pl.col("p_origin").alias("p2")
    )
    joined = (
        top.join(second, on=["estimator", "txid"], how="left")
        .with_columns(pl.col("p2").fill_null(0.0))
        .with_columns((pl.col("p1") - pl.col("p2")).alias("derived"))
    )
    problems: list[str] = []
    wrong = joined.filter((pl.col("recorded") - pl.col("derived")).abs() > EPSILON).height
    if wrong:
        problems.append(
            f"{wrong} transactions whose margin is not the top two p_origin values subtracted. "
            "Section 6 defines the column, so a different quantity under that name misleads."
        )
    varying = (
        estimates.group_by("estimator", "txid").agg(pl.col("margin").n_unique().alias("distinct"))
    ).filter(pl.col("distinct") > 1)
    if varying.height:
        problems.append(
            f"{varying.height} transactions carry more than one margin value across their rows"
        )
    return problems


def _coverage(normalised: Path, estimates: pl.DataFrame) -> list[str]:
    """One row per candidate peer per txid, and every estimator ranking the same candidates.

    The candidate set is derived from `normalised/announcements.parquet`, which is the input
    SHASTRA was handed: section 6's "a txid with nine announcing peers produces nine rows" is a
    statement about that file, so it is the only place the expected set can honestly come from.
    """
    announcements = pl.read_parquet(
        normalised / "announcements.parquet", columns=["txid", "peer_ip"]
    ).unique()
    problems: list[str] = []
    names = sorted(estimates["estimator"].unique().to_list())
    for name in names:
        rows = estimates.filter(pl.col("estimator") == name).select("txid", "peer_ip")
        if rows.height != rows.unique().height:
            problems.append(f"{name}: the same (txid, peer) pair is ranked more than once")
        missing = announcements.join(rows, on=["txid", "peer_ip"], how="anti").height
        extra = rows.join(announcements, on=["txid", "peer_ip"], how="anti").height
        if missing:
            problems.append(
                f"{name}: {missing} announcing peers have no row, so the estimator scored fewer "
                "candidates than the capture holds"
            )
        if extra:
            problems.append(
                f"{name}: {extra} ranked candidates announced nothing in normalised/, so a peer "
                "was invented"
            )
    return problems


def check(normalised: Path, signals: Path) -> list[str]:
    """Every way `signals/` fails contract section 6. Empty means it holds."""
    problems: list[str] = []
    for name in ("origin_estimates.parquet", "typology_hits.parquet", "entity_types.parquet"):
        if not (signals / name).is_file():
            problems.append(f"no {name} in {signals}, which section 6 requires")
    if problems:
        return problems

    estimates = pl.read_parquet(signals / "origin_estimates.parquet")
    problems += _schema(estimates, ORIGIN_ESTIMATES, "origin_estimates.parquet")
    if problems:
        # Every check below indexes columns by name, so a wrong shape is reported alone rather
        # than buried under the KeyErrors it would cause.
        return problems

    problems += _features(estimates)
    problems += _vocabularies(estimates)
    if estimates.is_empty():
        problems.append("origin_estimates.parquet has no rows, so nothing was estimated")
        return problems
    problems += _sums(estimates)
    problems += _ranking(estimates)
    problems += _margins(estimates)
    problems += _coverage(normalised, estimates)

    hits = pl.read_parquet(signals / "typology_hits.parquet")
    problems += _schema(hits, TYPOLOGY_HITS, "typology_hits.parquet")
    stray = set(hits["typology"].drop_nulls().to_list()) - TYPOLOGIES if hits.height else set()
    if stray:
        problems.append(f"typology values outside contract section 6: {sorted(stray)}")

    types = pl.read_parquet(signals / "entity_types.parquet")
    problems += _schema(types, ENTITY_TYPES, "entity_types.parquet")
    if types.height:
        stray_basis = set(types["basis"].explode().drop_nulls().to_list()) - BASIS
        if stray_basis:
            problems.append(f"basis values outside contract section 6: {sorted(stray_basis)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        sys.stderr.write("usage: check_signals.py <normalised-dir> <signals-dir>\n")
        return 2
    normalised, signals = Path(args[0]), Path(args[1])
    for root in (normalised, signals):
        if not root.is_dir():
            sys.stderr.write(f"check_signals: {root} is not a directory\n")
            return 2

    problems = check(normalised, signals)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_signals: {len(problems)} problems in {signals}\n")
        return 1

    estimates = pl.read_parquet(
        signals / "origin_estimates.parquet", columns=["txid", "estimator", "abstain"]
    )
    names = sorted(estimates["estimator"].unique().to_list())
    abstained = (
        estimates.group_by("estimator")
        .agg(pl.col("txid").filter(pl.col("abstain")).n_unique().alias("n"))
        .sort("estimator")
    )
    summary = ", ".join(f"{row[0]} abstains on {row[1]}" for row in abstained.iter_rows())
    sys.stderr.write(
        f"check_signals: {signals} OK, {len(names)} estimators over "
        f"{estimates['txid'].n_unique()} transactions, {summary}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
