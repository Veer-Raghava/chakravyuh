"""MAYAJAAL-SPEC Layer 3: the peer network, and the only part of a run an observer can see.

The capture is not the run. A transaction is created by an entity, broadcast by whichever node
that entity happens to use, and then relayed hop by hop with an independent delay on every
link. Our observers are a handful of listening nodes, and a row exists only when a node that
dialled one of them announced a transaction to it before learning of that transaction from
somebody else. Everything else that happened on the network is unobserved, which is the whole
difficulty of the problem: the first announcement an observer receives is usually not the
originator's.

Three mechanisms make that true, and all three are physical rather than cosmetic.

  independent delays   A node does not forward on receipt. For every peer and every
                       transaction it draws a fresh delay, mean two seconds toward a peer it
                       dialled and five toward a peer that dialled it. The order in which
                       observers hear about a transaction is therefore not the order of the
                       hops that carried it, and there is no cascade to sort.
  first only           An observer records the announcement that told it something new. After
                       that it holds the transaction, so the rest are duplicates, and the
                       peers it has told stop announcing. One row per observer per transaction
                       is the whole of what a listening node learns, and how much of the
                       network it watches decides how often that one row names the originator
                       rather than how many rows there are.
  shared nodes         There are fewer nodes than entities, so an entity without a node of
                       its own broadcasts through one it shares. The IP in the capture belongs
                       to the node; the wallet behind it may well be someone else.

Nothing here reads a clock or a file. Every draw comes from the caller's generator.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field

from chakravyuh.mayajaal import entities
from chakravyuh.mayajaal.chain import Run
from chakravyuh.mayajaal.config import Config
from chakravyuh.mayajaal.entities import Population
from chakravyuh.mayajaal.regions import Regions

# How many nodes a node considers before choosing its outbound peers. Bitcoin Core picks from a
# bounded sample of its address manager rather than from every node it has ever heard of, so a
# graph optimised globally would be the wrong model: it should be good, not perfect.
CANDIDATE_MULTIPLE = 4

# Redraws allowed when an observer address collides with one already taken. The observer pool is
# a /24 against sixteen observers, so a collision is rare and a run of this many is impossible
# unless the pool has been shrunk below the observer count, which is the case worth failing on.
_IP_DRAW_LIMIT = 64

NO_OBSERVER = -1
PEER = "peer"
TOR_EXIT = "tor_exit"
VPN = "vpn"


def observer_id(index: int) -> str:
    """Stable name for one listening node, written to the capture's `observer_id` column."""
    return f"obs-{index:02d}"


def _bucket(ip: str) -> str:
    """The address group a peer belongs to: its /16 for IPv4, its /32 for IPv6.

    Bitcoin Core spreads its outbound connections across groups so that owning one netblock is
    not enough to eclipse a node. Ours is the same rule expressed as a weight penalty rather
    than a hard exclusion, which leaves the occasional doubled-up group a real graph has.
    """
    if ":" in ip:
        return ":".join(ip.split(":")[:2])
    return ".".join(ip.split(".")[:2])


@dataclass(frozen=True, slots=True)
class Node:
    """One network peer. `owner` is the entity whose IP this is, and None for infrastructure.

    `asn` and `country` are the enrichment a later stage would look up from the IP, already
    resolved here so the capture can carry them. Either may be None: a real geo database has
    prefixes it does not cover, and a stage that has never seen a null one will break on real
    data. The null is drawn once per node rather than per row, because a missing prefix stays
    missing.
    """

    ip: str
    region: int
    port: int
    asn: int | None
    country: str | None
    owner: int | None
    kind: str


@dataclass(frozen=True, slots=True)
class Origin:
    """Truth for one transaction: where it entered the network, which no observer sees.

    `node` is the node that first sent it, not the entity's own node, and for a Tor or VPN
    broadcast that is the exit rather than the sender. This is deliberate: the answer key has
    to name the IP an attribution method could conceivably identify. Recording the sender's
    real address for a transaction that never touched the network from it would make the
    metric unwinnable and therefore meaningless. `used_tor` and `used_vpn` are how evaluation
    slices the score by what the sender was hiding behind.

    `tx_index` is the position in `run.txs` this row answers for. It is carried rather than
    implied, because coinbase transactions are skipped and the list is therefore shorter than
    `run.txs` and no longer aligned with it. A reader that recovered the transaction by
    reapplying the same filter would agree with this list only for as long as the two filters
    stayed identical.
    """

    tx_index: int
    node: int
    entity: int
    broadcast_us: int
    used_tor: bool
    used_vpn: bool
    observed_by_n: int


@dataclass(slots=True)
class Capture:
    """Every recorded announcement, in column form and ascending by time.

    One row is one announcement, and the chain columns repeat across every row announcing the
    same transaction. Holding those repeats here would be storing the same address list a dozen
    times over, so a row carries only an index into the run's transactions and the export joins
    the rest in as it writes.

    ponytail: the whole capture is materialised in memory. The ceiling is roughly the row
    budget of one run; streaming the shards straight out of the announce loop is the upgrade if
    a target row count ever stops fitting.
    """

    tx_index: list[int] = field(default_factory=list)
    src_node: list[int] = field(default_factory=list)
    observer: list[int] = field(default_factory=list)
    time_us: list[int] = field(default_factory=list)
    is_inv: list[bool] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.tx_index)


@dataclass(frozen=True, slots=True)
class Topology:
    """The graph. `outbound` is who a node dialled, `inbound` is who dialled it.

    Both directions are kept because a node relays to every peer it has, and a flood that
    travelled only along outbound edges would be a different, slower network than Bitcoin's.
    """

    nodes: tuple[Node, ...]
    observers: tuple[Node, ...]
    outbound: tuple[tuple[int, ...], ...]
    inbound: tuple[tuple[int, ...], ...]
    # Which observer a node dialled, or NO_OBSERVER. The only links a row can ever exist on.
    watched: tuple[int, ...]
    # The node each entity broadcasts through: its own if it runs one, a shared one otherwise.
    home: tuple[int, ...]
    tor_exits: tuple[int, ...]
    vpn_nodes: tuple[int, ...]


@dataclass(slots=True)
class Network:
    """What layer 3 produced: the graph, the answer key, and the observable rows."""

    topology: Topology
    origins: tuple[Origin, ...]
    capture: Capture


def _owners(cfg: Config, pop: Population, rng: random.Random, n_nodes: int) -> list[int]:
    """Which entities run a reachable node, weighted by how much traffic they originate.

    An exchange runs its own infrastructure and an individual usually does not, so the weight
    is the type's transaction rate. Sampling without replacement by the exponential-key method
    rather than by rejection, because the weights span a factor of sixty and a rejection loop
    would spend most of its draws rediscovering the same busy entities.
    """
    keys = sorted(
        (rng.random() ** (1.0 / cfg.type_of(entity.entity_type).tx_rate), index)
        for index, entity in enumerate(pop.entities)
    )
    return sorted(index for _, index in keys[len(keys) - n_nodes :])


def _node(
    cfg: Config,
    table: Regions,
    rng: random.Random,
    *,
    ip: str,
    region: int,
    kind: str,
    owner: int | None,
    asn: int,
) -> Node:
    net = cfg.network
    return Node(
        ip=ip,
        region=region,
        port=rng.randint(*net.ephemeral_ports),
        asn=None if rng.random() < net.unresolved_asn_share else asn,
        country=None if rng.random() < net.unresolved_geo_share else table.countries[region],
        owner=owner,
        kind=kind,
    )


def _peers(cfg: Config, nodes: list[Node], table: Regions, rng: random.Random) -> list[list[int]]:
    """Outbound peers per node: latency-weighted, address-bucket-penalised, inbound-capped.

    Not uniform, because a uniform graph has no geography in it and every node would be four
    hops from every other. Weighting by inverse latency gives the regional clustering a real
    network has; penalising a bucket already used pushes back against it, which is exactly the
    tension Core's own selection lives in. The inbound cap is what stops the best-connected
    region from becoming a hub every path runs through.
    """
    net = cfg.network
    total = len(nodes)
    sample = min(total - 1, CANDIDATE_MULTIPLE * net.outbound_per_node)
    buckets = [_bucket(node.ip) for node in nodes]
    taken = [0] * total
    out: list[list[int]] = []
    for source in range(total):
        pool: dict[int, None] = {}
        while len(pool) < sample:
            pick = rng.randrange(total)
            if pick != source:
                pool[pick] = None
        cands = list(pool)
        used: dict[str, None] = {}
        chosen: list[int] = []
        home = nodes[source].region
        while cands and len(chosen) < net.outbound_per_node:
            weights = [
                0.0
                if taken[c] >= net.max_inbound
                else (net.bucket_penalty if buckets[c] in used else 1.0)
                / table.latency_us[home][nodes[c].region]
                for c in cands
            ]
            spread = sum(weights)
            if spread <= 0.0:
                break
            mark = rng.random() * spread
            index = len(cands) - 1
            for position, weight in enumerate(weights):
                mark -= weight
                if mark <= 0.0:
                    index = position
                    break
            target = cands.pop(index)
            used[buckets[target]] = None
            taken[target] += 1
            chosen.append(target)
        out.append(chosen)
    return out


def _topology(cfg: Config, pop: Population, rng: random.Random) -> Topology:
    """Build the node set, wire it up, and decide which links we get to watch."""
    net = cfg.network
    table = pop.regions
    n_regions = len(table)
    picker = table.picker()
    n_peers = min(net.n_nodes, len(pop.entities))
    owners = _owners(cfg, pop, rng, n_peers)
    nodes = [
        _node(
            cfg,
            table,
            rng,
            # A node's address is its owner's, so an entity that runs one is findable by IP and
            # an entity that shares one is not. That asymmetry is the attribution problem.
            ip=pop.entities[owner].ips[0],
            region=pop.entities[owner].region,
            kind=PEER,
            owner=owner,
            asn=table.asns[pop.entities[owner].region],
        )
        for owner in owners
    ]
    infra: dict[str, list[int]] = {TOR_EXIT: [], VPN: []}
    for count, kind, pool, asn in (
        (net.n_tor_exits, TOR_EXIT, net.tor_pool, net.tor_asn),
        (net.n_vpn_nodes, VPN, net.vpn_pool, net.vpn_asn),
    ):
        for _ in range(count):
            region = picker.pick(rng)
            infra[kind].append(len(nodes))
            nodes.append(
                _node(
                    cfg,
                    table,
                    rng,
                    ip=entities.pool_ip(rng, pool, region, n_regions),
                    region=region,
                    kind=kind,
                    owner=None,
                    asn=asn,
                )
            )
    # Observers listen, so a monitored node dials them and the announcement carries that node's
    # ephemeral source port. That port is what separates two entities behind one CGNAT address.
    # Addresses are drawn until they are distinct: two observers sharing one `dst_ip` makes
    # `dst_ip` useless as a sensor key, and any later group-by on it silently merges them.
    observers: list[Node] = []
    taken: set[str] = set()
    for _ in range(net.n_observers):
        region = picker.pick(rng)
        for _attempt in range(_IP_DRAW_LIMIT):
            ip = entities.pool_ip(rng, net.observer_pool, region, n_regions)
            if ip not in taken:
                break
        else:
            raise ValueError(
                f"observer pool {net.observer_pool} cannot supply {net.n_observers} "
                "distinct addresses across the configured regions"
            )
        taken.add(ip)
        observers.append(
            Node(
                ip=ip,
                region=region,
                port=net.listen_port,
                asn=table.asns[region],
                country=table.countries[region],
                owner=None,
                kind="observer",
            )
        )

    home: list[int] = []
    mine = {owner: index for index, owner in enumerate(owners)}
    for index in range(len(pop.entities)):
        found = mine.get(index)
        home.append(rng.randrange(n_peers) if found is None else found)

    outbound = _peers(cfg, nodes, table, rng)
    watched = [NO_OBSERVER] * len(nodes)
    reach = min(len(nodes), round(net.observer_fraction * len(nodes)))
    for node in rng.sample(range(len(nodes)), reach):
        # Drawn per node rather than round robin: node indices run in entity-type order, so
        # dealing observers out in sequence would make `observer_id` a proxy for entity type.
        watched[node] = rng.randrange(net.n_observers)
    # A monitored node spends one of its eight outbound slots on the observer, so it has one
    # fewer ordinary peer. Adding a ninth connection instead would make the monitored quarter of
    # the network measurably better connected than the rest.
    peers = [
        adjacent[:-1] if flag != NO_OBSERVER else adjacent
        for adjacent, flag in zip(outbound, watched, strict=True)
    ]
    reverse: list[list[int]] = [[] for _ in nodes]
    for source, adjacent in enumerate(peers):
        for target in adjacent:
            reverse[target].append(source)
    return Topology(
        nodes=tuple(nodes),
        observers=tuple(observers),
        outbound=tuple(tuple(a) for a in peers),
        inbound=tuple(tuple(a) for a in reverse),
        watched=tuple(watched),
        home=tuple(home),
        tor_exits=tuple(infra[TOR_EXIT]),
        vpn_nodes=tuple(infra[VPN]),
    )


def _broadcast(cfg: Config, run: Run, rng: random.Random) -> list[int]:
    """When each transaction was first sent, which is before the block that confirmed it.

    Drawn inside the interval preceding confirmation rather than from a transaction's position
    within its block. Position is not observable, and it is not random either: campaign
    transactions are built after the ordinary traffic of the same block, so a timestamp derived
    from position would let a model recognise a campaign by its place in the file.

    A child is then pushed after its parent. The ledger allows spending an output created in the
    same block, so this ordering has to be imposed rather than assumed, and creation order is a
    valid topological order to impose it in.
    """
    interval = int(cfg.chain.block_interval_s * 1_000_000)
    opens: dict[int, int] = {}
    previous = run.blocks[0].time_us - interval
    for block in run.blocks:
        opens[block.height] = previous
        previous = block.time_us
    sent: dict[str, int] = {}
    out: list[int] = []
    for tx in run.txs:
        if tx.is_coinbase:
            # A coinbase does not exist before its block, so it is seen with the block.
            when = tx.time_us
        else:
            start = opens[tx.height]
            when = start + rng.randrange(max(1, tx.time_us - start))
            for parent, _ in tx.inputs:
                earlier = sent.get(parent)
                if earlier is not None and earlier >= when:
                    when = earlier + 1
        sent[tx.txid] = when
        out.append(when)
    return out


def _flood(
    topo: Topology, cfg: Config, table: Regions, rng: random.Random, origin: int, start_us: int
) -> tuple[list[int], dict[int, int]]:
    """Relay the transaction outward, returning the earliest arrival at each node reached.

    Dijkstra, not a breadth-first sweep. With an independent delay on every link the node that
    hears first is not the node fewest hops away, and that is the point: a peer two hops from
    the origin down two fast links beats a direct peer whose timer happened to draw long.

    Expansion stops at `flood_frontier` nodes, and that bound is nearly free rather than a
    corner cut. Only the earliest arrival at each observer is ever recorded, and the node that
    gets there first is by definition an early one, so the nodes the frontier drops are ones
    whose announcements would have been discarded as duplicates.

    ponytail: the frontier's cost is linear and its effect on the recorded rows is measurable.
    `tests/test_network.py` asserts that doubling it barely moves the first-seen rate, which is
    the check that the bound is still in the harmless regime for a given topology.
    """
    net = cfg.network
    outward = net.relay_delay_outbound_us
    inward = net.relay_delay_inbound_us
    best: dict[int, int] = {origin: start_us}
    queue: list[tuple[int, int]] = [(start_us, origin)]
    order: list[int] = []
    while queue and len(order) < net.flood_frontier:
        when, node = heapq.heappop(queue)
        if best[node] < when:
            continue
        order.append(node)
        region = topo.nodes[node].region
        for peers, mean in ((topo.outbound[node], outward), (topo.inbound[node], inward)):
            for peer in peers:
                # Independent per peer and per transaction. Nothing is cached and nothing is
                # shared: this single draw is what stops the capture being a sorted cascade.
                arrive = (
                    when
                    + int(rng.expovariate(1.0 / mean))
                    + table.link_us(region, topo.nodes[peer].region, rng)
                )
                if arrive < best.get(peer, arrive + 1):
                    best[peer] = arrive
                    heapq.heappush(queue, (arrive, peer))
    return order, best


def _announce(
    topo: Topology,
    cfg: Config,
    table: Regions,
    rng: random.Random,
    order: list[int],
    learn: dict[int, int],
    deadline: int,
) -> list[tuple[int, int, int]]:
    """What each observer recorded for this transaction, as (observer, node, arrival).

    Every monitored node that heard the transaction starts its own timer and eventually
    announces it, but an observer records only the announcement that told it something it did
    not already know. Once it has the transaction the rest are duplicates it already holds, and
    a node that has been told the observer holds it cancels its pending announcement anyway.
    One row per observer per transaction is therefore the whole of what a listening node learns,
    and it is exactly the observation the attribution literature works from: which peer, of the
    ones watching, spoke first.

    The consequence is that rows per transaction are bounded by the number of observers rather
    than by how much of the network they watch. Coverage decides how often the first speaker is
    the originator; it does not decide how many rows there are.

    `deadline` is the moment the transaction's block was mined. An announcement that would have
    arrived at or after it is dropped, because a node that already has the transaction in a
    block does not relay it as a loose transaction: it relays the block. An observer whose only
    announcement falls past the deadline therefore records nothing for this transaction, and
    that is the honest outcome rather than a gap to fill.
    """
    net = cfg.network
    heard: dict[int, tuple[int, int]] = {}
    for node in order:
        which = topo.watched[node]
        if which == NO_OBSERVER:
            continue
        # Independent per peer and per transaction, like every other relay decision.
        fires = learn[node] + int(rng.expovariate(1.0 / net.relay_delay_outbound_us))
        arrive = fires + table.link_us(topo.nodes[node].region, topo.observers[which].region, rng)
        if arrive >= deadline:
            continue
        first = heard.get(which)
        if first is None or arrive < first[0]:
            heard[which] = (arrive, node)
    return [(which, node, arrive) for which, (arrive, node) in heard.items()]


def build(cfg: Config, run: Run, rng: random.Random) -> Network:
    """Propagate every transaction and record what the observers received. Deterministic.

    Evasion is a choice about where a transaction enters the network, so it is one draw per
    transaction against the two configured shares. A Tor exit and a VPN node are ordinary graph
    members that relay like anything else, and either may itself be monitored, so hiding behind
    one is a strong defence rather than a guaranteed one.

    Coinbase transactions never enter this loop. A coinbase is created by the miner inside the
    block that contains it and is never relayed as a loose transaction, so a capture holding
    coinbase announcements is holding rows that could not exist. They have no originating peer
    either, which is why `origins` covers the announced transactions and nothing else.
    """
    net = cfg.network
    table = run.population.regions
    topo = _topology(cfg, run.population, rng)
    times = _broadcast(cfg, run, rng)
    capture = Capture()
    origins: list[Origin] = []
    vpn_edge = net.tor_share + net.vpn_share
    for index, tx in enumerate(run.txs):
        if tx.is_coinbase:
            continue
        pick = rng.random()
        used_tor = pick < net.tor_share and bool(topo.tor_exits)
        used_vpn = net.tor_share <= pick < vpn_edge and bool(topo.vpn_nodes)
        if used_tor:
            node = topo.tor_exits[rng.randrange(len(topo.tor_exits))]
        elif used_vpn:
            node = topo.vpn_nodes[rng.randrange(len(topo.vpn_nodes))]
        else:
            node = topo.home[tx.sender]
        order, learn = _flood(topo, cfg, table, rng, node, times[index])
        watchers: dict[int, None] = {}
        for which, source, arrive in _announce(
            topo, cfg, table, rng, order, learn, deadline=tx.time_us
        ):
            capture.tx_index.append(index)
            capture.src_node.append(source)
            capture.observer.append(which)
            capture.time_us.append(arrive)
            capture.is_inv.append(rng.random() < net.inv_share)
            watchers[which] = None
        origins.append(
            Origin(
                tx_index=index,
                node=node,
                entity=tx.sender,
                broadcast_us=times[index],
                used_tor=used_tor,
                used_vpn=used_vpn,
                observed_by_n=len(watchers),
            )
        )
    _sort(capture)
    return Network(topology=topo, origins=tuple(origins), capture=capture)


def _sort(capture: Capture) -> None:
    """Put the rows in the order a packet capture would have them: ascending by arrival.

    Ties break on transaction and then on announcing node so the file is a function of the seed
    and not of dictionary iteration. Two announcements can share a microsecond.
    """
    order = sorted(
        range(len(capture)),
        key=lambda i: (capture.time_us[i], capture.tx_index[i], capture.src_node[i]),
    )
    capture.tx_index = [capture.tx_index[i] for i in order]
    capture.src_node = [capture.src_node[i] for i in order]
    capture.observer = [capture.observer[i] for i in order]
    capture.time_us = [capture.time_us[i] for i in order]
    capture.is_inv = [capture.is_inv[i] for i in order]
