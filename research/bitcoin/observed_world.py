"""Reusable in-memory P2P-world adapter; simulator answer keys returned separately for research."""

from __future__ import annotations

import hashlib
import random
from pathlib import Path

import polars as pl
from buddhi_world_transfer import activity
from jaal_partition_transfer import observable_shape
from jaal_seed_transfer import frame_from_run

from chakravyuh.mayajaal import adversary, chain, config, network
from chakravyuh.setu import normalise
from chakravyuh.setu.enrich import Enricher


def generate(seed):
    cfg = config.load(
        Path("data/generated/agency-v2/config.effective.json"), seed=seed, anchor=Path(".")
    )
    adv = adversary.Adversary(cfg, random.Random(seed + 1))
    run = chain.generate(cfg, random.Random(seed), adv.plan)
    net = network.build(cfg, run, random.Random(seed + 2))
    cap, nodes = net.capture, net.topology.nodes
    ann = pl.DataFrame(
        {
            "row_id": range(len(cap)),
            "txid": [run.txs[i].txid for i in cap.tx_index],
            "peer_ip": [nodes[i].ip for i in cap.src_node],
            "observer_ip": [net.topology.observers[i].ip for i in cap.observer],
            "seen_us": cap.time_us,
        }
    )
    ips = (
        pl.DataFrame(
            {
                "peer_ip": [nodes[i].ip for i in cap.src_node],
                "asn": [nodes[i].asn for i in cap.src_node],
            },
            schema={"peer_ip": pl.String, "asn": pl.Int32},
        )
        .group_by("peer_ip")
        .agg(pl.col("asn").drop_nulls().first())
    )
    facts = normalise.peer_facts(sorted(ann["peer_ip"].unique().to_list()), Enricher())
    peers = ips.join(facts, on="peer_ip").select(
        "peer_ip", pl.coalesce("asn", "v_asn").alias("asn"), "net_class"
    )
    tx, addresses, owners = frame_from_run(run)
    tx = (
        observable_shape(tx)
        .with_columns(
            pl.col("output_amounts").list.sum().alias("total_out_sats"),
            pl.Series("fee_rate_sat_vb", [t.fee_sats / t.vsize_vb for t in run.txs]),
        )
        .drop("first_seen_us")
        .join(ann.group_by("txid").agg(pl.col("seen_us").min().alias("first_seen_us")), on="txid")
    )
    seen = (
        tx.select(
            "first_seen_us", pl.concat_list("input_addresses", "output_addresses").alias("address")
        )
        .explode("address")
        .drop_nulls("address")
        .group_by("address")
        .agg(pl.col("first_seen_us").min())
    )
    addresses = addresses.drop("first_seen_us").join(seen, on="address")
    labels = pl.DataFrame({"address": list(owners), "owner": list(owners.values())})
    campaigns = pl.DataFrame(
        [
            {
                "txids": c.txids,
                "entity_ids": [run.population.entities[i].entity_id for i in c.participants],
            }
            for c in adv.records()
        ],
        schema={"txids": pl.List(pl.String), "entity_ids": pl.List(pl.String)},
    )
    metadata = {
        "seed": seed,
        "observed_transactions": tx.height,
        "announcements": ann.height,
        "observers": len(net.topology.observers),
        "observed_txid_sha256": hashlib.sha256(
            "\n".join(sorted(tx["txid"].to_list())).encode()
        ).hexdigest(),
    }
    return tx, addresses, ann, peers, labels, activity(tx, labels, campaigns), metadata
