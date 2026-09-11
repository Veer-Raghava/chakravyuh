"""S02 gate: the network layer is only useful if the capture is neither a lookup nor a lottery.

Three things are checked here that nothing else can check. That the population is derived rather
than loaded, which is what lets S02 extend S01 in one process without reading its output back.
That the relay timing produces independent per-peer delays rather than a sorted cascade, because a
cascade makes `first announcement seen` the answer and the whole benchmark a lookup. And that the
capture carries no column that exists only in the answer key.

The run is generated once per module by the real CLI, at the path the layout says it belongs at,
and both trees are removed afterwards. Reading `ground_truth/` here is deliberate and allowed: a
test may, nothing under `src/` outside `chakravyuh.eval` may, and
`test_contracts.py` greps the source tree to keep it that way.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

import polars as pl
import pytest

from chakravyuh.eval import validate
from chakravyuh.mayajaal import adversary, chain, config, export, ledger, network, writers
from chakravyuh.mayajaal.__main__ import main
from chakravyuh.mayajaal.writers import CAMPAIGN_SCHEMA, ENTITY_SCHEMA, ORIGIN_SCHEMA

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "run_config.json"
# Enough illicit budget for at least one campaign to run: campaigns are bounded by
# `illicit_tx_share`, so a smaller run generates none and the campaign assertions below would
# pass by being vacuous.
TXS = 4000
ENTITIES = 800
RUN_ID = "_test-network"


@pytest.fixture(scope="module")
def cfg() -> config.Config:
    return config.load(CONFIG, n_txs=TXS, n_entities=ENTITIES)


def _wipe(roots: writers.Roots) -> None:
    for path in (roots.observable, roots.truth, roots.measurements):
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def roots() -> Iterator[writers.Roots]:
    place = writers.run_roots(REPO / "data" / "generated" / RUN_ID)
    _wipe(place)
    try:
        argv = ["--config", str(CONFIG), "--out", str(place.observable)]
        argv += ["--txs", str(TXS), "--entities", str(ENTITIES)]
        assert main(argv) == 0
        yield place
    finally:
        _wipe(place)


@pytest.fixture(scope="module")
def capture(roots: writers.Roots) -> pl.DataFrame:
    shards = sorted((roots.observable / export.CSV_DIR).glob("part-*.csv"))
    assert shards, "the exporter wrote no CSV shard"
    return pl.concat([pl.read_csv(shard, infer_schema_length=0) for shard in shards])


@pytest.fixture(scope="module")
def origins(roots: writers.Roots) -> pl.DataFrame:
    return pl.read_parquet(roots.truth / "origins.parquet")


@pytest.fixture(scope="module")
def txs(roots: writers.Roots) -> pl.DataFrame:
    return pl.read_parquet(roots.observable / "chain" / "transactions.parquet")


@pytest.fixture(scope="module")
def derived(cfg: config.Config) -> chain.Run:
    """The first two layers replayed in this process, in the order `__main__` runs them.

    Two tests need a run that was built here rather than read back: the one that asserts the
    population is derived from `(config, seed)` alone, and the one that rebuilds the peer graph at
    a different frontier. Sharing it costs one generation instead of two.
    """
    plotter = adversary.Adversary(cfg=cfg, rng=random.Random(cfg.seed + 1))
    run = chain.generate(cfg, random.Random(cfg.seed), plotter.plan)
    plotter.apply_typologies(run.population)
    return run


@pytest.fixture(scope="module")
def carried(cfg: config.Config, derived: chain.Run) -> network.Network:
    """The peer layer over `derived`, at the seed `__main__` gives it.

    In memory rather than read back from the run directory, because the two rules about what a
    node may announce are stated in microseconds against `Tx.time_us`, and the exported capture
    carries a formatted timestamp instead. Checking them here compares the numbers the generator
    actually worked with.
    """
    return network.build(cfg, derived, random.Random(cfg.seed + 2))


def _first_seen_rate(net: network.Network) -> float:
    """How often the earliest recorded announcement of a transaction came from its true origin.

    Computed from the in-memory network so the frontier test needs no run directory. The capture is
    ascending by time, so the first row seen for a transaction is its earliest announcement.

    The denominator is every broadcast transaction, not every transaction an observer recorded,
    which is the denominator the validator's leakage scores use. A transaction that reached no
    observer is one no rule can ever get right, and leaving it out would flatter every rate here.
    """
    origins = {one.tx_index: one for one in net.origins}
    earliest: dict[int, int] = {}
    capture = net.capture
    for index in range(len(capture)):
        earliest.setdefault(capture.tx_index[index], capture.src_node[index])
    hits = sum(1 for tx, node in earliest.items() if node == origins[tx].node)
    return hits / max(len(origins), 1)


def test_the_population_is_derived_from_the_config_and_seed_alone(
    cfg: config.Config, derived: chain.Run, roots: writers.Roots
) -> None:
    """The brief's requirement, and the reason S02 never opens S01's output.

    The expected frame is built by hand here rather than by calling the writer's own helper: if
    both sides came from one function, this would prove the population is deterministic and prove
    nothing about what was written. Rebuilding it column by column is what makes a mismatch in the
    mapping fail too.

    Only the first two layers are replayed, in `derived`. The network layer is deliberately left
    out, so this also asserts that building the peer graph does not reach back into the population.
    """
    people = derived.population.entities

    expected = pl.DataFrame(
        {
            "entity_id": [one.entity_id for one in people],
            "entity_type": [one.entity_type for one in people],
            "is_illicit": [one.is_illicit for one in people],
            "typologies": [list(one.typologies) for one in people],
            "addresses": [list(one.addresses) for one in people],
            "ips": [list(one.ips) for one in people],
            "behind_cgnat": [one.behind_cgnat for one in people],
        },
        schema=ENTITY_SCHEMA,
    )
    written = pl.read_parquet(roots.truth / "entities.parquet")
    assert expected.height == cfg.world.n_entities
    assert written.equals(expected)


def test_every_encoding_carries_section_ones_columns_in_section_ones_order(
    roots: writers.Roots, capture: pl.DataFrame
) -> None:
    """Three writers, one column order, and the order is the contract's.

    `export.rows` builds each row by inserting keys in `export.COLUMNS` order and all three
    encodings iterate that dict, so a reordering there silently reorders the CSV. Asserting on the
    artifacts rather than on the function is what catches it.
    """
    assert capture.columns == list(export.COLUMNS)

    shard = next(iter(sorted((roots.observable / export.JSON_DIR).glob("part-*.jsonl"))))
    with shard.open(encoding="utf-8") as handle:
        assert tuple(json.loads(handle.readline())) == export.COLUMNS

    sample = roots.observable / export.XML_DIR / "sample.xml"
    first = ElementTree.parse(sample).getroot().find("row")
    assert first is not None
    assert tuple(child.tag for child in first) == export.COLUMNS


def test_the_capture_is_not_a_sorted_cascade(cfg: config.Config, capture: pl.DataFrame) -> None:
    """The requirement the whole layer stands on, measured on the artifact.

    A node that forwarded immediately would deliver every transaction to the observers in one
    fixed order, decided by the topology and never by the draw. Two consequences are checked: the
    order in which the observers hear a transaction is almost never repeated, and no observer is
    the one that hears first often enough to be worth guessing.
    """
    arrivals = capture.group_by("txid", maintain_order=True).agg(
        pl.col("observer_id").str.join(">").alias("order")
    )
    assert arrivals["order"].n_unique() > arrivals.height * 0.9

    first = capture.unique(subset="txid", keep="first", maintain_order=True)["observer_id"]
    assert first.n_unique() == cfg.network.n_observers
    busiest = first.value_counts()["count"].max()
    assert isinstance(busiest, int)
    assert busiest / first.len() < 0.25


def test_only_what_reached_an_observer_was_recorded(
    cfg: config.Config, capture: pl.DataFrame, origins: pl.DataFrame
) -> None:
    """Requirement 4. An observer is a listening node, not a tap on the whole network.

    `observed_by_n` is the answer key's count of who saw a transaction, and it has to agree with
    the capture row for row. The interesting half is the floor: if every observer saw everything,
    `observer_fraction` would be doing nothing and reach would carry no signal.
    """
    ids = {network.observer_id(index) for index in range(cfg.network.n_observers)}
    assert set(capture["observer_id"].unique()) <= ids
    assert capture["dst_ip"].n_unique() == capture["observer_id"].n_unique()

    seen = capture.group_by("txid").agg(pl.col("observer_id").n_unique().alias("seen"))
    joined = origins.join(seen, on="txid", how="left").with_columns(pl.col("seen").fill_null(0))
    assert joined.filter(pl.col("observed_by_n") != pl.col("seen")).height == 0
    assert joined.filter(pl.col("observed_by_n") < cfg.network.n_observers).height > 0


def test_evasion_moves_the_broadcast_behind_a_tor_exit_or_a_vpn(
    cfg: config.Config, origins: pl.DataFrame
) -> None:
    """Requirement 6, and the reason `true_origin_ip` is the entry node rather than the sender.

    A Tor broadcast that recorded the sender's own address as truth would ask a later stage to
    identify an address that never appeared on the wire. So the answer key names the exit, and the
    flags are how evaluation separates the scoreable transactions from the deliberately hidden
    ones. The pool prefixes come from the config, which is what makes the check independent of how
    the pools were carved up.
    """
    assert origins.filter(pl.col("used_tor") & pl.col("used_vpn")).height == 0
    for column, share, pool in (
        ("used_tor", cfg.network.tor_share, cfg.network.tor_pool),
        ("used_vpn", cfg.network.vpn_share, cfg.network.vpn_pool),
    ):
        measured = origins[column].mean()
        assert isinstance(measured, float)
        assert abs(measured - share) <= share * 0.4
        prefix = pool.split("/")[0].rsplit(".", 1)[0] + "."
        hidden = origins.filter(pl.col(column))
        assert hidden["true_origin_ip"].str.starts_with(prefix).all()


def test_the_answer_key_names_exactly_one_originator_per_transaction(
    roots: writers.Roots, origins: pl.DataFrame, txs: pl.DataFrame
) -> None:
    """Requirement 7. One row per announced transaction on the chain, no more and no fewer.

    Coinbase is excluded on both sides. A coinbase is minted by the miner inside its own block
    and never relayed as a loose transaction, so it has no originating peer to name and an
    answer key that invented one would be asking a later stage to attribute a broadcast that
    never happened.
    """
    spends = txs.filter(~pl.col("is_coinbase"))
    assert list(origins.schema.items()) == list(ORIGIN_SCHEMA.items())
    assert origins.height == spends.height
    assert origins["txid"].n_unique() == origins.height
    assert spends.join(origins, on="txid", how="anti").height == 0
    assert txs.filter(pl.col("is_coinbase")).join(origins, on="txid", how="semi").height == 0
    assert (origins["broadcast_us"] > 0).all()


def test_a_node_announces_only_what_it_could_have_announced(
    derived: chain.Run, carried: network.Network
) -> None:
    """The two rules about what may appear on the wire, both checked against the chain itself.

    A coinbase is minted by the miner inside its own block and is never relayed as a loose
    transaction, so a capture holding one is holding a row that could not exist. And a peer that
    already has the confirming block relays the block, not the transaction inside it, so an
    arrival at or after the block's own timestamp is equally impossible. Both would hand S03
    arrival times drawn from events no observer could have recorded.
    """
    txs = derived.txs
    capture = carried.capture
    announced = {capture.tx_index[index] for index in range(len(capture))}
    assert announced, "the capture is empty, so these rules would hold vacuously"
    assert not [index for index in announced if txs[index].is_coinbase]
    assert not [one for one in carried.origins if txs[one.tx_index].is_coinbase]
    assert not [
        index
        for index in range(len(capture))
        if capture.time_us[index] >= txs[capture.tx_index[index]].time_us
    ]


def test_no_address_belongs_to_two_owners(roots: writers.Roots, txs: pl.DataFrame) -> None:
    """Requirement 2's answer key only means something if an address names one entity.

    Two mechanisms could break this and they fail in different places, so both are checked. An
    address minted twice merges two entities in the S04 clustering answer key. A block reward
    paid to an address the endowment already seeded merges a mining pool with a wallet, which is
    the same defect arriving through the coinbase instead of through the address factory.
    """
    entities = pl.read_parquet(roots.truth / "entities.parquet")
    owned = entities.select("entity_id", "addresses").explode("addresses")
    assert owned["addresses"].n_unique() == owned.height

    endowment = pl.read_parquet(roots.observable / "chain" / "endowment.parquet")
    rewards = set(txs.filter(pl.col("is_coinbase"))["output_addresses"].explode())
    assert rewards, "no block paid a reward, so the overlap check would hold vacuously"
    assert not rewards & set(endowment["address"])


def test_a_txid_is_the_hash_of_the_transaction_it_names(txs: pl.DataFrame) -> None:
    """Computed by hand, because the truncation policy depends on the shape of this string.

    Section 11 renders a txid as its first eight and last four characters. A counter formatted
    into a fixed-width field gives every txid in a run the same last four, so the rendered form
    would carry four characters of nothing and two different transactions would read alike on
    screen. Deriving the id from the transaction's own inputs and outputs spreads all sixty-four.
    """
    expected = hashlib.sha256(b"chakravyuh-tx\x00\x00abc:0\x00bc1qxyz:p2wpkh:500").hexdigest()
    assert ledger.txid_for([("abc", 0)], [("bc1qxyz", "p2wpkh", 500)]) == expected

    assert txs["txid"].n_unique() == txs.height
    # Birthday collisions across four hex characters account for a few per cent at this run
    # size. Anything near one distinct tail, which is what a counter produces, is nowhere near.
    assert txs["txid"].str.slice(-4).n_unique() > txs.height * 0.9


def test_campaigns_are_agents_whose_moves_are_on_the_chain(
    roots: writers.Roots, txs: pl.DataFrame
) -> None:
    """Requirement 5, both halves.

    A campaign row is only meaningful if the transactions it claims exist, and a typology on an
    entity is only meaningful if a campaign put it there. So the txids are checked against the
    chain, and the labels are checked against the campaigns in both directions: every campaign
    entity carries its typology, and no entity carries a typology no campaign gave it.
    """
    campaigns = pl.read_parquet(roots.truth / "campaigns.parquet")
    entities = pl.read_parquet(roots.truth / "entities.parquet")
    assert list(campaigns.schema.items()) == list(CAMPAIGN_SCHEMA.items())
    assert campaigns.height > 0, "no campaign ran, so nothing here is being tested"

    on_chain = set(txs["txid"].to_list())
    labels: dict[str, set[str]] = {}
    for row in campaigns.iter_rows(named=True):
        assert row["txids"], "a campaign with no transaction is not a campaign"
        assert set(row["txids"]) <= on_chain
        assert row["start_us"] <= row["end_us"]
        assert row["total_sats"] > 0
        for who in row["entity_ids"]:
            labels.setdefault(who, set()).add(row["typology"])

    for row in entities.iter_rows(named=True):
        assert set(row["typologies"]) == labels.get(row["entity_id"], set())


def test_doubling_the_flood_frontier_barely_moves_the_first_seen_rate(
    cfg: config.Config, derived: chain.Run
) -> None:
    """The claim `network._flood`'s docstring makes, which is what licenses the frontier bound.

    Only the earliest arrival at an observer is ever recorded, so the nodes an expansion bound
    drops are ones whose announcements would have been discarded as duplicates anyway. If that is
    true, doubling the bound cannot move the measured leakage; if it is false, the bound is
    silently shaping the benchmark and has to go.
    """
    rates = []
    for frontier in (cfg.network.flood_frontier, cfg.network.flood_frontier * 2):
        wider = replace(cfg, network=replace(cfg.network, flood_frontier=frontier))
        rates.append(_first_seen_rate(network.build(wider, derived, random.Random(cfg.seed + 2))))
    assert all(rate > 0.0 for rate in rates)
    assert abs(rates[0] - rates[1]) <= 0.05


def test_no_capture_encoding_names_a_ground_truth_column(roots: writers.Roots) -> None:
    """The quarantine gate for this stage, on the three encodings and the chain files.

    Names, because a leaked label arrives as a column and a column arrives with a name. The list is
    imported from the validator rather than copied, so the two cannot drift apart: that module is
    the one place allowed to know what an answer-key column is called.
    """
    forbidden = set(validate.TRUTH_COLUMNS)
    checked = 0
    for path in sorted(roots.observable.rglob("*")):
        if path.suffix == ".csv":
            with path.open(encoding="utf-8") as handle:
                names = set(handle.readline().strip().split(","))
        elif path.suffix == ".jsonl":
            with path.open(encoding="utf-8") as handle:
                names = set(json.loads(handle.readline()))
        elif path.suffix == ".parquet":
            names = set(pl.read_parquet_schema(path))
        elif path.suffix == ".xml":
            row = ElementTree.parse(path).getroot().find("row")
            names = {child.tag for child in row} if row is not None else set()
        else:
            continue
        checked += 1
        assert not names & forbidden, f"{path.name} names {sorted(names & forbidden)}"
    assert checked >= 6, "the walk found fewer files than one run writes, so it proved nothing"
