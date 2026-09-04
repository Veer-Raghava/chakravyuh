"""MAYAJAAL-SPEC Layer 1: the entity population, its wallets and its activity schedules.

A population, not a list of addresses. Every entity carries the wallet policy and the online
schedule its type implies, and the awkward cases downstream stages have to cope with — a
hot wallet reused thousands of times, a single-address mule, two entities behind one CGNAT
address — fall out of those policies rather than being injected afterwards.

Nothing here is random without a caller-supplied `random.Random`. Nothing here reads a clock.

Identifiers are synthetic by construction, because an invented identifier that happens to be
real is a forensics tool leaking someone's data:

  addresses   carry "gen0i" in the body. "i" is absent from the bech32 charset and "0" is
              absent from the base58 alphabet, so a bech32-shaped result can never decode
              and a base58-shaped result can never checksum.
  IPv4        198.18.0.0/15, the RFC 2544 benchmarking range, and 100.64.0.0/10, the
              RFC 6598 CGNAT range. Neither is globally routable.
  IPv6        2001:db8::/32, the RFC 3849 documentation prefix.
"""

from __future__ import annotations

import functools
import ipaddress
import random
from dataclasses import dataclass, field

from chakravyuh.mayajaal import weighted
from chakravyuh.mayajaal.config import Config, TypeSpec
from chakravyuh.mayajaal.weighted import WeightedIndex

# Real mainnet prefixes and lengths, so a length-based or prefix-based script_type rule in a
# later stage behaves the way it would on real data. These are protocol facts, not knobs.
ADDRESS_SHAPES: dict[str, tuple[str, int, str]] = {
    "p2pkh": ("1", 34, "2"),
    "p2sh": ("3", 34, "2"),
    "p2wpkh": ("bc1q", 42, "q"),
    "p2wsh": ("bc1q", 62, "q"),
    "p2tr": ("bc1p", 62, "q"),
}
INVALID_MARKER = "gen0i"
HOURS_PER_DAY = 24
US_PER_HOUR = 3_600_000_000


def hour_of(time_us: int) -> int:
    """UTC hour of day for a microsecond timestamp. No datetime, so no clock and no locale."""
    return (time_us // US_PER_HOUR) % HOURS_PER_DAY


@dataclass(slots=True)
class AddressFactory:
    """Mints unique, structurally invalid addresses. The counter is the uniqueness proof."""

    kinds: WeightedIndex[str]
    minted: int = 0

    def mint(self, rng: random.Random, kind: str | None = None) -> tuple[str, str]:
        chosen = self.kinds.pick(rng) if kind is None else kind
        prefix, width, pad = ADDRESS_SHAPES[chosen]
        head = prefix + INVALID_MARKER
        tag = f"{self.minted:x}"
        self.minted += 1
        fill = width - len(head) - len(tag)
        if fill < 0:
            raise ValueError(f"address counter overflowed the {chosen} width: {self.minted}")
        # Padding sits between the marker and the tag so the tag lands last. peek.py truncates
        # to first six and last four, and two addresses that redact to the same string would
        # make truncated output useless to read.
        return head + pad * fill + tag, chosen


@dataclass(slots=True)
class Entity:
    """One actor. `addresses` and `address_kinds` stay parallel and grow as the run proceeds."""

    entity_id: str
    entity_type: str
    is_illicit: bool
    reuse_rate: float
    change_policy: str
    ips: tuple[str, ...]
    behind_cgnat: bool
    active_start: int
    active_len: int
    addresses: list[str] = field(default_factory=list)
    address_kinds: list[str] = field(default_factory=list)

    def active_at(self, hour: int) -> bool:
        return (hour - self.active_start) % HOURS_PER_DAY < self.active_len

    def _mint(
        self, rng: random.Random, factory: AddressFactory, kind: str | None
    ) -> tuple[str, str]:
        address, chosen = factory.mint(rng, kind)
        self.addresses.append(address)
        self.address_kinds.append(chosen)
        return address, chosen

    def receive_address(self, rng: random.Random, factory: AddressFactory) -> tuple[str, str]:
        """An address to be paid at, honouring this entity's reuse policy."""
        if self.addresses and rng.random() < self.reuse_rate:
            index = rng.randrange(len(self.addresses))
            return self.addresses[index], self.address_kinds[index]
        return self._mint(rng, factory, None)

    def change_address(
        self, rng: random.Random, factory: AddressFactory, kind: str
    ) -> tuple[str, bool]:
        """Change address of the same script type as the inputs. True if it is a reused one.

        A reused change address is what makes the change heuristic wrong sometimes, which is
        why the flag is returned rather than discarded: the caller records it as the
        heuristic violation it is.
        """
        if self.change_policy == "reuse":
            matches = [i for i, k in enumerate(self.address_kinds) if k == kind]
            if matches:
                return self.addresses[rng.choice(matches)], True
        return self._mint(rng, factory, kind)[0], False


@dataclass(frozen=True, slots=True)
class Population:
    """The world, plus the sampling tables the transaction loop needs on its hot path."""

    entities: tuple[Entity, ...]
    senders_by_hour: tuple[WeightedIndex[int], ...]
    receivers: WeightedIndex[int]
    pools: tuple[int, ...]
    hashrate: WeightedIndex[int]
    factory: AddressFactory


@functools.cache
def _pool_range(cidr: str) -> tuple[int, int, int]:
    net = ipaddress.ip_network(cidr)
    return int(net.network_address), net.num_addresses, net.version


def _ip(rng: random.Random, pool: tuple[int, int, int]) -> str:
    base, size, version = pool
    value = base + rng.randrange(size)
    if version == 4:
        return str(ipaddress.IPv4Address(value))
    return str(ipaddress.IPv6Address(value))


def _cgnat_share(cfg: Config, type_name: str) -> float:
    """MAYAJAAL-SPEC gives a CGNAT share for exactly these two types. Everyone else is 0."""
    if type_name == "individual":
        return cfg.world.cgnat_share_individuals
    if type_name == "mule":
        return cfg.world.cgnat_share_mules
    return 0.0


def _counts(cfg: Config) -> dict[str, int]:
    """Entities per type, rounded, with the rounding drift given to the largest share."""
    total = cfg.world.n_entities
    counts = {spec.name: round(spec.share * total) for spec in cfg.types}
    order = sorted(cfg.types, key=lambda spec: (-spec.share, spec.name))
    counts[order[0].name] += total - sum(counts.values())
    if counts[order[0].name] < 0:
        raise ValueError(f"n_entities={total} is too small to hold the configured type shares")
    return counts


def _one(cfg: Config, spec: TypeSpec, index: int, rng: random.Random) -> Entity:
    world = cfg.world
    behind_cgnat = rng.random() < _cgnat_share(cfg, spec.name)
    if behind_cgnat:
        pool = _pool_range(world.cgnat_pool)
    elif rng.random() < world.ipv6_share:
        pool = _pool_range(world.ipv6_pool)
    else:
        pool = _pool_range(world.ipv4_pool)
    low, high = world.ips_per_entity
    n_ips = rng.randint(low, high)
    len_low, len_high = world.active_hours_len
    return Entity(
        entity_id=f"ent-{index:06d}",
        entity_type=spec.name,
        is_illicit=False,
        reuse_rate=spec.reuse_rate,
        change_policy=spec.change_policy,
        ips=tuple(_ip(rng, pool) for _ in range(n_ips)),
        behind_cgnat=behind_cgnat,
        active_start=rng.randrange(HOURS_PER_DAY),
        active_len=rng.randint(len_low, len_high),
    )


def build(cfg: Config, rng: random.Random) -> Population:
    """Build the population and every sampling table over it. Deterministic given `rng`."""
    factory = AddressFactory(kinds=weighted.build(cfg.chain.script_weights.items()))
    counts = _counts(cfg)
    entities: list[Entity] = []
    for spec in cfg.types:
        for _ in range(counts[spec.name]):
            entity = _one(cfg, spec, len(entities), rng)
            n_low, n_high = spec.n_addresses
            for _ in range(rng.randint(n_low, n_high)):
                entity._mint(rng, factory, None)
            entities.append(entity)

    illicit_pool = [i for i, e in enumerate(entities) if cfg.type_of(e.entity_type).illicit_capable]
    want = round(cfg.world.illicit_entity_share * len(entities))
    for index in rng.sample(illicit_pool, min(want, len(illicit_pool))):
        entities[index].is_illicit = True

    senders = tuple(
        weighted.build(
            (i, cfg.type_of(e.entity_type).tx_rate)
            for i, e in enumerate(entities)
            if e.active_at(hour)
        )
        for hour in range(HOURS_PER_DAY)
    )
    receivers = weighted.build(
        (i, cfg.type_of(e.entity_type).receive_rate) for i, e in enumerate(entities)
    )
    pools = tuple(i for i, e in enumerate(entities) if e.entity_type == "mining_pool")
    if not pools:
        raise ValueError(
            f"n_entities={cfg.world.n_entities} rounds the mining_pool share to zero, "
            "so no coinbase has anywhere to be paid"
        )
    hashrate = weighted.build(
        (i, rng.lognormvariate(cfg.chain.hashrate_mu, cfg.chain.hashrate_sigma)) for i in pools
    )
    return Population(
        entities=tuple(entities),
        senders_by_hour=senders,
        receivers=receivers,
        pools=pools,
        hashrate=hashrate,
        factory=factory,
    )
