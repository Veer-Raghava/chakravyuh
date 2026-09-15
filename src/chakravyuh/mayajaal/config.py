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


def _fpair(node: Mapping[str, Any], path: str, key: str) -> tuple[float, float]:
    """A two-element list of numbers. Order is not checked: `move_weights` uses it as a pair
    of endpoints to interpolate between, and a cautious weight below the hurried one is a
    legitimate way to describe a move a hurried campaign prefers."""
    value = _get(node, path, key)
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError(f"run_config.json: {path}{key} must be a two-element list, got {value!r}")
    low, high = value
    for item in (low, high):
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise TypeError(f"run_config.json: {path}{key} must hold numbers, got {value!r}")
    return float(low), float(high)


def _strs(node: Mapping[str, Any], path: str, key: str) -> tuple[str, ...]:
    value = _get(node, path, key)
    if not isinstance(value, list) or not value:
        raise TypeError(f"run_config.json: {path}{key} must be a non-empty list, got {value!r}")
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"run_config.json: {path}{key} must hold strings, got {value!r}")
    return tuple(value)


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
    illicit_tx_share: float
    cgnat_share_individuals: float
    cgnat_share_mules: float
    cgnat_addresses_per_region: int
    ips_per_entity: tuple[int, int]
    ipv6_share: float
    ipv4_pool: str
    cgnat_pool: str
    ipv6_pool: str
    active_hours_len: tuple[int, int]


@dataclass(frozen=True, slots=True)
class NetworkSpec:
    """MAYAJAAL-SPEC Layer 3. `observer_fraction` is the parameter that decides everything."""

    n_nodes: int
    outbound_per_node: int
    max_inbound: int
    relay_delay_outbound_mean_s: float
    relay_delay_inbound_mean_s: float
    latency_matrix: Path
    n_observers: int
    observer_fraction: float
    tor_share: float
    vpn_share: float
    bucket_penalty: float
    flood_frontier: int
    n_tor_exits: int
    n_vpn_nodes: int
    unresolved_asn_share: float
    unresolved_geo_share: float
    inv_share: float
    listen_port: int
    ephemeral_ports: tuple[int, int]
    observer_pool: str
    tor_pool: str
    vpn_pool: str
    tor_asn: int
    vpn_asn: int

    @property
    def relay_delay_outbound_us(self) -> float:
        return self.relay_delay_outbound_mean_s * 1_000_000.0

    @property
    def relay_delay_inbound_us(self) -> float:
        return self.relay_delay_inbound_mean_s * 1_000_000.0


@dataclass(frozen=True, slots=True)
class AdversarySpec:
    """MAYAJAAL-SPEC Layer 4. `move_weights` maps a move to a (cautious, hurried) pair of
    weights; a campaign interpolates between them by its own risk appetite, so the move mix
    is a consequence of the agent's disposition rather than a typology stamped on the graph."""

    n_campaigns: int
    moves_per_campaign: tuple[int, int]
    risk_appetite_dist: str
    structuring_threshold_sats: int
    peel_share: tuple[float, float]
    split_outputs: tuple[int, int]
    mix_outputs: tuple[int, int]
    merge_inputs: tuple[int, int]
    dwell_blocks: tuple[int, int]
    move_gap_blocks: tuple[int, int]
    move_weights: Mapping[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class ExportSpec:
    shard_rows: int
    formats: tuple[str, ...]
    xml_sample_rows: int


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
    announcements_per_tx_tolerance: float
    origin_recoverable_min: float
    first_seen_leakage_min: float
    first_seen_leakage_max: float
    trivial_rule_max: float
    tree_leakage_max: float
    delay_cv_min: float
    block_interval_cv_min: float
    block_interval_cv_max: float


@dataclass(frozen=True, slots=True)
class EvalSpec:
    """How a run is split into a training window and a holdout, and when an estimator abstains.

    These are properties of the run, not of the generator: MAYAJAAL never reads them. They live
    here because `config.effective.json` is copied into every run directory, so a stage that scores
    against a run can recover the split policy that run was measured under instead of hardcoding a
    fraction of its own. `train_fraction` is a share of the capture's observed time span; the
    boundary microsecond it implies is derived by `chakravyuh.eval.split` and by nothing else.
    """

    train_fraction: float
    margin_floor: float
    min_announcements: int


@dataclass(frozen=True, slots=True)
class Config:
    seed: int
    n_txs: int
    mean_announcements_per_tx: int
    world: WorldSpec
    chain: ChainSpec
    network: NetworkSpec
    adversary: AdversarySpec
    export: ExportSpec
    validation: ValidationSpec
    evaluation: EvalSpec
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
        illicit_tx_share=_float(node, "world.", "illicit_tx_share"),
        cgnat_share_individuals=_float(node, "world.", "cgnat_share_individuals"),
        cgnat_share_mules=_float(node, "world.", "cgnat_share_mules"),
        cgnat_addresses_per_region=_int(node, "world.", "cgnat_addresses_per_region"),
        ips_per_entity=_pair(node, "world.", "ips_per_entity"),
        ipv6_share=_float(node, "world.", "ipv6_share"),
        ipv4_pool=_str(pools, "world.ip_pools.", "ipv4"),
        cgnat_pool=_str(pools, "world.ip_pools.", "cgnat"),
        ipv6_pool=_str(pools, "world.ip_pools.", "ipv6"),
        active_hours_len=_pair(node, "world.", "active_hours_len"),
    )


def _network(node: Mapping[str, Any], anchor: Path) -> NetworkSpec:
    """`anchor` is the directory holding run_config.json, so `latency_matrix` resolves beside
    the config that named it rather than against whatever the working directory happens to be."""
    pools = _obj(node, "network.", "ip_pools")
    return NetworkSpec(
        n_nodes=_int(node, "network.", "n_nodes"),
        outbound_per_node=_int(node, "network.", "outbound_per_node"),
        max_inbound=_int(node, "network.", "max_inbound"),
        relay_delay_outbound_mean_s=_float(node, "network.", "relay_delay_outbound_mean_s"),
        relay_delay_inbound_mean_s=_float(node, "network.", "relay_delay_inbound_mean_s"),
        latency_matrix=anchor / _str(node, "network.", "latency_matrix"),
        n_observers=_int(node, "network.", "n_observers"),
        observer_fraction=_float(node, "network.", "observer_fraction"),
        tor_share=_float(node, "network.", "tor_share"),
        vpn_share=_float(node, "network.", "vpn_share"),
        bucket_penalty=_float(node, "network.", "bucket_penalty"),
        flood_frontier=_int(node, "network.", "flood_frontier"),
        n_tor_exits=_int(node, "network.", "n_tor_exits"),
        n_vpn_nodes=_int(node, "network.", "n_vpn_nodes"),
        unresolved_asn_share=_float(node, "network.", "unresolved_asn_share"),
        unresolved_geo_share=_float(node, "network.", "unresolved_geo_share"),
        inv_share=_float(node, "network.", "inv_share"),
        listen_port=_int(node, "network.", "listen_port"),
        ephemeral_ports=_pair(node, "network.", "ephemeral_ports"),
        observer_pool=_str(pools, "network.ip_pools.", "observer"),
        tor_pool=_str(pools, "network.ip_pools.", "tor_exit"),
        vpn_pool=_str(pools, "network.ip_pools.", "vpn"),
        tor_asn=_int(node, "network.", "tor_asn"),
        vpn_asn=_int(node, "network.", "vpn_asn"),
    )


def _adversary(node: Mapping[str, Any]) -> AdversarySpec:
    raw = _obj(node, "adversary.", "move_weights")
    return AdversarySpec(
        n_campaigns=_int(node, "adversary.", "n_campaigns"),
        moves_per_campaign=_pair(node, "adversary.", "moves_per_campaign"),
        risk_appetite_dist=_str(node, "adversary.", "risk_appetite_dist"),
        structuring_threshold_sats=_int(node, "adversary.", "structuring_threshold_sats"),
        peel_share=_fpair(node, "adversary.", "peel_share"),
        split_outputs=_pair(node, "adversary.", "split_outputs"),
        mix_outputs=_pair(node, "adversary.", "mix_outputs"),
        merge_inputs=_pair(node, "adversary.", "merge_inputs"),
        dwell_blocks=_pair(node, "adversary.", "dwell_blocks"),
        move_gap_blocks=_pair(node, "adversary.", "move_gap_blocks"),
        move_weights={name: _fpair(raw, "adversary.move_weights.", name) for name in sorted(raw)},
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


def _eval(node: Mapping[str, Any]) -> EvalSpec:
    spec = EvalSpec(
        train_fraction=_float(node, "eval.", "train_fraction"),
        margin_floor=_float(node, "eval.", "margin_floor"),
        min_announcements=_int(node, "eval.", "min_announcements"),
    )
    if not 0.0 < spec.train_fraction < 1.0:
        raise ValueError(
            f"run_config.json: eval.train_fraction must be strictly between 0 and 1, got "
            f"{spec.train_fraction}. At 0 there is nothing to train on and at 1 there is nothing "
            "held out, and either way the number a gate reads is not a measurement."
        )
    if not 0.0 <= spec.margin_floor < 1.0:
        raise ValueError(
            f"run_config.json: eval.margin_floor must be in [0, 1), got {spec.margin_floor}"
        )
    if spec.min_announcements < 1:
        raise ValueError(
            f"run_config.json: eval.min_announcements must be positive, got "
            f"{spec.min_announcements}"
        )
    return spec


# The one leaf `--set` may not touch. Everything else in the file is a scalar describing the
# world; this one names a file on disk, and an override that can rewrite it is a second path
# argument wearing a different hat.
_UNSETTABLE: frozenset[str] = frozenset({"network.latency_matrix"})


def _coerce(current: object, path: str, text: str) -> object:
    """Parse `text` into the type the leaf already holds. The existing value is the schema."""
    if isinstance(current, bool):
        if text not in ("true", "false"):
            raise ValueError(f"--set {path}: expected true or false, got {text!r}")
        return text == "true"
    if isinstance(current, int):
        try:
            return int(text)
        except ValueError:
            raise ValueError(f"--set {path}: expected an integer, got {text!r}") from None
    if isinstance(current, float):
        try:
            return float(text)
        except ValueError:
            raise ValueError(f"--set {path}: expected a number, got {text!r}") from None
    if isinstance(current, str):
        return text
    raise TypeError(
        f"--set {path}: only a scalar leaf can be overridden, and this one holds "
        f"{type(current).__name__}. Name the leaf inside it instead."
    )


def _apply_overrides(root: dict[str, Any], overrides: Mapping[str, str]) -> None:
    """Fold dotted `key=value` overrides into the parsed config in place, before any check runs.

    Applied before `_check`, so an override that makes the world impossible fails the same way a
    bad file does rather than producing a wrong run. The mutated dict is the one that becomes
    `Config.effective` and is written to `config.effective.json`, so a run always records the
    parameters that produced it, never the file's defaults.

    A key must name a leaf that already exists. That is the entire safety property: a typo cannot
    invent a knob, so a sweep whose `--set network.observer_fractoin=0.02` silently did nothing is
    impossible. Values are scalars, coerced to the leaf's current type, and never paths.
    """
    for path, text in sorted(overrides.items()):
        if path in _UNSETTABLE:
            raise ValueError(
                f"--set {path} is refused: that key names a file, and the only path argument in "
                "this system is --out."
            )
        parts = path.split(".")
        if not all(parts):
            raise ValueError(f"--set {path!r} is not a dotted key")
        node: Any = root
        for depth, part in enumerate(parts[:-1]):
            if not isinstance(node, dict) or part not in node:
                walked = ".".join(parts[: depth + 1])
                raise KeyError(f"--set {path}: run_config.json has no {walked}")
            node = node[part]
        leaf = parts[-1]
        if not isinstance(node, dict) or leaf not in node:
            raise KeyError(
                f"--set {path}: run_config.json has no such key. An override may only change a "
                "value that already exists, or a misspelling would quietly do nothing."
            )
        node[leaf] = _coerce(node[leaf], path, text)


def load(
    path: Path,
    *,
    seed: int | None = None,
    n_txs: int | None = None,
    n_entities: int | None = None,
    anchor: Path | None = None,
    overrides: Mapping[str, str] | None = None,
) -> Config:
    """Parse `path`, apply the CLI overrides, and check the config is self-consistent.

    `n_txs` defaults to `target_rows // mean_announcements_per_tx`, because the spec asks
    callers to think in capture rows and one transaction becomes about nine rows once S02
    attaches announcements. `target_rows` is left untouched in the effective copy: it is
    S02's target, and rewriting it here would erase what the operator actually asked for.

    `anchor` is the directory the config's own relative paths resolve against, `path.parent` by
    default. The one caller that passes it is the validator, which loads the `config.effective.json`
    copied into a run directory: that copy names `regions.yaml` exactly as the original did, and
    the original's neighbour is in the repository root rather than beside the copy.

    `overrides` is the generic `--set key=value` door, described on `_apply_overrides`. It exists
    because the S06 accuracy curve needs five worlds that differ in one number, and five near
    identical config files would drift apart the first time anyone edited four of them.
    """
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"{path} must hold a JSON object")
    root: dict[str, Any] = raw
    if overrides:
        _apply_overrides(root, overrides)

    resolved_seed = _int(root, "", "seed") if seed is None else seed
    mean_announcements = _int(root, "", "mean_announcements_per_tx")
    if mean_announcements < 1:
        raise ValueError(f"mean_announcements_per_tx must be positive, got {mean_announcements}")
    if n_txs is None:
        n_txs = _int(root, "", "target_rows") // mean_announcements
    if n_txs < 1:
        raise ValueError(f"transaction count must be positive, got {n_txs}")

    world_node = _obj(root, "", "world")
    if n_entities is not None:
        world_node["n_entities"] = n_entities
    chain_node = _obj(root, "", "chain")
    valid_node = _obj(root, "", "validation")
    eval_node = _obj(root, "", "eval")
    types_node = _obj(root, "", "types")
    export_node = _obj(root, "", "export")

    chain = _chain(chain_node)
    types = tuple(
        _type_spec(name, _obj(types_node, "types.", name), chain.address_reuse_rate)
        for name in sorted(types_node)
    )
    network = _network(_obj(root, "", "network"), path.parent if anchor is None else anchor)
    adversary = _adversary(_obj(root, "", "adversary"))
    _check(chain, types, network, adversary)
    world = _world(world_node)

    effective = dict(root)
    effective["seed"] = resolved_seed
    effective["world"] = world_node
    effective["n_transactions"] = n_txs
    # `network.n_nodes` is a ceiling, not a count. The graph gives one peer to each entity and
    # stops there, then adds the Tor exits and VPN nodes, so a 5000-node ceiling over a 4000
    # entity population yields 4160 nodes and the run manifest records 4160. Both numbers are
    # already in this file, but only as inputs to an arithmetic nobody should have to find in
    # network.py to explain a manifest, so the result is recorded alongside them.
    effective["n_nodes_effective"] = (
        min(network.n_nodes, world.n_entities) + network.n_tor_exits + network.n_vpn_nodes
    )
    return Config(
        seed=resolved_seed,
        n_txs=n_txs,
        mean_announcements_per_tx=mean_announcements,
        world=world,
        chain=chain,
        network=network,
        adversary=adversary,
        export=ExportSpec(
            shard_rows=_int(export_node, "export.", "shard_rows"),
            formats=_strs(export_node, "export.", "formats"),
            xml_sample_rows=_int(export_node, "export.", "xml_sample_rows"),
        ),
        validation=ValidationSpec(
            value_p99_over_p50_min=_float(valid_node, "validation.", "value_p99_over_p50_min"),
            value_p999_over_p50_min=_float(valid_node, "validation.", "value_p999_over_p50_min"),
            multi_input_rate_tolerance=_float(
                valid_node, "validation.", "multi_input_rate_tolerance"
            ),
            announcements_per_tx_tolerance=_float(
                valid_node, "validation.", "announcements_per_tx_tolerance"
            ),
            origin_recoverable_min=_float(valid_node, "validation.", "origin_recoverable_min"),
            first_seen_leakage_min=_float(valid_node, "validation.", "first_seen_leakage_min"),
            first_seen_leakage_max=_float(valid_node, "validation.", "first_seen_leakage_max"),
            trivial_rule_max=_float(valid_node, "validation.", "trivial_rule_max"),
            tree_leakage_max=_float(valid_node, "validation.", "tree_leakage_max"),
            delay_cv_min=_float(valid_node, "validation.", "delay_cv_min"),
            block_interval_cv_min=_float(valid_node, "validation.", "block_interval_cv_min"),
            block_interval_cv_max=_float(valid_node, "validation.", "block_interval_cv_max"),
        ),
        evaluation=_eval(eval_node),
        types=types,
        effective=effective,
    )


_MOVES = ("peel", "split", "merge", "mix", "hop", "structure", "dwell", "cash_out")


def _check(
    chain: ChainSpec,
    types: tuple[TypeSpec, ...],
    network: NetworkSpec,
    adversary: AdversarySpec,
) -> None:
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
    if network.tor_share + network.vpn_share >= 1.0:
        raise ValueError("network.tor_share + network.vpn_share must leave room for clear traffic")
    if not 0.0 < network.observer_fraction <= 1.0:
        raise ValueError(
            f"network.observer_fraction must be in (0, 1], got {network.observer_fraction}"
        )
    if network.n_observers < 1:
        raise ValueError("network.n_observers must be at least one, or nothing is ever recorded")
    if network.outbound_per_node < 1 or network.flood_frontier < 2:
        raise ValueError("network.outbound_per_node and flood_frontier must allow propagation")
    if set(adversary.move_weights) != set(_MOVES):
        missing = sorted(set(_MOVES) - set(adversary.move_weights))
        extra = sorted(set(adversary.move_weights) - set(_MOVES))
        raise ValueError(f"adversary.move_weights: missing {missing}, unknown {extra}")
    if adversary.moves_per_campaign[0] < 1:
        raise ValueError("adversary.moves_per_campaign must start at one move or more")
