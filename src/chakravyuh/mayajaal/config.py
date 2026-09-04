"""Load `run_config.json` into frozen, typed parameter objects.

Every number MAYAJAAL uses arrives through here. There is no default anywhere in this
module: a missing key raises, naming the path it was looked for under. That is deliberate
and it is the mechanism behind the stage rule "no hardcoded parameter" — a knob that does
not exist in the config file cannot be silently supplied by code instead.

The three CLI overrides (seed, transaction count, entity count) are the exception the spec
itself defines (`mayajaal --txs 100000 --seed 42`). They are folded into `Config.effective`,
which is the dict written back out beside the run, so a run's own directory always records
the parameters that produced it rather than the file's defaults.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _get(node: Mapping[str, Any], path: str, key: str) -> object:
    """Returns `object`, not `Any`: every caller below has to prove the type it wants."""
    if key not in node:
        raise KeyError(f"run_config.json: missing {path}{key}")
    return node[key]


def _int(node: Mapping[str, Any], path: str, key: str) -> int:
    value = _get(node, path, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"run_config.json: {path}{key} must be an integer, got {value!r}")
    return value


def _float(node: Mapping[str, Any], path: str, key: str) -> float:
    value = _get(node, path, key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"run_config.json: {path}{key} must be a number, got {value!r}")
    return float(value)


def _bool(node: Mapping[str, Any], path: str, key: str) -> bool:
    value = _get(node, path, key)
    if not isinstance(value, bool):
        raise TypeError(f"run_config.json: {path}{key} must be true or false, got {value!r}")
    return value


def _str(node: Mapping[str, Any], path: str, key: str) -> str:
    value = _get(node, path, key)
    if not isinstance(value, str):
        raise TypeError(f"run_config.json: {path}{key} must be a string, got {value!r}")
    return value


def _obj(node: Mapping[str, Any], path: str, key: str) -> dict[str, Any]:
    value = _get(node, path, key)
    if not isinstance(value, dict):
        raise TypeError(f"run_config.json: {path}{key} must be an object, got {value!r}")
    return dict(value)


def _pair(node: Mapping[str, Any], path: str, key: str) -> tuple[int, int]:
    """An inclusive [low, high] integer range. High below low is a config error, not a clamp."""
    value = _get(node, path, key)
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError(f"run_config.json: {path}{key} must be a two-element list, got {value!r}")
    low, high = value
    if isinstance(low, bool) or isinstance(high, bool):
        raise TypeError(f"run_config.json: {path}{key} must hold integers, got {value!r}")
    if not isinstance(low, int) or not isinstance(high, int):
        raise TypeError(f"run_config.json: {path}{key} must hold integers, got {value!r}")
    if high < low:
        raise ValueError(f"run_config.json: {path}{key} is inverted: {value!r}")
    return low, high


def _weights(node: Mapping[str, Any], path: str, key: str) -> dict[str, float]:
    raw = _obj(node, path, key)
    out = {name: _float(raw, f"{path}{key}.", name) for name in raw}
    if not out:
        raise ValueError(f"run_config.json: {path}{key} is empty")
    return out


def _ints(node: Mapping[str, Any], path: str, key: str) -> dict[str, int]:
    raw = _obj(node, path, key)
    return {name: _int(raw, f"{path}{key}.", name) for name in raw}


@dataclass(frozen=True, slots=True)
class TypeSpec:
    """One row of MAYAJAAL-SPEC Layer 1's entity table, plus its wallet and value policy."""

    name: str
    share: float
    tx_rate: float
    receive_rate: float
    value_mu: float
    value_sigma: float
    n_addresses: tuple[int, int]
    reuse_rate: float
    change_policy: str
    outputs: tuple[int, int]
    equal_outputs: bool
    illicit_capable: bool


@dataclass(frozen=True, slots=True)
class WorldSpec:
    n_entities: int
    illicit_entity_share: float
    cgnat_share_individuals: float
    cgnat_share_mules: float
    ips_per_entity: tuple[int, int]
    ipv6_share: float
    ipv4_pool: str
    cgnat_pool: str
    ipv6_pool: str
    active_hours_len: tuple[int, int]


@dataclass(frozen=True, slots=True)
class ChainSpec:
    start_height: int
    genesis_us: int
    block_interval_s: float
    txs_per_block: int
    min_blocks: int
    coinbase_subsidy_sats: int
    coinbase_maturity_blocks: int
    pool_payout_interval_blocks: int
    pool_payout_outputs: tuple[int, int]
    hashrate_mu: float
    hashrate_sigma: float
    dust_threshold_sats: int
    min_payment_sats: int
    multi_input_rate: float
    multi_input_controller_gain: float
    collaborative_multi_input_rate: float
    max_pick_attempts: int
    coin_select_window: int
    address_reuse_rate: float
    round_payment_rate: float
    round_to_sats: int
    endow_utxos: tuple[int, int]
    endow_mu_offset: float
    endow_sigma: float
    fee_mu: float
    fee_sigma: float
    fee_min_sat_per_vb: int
    fee_max_sat_per_vb: int
    script_weights: Mapping[str, float]
    vsize_overhead_vb: int
    input_vb: Mapping[str, int]
    output_vb: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class ValidationSpec:
    """Thresholds the tests assert against, so a tuning change moves the bar in one place."""

    value_p99_over_p50_min: float
    value_p999_over_p50_min: float
    multi_input_rate_tolerance: float


@dataclass(frozen=True, slots=True)
class Config:
    seed: int
    n_txs: int
    world: WorldSpec
    chain: ChainSpec
    validation: ValidationSpec
    types: tuple[TypeSpec, ...]
    effective: Mapping[str, Any]

    @property
    def n_blocks(self) -> int:
        """Blocks needed to hold `n_txs`, floored so a small run still has a real timeline.

        Without the floor a 2,000-transaction test run fits in one block, which would give
        coinbase maturity nothing to mature over and would put every transaction at one
        timestamp. `txs_per_block` is therefore a sampling-density knob, not a claim that
        real blocks hold thirty transactions.
        """
        return max(self.chain.min_blocks, -(-self.n_txs // self.chain.txs_per_block))

    def type_of(self, name: str) -> TypeSpec:
        for spec in self.types:
            if spec.name == name:
                return spec
        raise KeyError(f"no entity type named {name!r} in run_config.json types")


def _type_spec(name: str, node: Mapping[str, Any], reuse_fallback: float) -> TypeSpec:
    path = f"types.{name}."
    value = _obj(node, path, "value")
    return TypeSpec(
        name=name,
        share=_float(node, path, "share"),
        tx_rate=_float(node, path, "tx_rate"),
        receive_rate=_float(node, path, "receive_rate"),
        value_mu=_float(value, f"{path}value.", "mu"),
        value_sigma=_float(value, f"{path}value.", "sigma"),
        n_addresses=_pair(node, path, "n_addresses"),
        # The only fallback in the module, and it resolves to another config key rather
        # than to a literal: MAYAJAAL-SPEC keeps one population-wide address_reuse_rate.
        reuse_rate=_float(node, path, "reuse_rate") if "reuse_rate" in node else reuse_fallback,
        change_policy=_str(node, path, "change_policy"),
        outputs=_pair(node, path, "outputs"),
        equal_outputs=_bool(node, path, "equal_outputs"),
        illicit_capable=_bool(node, path, "illicit_capable"),
    )


def _world(node: Mapping[str, Any]) -> WorldSpec:
    pools = _obj(node, "world.", "ip_pools")
    return WorldSpec(
        n_entities=_int(node, "world.", "n_entities"),
        illicit_entity_share=_float(node, "world.", "illicit_entity_share"),
        cgnat_share_individuals=_float(node, "world.", "cgnat_share_individuals"),
        cgnat_share_mules=_float(node, "world.", "cgnat_share_mules"),
        ips_per_entity=_pair(node, "world.", "ips_per_entity"),
        ipv6_share=_float(node, "world.", "ipv6_share"),
        ipv4_pool=_str(pools, "world.ip_pools.", "ipv4"),
        cgnat_pool=_str(pools, "world.ip_pools.", "cgnat"),
        ipv6_pool=_str(pools, "world.ip_pools.", "ipv6"),
        active_hours_len=_pair(node, "world.", "active_hours_len"),
    )


def _chain(node: Mapping[str, Any]) -> ChainSpec:
    hashrate = _obj(node, "chain.", "hashrate_dist")
    endow = _obj(node, "chain.", "endowment")
    fee = _obj(node, "chain.", "fee_rate")
    vsize = _obj(node, "chain.", "vsize")
    return ChainSpec(
        start_height=_int(node, "chain.", "start_height"),
        genesis_us=_int(node, "chain.", "genesis_us"),
        block_interval_s=_float(node, "chain.", "block_interval_s"),
        txs_per_block=_int(node, "chain.", "txs_per_block"),
        min_blocks=_int(node, "chain.", "min_blocks"),
        coinbase_subsidy_sats=_int(node, "chain.", "coinbase_subsidy_sats"),
        coinbase_maturity_blocks=_int(node, "chain.", "coinbase_maturity_blocks"),
        pool_payout_interval_blocks=_int(node, "chain.", "pool_payout_interval_blocks"),
        pool_payout_outputs=_pair(node, "chain.", "pool_payout_outputs"),
        hashrate_mu=_float(hashrate, "chain.hashrate_dist.", "mu"),
        hashrate_sigma=_float(hashrate, "chain.hashrate_dist.", "sigma"),
        dust_threshold_sats=_int(node, "chain.", "dust_threshold_sats"),
        min_payment_sats=_int(node, "chain.", "min_payment_sats"),
        multi_input_rate=_float(node, "chain.", "multi_input_rate"),
        multi_input_controller_gain=_float(node, "chain.", "multi_input_controller_gain"),
        collaborative_multi_input_rate=_float(node, "chain.", "collaborative_multi_input_rate"),
        max_pick_attempts=_int(node, "chain.", "max_pick_attempts"),
        coin_select_window=_int(node, "chain.", "coin_select_window"),
        address_reuse_rate=_float(node, "chain.", "address_reuse_rate"),
        round_payment_rate=_float(node, "chain.", "round_payment_rate"),
        round_to_sats=_int(node, "chain.", "round_to_sats"),
        endow_utxos=_pair(endow, "chain.endowment.", "utxos_per_entity"),
        endow_mu_offset=_float(endow, "chain.endowment.", "mu_offset"),
        endow_sigma=_float(endow, "chain.endowment.", "sigma"),
        fee_mu=_float(fee, "chain.fee_rate.", "mu"),
        fee_sigma=_float(fee, "chain.fee_rate.", "sigma"),
        fee_min_sat_per_vb=_int(fee, "chain.fee_rate.", "min_sat_per_vb"),
        fee_max_sat_per_vb=_int(fee, "chain.fee_rate.", "max_sat_per_vb"),
        script_weights=_weights(node, "chain.", "script_type_weights"),
        vsize_overhead_vb=_int(vsize, "chain.vsize.", "overhead_vb"),
        input_vb=_ints(vsize, "chain.vsize.", "input_vb"),
        output_vb=_ints(vsize, "chain.vsize.", "output_vb"),
    )


def load(
    path: Path,
    *,
    seed: int | None = None,
    n_txs: int | None = None,
    n_entities: int | None = None,
) -> Config:
    """Parse `path`, apply the three CLI overrides, and check the config is self-consistent.

    `n_txs` defaults to `target_rows // mean_announcements_per_tx`, because the spec asks
    callers to think in capture rows and one transaction becomes about nine rows once S02
    attaches announcements. `target_rows` is left untouched in the effective copy: it is
    S02's target, and rewriting it here would erase what the operator actually asked for.
    """
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"{path} must hold a JSON object")
    root: dict[str, Any] = raw

    resolved_seed = _int(root, "", "seed") if seed is None else seed
    if n_txs is None:
        n_txs = _int(root, "", "target_rows") // _int(root, "", "mean_announcements_per_tx")
    if n_txs < 1:
        raise ValueError(f"transaction count must be positive, got {n_txs}")

    world_node = _obj(root, "", "world")
    if n_entities is not None:
        world_node["n_entities"] = n_entities
    chain_node = _obj(root, "", "chain")
    valid_node = _obj(root, "", "validation")
    types_node = _obj(root, "", "types")

    chain = _chain(chain_node)
    types = tuple(
        _type_spec(name, _obj(types_node, "types.", name), chain.address_reuse_rate)
        for name in sorted(types_node)
    )
    _check(chain, types)

    effective = dict(root)
    effective["seed"] = resolved_seed
    effective["world"] = world_node
    effective["n_transactions"] = n_txs
    return Config(
        seed=resolved_seed,
        n_txs=n_txs,
        world=_world(world_node),
        chain=chain,
        validation=ValidationSpec(
            value_p99_over_p50_min=_float(valid_node, "validation.", "value_p99_over_p50_min"),
            value_p999_over_p50_min=_float(valid_node, "validation.", "value_p999_over_p50_min"),
            multi_input_rate_tolerance=_float(
                valid_node, "validation.", "multi_input_rate_tolerance"
            ),
        ),
        types=types,
        effective=effective,
    )


def _check(chain: ChainSpec, types: tuple[TypeSpec, ...]) -> None:
    """Reject a config that cannot describe a world, rather than generating a wrong one."""
    share = sum(spec.share for spec in types)
    if abs(share - 1.0) > 1e-9:
        raise ValueError(f"types shares must sum to 1.0, got {share}")
    weight = sum(chain.script_weights.values())
    if abs(weight - 1.0) > 1e-9:
        raise ValueError(f"chain.script_type_weights must sum to 1.0, got {weight}")
    for kind in chain.script_weights:
        for table, label in ((chain.input_vb, "input_vb"), (chain.output_vb, "output_vb")):
            if kind not in table:
                raise ValueError(f"chain.vsize.{label} has no entry for script type {kind!r}")
    for spec in types:
        if spec.change_policy not in ("fresh", "reuse"):
            raise ValueError(f"types.{spec.name}.change_policy must be fresh or reuse")
