"""The only module that writes. The only module allowed to name `ground_truth/`.

`tests/test_contracts.py` greps every file under `src/` for that path and exempts exactly one:
this file. The exemption is paid for by a second assertion, that this module never opens a file
for reading in any form — no dataframe loader, no text or byte load, no directory listing, and
no file handle that was not opened with an explicit write mode. The door opens outwards only,
which is what makes a one-file exemption safe rather than a loophole.

That has two visible consequences. Section 10 wants a sha256 of every output, and the obvious
way to get one is to write the file and hash it back. This module cannot do that, so every
frame is serialised into a buffer, the buffer is hashed, and the buffer is written. The hash
covers the bytes that went to disk because they are the same bytes. The second consequence is
that the guard against overwriting a different run lives in `preflight.py`: deciding that
question means looking at a manifest already on disk, which this module is not allowed to do.

Which columns are observable and which are truth is decided here, in the frame builders, and
nowhere else. `chain/` deliberately reuses the column names section 1 gives the capture rows,
so S02 fans a transaction out into announcements without renaming anything.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from chakravyuh import __version__
from chakravyuh.mayajaal import export, preflight
from chakravyuh.mayajaal.adversary import Campaign
from chakravyuh.mayajaal.chain import Run
from chakravyuh.mayajaal.config import Config
from chakravyuh.mayajaal.network import Network


def _repo_root() -> Path:
    """The directory holding `pyproject.toml`, found by walking up from this file.

    Deliberately not `Path.cwd()`. The working directory is wherever the operator happened to
    stand, so anchoring to it lets a run launched from a subdirectory create a second
    quarantine tree there, outside `.gitignore`, while every test still passes.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError(f"no pyproject.toml above {__file__}: cannot locate the repository root")


REPO_ROOT = _repo_root()
TRUTH_ROOT = REPO_ROOT / "ground_truth"
MEASUREMENTS_ROOT = REPO_ROOT / "measurements"

# A run id becomes a directory name in three trees, so it has to be a plain name in all
# three. An allowlist, not a blocklist of separators: a separator is the one character
# `Path.name` can never contain, so a blocklist could never fire, while `..` and the empty
# name both slip through unless something spells out what a name may be made of.
RUN_ID = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True, slots=True)
class Written:
    path: str
    sha256: str
    rows: int


@dataclass(frozen=True, slots=True)
class Roots:
    """The three directories one run id owns. Siblings, never nested."""

    run_id: str
    observable: Path
    truth: Path
    measurements: Path


def run_roots(out: Path) -> Roots:
    """Validate `--out` and derive the two siblings it implies. Raises before anything is written.

    `measurements/` is derived here and written by nobody at S01. It is returned anyway so the
    layout has one definition rather than a fresh one in each later stage that needs it.
    """
    if out.name in ("", ".", "..") or not RUN_ID.match(out.name):
        raise ValueError(
            f"--out must end in a plain run name matching {RUN_ID.pattern}, got {str(out)!r}. "
            "That name becomes a directory in three trees, and an empty name, '.' or '..' "
            "would put the answer key flat in the shared root that the per-run layout exists "
            "to prevent."
        )
    observable = (out if out.is_absolute() else Path.cwd() / out).resolve()
    if not observable.is_relative_to(REPO_ROOT):
        raise ValueError(
            f"--out must be inside {REPO_ROOT}, got {observable}. Ground truth is derived from "
            "the run name rather than passed in, so an --out that escapes the repository would "
            "separate a run from its answer key and land that answer key outside the one "
            "quarantined, gitignored tree that keeps labels out of commits."
        )
    return Roots(out.name, observable, TRUTH_ROOT / out.name, MEASUREMENTS_ROOT / out.name)


def _put(payload: bytes, base: Path, rel: str, rows: int) -> Written:
    """Write `payload` and record its path relative to its own tree, never absolutely.

    An absolute path in a manifest is a path on one machine, and S09 replays a packet on a
    different one.
    """
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return Written(rel, hashlib.sha256(payload).hexdigest(), rows)


def _emit(frame: pl.DataFrame, base: Path, rel: str, schema: dict[str, pl.DataType]) -> Written:
    """Serialise, hash the buffer, write the buffer. The schema is checked, never inferred."""
    if list(frame.schema.items()) != list(schema.items()):
        raise TypeError(f"{rel}: schema drifted from the contract: {frame.schema}")
    buffer = io.BytesIO()
    frame.write_parquet(buffer)
    return _put(buffer.getvalue(), base, rel, frame.height)


def _emit_text(text: str, base: Path, rel: str) -> Written:
    return _put(text.encode("utf-8"), base, rel, 0)


SATS = pl.Int64()
COUNT = pl.Int32()
TEXT = pl.String()
TEXTS = pl.List(pl.String)

# Section 1's own names, so S02 has nothing to rename. `is_coinbase` is the one addition, and
# it is not a section 2 name: a coinbase is a public fact about a transaction, not a label.
TX_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "block_height": pl.Int64(),
    "block_time_us": pl.Int64(),
    "is_coinbase": pl.Boolean(),
    "input_txids": TEXTS,
    "input_vouts": pl.List(pl.Int32),
    "input_addresses": TEXTS,
    "input_amounts": pl.List(pl.Int64),
    "output_addresses": TEXTS,
    "output_amounts": pl.List(pl.Int64),
    "script_types": TEXTS,
    "fee_sats": SATS,
    "fee_rate_sat_vb": COUNT,
    "vsize": COUNT,
}

SEED_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "vout": COUNT,
    "address": TEXT,
    "script_type": TEXT,
    "sats": SATS,
    "height": pl.Int64(),
}

BLOCK_SCHEMA: dict[str, pl.DataType] = {
    "height": pl.Int64(),
    "time_us": pl.Int64(),
    "n_txs": COUNT,
    "coinbase_txid": TEXT,
    "subsidy_sats": SATS,
    "fees_sats": SATS,
}

# Section 2, exactly. Neither table gains a column here, and neither loses one.
ENTITY_SCHEMA: dict[str, pl.DataType] = {
    "entity_id": TEXT,
    "entity_type": TEXT,
    "is_illicit": pl.Boolean(),
    "typologies": TEXTS,
    "addresses": TEXTS,
    "ips": TEXTS,
    "behind_cgnat": pl.Boolean(),
}

CAMPAIGN_SCHEMA: dict[str, pl.DataType] = {
    "campaign_id": TEXT,
    "typology": TEXT,
    "entity_ids": TEXTS,
    "txids": TEXTS,
    "start_us": pl.Int64(),
    "end_us": pl.Int64(),
    "total_sats": SATS,
}

ORIGIN_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "true_origin_ip": TEXT,
    "true_origin_entity_id": TEXT,
    "broadcast_us": pl.Int64(),
    "used_tor": pl.Boolean(),
    "used_vpn": pl.Boolean(),
    "observed_by_n": COUNT,
}

# Per-transaction truth, which section 2 has no table for. Recorded in docs/DECISIONS.md by
# name, and quarantined with the rest: `change_index` is the answer key for the change
# heuristic and `input_entity_ids` is the answer key for common-input-ownership.
CHAIN_TX_SCHEMA: dict[str, pl.DataType] = {
    "txid": TEXT,
    "entity_id": TEXT,
    "input_entity_ids": TEXTS,
    "change_index": COUNT,
    "heuristic_violation": TEXT,
    "block_height": pl.Int64(),
}


def _transactions(run: Run) -> pl.DataFrame:
    txs = run.txs
    return pl.DataFrame(
        {
            "txid": [tx.txid for tx in txs],
            "block_height": [tx.height for tx in txs],
            "block_time_us": [tx.time_us for tx in txs],
            "is_coinbase": [tx.is_coinbase for tx in txs],
            "input_txids": [[point[0] for point in tx.inputs] for tx in txs],
            "input_vouts": [[point[1] for point in tx.inputs] for tx in txs],
            "input_addresses": [list(tx.input_addresses) for tx in txs],
            "input_amounts": [list(tx.input_sats) for tx in txs],
            "output_addresses": [list(tx.output_addresses) for tx in txs],
            "output_amounts": [list(tx.output_sats) for tx in txs],
            "script_types": [list(tx.output_kinds) for tx in txs],
            "fee_sats": [tx.fee_sats for tx in txs],
            "fee_rate_sat_vb": [tx.fee_rate for tx in txs],
            "vsize": [tx.vsize_vb for tx in txs],
        },
        schema=TX_SCHEMA,
    )


def _seeds(run: Run) -> pl.DataFrame:
    seeds = run.seeds
    return pl.DataFrame(
        {
            "txid": [seed.txid for seed in seeds],
            "vout": [seed.vout for seed in seeds],
            "address": [seed.address for seed in seeds],
            "script_type": [seed.script_type for seed in seeds],
            "sats": [seed.sats for seed in seeds],
            "height": [seed.height for seed in seeds],
        },
        schema=SEED_SCHEMA,
    )


def _blocks(run: Run) -> pl.DataFrame:
    blocks = run.blocks
    return pl.DataFrame(
        {
            "height": [block.height for block in blocks],
            "time_us": [block.time_us for block in blocks],
            "n_txs": [block.n_txs for block in blocks],
            "coinbase_txid": [block.coinbase_txid for block in blocks],
            "subsidy_sats": [block.subsidy_sats for block in blocks],
            "fees_sats": [block.fees_sats for block in blocks],
        },
        schema=BLOCK_SCHEMA,
    )


def _entities(run: Run) -> pl.DataFrame:
    people = run.population.entities
    return pl.DataFrame(
        {
            "entity_id": [one.entity_id for one in people],
            "entity_type": [one.entity_type for one in people],
            "is_illicit": [one.is_illicit for one in people],
            # Set by the adversary layer from the campaigns that actually ran, and empty for
            # every entity no campaign routed value through. A label with no transaction behind
            # it would be an unscoreable claim, so nothing here derives one from the type.
            "typologies": [list(one.typologies) for one in people],
            "addresses": [list(one.addresses) for one in people],
            "ips": [list(one.ips) for one in people],
            "behind_cgnat": [one.behind_cgnat for one in people],
        },
        schema=ENTITY_SCHEMA,
    )


def _campaigns(run: Run, records: Sequence[Campaign]) -> pl.DataFrame:
    """One row per campaign that built something, in campaign id order.

    `entity_ids` are the entities value actually passed through, not the ones a campaign was
    planned around, which is why they come from the record rather than from the plan.
    """
    people = run.population.entities
    return pl.DataFrame(
        {
            "campaign_id": [one.campaign_id for one in records],
            "typology": [one.typology() for one in records],
            "entity_ids": [[people[i].entity_id for i in one.participants] for one in records],
            "txids": [list(one.txids) for one in records],
            "start_us": [one.start_us for one in records],
            "end_us": [one.end_us for one in records],
            "total_sats": [one.total_sats for one in records],
        },
        schema=CAMPAIGN_SCHEMA,
    )


def _origins(run: Run, net: Network) -> pl.DataFrame:
    """Exactly one row per announced transaction: who really sent it, and from which node.

    `true_origin_ip` is the node the transaction entered the network from, so for a Tor or VPN
    broadcast it is the exit rather than the sender's own address. That is the IP an attribution
    method could conceivably recover; naming an address the transaction never crossed the
    network from would make the metric unwinnable.

    Coinbase transactions are absent, because they are never gossiped and so have no
    originating peer to name. The transaction each row answers for is read back through
    `Origin.tx_index` rather than by reapplying `network.build`'s own coinbase filter here: two
    copies of one filter agree only until one of them changes, and the failure that produces is
    silent, pairing every row's txid with a different transaction's answer. The validator still
    asserts the resulting txid set matches the chain, because this table is the answer key and
    an answer key is worth checking twice.
    """
    people = run.population.entities
    nodes = net.topology.nodes
    origins = net.origins
    return pl.DataFrame(
        {
            "txid": [run.txs[one.tx_index].txid for one in origins],
            "true_origin_ip": [nodes[one.node].ip for one in origins],
            "true_origin_entity_id": [people[one.entity].entity_id for one in origins],
            "broadcast_us": [one.broadcast_us for one in origins],
            "used_tor": [one.used_tor for one in origins],
            "used_vpn": [one.used_vpn for one in origins],
            "observed_by_n": [one.observed_by_n for one in origins],
        },
        schema=ORIGIN_SCHEMA,
    )


def _chain_txs(run: Run) -> pl.DataFrame:
    people = run.population.entities
    txs = [tx for tx in run.txs if not tx.is_coinbase]
    return pl.DataFrame(
        {
            "txid": [tx.txid for tx in txs],
            "entity_id": [people[tx.sender].entity_id for tx in txs],
            "input_entity_ids": [[people[i].entity_id for i in tx.input_owners] for tx in txs],
            "change_index": [tx.change_index for tx in txs],
            "heuristic_violation": ["|".join(sorted(tx.violations)) for tx in txs],
            "block_height": [tx.height for tx in txs],
        },
        schema=CHAIN_TX_SCHEMA,
    )


def _entry(written: Written) -> dict[str, object]:
    return {"path": written.path, "sha256": written.sha256, "rows": written.rows}


def _write_capture(
    cfg: Config,
    run: Run,
    net: Network,
    roots: Roots,
    *,
    consumed: Written,
    started_at_us: int,
    finished_at_us: int,
    config_sha256: str,
) -> None:
    """Write every export directory and give each one its own section 10 manifest.

    A part is written as it is produced rather than after all of them are, so the memory cost of
    the export is one shard of text and not the whole capture in three encodings at once.

    `counts.in` is the same number in all three manifests, the announcements the exporter was
    handed. `counts.out` is what each directory actually carries, so the XML sample's difference
    is a real drop with a reason, and `in == out + dropped` holds per directory rather than only
    in total.
    """
    offered = export.offered(net)
    grouped: dict[str, list[Written]] = {}
    for part in export.parts(cfg, run, net):
        grouped.setdefault(part.directory, []).append(
            _put(part.text.encode("utf-8"), roots.observable, part.rel, part.rows)
        )

    for directory, files in grouped.items():
        produced = sum(one.rows for one in files)
        missing = offered - produced
        _emit_text(
            json.dumps(
                {
                    "stage": "mayajaal",
                    "run_id": roots.run_id,
                    "started_at_us": started_at_us,
                    "finished_at_us": finished_at_us,
                    "code_version": __version__,
                    "seed": cfg.seed,
                    "config_sha256": config_sha256,
                    "params": {
                        "n_transactions": len(run.txs),
                        "n_nodes": len(net.topology.nodes),
                        "n_observers": cfg.network.n_observers,
                        "shard_rows": cfg.export.shard_rows,
                    },
                    "inputs": [_entry(consumed)],
                    "outputs": [_entry(one) for one in files],
                    "counts": {
                        "in": offered,
                        "out": produced,
                        "dropped": missing,
                        "drop_reasons": {"not sampled": missing} if missing else {},
                    },
                    "warnings": [],
                    "optional_deps": {"geolite2": False, "kuzu": False, "gpu": False},
                },
                indent=2,
            )
            + "\n",
            roots.observable,
            f"{directory}/_meta.json",
        )


def write_run(
    run: Run,
    cfg: Config,
    out: Path,
    *,
    started_at_us: int,
    finished_at_us: int,
    net: Network | None = None,
    campaigns: Sequence[Campaign] = (),
) -> Path:
    """Write every artifact of one run and return the path of its observable manifest.

    Three sibling trees, one run id: `<out>/` for what an observer could have seen,
    `ground_truth/<run>/` for the answer key, `measurements/<run>/` for scores. Sibling rather
    than nested, because a later stage handed the run directory as its input root can walk
    into a nested answer key with a plain glob. The truth path is derived from the run name and
    is not a parameter: an argument for where truth lands is an argument that could point
    somewhere unquarantined.

    Each tree carries its own manifest, and so does each export directory, because each is a
    separate file set a later stage could be handed on its own. The observable ones name only
    observable files, so the observable tree holds no machine-readable pointer to the answer key.

    `net` is optional so a chain-only run is still writable: the contract test for the chain
    layer builds no network, and a network it does not need is not a network it should have to
    construct. Without one there are no announcements to export and no entry point to record.
    """
    roots = run_roots(out)

    # Hashed before anything is written, because the clobber guard compares this hash against
    # what a previous run recorded. The run name is deliberately not part of it: the hash then
    # identifies a set of parameters rather than a directory, and `config.effective.json` stays
    # byte-identical between two runs of the same config under different names.
    config_json = json.dumps(cfg.effective, indent=2, sort_keys=True) + "\n"
    config_sha256 = hashlib.sha256(config_json.encode("utf-8")).hexdigest()
    preflight.refuse_to_clobber(
        (
            preflight.Slot(roots.observable, roots.observable / "chain" / "_meta.json"),
            preflight.Slot(roots.truth, roots.truth / "_meta.json"),
        ),
        config_sha256=config_sha256,
    )

    consumed = _emit_text(config_json, roots.observable, "config.effective.json")
    observable = [
        _emit(_transactions(run), roots.observable, "chain/transactions.parquet", TX_SCHEMA),
        _emit(_seeds(run), roots.observable, "chain/endowment.parquet", SEED_SCHEMA),
        _emit(_blocks(run), roots.observable, "chain/blocks.parquet", BLOCK_SCHEMA),
    ]
    quarantined = [
        _emit(_entities(run), roots.truth, "entities.parquet", ENTITY_SCHEMA),
        _emit(_campaigns(run, campaigns), roots.truth, "campaigns.parquet", CAMPAIGN_SCHEMA),
        _emit(_chain_txs(run), roots.truth, "chain_txs.parquet", CHAIN_TX_SCHEMA),
    ]
    if net is not None:
        quarantined.append(_emit(_origins(run, net), roots.truth, "origins.parquet", ORIGIN_SCHEMA))
        _write_capture(
            cfg,
            run,
            net,
            roots,
            consumed=consumed,
            started_at_us=started_at_us,
            finished_at_us=finished_at_us,
            config_sha256=config_sha256,
        )

    dropped = sum(run.counters.drops.values())
    meta = {
        "stage": "mayajaal",
        "run_id": roots.run_id,
        "started_at_us": started_at_us,
        "finished_at_us": finished_at_us,
        "code_version": __version__,
        "seed": cfg.seed,
        "config_sha256": config_sha256,
        "params": {
            "n_transactions": cfg.n_txs,
            "n_blocks": cfg.n_blocks,
            "n_entities": cfg.world.n_entities,
            "multi_input_rate_target": cfg.chain.multi_input_rate,
            "multi_input_rate_measured": run.multi_input_rate,
        },
        # The parameters that produced this run, including the CLI overrides, recorded as the
        # stage's input because that is what it consumed. The template at the repository root
        # is not hashed here: hashing it would mean opening it, and this module does not.
        "inputs": [_entry(consumed)],
        "outputs": [_entry(w) for w in observable],
        "counts": {
            "in": run.counters.attempts,
            "out": run.counters.built,
            "dropped": dropped,
            "drop_reasons": dict(run.counters.drops),
        },
        "warnings": [
            f"{count} of {run.counters.attempts} payment attempts dropped: {reason}"
            for reason, count in sorted(run.counters.drops.items())
        ],
        "optional_deps": {"geolite2": False, "kuzu": False, "gpu": False},
    }
    _emit_text(json.dumps(meta, indent=2) + "\n", roots.observable, "chain/_meta.json")

    # No timestamps in the truth manifest. Section 10 asks for wall-clock start and finish on a
    # stage's output, and this tree is nobody's input except `chakravyuh.eval`. Leaving them out
    # keeps the answer key reproducible field for field, not merely row for row.
    _emit_text(
        json.dumps(
            {
                "stage": "mayajaal",
                "run_id": roots.run_id,
                "code_version": __version__,
                "seed": cfg.seed,
                "config_sha256": config_sha256,
                "outputs": [_entry(w) for w in quarantined],
            },
            indent=2,
        )
        + "\n",
        roots.truth,
        "_meta.json",
    )
    return roots.observable / "chain" / "_meta.json"
