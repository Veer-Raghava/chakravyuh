"""SHASTRA: what must hold when an estimate is written for every candidate peer.

Three groups of tests. The behaviour group works from hand-built frames small enough to check
by eye, because the honesty rules of contract section 6 — no renormalisation, no rank 1 on an
abstention, ties break deterministically — are properties of `_finalise` and a fixture-sized
frame shows them without a LightGBM fit anywhere near. The stage group runs the real pipeline
over the committed capture fixture, sealed and normalised fresh inside a throwaway repo root,
so the path guards are exercised rather than stepped around. The quarantine group holds the
two Law 2 rules only a real run can demonstrate, and both of its tests are registered in
`tests/conftest.py` for `make verify-quarantine`.

Nothing here builds a capture or fits the learned model: `make verify-s06` does both at gate
scale in two separate interpreters, and a test that re-ran the fit would be a slower, weaker
copy of the byte-compare that gate already does.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import polars as pl
import pytest

from chakravyuh.jaal.stage import build_run as build_graph
from chakravyuh.jaal.stage import resolve_in as jaal_in
from chakravyuh.jaal.stage import resolve_out as jaal_out
from chakravyuh.kavach.seal import resolve_out as kavach_out
from chakravyuh.kavach.seal import seal
from chakravyuh.setu.stage import normalise_run
from chakravyuh.setu.stage import resolve_in as setu_in
from chakravyuh.setu.stage import resolve_out as setu_out
from chakravyuh.shastra import estimate, features
from chakravyuh.shastra.stage import build_run, resolve_in, resolve_out, settings

REPO = Path(__file__).resolve().parent.parent
FIXTURE_CAPTURE = REPO / "data" / "fixtures" / "capture" / "capture.csv"

# Contract section 6, transcribed by hand rather than imported from the writer. A schema test
# that reads the same constant the code writes from asserts only that a module equals itself.
CONTRACT_ORIGIN_ESTIMATES: list[tuple[str, str]] = [
    ("txid", "String"),
    ("peer_ip", "String"),
    ("p_origin", "Float64"),
    ("rank", "Int32"),
    ("margin", "Float64"),
    ("features", "Struct"),
    ("estimator", "String"),
    ("abstain", "Boolean"),
    ("abstain_reason", "String"),
]
CONTRACT_FEATURES: list[tuple[str, str]] = [
    ("delta_first_us", "Int64"),
    ("rank_in_tx", "Int32"),
    ("n_announcements", "Int32"),
    ("n_observers_seen", "Int32"),
    ("peer_frac_rank_one", "Float64"),
    ("peer_n_txids", "Int32"),
    ("net_class", "String"),
    ("announce_spread_us", "Int64"),
]
CONTRACT_ESTIMATORS = {"first_spy", "weighted_first_seen", "bayes_peer_prior", "ensemble"}
CONTRACT_ABSTAIN_REASONS = {
    "tor_present",
    "single_observer",
    "margin_below_floor",
    "too_few_announcements",
}
CONTRACT_TYPOLOGIES = {
    "peel_chain",
    "structuring",
    "fan_out",
    "pass_through",
    "coinjoin_like",
    "rapid_hop",
}
CONTRACT_ENTITY_TYPES_BASIS = {
    "coinbase_origination",
    "payout_cadence",
    "long_dwell",
    "high_fanout",
    "port_diversity",
    "known_service_pattern",
}


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo root holding `data/` and nothing else, with the process moved into it.

    SHASTRA's path guard is relative to the working directory, like JAAL's, so running from
    inside `tmp_path` is what makes `resolve_in` and `resolve_out` do real work.
    """
    (tmp_path / "data" / "generated").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run(workspace: Path, name: str = "run") -> Path:
    """Seal, normalise and graph the committed fixture, then estimate over the result.

    The fixture rather than a generated capture: 197 rows, 26 transactions, 24 peers, every
    value chosen by hand, and it carries the documented bad row so the whole path is
    post-rejection like every real run's. No labels exist anywhere under `tmp_path`, so the
    learned estimator takes its label-free fallback path and the output is pure `first_spy`
    ordering behind both names — which is exactly the state Law 2 rule 6 demands work.
    """
    target = workspace / "data" / "capture.csv"
    target.write_bytes(FIXTURE_CAPTURE.read_bytes())
    seal(target, kavach_out(Path("data/generated") / name))
    run = workspace / "data" / "generated" / name
    normalise_run(setu_in(run / "sealed"), setu_out(run))
    build_graph(jaal_in(run / "normalised"), jaal_out(run))
    build_run(resolve_in(run / "normalised"), resolve_out(run))
    return run


def _signals(run: Path) -> pl.DataFrame:
    return pl.read_parquet(run / "signals" / "origin_estimates.parquet")


def _rows(**overrides: object) -> pl.DataFrame:
    """A six-announcement, three-transaction feature input with every value chosen by hand.

    Tx `aa`: two peers, `p1` seen first, `p2` one millisecond later — the ordering case.
    Tx `bb`: one peer, one announcement, one observer — the `single_observer` abstain.
    Tx `cc`: one peer announcing twice to two observers — the one case where
    `n_observers_seen` is two and `announce_spread_us` is non-zero.
    Every column `features.candidates` emits is present, because `_finalise` consumes the full
    frame and a missing one would be a KeyError here rather than a silent null in the wild.
    """
    base: dict[str, object] = {
        "row_id": [0, 1, 2, 3, 4, 5],
        "txid": ["aa", "aa", "bb", "cc", "cc", "aa"],
        "peer_ip": [
            "198.51.100.1",
            "198.51.100.2",
            "198.51.100.1",
            "198.51.100.3",
            "198.51.100.3",
            "198.51.100.1",
        ],
        "observer_ip": [
            "198.51.100.9",
            "198.51.100.9",
            "198.51.100.10",
            "198.51.100.9",
            "198.51.100.10",
            "198.51.100.10",
        ],
        "seen_us": [1_000, 1_001, 9_000, 5_000, 5_004, 1_002],
        "rank_in_tx": [1, 2, 1, 1, 1, 1],
        "delta_first_us": [0, 1, 0, 0, 4, 2],
        "net_class": [None, "hosting", None, None, None, None],
    }
    base.update(overrides)
    return pl.DataFrame(
        base,
        schema={
            "row_id": pl.Int64(),
            "txid": pl.String(),
            "peer_ip": pl.String(),
            "observer_ip": pl.String(),
            "seen_us": pl.Int64(),
            "rank_in_tx": pl.Int32(),
            "delta_first_us": pl.Int64(),
            "net_class": pl.String(),
        },
    )


def _peers() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "peer_ip": ["198.51.100.1", "198.51.100.2", "198.51.100.3"],
            "n_txids": [3, 1, 1],
            "frac_rank_one": [2 / 3, 0.0, 1.0],
        },
        schema={
            "peer_ip": pl.String(),
            "n_txids": pl.Int32(),
            "frac_rank_one": pl.Float64(),
        },
    )


def _transactions() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "txid": ["aa", "bb", "cc"],
            "input_addresses": [["1payer"], ["1other"], [None]],
        },
        schema={
            "txid": pl.String(),
            "input_addresses": pl.List(pl.String()),
        },
    )


def _edges() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "src": ["peer:198.51.100.1", "peer:198.51.100.3", "tx:aa"],
            "dst": ["asn:64496", "asn:64497", "peer:198.51.100.1"],
        },
        schema={"src": pl.String(), "dst": pl.String()},
    )


def _candidates() -> pl.DataFrame:
    return features.candidates(_rows(), _peers(), _transactions(), _edges())


def _first_spy(
    frame: pl.DataFrame, margin_floor: float = 0.0, min_announcements: int = 1
) -> pl.DataFrame:
    """`first_spy` with the floors dropped by default, so the ordering itself is what a test
    asserts rather than the thresholds it happened to set."""
    return estimate.first_spy(frame, margin_floor=margin_floor, min_announcements=min_announcements)


# --- behaviour: the honesty rules of section 6 ---------------------------------------------


def test_one_row_per_candidate_peer_not_per_announcement() -> None:
    """Six announcements, three transactions, four candidate pairs. Grouped to the peer."""
    frame = _candidates()
    assert frame.height == 4
    assert set(frame["txid"].to_list()) == {"aa", "bb", "cc"}
    assert frame.filter(pl.col("txid") == "aa").height == 2  # p1's two rows folded into one


def test_the_hand_built_features_are_computed_by_eye() -> None:
    """`aa`'s p1 row: earliest sighting 1000, two observers, spread two, payer_shared one.

    Two observers exist in the fixture, so a peer both of them heard leaves none blind and a
    peer one heard leaves one. `payer_shared` is one for both of `aa`'s peers, because
    `1payer`'s only transaction was announced by both.
    """
    aa_p1 = (
        _candidates()
        .filter((pl.col("txid") == "aa") & (pl.col("peer_ip") == "198.51.100.1"))
        .row(0, named=True)
    )
    assert aa_p1["seen_us"] == 1_000
    assert aa_p1["delta_first_us"] == 0
    assert aa_p1["n_announcements"] == 2
    assert aa_p1["n_observers_seen"] == 2
    assert aa_p1["n_observers_blind"] == 0
    assert aa_p1["announce_spread_us"] == 2
    assert aa_p1["payer_shared"] == 1
    assert aa_p1["peer_degree"] == 2
    assert aa_p1["n_candidates"] == 2

    cc = _candidates().filter(pl.col("txid") == "cc").row(0, named=True)
    assert cc["n_observers_seen"] == 2
    assert cc["n_observers_blind"] == 0
    assert cc["announce_spread_us"] == 4


def test_first_spy_ranks_by_first_seen_and_breaks_ties_on_row_id() -> None:
    """The whole of pass one: `delta_first_us` ascending, tie broken by capture position.

    `aa` gets p1 first (0 microseconds against p2's one), then p2. The probabilities are a
    stated geometric belief, so rank one is a half and rank two a quarter, and their
    difference is the margin.
    """
    ranked = _first_spy(_candidates())
    aa = ranked.filter(pl.col("txid") == "aa").sort("rank")
    assert aa["peer_ip"].to_list() == ["198.51.100.1", "198.51.100.2"]
    assert aa["p_origin"].to_list() == pytest.approx([0.5, 0.25])
    assert aa["margin"].to_list() == pytest.approx([0.25, 0.25])
    assert aa["abstain"].to_list() == [False, False]


def test_an_abstaining_transaction_has_no_rank_one_row() -> None:
    """Section 6: a refusal must never be readable as an accusation. Ranks start at two.

    `bb` was heard by one observer, so it abstains with `single_observer` no matter what the
    floors are; the assertion runs with the floors raised as well so the reason is provably
    the observer rule and not a margin that happened to fire.
    """
    for knobs in ((0.0, 1), (0.9, 9)):
        ranked = _first_spy(_candidates(), *knobs)
        bb = ranked.filter(pl.col("txid") == "bb")
        assert bb["abstain"].to_list() == [True]
        assert bb["abstain_reason"].to_list() == ["single_observer"]
        assert bb["rank"].to_list() == [2]
        assert ranked.filter((pl.col("txid") == "bb") & (pl.col("rank") == 1)).height == 0


def test_p_origin_is_capped_not_renormalised() -> None:
    """A transaction whose probabilities sum below one keeps the shortfall.

    "None of these peers is the originator" is a real state of the world and the sum is how
    the file says it. Every transaction here — abstaining and not — sums below one, and a
    renormalising implementation would write exactly 1.0 for each of them.
    """
    ranked = _first_spy(_candidates())
    sums = ranked.group_by("txid").agg(pl.col("p_origin").sum().alias("s"))
    assert sums.height == 3
    # aa: 0.5 + 0.25. bb and cc: one candidate each at 0.5, abstaining and not.
    assert sorted(sums["s"].to_list()) == pytest.approx([0.5, 0.5, 0.75])
    # Same root `type: ignore[operator]` as tests/test_chain.py:136: a Polars Series min/max
    # can be a date or a list, and only the float branch is real here.
    assert ranked["p_origin"].max() <= 1.0  # type: ignore[operator]


def test_a_single_candidate_carries_its_own_probability_as_the_margin() -> None:
    """No rank two exists, so zero would claim a certainty nobody assigned.

    `bb` abstains for the observer reason and `cc` does not, and both have one candidate.
    """
    ranked = _first_spy(_candidates())
    for txid, expected_p, expected_margin in (("bb", 0.5, 0.5), ("cc", 0.5, 0.5)):
        row = ranked.filter(pl.col("txid") == txid).row(0, named=True)
        assert row["p_origin"] == pytest.approx(expected_p)
        assert row["margin"] == pytest.approx(expected_margin)


def test_a_tor_candidate_abstains_whatever_the_margin() -> None:
    """`tor_present` outranks every other reason: an exit relay's timing says nothing about
    who paid, and the honest answer through Tor is that this capture cannot give one.

    The floor is zero and the transaction has a wide margin, so only the Tor rule can fire.
    """
    rows = _rows(net_class=["tor_exit", "hosting", None, None, None, None])
    ranked = estimate.first_spy(
        features.candidates(rows, _peers(), _transactions(), _edges()),
        margin_floor=0.0,
        min_announcements=1,
    )
    aa = ranked.filter(pl.col("txid") == "aa")
    assert aa["abstain"].to_list() == [True, True]
    assert aa["abstain_reason"].unique().to_list() == ["tor_present"]
    assert aa["rank"].min() == 2


def test_the_margin_floor_reads_the_separation_not_the_absolute_margin() -> None:
    """A floor of 0.9 rejects 0.5-vs-0.25 (separation one third) and accepts nothing here.

    The absolute margin is 0.25 in both cases; what differs is that a calibrated probability
    lives on the scale of the base rate, so the floor is applied to `(p1 - p2) / (p1 + p2)`,
    which is one when the leader stands alone and zero when the top two tie.
    """
    ranked = estimate.first_spy(_candidates(), margin_floor=0.9, min_announcements=1)
    abstains = ranked.filter(pl.col("abstain")).select("txid", "abstain_reason")
    assert set(abstains["abstain_reason"].to_list()) == {
        "single_observer",
        "margin_below_floor",
    }
    # `cc` has a clean 0.5 probability and no runner-up, so its separation is one and it acts.
    assert ranked.filter((pl.col("txid") == "cc") & pl.col("abstain")).height == 0


def test_min_announcements_counts_a_grouped_candidates_rows() -> None:
    """The floor counts a candidate's own rows after grouping, summed across the transaction:
    `aa` holds three (p1's two and p2's one), `cc` holds two, `bb` holds one. A floor of three
    spares only `aa`, and `bb` falls to the observer rule first, being the more specific
    finding. The margin floor is zero, so nothing else can fire."""
    ranked = estimate.first_spy(_candidates(), margin_floor=0.0, min_announcements=3)
    reasons = dict(
        zip(
            ranked.filter(pl.col("abstain")).get_column("txid"),
            ranked.filter(pl.col("abstain")).get_column("abstain_reason"),
            strict=False,
        )
    )
    assert reasons == {"bb": "single_observer", "cc": "too_few_announcements"}


def test_the_reason_priority_names_the_most_specific_rule() -> None:
    """`bb` trips three rules at once and reports the observer one, not the margin one."""
    ranked = estimate.first_spy(_candidates(), margin_floor=0.9, min_announcements=9)
    bb = ranked.filter(pl.col("txid") == "bb")
    assert bb["abstain_reason"].to_list() == ["single_observer"]


def test_ties_break_deterministically_between_two_interpreters() -> None:
    """Two peers at the same microsecond: min-ranking says both are rank 1, and the
    estimator must still write one order. `row_id` is the tie-break, so two processes agree."""
    rows = _rows()
    tied = rows.with_columns(pl.lit(1_000).alias("seen_us"), pl.lit(0).alias("delta_first_us"))
    ranked = estimate.first_spy(
        features.candidates(tied, _peers(), _transactions(), _edges()),
        margin_floor=0.0,
        min_announcements=1,
    )
    aa = ranked.filter(pl.col("txid") == "aa").sort("rank")
    assert aa["peer_ip"].to_list() == ["198.51.100.1", "198.51.100.2"]
    again = estimate.first_spy(
        features.candidates(tied, _peers(), _transactions(), _edges()),
        margin_floor=0.0,
        min_announcements=1,
    )
    assert (
        aa["peer_ip"].to_list()
        == again.filter(pl.col("txid") == "aa").sort("rank")["peer_ip"].to_list()
    )


def test_labels_absent_the_estimator_falls_back_and_says_so() -> None:
    """Law 2 rule 6: with the answer key moved away the stage completes, warns, and falls
    back to the strongest label-free rule rather than a partial model."""
    scored, fit = estimate.ensemble(
        _candidates(),
        None,
        boundary_us=None,
        margin_floor=0.0,
        min_announcements=1,
        seed=0,
    )
    assert fit.trained is False
    assert fit.reason == "answer_key_absent"
    assert set(scored["estimator"].unique().to_list()) == {"ensemble"}
    # The fallback is the payer-linkage-then-first-seen rule, so `aa`'s p1 (payer_shared one)
    # outranks p2 (zero) even though the two tie on nothing else.
    aa = scored.filter(pl.col("txid") == "aa").sort("rank")
    assert aa["peer_ip"].to_list() == ["198.51.100.1", "198.51.100.2"]


def test_no_training_row_sits_at_or_after_the_boundary() -> None:
    """The belt-and-braces mask: even a caller that handed in unfiltered labels gets the
    window re-applied over `seen_us`, half-open, so a row exactly on the boundary is out.

    The labels below claim `aa` (seen at 1000) and `cc` (seen at 5000) with a boundary of
    3000. Only `aa` survives to the join, and a `Fit` that had trained on `cc` would be the
    holdout leak the whole door exists to prevent.
    """
    labels = pl.DataFrame(
        {"txid": ["aa", "cc"], "origin_peer_ip": ["198.51.100.1", "198.51.100.3"]},
        schema={"txid": pl.String(), "origin_peer_ip": pl.String()},
    )
    _, fit = estimate.ensemble(
        _candidates(),
        labels,
        boundary_us=3_000,
        margin_floor=0.0,
        min_announcements=1,
        seed=0,
    )
    assert fit.n_train_rows < _candidates().height  # rows were removed by the mask
    assert fit.n_train_txids <= 1  # and only `aa`'s rows can be


def test_the_split_boundary_is_one_formula_in_one_place() -> None:
    """Rider 4: SHASTRA and the label door must derive the same boundary from the same
    capture, or the mask in `estimate.ensemble` and the filter in `eval.labels` disagree
    about what "training window" means and the intersection is quietly smaller than either.

    Both read the capture's observed span through `eval.split.boundary_us`, floored and
    half-open, so this is a property of that one function: the same span and fraction give
    the same microsecond, and the boundary always lands strictly inside the span.
    """
    from chakravyuh.eval.split import boundary_us

    assert boundary_us(1_000, 1_000, 0.7) == 1_001  # zero span: nothing to hold out
    assert boundary_us(0, 1_000_000, 0.7) == 700_000
    assert boundary_us(1_000, 5_001_000, 0.5) == 2_501_000  # floored, over the span
    # Floored, not rounded, so no world ever rounds its way to a half microsecond.
    assert boundary_us(0, 3, 0.7) == 2
    with pytest.raises(ValueError, match="strictly between"):
        boundary_us(0, 1_000, 1.0)


def test_a_zero_length_span_holds_out_nothing_and_says_so() -> None:
    """Every row shares one microsecond: the boundary lands past the last row and the whole
    capture is training window. An estimator that found an empty holdout must report it
    rather than silently widening its window."""
    from chakravyuh.eval.split import boundary_us, window_of

    boundary = boundary_us(7_000, 7_000, 0.7)
    assert window_of(7_000, boundary) == "train"
    assert boundary > 7_000


def test_the_sweep_door_cannot_invent_a_knob() -> None:
    """The whole sweep rests on `--set`: five worlds differ only by `observer_fraction`, and
    the S06 gate moves three more validation bands through the same door.

    The safety property is that a key must name a leaf that already exists, so a typo like
    `observer_fractoin` is a hard error rather than a sweep that silently ran the default
    world five times and called it a curve. Pre-authorised in rider 5, and tested here
    because this is the stage that depends on it.

    `load`'s `--txs`/`--entities` path arguments are omitted: this test is about the override
    door, not the world it builds, and a rejected override never reaches generation anyway.
    """
    from chakravyuh.mayajaal import config

    with pytest.raises(KeyError, match="has no such key"):
        config.load(REPO / "run_config.json", overrides={"network.observer_fractoin": "0.02"})
    with pytest.raises(KeyError, match="has no network.observer_fractoin"):
        config.load(REPO / "run_config.json", overrides={"network.observer_fractoin.x": "0.02"})
    with pytest.raises(KeyError, match="has no such key"):
        config.load(REPO / "run_config.json", overrides={"nodots": "1"})
    # The refused path override, and the type coercion the leaf's own value dictates.
    with pytest.raises(ValueError, match="names a file"):
        config.load(REPO / "run_config.json", overrides={"network.latency_matrix": "elsewhere"})
    with pytest.raises(ValueError, match="expected an integer"):
        config.load(REPO / "run_config.json", overrides={"network.n_observers": "sixteen"})
    # And the working case, read back out of the effective copy a run would carry.
    cfg = config.load(REPO / "run_config.json", overrides={"network.observer_fraction": "0.02"})
    assert cfg.network.observer_fraction == pytest.approx(0.02)


# --- behaviour: the vendor path -------------------------------------------------------------

sys.path.insert(0, str(REPO / "scripts"))
import make_vendor_lists  # noqa: E402

from chakravyuh.mayajaal.regions import load as load_regions  # noqa: E402

_CFG = json.loads((REPO / "run_config.json").read_text(encoding="utf-8"))
_REGIONS = load_regions(REPO / "regions.yaml")


def _vendor() -> Path:
    """A synthetic vendor tree from `scripts/make_vendor_lists.py`, the generator this repo
    ships for exactly this purpose.

    The script derives the tree from `run_config.json` and `regions.yaml` alone — the world's
    own address pools, never a run, never a truth key — so building it here exercises the
    same files an operator would fetch deliberately.

    Written under the *session* temp directory, one level above the workspace: an un-vendored
    SETU run resolves `vendor/` relative to the process working directory, which is the
    workspace, so a tree built there would leak into every later plain run in the same
    workspace and the contrast this file asserts would vanish. Never the repository's own
    `vendor/` either: populating that directory turns `make verify-s04` red, because that
    gate asserts SETU's absent-vendor warnings.
    """
    out = Path(tempfile.gettempdir()) / f"chakravyuh-vendor-{os.getpid()}" / "vendor"
    make_vendor_lists.build(out, _CFG, _REGIONS)
    return out


def test_a_vendored_run_resolves_net_class_and_abstains_on_tor(
    workspace: Path,
) -> None:
    """Open problem 9's payoff: with a vendor tree, `tor_present` fires on a real run.

    The fixture capture announces six of its rows from `192.0.2.0/24`, the config's own
    `tor_exit` pool, so those peers enrich to `tor_exit` and every transaction they touched
    abstains with `tor_present` under both estimators. The un-vendored run abstains on
    nothing of the kind, which is the comparison that proves the rule fired for the reason
    the vendor tree says and not by accident.
    """
    from chakravyuh.setu.enrich import Enricher

    vendor = _vendor()
    enricher = Enricher(root=vendor)
    assert enricher.available and enricher.has_tor
    # The pool's own class, from the world's configuration alone.
    assert enricher.lookup("192.0.2.11").net_class == "tor_exit"

    target = workspace / "data" / "capture.csv"
    target.write_bytes(FIXTURE_CAPTURE.read_bytes())
    seal(target, kavach_out(Path("data/generated") / "vendored"))
    run = workspace / "data" / "generated" / "vendored"
    normalise_run(setu_in(run / "sealed"), setu_out(run), vendor)
    build_graph(jaal_in(run / "normalised"), jaal_out(run))
    build_run(resolve_in(run / "normalised"), resolve_out(run))

    signals = _signals(run)
    tor_peers = {ip for ip in signals["peer_ip"].unique().to_list() if ip.startswith("192.0.2.")}
    assert tor_peers, "the fixture's Tor-pool peers did not survive the pipeline"
    touched = signals.filter(pl.col("peer_ip").is_in(list(tor_peers)))
    assert touched.filter(pl.col("abstain_reason") == "tor_present").height > 0
    # And it is the vendor that did it: the un-vendored run has no net_class at all.
    plain = _signals(_run(workspace, "plain"))
    assert plain.filter(pl.col("abstain_reason") == "tor_present").height == 0
    assert plain["features"].struct.field("net_class").null_count() == plain.height


def test_the_vendor_tree_classifies_every_pool_the_world_defines() -> None:
    """Each pool lands on the class it was configured to be, and the region partition agrees
    both ways: an address drawn from a region's slice reads back as that region, and its
    country is that region's country.

    This is the `region_of` inverse documented in `mayajaal/entities.py`, checked here
    because the vendor rows are slices — a row whose boundaries were off by one address
    would silently shift a peer into the wrong ASN and the wrong net class.
    """
    import random

    from chakravyuh.mayajaal import entities
    from chakravyuh.setu.enrich import Enricher

    enricher = Enricher(root=_vendor())

    pools = {
        "ipv4": "residential",
        "cgnat": "mobile",
        "ipv6": "residential",
        "observer": "residential",
        "tor_exit": "tor_exit",
        "vpn": "vpn_suspect",
    }
    rng = random.Random(11)
    n_regions = len(_REGIONS)
    for pool, expected in pools.items():
        cidr = _CFG["world"]["ip_pools"].get(pool) or _CFG["network"]["ip_pools"][pool]
        checked = 0
        for region in range(n_regions):
            for _ in range(3):
                ip = entities.pool_ip(rng, cidr, region, n_regions)
                facts = enricher.lookup(ip)
                assert facts.net_class == expected, f"{pool} gave {facts.net_class} for {ip}"
                assert facts.geo_country == _REGIONS.countries[region]
                assert entities.region_of(ip, (cidr,), n_regions) == region
                checked += 1
        assert checked == n_regions * 3


# --- stage ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("origin_estimates.parquet", CONTRACT_ORIGIN_ESTIMATES),
        ("typology_hits.parquet", None),
        ("entity_types.parquet", None),
    ],
)
def test_every_output_matches_contract_section_six(
    workspace: Path, name: str, expected: object
) -> None:
    """Column names, order and dtypes, against the document rather than against the writer."""
    signals = _run(workspace) / "signals"
    schema_read = pl.read_parquet_schema(signals / name)
    found = [(key, str(value)) for key, value in schema_read.items()]
    if expected is None:
        assert found == _transcribe(name)
        return
    # `features` is a struct whose interior is checked field by field in its own test below,
    # so only its kind is compared here.
    assert [(key, value if key != "features" else "Struct") for key, value in found] == expected


def _transcribe(name: str) -> list[tuple[str, str]]:
    """The deferred files' schemas, transcribed from contract section 6 by hand.

    Empty by design: section 6 states no nullability for either table, so a row of
    placeholders would be a row an auditor must reject, and the honest shape of "this stage
    does not do typologies yet" is the exact schema with zero rows.
    """
    if name == "typology_hits.parquet":
        return [
            ("hit_id", "String"),
            ("typology", "String"),
            ("subject_id", "String"),
            ("txids", "List(String)"),
            ("strength", "Float64"),
            ("params", "Struct({'threshold': Float64, 'window_us': Int64})"),
        ]
    return [
        ("subject_id", "String"),
        ("predicted_type", "String"),
        ("confidence", "Float64"),
        ("basis", "List(String)"),
        ("exempt_from_scoring", "Boolean"),
    ]


def test_the_features_struct_holds_the_contract_eight_first(workspace: Path) -> None:
    """Section 6 names eight fields "at minimum", and the struct carries them in the
    contract's order so a reader diffing the two lines up without searching."""
    frame = _signals(_run(workspace))
    dtype = frame.schema["features"]
    assert isinstance(dtype, pl.Struct)
    fields = [(field.name, str(field.dtype)) for field in dtype.fields]
    for (name, got), (want_name, want_dtype) in zip(fields, CONTRACT_FEATURES, strict=False):
        assert name == want_name
        assert got == want_dtype
    assert len(fields) >= len(CONTRACT_FEATURES)


def test_the_vocabulary_is_closed_and_both_estimators_are_written(workspace: Path) -> None:
    """Every `estimator` and `abstain_reason` is one contract section 6 permits, and the two
    built estimators are both present — the gate has to compare pass one against pass two
    on the same run."""
    frame = _signals(_run(workspace))
    assert set(frame["estimator"].unique().to_list()) <= CONTRACT_ESTIMATORS
    assert {"first_spy", "ensemble"} <= set(frame["estimator"].unique().to_list())
    reasons = set(frame["abstain_reason"].drop_nulls().to_list())
    assert reasons <= CONTRACT_ABSTAIN_REASONS
    assert reasons, "the fixture run abstained on nothing, so the vocabulary check was vacuous"


def test_ranking_and_sum_invariants_hold_over_a_real_run(workspace: Path) -> None:
    """The four invariants a schema check cannot see, over the real fixture pipeline:

    no abstaining transaction carries a rank 1 row; ranks are contiguous with no gaps or
    shares and start at `abstain + 1`; `p_origin` sums to at most one per transaction; and
    the margin is constant within a transaction, because it is a property of the top two.
    """
    frame = _signals(_run(workspace))
    assert frame.filter(pl.col("abstain") & (pl.col("rank") == 1)).height == 0

    grouped = frame.group_by("estimator", "txid").agg(
        pl.col("rank").min().alias("lo"),
        pl.col("rank").max().alias("hi"),
        pl.col("rank").n_unique().alias("distinct"),
        pl.len().alias("n"),
        pl.col("abstain").first().alias("abstained"),
        pl.col("p_origin").sum().alias("s"),
        pl.col("margin").n_unique().alias("margins"),
    )
    # A transaction abstains as a whole or not at all, and its lowest rank is 2 exactly then.
    assert grouped.filter(pl.col("lo") != pl.col("abstained").cast(pl.Int32) + 1).height == 0
    assert grouped.filter((pl.col("hi") - pl.col("lo") + 1) != pl.col("n")).height == 0
    assert grouped.filter(pl.col("distinct") != pl.col("n")).height == 0
    assert grouped.filter(pl.col("s") > 1.0 + 1e-9).height == 0
    assert grouped.filter(pl.col("margins") != 1).height == 0
    # Anti-vacuity: the fixture must actually abstain somewhere, or none of this proved much.
    assert frame.filter(pl.col("abstain")).height > 0


def test_the_stage_accounts_for_every_announcement_row(workspace: Path) -> None:
    """Section 10's grain: announcement rows in, candidate pairs out, the difference
    dropped by the grouping, and both estimators' rows accounted for in `outputs`."""
    run = _run(workspace)
    meta = json.loads((run / "signals" / "_meta.json").read_text(encoding="utf-8"))
    announcements = pl.read_parquet(run / "normalised" / "announcements.parquet")
    frame = _signals(run)

    counts = meta["counts"]
    assert counts["in"] == announcements.height
    assert counts["out"] * 2 == frame.height
    assert counts["in"] == counts["out"] + counts["dropped"]

    by_name = {entry["path"]: entry["rows"] for entry in meta["outputs"]}
    assert by_name["signals/origin_estimates.parquet"] == frame.height
    assert by_name["signals/typology_hits.parquet"] == 0
    assert by_name["signals/entity_types.parquet"] == 0


def test_no_candidate_peer_is_missing_or_invented(workspace: Path) -> None:
    """The estimator writes exactly the announcing peers `normalised/` holds, one row each."""
    run = _run(workspace)
    announcements = pl.read_parquet(run / "normalised" / "announcements.parquet")
    expected = set(
        zip(announcements["txid"].to_list(), announcements["peer_ip"].to_list(), strict=False)
    )
    frame = _signals(run)
    for estimator in frame["estimator"].unique().to_list():
        found = set(
            zip(
                frame.filter(pl.col("estimator") == estimator)["txid"].to_list(),
                frame.filter(pl.col("estimator") == estimator)["peer_ip"].to_list(),
                strict=False,
            )
        )
        assert found == expected, estimator


def test_meta_records_the_eval_knobs_and_the_fallback(workspace: Path) -> None:
    """A hand-built run directory carries no `config.effective.json`, so the stage's
    defaults apply, the meta says they did, and the label-free fallback is named."""
    run = _run(workspace)
    meta = json.loads((run / "signals" / "_meta.json").read_text(encoding="utf-8"))
    config = settings(run)
    assert config.from_config is False

    assert meta["params"]["margin_floor"] == config.margin_floor
    assert meta["params"]["min_announcements"] == config.min_announcements
    assert meta["params"]["train_fraction"] == config.train_fraction
    assert "ensemble_is_heuristic_answer_key_absent" in meta["warnings"]
    assert meta["params"]["model"] is None
    assert meta["optional_deps"]["geolite2"] is False


def test_two_builds_of_one_normalised_agree(workspace: Path) -> None:
    """Determinism inside one process. The gate repeats it across two, which is the test."""
    run = _run(workspace)
    first = (run / "signals" / "origin_estimates.parquet").read_bytes()
    build_run(resolve_in(run / "normalised"), resolve_out(run))
    assert (run / "signals" / "origin_estimates.parquet").read_bytes() == first


def test_the_input_path_guard_refuses_a_sibling_tree(workspace: Path) -> None:
    """`--in` is allowlisted to `data/`, so an operator cannot point SHASTRA at the answer
    key even by wanting to: the key is a sibling tree, not under `data/`."""
    from chakravyuh.shastra.stage import InputPathError

    with pytest.raises(InputPathError, match="outside"):
        resolve_in(workspace / "elsewhere" / "normalised")


# --- quarantine -----------------------------------------------------------------------------


def test_shastra_builds_with_the_answer_key_absent(workspace: Path) -> None:
    """Law 2 rule 6, run rather than asserted.

    A subprocess whose working directory holds only `data/`. The answer key is not merely
    unread here, it does not exist on any path the process could construct, so a stage that
    had quietly grown a dependency on it cannot complete. Run twice: once plain, and once
    with --score, which must degrade to a warning rather than die.
    """
    _run(workspace, "isolated")
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "from chakravyuh.shastra.stage import build_run, resolve_in, resolve_out;"
        "build_run(resolve_in(Path('data/generated/isolated/normalised')),"
        " resolve_out(Path('data/generated/isolated')))"
    )
    finished = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-2000:]

    meta = json.loads(
        (workspace / "data" / "generated" / "isolated" / "signals" / "_meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert meta["counts"]["in"] == meta["counts"]["out"] + meta["counts"]["dropped"]
    assert meta["counts"]["out"] > 0

    scored = subprocess.run(
        [
            sys.executable,
            "-m",
            "chakravyuh.shastra",
            "--in",
            "data/generated/isolated/normalised",
            "--out",
            "data/generated/isolated",
            "--score",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert scored.returncode == 0, scored.stderr[-2000:]
    assert "nothing was scored" in scored.stderr
    # And nothing was created outside data/, because there was nothing to write a measurement to.
    assert sorted(one.name for one in workspace.iterdir()) == ["data"]


def test_no_signals_artifact_names_the_quarantine(workspace: Path) -> None:
    """Law 2 rule 4: no observable file may contain either quarantined path, as a name or a
    value. `signals/` is the stage most tempted — it is the one that scores — and this is
    the file the source-tree grep in `tests/test_contracts.py` cannot see into.

    The literals are reconstructed rather than written, so this file does not itself hold
    the two strings the source-tree grep looks for.
    """
    forbidden = ("ground" + "_truth", "measure" + "ments")
    signals = _run(workspace) / "signals"

    checked = 0
    for path in sorted(signals.rglob("*")):
        if not path.is_file():
            continue
        checked += 1
        if path.suffix == ".json":
            text = path.read_text(encoding="utf-8")
            assert not any(one in text for one in forbidden), f"{path.name} names the quarantine"
            continue
        frame = pl.read_parquet(path)
        assert not set(frame.columns) & set(forbidden)
        for column in frame.columns:
            if frame.schema[column] != pl.String():
                continue
            values = frame[column].drop_nulls()
            for one in forbidden:
                assert (
                    values.str.contains(one, literal=True).sum() == 0
                ), f"{path.name}.{column} carries {one!r}"
    assert checked >= 4, "the walk found fewer files than one signals/ writes, so it proved nothing"

    # The source side of the same rule: no SHASTRA module may name either path.
    for module in sorted((REPO / "src" / "chakravyuh" / "shastra").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        assert not any(one in text for one in forbidden), f"{module.name} names the quarantine"
