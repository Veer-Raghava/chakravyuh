# MAYAJAAL · the data generator

Named for an illusory world. It builds the dataset nobody has, and its correctness is the
foundation under every number this project ever prints.

## Why this is a real deliverable and not scaffolding

Chain analytics datasets exist and some are excellent. Network measurement studies exist.
**No public dataset has both layers with a label saying which peer actually originated each
transaction.** That is precisely why origin estimation is unsolved in the open literature,
and it is why we cannot skip this.

The methodology is established in adjacent work. IBM built AMLSim and released the AMLworld
datasets, and their NeurIPS 2023 paper argues that synthetic data is better than real data
for benchmarking anti money laundering models, because ground truth labels are complete
while most real laundering is never detected and therefore never labelled. Tide, 2026, is an
open source generator on the same reasoning. We are doing standard practice in a field where
the labels do not exist any other way.

## Two modes, one output contract

```
mayajaal --source synthetic  --txs 100000 --seed 42 --out data/generated/run-A
mayajaal --source real-slice --graph vendor/btc-graph/ --txs 100000 --seed 42 --out run-B
```

Byte-identical column sets from both. Nothing downstream knows which produced its input.

**Synthetic mode** builds the whole world, chain layer included. It is the default, it works
offline forever, it has no licence question, and it is the only mode where you can turn a
knob and ask what happens. You need that to write honest numbers.

**Real slice mode** takes the chain layer from a real published Bitcoin transaction graph and
synthesises only the network layer on top. The candidate source is the *Nature Scientific
Data* dataset behind arXiv 2411.10325, 252 million nodes and 785 million edges over about
thirteen years and roughly 670 million transactions, with two labelled subsets, one of about
34,000 labelled nodes. ORBITAAL, also in *Nature Scientific Data*, is an alternative with
entity to entity temporal graphs from 2009 to 2021.

Why both. Synthetic mode is how we measure. Real slice mode is how we answer the one attack
that actually lands on a synthetic benchmark: *you invented the data and then solved your own
invention*. In real slice mode the half we did not invent is real, peer reviewed and citable,
and the only synthesised half is the half that does not exist anywhere for anyone.

Before real slice mode is used for anything published, two things must be recorded in
`docs/DECISIONS.md`: the licence line copied from the source record with the date checked,
and the exact sampling parameters. If the licence does not clearly permit redistribution, the
real slice stays local for measurement and only synthetic data is committed or shipped.

## Layer 1 · The entity world

A population, not a list of addresses. This is what makes the awkward cases real rather than
injected.

| Type | Share | Behaviour that must be visible in the data |
|---|---|---|
| `individual` | ~55% | Few transactions, small values, long dwell, one or two addresses reused |
| `merchant` | ~12% | Many small inbound, periodic consolidation outbound |
| `exchange` | ~4% | Very high degree, hot wallet consolidation, huge address count, many counterparties |
| `mining_pool` | ~1% | Coinbase origination, regular payout cadence, high fan out, long dwell |
| `service` | ~8% | Gambling or payment processor, high volume, medium degree |
| `mixer` | ~2% | Equal value outputs, uniform amounts, high fan out then fan in |
| `darknet_market` | ~2% | Many small inbound from many entities, batched withdrawal |
| `ransomware` | ~1% | Bursty large inbound to a fresh address, rapid onward movement |
| `scam` | ~3% | Many inbound in a short window, then a single sweep |
| `mule` | ~12% | Short lived, receives once, forwards nearly everything, near zero final balance |

Each entity gets a wallet, being a set of addresses with a reuse policy and a change policy,
and a network presence:

- one or more IPs, with `behind_cgnat` true for a configurable share of individuals and mules
- an ASN and country drawn from a weighted table, with an India weight you can raise so the
  demo has domestic leads in it
- a `net_class` of `residential`, `mobile`, `hosting`, `vpn` or `tor`
- an online schedule, because an entity that transacts at a uniform rate around the clock is
  a giveaway that the data is fake

`behind_cgnat` matters more than its size suggests. Two different entities sharing one public
IP on different source ports is the case that proves why `src_port` is in the problem
statement schema, and the fixture set must contain it.

## Layer 2 · The chain, as a real UTXO ledger

Not a random graph with amounts sprinkled on it. An actual ledger, because half the awkward
cases we need only emerge from the accounting.

State is a UTXO set: `(txid, vout) -> (address, sats, height)`. Blocks arrive on an
exponential inter-arrival with mean 600 seconds. Each block pays a coinbase to a pool weighted
by hashrate share.

To build one transaction: pick an entity by its activity schedule, decide an amount from that
entity type's value distribution, select inputs from its own UTXOs by a coin selection policy,
compute a fee from a fee rate distribution multiplied by an estimated vsize, create the
payment output and a change output when there is a remainder above the dust threshold, then
assign addresses according to the entity's reuse policy.

Five things this must get right, because each one is a case our own heuristics depend on.

**Value conservation.** Inputs equal outputs plus fee, exactly, in integer satoshis. A
generator that is off by a satoshi anywhere will teach a model to detect the generator.

**Change addresses that are actually findable.** The change heuristic is one of our detection
tools, so the generator must produce change the way real wallets do, meaning a fresh address
of the same script type as the inputs, usually not the round-numbered output, and it must
record `change_index` in ground truth so the heuristic can be scored rather than assumed.

**Multi-input transactions.** The common input ownership heuristic only has something to find
when entities genuinely spend several of their own UTXOs together. Coin selection must produce
multi-input spends at a realistic rate, and it must occasionally produce a collaborative
multi-input transaction that violates the heuristic, because that violation is the reason the
measured precision is 0.36 and not 0.9.

**Heavy tailed values.** A log-normal or truncated power law for value, and a separate
distribution for fee rate. Never a normal distribution. A validator check asserts the tail.

**Address reuse.** A mix of single use and heavily reused addresses. Exchanges reuse a hot
wallet. Individuals sometimes reuse and sometimes do not.

## Layer 3 · The network, which is the part that matters

This is where the dataset becomes something no one else has, so it gets the most care.

**Topology.** Build a peer graph over `n_nodes` reachable nodes, default 5,000. Each node
opens `8` outbound connections and accepts inbound up to a cap, which is Bitcoin Core's
default and is the reason nine announcing peers is the canonical number in our deck: the
originator plus its eight outbound neighbours is the first wave anyone sees. Outbound peer
selection is weighted by latency and by address bucket, not uniform, because real peer
selection is not uniform and the resulting graph has different propagation behaviour.

**Latency.** A region to region base latency matrix in milliseconds, plus per link jitter.
Nodes in the same region are tens of milliseconds apart, across continents a few hundred.

**Relay timing, and this is the crucial detail.** A node does not forward a transaction the
instant it learns of it. Bitcoin Core queues the announcement and sends it after an
independently drawn Poisson delay per peer, deliberately, as a privacy measure. Defaults to
start from: mean 2 seconds toward outbound peers and mean 5 seconds toward inbound peers,
drawn independently for every peer and every transaction.

That single mechanism is why this problem is hard and why our approach is the right one.
First-seen order is noisy, not merely delayed, so a naive first-spy guess is weak. What
survives the noise is the aggregate: which peer is early *across many observations*, how
tightly the announcement times cluster, and which of our observers saw nothing. If the
generator emitted a clean sorted cascade instead, our estimator would look brilliant and
would be worthless. The validator explicitly tests that the delay pattern is not a clean
cascade.

**Observers, and the honesty knob.** We do not see the network. We run `n_observers` listening
nodes, default 16, each connected to a random subset of peers, and **we record only
announcements that reach one of our observers**. `observer_fraction` is the share of the
network our observers are peered with, and it is the single most important parameter in this
project. Origin inference accuracy is almost entirely a function of it, which is why
published success rates for originating IP inference span 11% to 60% depending on observer
stealth and reach, and why our evaluation reports a curve over this parameter instead of one
number.

Default sweep for evaluation: `0.02, 0.05, 0.10, 0.25, 0.50`.

**Evasion.** A configurable share of transactions is broadcast through Tor, meaning the
observed peer is a Tor exit and origin estimation should abstain, or through a VPN or hosting
provider, meaning the peer IP is real but attribution stops at the provider. Ground truth
records which. These are not adversarial extras, they are why the tool must be able to say
"I cannot answer this one".

## Layer 4 · The adversary, as agents rather than as patterns

Do not stamp typology shapes into the graph. Give bad actors goals and let the shapes emerge,
because a stamped pattern is detectable by the stamp and an emergent one is not.

Each campaign has a source of illicit funds, an amount, a deadline, a risk appetite and a
target, usually an exchange deposit address. The agent then composes moves:

| Move | What it does | Emergent signature |
|---|---|---|
| `peel` | Send a small slice onward, keep the remainder as change, repeat | Long chain, decreasing balance, similar slice sizes |
| `split` | Fan out across many fresh addresses | High out-degree, low value per output |
| `merge` | Consolidate several addresses into one | High in-degree, multi-input |
| `mix` | Equal value outputs among unrelated inputs | `has_equal_outputs`, uniform amounts |
| `hop` | Move immediately on receipt | Very short dwell time |
| `structure` | Keep every transfer under a threshold | Value distribution clipped just below a round number |
| `dwell` | Wait to break temporal correlation | Long gap between receive and spend |
| `cash_out` | Deposit to an exchange | Terminal edge into a high degree entity |

A campaign is a sequence of these chosen against its risk appetite, so a cautious campaign
peels and dwells and a hurried one hops and cashes out. The ground truth records the campaign,
its moves in order, and every txid involved, which lets us score detection at campaign level
rather than only transaction level. Campaign level recall is the number an investigator
actually cares about, because catching one transaction in a chain of forty is catching the
chain.

Keep the illicit share small. Default 0.6% of transactions and about 3% of entities. A
balanced dataset would make every metric meaningless and would hide the imbalance problem that
Slide 4 exists to answer.

## Layer 5 · Export

```
data/generated/<run_id>/
  capture/           part-0000.csv.zst …          the PS schema, sharded
  capture_json/      part-0000.jsonl.zst          same rows, for the JSON path
  capture_xml/       sample.xml                   small only, to prove the XML reader works
  ground_truth/      origins, entities, campaigns  .parquet
  validation/        report.json, report.md, plots/
  run_config.json    every parameter and the seed
```

Sharding is not a detail. It is what makes a one million row run resumable and what lets the
demo load instantly from a precomputed run. Shard on time so that a shard is a coherent slice.

XML is deliberately a small sample, not the full run. The problem statement asks the tool to
accept XML, and it must, but nobody should ever generate a million rows of XML and neither
should we pretend to.

Row count arithmetic to keep in mind: with a mean of nine announcements per transaction,
1,000,000 rows is about 111,000 transactions. Target row counts, not transaction counts, when
someone asks for a size.

## Layer 6 · Validation, which is the part that protects us

`make validate-data` writes `validation/report.json` and a readable `report.md`. The
`truth-checker` subagent reads it and reports only what is wrong.

**Hard invariants.** Value conservation per transaction. No negative fee. Every input spends an
existing unspent output as of that height. Every txid has at least one announcement. Exactly
one true originator per txid. Per peer announcement times non-decreasing. No ground truth
column name present in any observable file.

**Distribution checks against published behaviour.** Heavy tailed value distribution.
Announcements per txid centred near the configured mean. Inter-announcement delays consistent
with independent per peer Poisson draws rather than a sorted cascade. Block intervals
approximately exponential with mean 600 seconds. Address graph degree distribution heavy
tailed.

**Leakage checks, and these are the ones that matter most.** For each of these trivial rules,
report how often it identifies the true originator: always the first announcement seen, always
the numerically lowest IP, always the peer with the most announcements, always the first row in
file order. Then train a depth-2 decision tree on observable columns alone and report its
accuracy at predicting the originator.

If any trivial rule scores high, the dataset is broken. Note carefully that "first announcement
seen" is *supposed* to be somewhat predictive, since that is the real first-spy signal, but if
it scores near 1.0 then the relay delays are not doing their job and the whole benchmark is
fake. The acceptance band for that specific rule sits between roughly 0.15 and 0.6 at default
observer fraction, which is where the published range for real networks sits. Outside that
band, fix the generator before trusting a single downstream number.

## Parameters

Everything below lives in `run_config.json`, nothing is hardcoded, and every default is a
starting point to be tuned against the validator rather than a fact.

```yaml
seed: 42
target_rows: 1000000            # rows, not transactions
mean_announcements_per_tx: 9

world:
  n_entities: 20000
  illicit_entity_share: 0.03
  illicit_tx_share: 0.006
  cgnat_share_individuals: 0.35
  india_weight: 0.25            # raise for a domestically relevant demo

chain:
  block_interval_s: 600         # exponential
  value_dist: lognormal
  fee_rate_dist: lognormal
  dust_threshold_sats: 546
  multi_input_rate: 0.35
  address_reuse_rate: 0.30

network:
  n_nodes: 5000
  outbound_per_node: 8          # Bitcoin Core default
  max_inbound: 125
  relay_delay_outbound_mean_s: 2.0    # independent Poisson draw per peer per tx
  relay_delay_inbound_mean_s: 5.0
  latency_matrix: regions.yaml
  n_observers: 16
  observer_fraction: 0.10       # the number that decides everything
  tor_share: 0.04
  vpn_share: 0.08

adversary:
  n_campaigns: 120
  moves_per_campaign: [3, 40]
  risk_appetite_dist: uniform

export:
  shard_rows: 250000
  formats: [csv, jsonl]
  xml_sample_rows: 500
```

## The one intellectual risk, stated plainly

A generator we wrote, feeding an estimator we wrote, proves nothing on its own. This is the
strongest possible criticism of this whole approach and it deserves a real answer rather than a
disclaimer. Four defences, all of which are work rather than words:

**One. Parameter holdout.** Train and tune on one regime, evaluate on another. Different
topology seed, different latency matrix, different relay delay means, different observer
fraction. If accuracy collapses when the parameters move, we learned the generator, not the
problem, and we need to know that before a judge finds it.

**Two. Real chain topology.** Real slice mode removes half the invention. Report the estimator
on both and put both numbers in the eval report.

**Three. Report the curve, never the point.** Accuracy as a function of observer fraction,
reported separately for clear, VPN and Tor traffic. A curve that behaves the way the published
literature says real networks behave is evidence. A single high number is not.

**Four. Chain-layer models validated against real labelled data.** The wallet risk model is
cross-checked on the public Elliptic dataset, 203k nodes and 234k edges with 166 features, which
is real and independently labelled. If our model works there too, the chain half is not an
artifact of our world.

Write this section's conclusion on a slide and say it out loud in the viva before anyone asks.
A team that names the weakness in its own benchmark and shows the four things it did about it
is in a completely different category from a team that reports one accuracy figure.