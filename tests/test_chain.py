"""S01 gate: the chain layer is only correct if its accounting is.

Every assertion here is either an identity that must hold on every transaction, or a shape the
generator was asked to produce. The accounting checks read the written Parquet rather than the
in-memory run, because what the next stage consumes is the file.
"""

from __future__ import annotations

import json
import random
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest

from chakravyuh.mayajaal import chain, config, writers
from chakravyuh.mayajaal.__main__ import main
from chakravyuh.mayajaal.writers import TX_SCHEMA

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import compare_runs  # noqa: E402

CONFIG = REPO / "run_config.json"
TXS = 1200
ENTITIES = 300
# Repo-relative and fixed, not a pytest tmp directory: ground truth is anchored to the
# repository root, so a run written from a tmp directory is refused now, correctly.
RUN_ID = "_test-chain"

# Section 2 column names that must never appear in an observable artifact. `addresses` and
# `txid` are section 2 names too, but section 1 requires them on the capture rows, so this
# list holds only the names that identify or label an entity.
TRUTH_ONLY = (
    "entity_id",
    "entity_type",
    "is_illicit",
    "typologies",
    "ips",
    "behind_cgnat",
    "campaign_id",
    "entity_ids",
    "change_index",
    "heuristic_violation",
    "true_origin_ip",
    "true_origin_entity_id",
)


@pytest.fixture(scope="module")
def cfg() -> config.Config:
    return config.load(CONFIG, n_txs=TXS, n_entities=ENTITIES)


def _wipe(roots: writers.Roots) -> None:
    for path in (roots.observable, roots.truth, roots.measurements):
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="module")
def roots() -> Iterator[writers.Roots]:
    """A real run, written by the real CLI, at the path the layout says it belongs at.

    Both trees are gitignored and both are removed before and after, so a test cannot leave a
    label file behind. The directory is wiped first rather than trusted: a leftover from a
    crashed run would otherwise be refused by the clobber guard.
    """
    place = writers.run_roots(REPO / "data" / "generated" / RUN_ID)
    _wipe(place)
    try:
        assert (
            main(
                [
                    "--config",
                    str(CONFIG),
                    "--out",
                    str(place.observable),
                    "--txs",
                    str(TXS),
                    "--entities",
                    str(ENTITIES),
                ]
            )
            == 0
        )
        yield place
    finally:
        _wipe(place)


@pytest.fixture(scope="module")
def run_dir(roots: writers.Roots) -> Path:
    return roots.observable


@pytest.fixture(scope="module")
def txs(run_dir: Path) -> pl.DataFrame:
    return pl.read_parquet(run_dir / "chain" / "transactions.parquet")


def test_the_observable_schema_is_exactly_what_the_contract_names(txs: pl.DataFrame) -> None:
    assert list(txs.schema.items()) == list(TX_SCHEMA.items())
    for name in TRUTH_ONLY:
        assert name not in txs.columns


def test_no_entity_identifier_reaches_the_observable_file(txs: pl.DataFrame) -> None:
    """Entity ids look like `ent-000123`. None of them may appear in a chain artifact."""
    for column in ("txid", "input_addresses", "output_addresses", "script_types"):
        flat = txs[column].explode() if txs.schema[column] == pl.List(pl.String) else txs[column]
        assert not flat.drop_nulls().str.contains("ent-").any()


def test_inputs_equal_outputs_plus_fee_on_every_transaction(txs: pl.DataFrame) -> None:
    """The identity the whole ledger rests on. Exact, in integers, with no tolerance."""
    spends = txs.filter(~pl.col("is_coinbase")).with_columns(
        total_in=pl.col("input_amounts").list.sum(),
        total_out=pl.col("output_amounts").list.sum(),
    )
    assert spends.height > 0
    assert spends.filter(pl.col("total_in") != pl.col("total_out") + pl.col("fee_sats")).is_empty()


def test_no_negative_fee_and_fees_are_not_all_zero(txs: pl.DataFrame) -> None:
    spends = txs.filter(~pl.col("is_coinbase"))
    assert spends["fee_sats"].min() >= 0  # type: ignore[operator]
    # A generator that forgot to charge a fee would satisfy the identity above and every
    # conservation check, and would still be wrong, so the median has to be a real fee.
    assert spends["fee_sats"].median() > 0  # type: ignore[operator]


def test_coinbase_pays_exactly_the_subsidy_plus_the_fees_of_its_block(
    run_dir: Path, txs: pl.DataFrame, cfg: config.Config
) -> None:
    blocks = pl.read_parquet(run_dir / "chain" / "blocks.parquet")
    assert blocks.height == cfg.n_blocks
    minted = (
        txs.filter(pl.col("is_coinbase"))
        .select("block_height", paid=pl.col("output_amounts").list.sum())
        .join(blocks, left_on="block_height", right_on="height", how="inner")
    )
    assert minted.height == cfg.n_blocks
    assert minted.filter(pl.col("paid") != pl.col("subsidy_sats") + pl.col("fees_sats")).is_empty()
    assert (blocks["subsidy_sats"] == cfg.chain.coinbase_subsidy_sats).all()


def test_every_input_spends_an_output_that_exists_and_is_unspent(
    run_dir: Path, txs: pl.DataFrame, cfg: config.Config
) -> None:
    """Replay the UTXO set from the files, in file order, and try to break it.

    This is the double-spend, spend-from-the-future and immature-coinbase check in one pass.
    Nothing is quoted in a failure message: an outpoint is an identifier.
    """
    unspent: dict[tuple[str, int], tuple[int, bool]] = {}
    for seed in pl.read_parquet(run_dir / "chain" / "endowment.parquet").iter_rows(named=True):
        unspent[(seed["txid"], seed["vout"])] = (seed["height"], False)
    assert unspent, "the ledger has to start with something to spend"

    maturity = cfg.chain.coinbase_maturity_blocks
    for row in txs.iter_rows(named=True):
        height = row["block_height"]
        for txid, vout in zip(row["input_txids"], row["input_vouts"], strict=True):
            spent = unspent.pop((txid, vout), None)
            assert spent is not None, "an input spends an output that is missing or already spent"
            born, from_coinbase = spent
            assert born <= height, "an input spends an output created at a later height"
            assert not from_coinbase or height - born >= maturity, "immature coinbase spent"
        for vout in range(len(row["output_amounts"])):
            unspent[(row["txid"], vout)] = (height, row["is_coinbase"])


def test_the_value_distribution_is_heavy_tailed(txs: pl.DataFrame, cfg: config.Config) -> None:
    """Quantile ratios, not a normality test.

    Non-normality is not heavy-tailedness: a uniform distribution is not normal either, and a
    uniform value distribution would make every amount-based signal downstream meaningless. The
    floors come from run_config.json so tuning the generator moves the bar in one place.
    """
    values = txs.filter(~pl.col("is_coinbase"))["output_amounts"].explode()
    p50, p99, p999 = (values.quantile(q) for q in (0.5, 0.99, 0.999))
    assert p50 and p99 and p999
    assert p99 / p50 >= cfg.validation.value_p99_over_p50_min
    assert p999 / p50 >= cfg.validation.value_p999_over_p50_min
    mean, median = values.mean(), values.median()
    assert isinstance(mean, float) and isinstance(median, float)
    assert mean > median


def test_the_multi_input_rate_is_near_the_configured_rate(
    txs: pl.DataFrame, cfg: config.Config
) -> None:
    spends = txs.filter(~pl.col("is_coinbase"))
    measured = spends.filter(pl.col("input_txids").list.len() > 1).height / spends.height
    target = cfg.chain.multi_input_rate
    assert abs(measured - target) <= target * cfg.validation.multi_input_rate_tolerance


@pytest.fixture(scope="module")
def truth(roots: writers.Roots) -> pl.DataFrame:
    return pl.read_parquet(roots.truth / "chain_txs.parquet")


def test_change_is_never_at_a_fixed_index(truth: pl.DataFrame) -> None:
    """A change output at output 0 every time would make the change heuristic free."""
    located = truth.filter(pl.col("change_index") >= 0)
    assert located.height > truth.height // 2
    assert located["change_index"].n_unique() >= 3


def test_the_truth_file_answers_the_ownership_question_for_every_spend(
    truth: pl.DataFrame, txs: pl.DataFrame
) -> None:
    spends = txs.filter(~pl.col("is_coinbase"))
    assert truth.height == spends.height
    assert truth["txid"].n_unique() == truth.height
    joined = spends.select("txid", n_inputs=pl.col("input_txids").list.len()).join(
        truth.select("txid", n_owners=pl.col("input_entity_ids").list.len()),
        on="txid",
        how="inner",
    )
    assert joined.height == spends.height
    assert joined.filter(pl.col("n_inputs") != pl.col("n_owners")).is_empty()
    # Both heuristics the generator is meant to break have to actually break somewhere, or the
    # answer key is a column of one value and S05 has nothing to measure.
    for heuristic in ("common_input_ownership", "change_address_reuse"):
        assert truth.filter(pl.col("heuristic_violation").str.contains(heuristic)).height > 0
    assert truth.filter(pl.col("heuristic_violation") == "").height > 0


def test_the_same_seed_gives_the_same_run_in_one_process(cfg: config.Config) -> None:
    """Two generations in this process must agree exactly, in memory and on disk.

    This does not make `make verify-s01`'s two-run byte comparison redundant, and the reverse is
    also true. Both generations here share one interpreter and therefore one PYTHONHASHSEED, so
    output that depends on set or dict iteration order would agree here and differ between
    processes. Only a second process catches that. What this test catches instead is a hidden
    source of state inside one process: a module-level cache, a counter that is not reset, an
    `lru_cache` keyed on something mutable.

    The written halves are compared with the same helper the Makefile uses, on purpose. If the
    masking there ever grew to cover a field that should have been compared, this test would
    stop being able to see it too, and the drift would be visible in one place instead of two.
    """
    first = chain.generate(cfg, random.Random(cfg.seed))
    second = chain.generate(cfg, random.Random(cfg.seed))
    assert first.txs == second.txs
    assert first.seeds == second.seeds
    assert first.blocks == second.blocks
    assert first.multi_input_rate == second.multi_input_rate

    here = writers.run_roots(REPO / "data" / "generated" / "_test-same-a")
    there = writers.run_roots(REPO / "data" / "generated" / "_test-same-b")
    _wipe(here)
    _wipe(there)
    try:
        writers.write_run(first, cfg, here.observable, started_at_us=1, finished_at_us=2)
        writers.write_run(second, cfg, there.observable, started_at_us=3, finished_at_us=4)
        assert compare_runs.differences(here.observable, there.observable) == []
        assert compare_runs.differences(here.truth, there.truth) == []
    finally:
        _wipe(here)
        _wipe(there)


def test_the_masked_manifest_still_carries_every_hash_and_count(run_dir: Path) -> None:
    """The masking helper must drop three fields and nothing else.

    A helper that stripped the hashes would make the byte gate pass on two different runs, and
    the gate would still look green, so the floor is asserted here rather than assumed.
    """
    payload = (run_dir / "chain" / "_meta.json").read_bytes()
    masked = compare_runs.canonical_meta(payload)
    assert compare_runs.MASKED == ("run_id", "started_at_us", "finished_at_us")
    for field in compare_runs.MASKED:
        assert f'"{field}"' not in masked
    for kept in ("sha256", "counts", "drop_reasons", "config_sha256", "params", "outputs"):
        assert f'"{kept}"' in masked
    original = json.loads(payload)
    assert json.loads(masked) == {
        key: value for key, value in original.items() if key not in compare_runs.MASKED
    }


def test_the_run_accounts_for_every_attempt(
    run_dir: Path, txs: pl.DataFrame, cfg: config.Config
) -> None:
    """Section 10's one equality: nothing may vanish without a reason and a number."""
    meta = json.loads((run_dir / "chain" / "_meta.json").read_text(encoding="utf-8"))
    counts = meta["counts"]
    assert counts["in"] == counts["out"] + counts["dropped"]
    assert counts["in"] == TXS
    assert sum(counts["drop_reasons"].values()) == counts["dropped"]
    assert all(len(entry["sha256"]) == 64 for entry in meta["outputs"])
    rows = {Path(entry["path"]).name: entry["rows"] for entry in meta["outputs"]}
    assert rows["transactions.parquet"] == txs.height
    assert meta["seed"] == cfg.seed
    assert len(meta["config_sha256"]) == 64
    # The manifest is a claim about this run's own directory, so every path in it has to be
    # relative to that directory. An absolute path is a path on one machine, and S09 replays a
    # packet on another one.
    for entry in meta["outputs"] + meta["inputs"]:
        assert not Path(entry["path"]).is_absolute()
        assert (run_dir / entry["path"]).is_file()
    assert [entry["path"] for entry in meta["inputs"]] == ["config.effective.json"]


def test_the_observable_manifest_lists_only_observable_files(run_dir: Path) -> None:
    """The answer key is not named here, and neither is the campaign file that lives with it."""
    meta = json.loads((run_dir / "chain" / "_meta.json").read_text(encoding="utf-8"))
    listed = {entry["path"] for entry in meta["outputs"]}
    assert listed == {
        "chain/transactions.parquet",
        "chain/endowment.parquet",
        "chain/blocks.parquet",
    }


def test_the_truth_tree_carries_its_own_manifest(roots: writers.Roots) -> None:
    """Section 10 is satisfied on both sides, which is what lets the observable side stay quiet."""
    meta = json.loads((roots.truth / "_meta.json").read_text(encoding="utf-8"))
    listed = {entry["path"]: entry for entry in meta["outputs"]}
    assert set(listed) == {"entities.parquet", "campaigns.parquet", "chain_txs.parquet"}
    assert listed["campaigns.parquet"]["rows"] == 0
    assert all(len(entry["sha256"]) == 64 for entry in listed.values())
    assert meta["run_id"] == RUN_ID
    observable = json.loads((roots.observable / "chain" / "_meta.json").read_text(encoding="utf-8"))
    # The same config produced both trees, and the shared hash is what the clobber guard
    # compares. Timestamps are absent here on purpose, so the answer key is reproducible.
    assert meta["config_sha256"] == observable["config_sha256"]
    assert "started_at_us" not in meta


def test_run_roots_derives_three_siblings_from_one_name() -> None:
    place = writers.run_roots(REPO / "data" / "generated" / "example")
    assert place.run_id == "example"
    assert place.observable == REPO / "data" / "generated" / "example"
    assert place.truth == REPO / "ground_truth" / "example"
    assert place.measurements == REPO / "measurements" / "example"
    # Relative and absolute must agree, since the CLI accepts either.
    if Path.cwd() == REPO:
        assert writers.run_roots(Path("data/generated/example")) == place


@pytest.mark.parametrize("out", [".", "..", "data/generated/sub dir", "data/generated/run$1"])
def test_a_run_name_that_is_not_a_plain_name_is_refused(out: str) -> None:
    """`--out .` used to give an empty run name and put the answer key in the shared root."""
    with pytest.raises(ValueError, match="plain run name"):
        writers.run_roots(Path(out))


def test_an_out_that_escapes_the_repository_is_refused(tmp_path: Path) -> None:
    """Truth is derived from the name, so an escaping --out separates a run from its answer key."""
    with pytest.raises(ValueError, match="must be inside"):
        writers.run_roots(tmp_path / "elsewhere")


def test_a_directory_with_no_manifest_is_never_written_over(cfg: config.Config) -> None:
    """The crashed-midway case: bytes on disk that nothing claims."""
    place = writers.run_roots(REPO / "data" / "generated" / "_test-orphan")
    _wipe(place)
    place.truth.mkdir(parents=True)
    try:
        run = chain.generate(cfg, random.Random(cfg.seed))
        with pytest.raises(FileExistsError, match="half-written"):
            writers.write_run(run, cfg, place.observable, started_at_us=1, finished_at_us=2)
        assert not (place.observable / "chain").exists()
    finally:
        _wipe(place)


def test_a_different_config_may_not_clobber_an_existing_run() -> None:
    """Same name, different parameters. Refused by content, and the message says how to proceed."""
    place = writers.run_roots(REPO / "data" / "generated" / "_test-clobber")
    _wipe(place)
    # Small, but not so small that the mining_pool share rounds to zero entities.
    args = ["--config", str(CONFIG), "--out", str(place.observable), "--entities", "200"]
    try:
        assert main([*args, "--txs", "120"]) == 0
        # Same config again is the same run regenerated, which is deterministic and therefore safe.
        assert main([*args, "--txs", "120"]) == 0
        with pytest.raises(FileExistsError) as raised:
            main([*args, "--txs", "121"])
        message = str(raised.value)
        assert str(place.observable) in message and str(place.truth) in message
        assert message.count("rm -rf") == 2
    finally:
        _wipe(place)


def test_no_observable_artifact_names_the_quarantine(roots: writers.Roots) -> None:
    """No observable byte may point at the answer key, in any run under data/generated/.

    A manifest that lists the truth files is a machine-readable index of where the labels are.
    Scanning the whole tree rather than only this run's directory means a stage that starts
    leaking into a run built by `make verify-s01` is caught by this same test.
    """
    generated = REPO / "data" / "generated"
    checked = 0
    for path in sorted(generated.rglob("*")):
        if not path.is_file():
            continue
        checked += 1
        payload = path.read_bytes()
        for token in (b"ground_truth", b"measurements"):
            assert token not in payload, f"{path.relative_to(generated)} names the quarantine"
    assert checked >= 5, f"only {checked} observable files scanned, so this proved nothing"
    assert (roots.observable / "chain" / "_meta.json").is_file()
