"""Measure future JAAL links entering BUDDHI's chronologically split subjects."""

from __future__ import annotations

from collections import Counter
from math import comb
from pathlib import Path
from typing import Any

import polars as pl
from common import digest, save

from chakravyuh.eval import labels
from chakravyuh.jaal import cluster

RUN = "agency-v2"
ROOT = Path("data/generated") / RUN
OUT = Path("research/bitcoin/results/buddhi-jaal-sensitivity")


def _groups(frame: pl.DataFrame, addresses: set[str]) -> dict[str, str]:
    result = {address: address for address in addresses}
    for index, row in enumerate(frame.iter_rows(named=True)):
        group_id = f"cluster:{index}"
        for address in row["addresses"]:
            if address in addresses:
                result[address] = group_id
    return result


def _measure(
    threshold: float,
    tx: pl.DataFrame,
    observed: pl.DataFrame,
    full_edges: pl.DataFrame,
    boundary: int,
) -> dict[str, Any]:
    early = set(observed.filter(pl.col("first_seen_us") < boundary)["address"].to_list())
    all_groups, _ = cluster.clusters(full_edges, threshold)
    early_edges = cluster.same_owner_edges(tx.filter(pl.col("first_seen_us") < boundary))
    early_groups, _ = cluster.clusters(early_edges, threshold)
    full_map = _groups(all_groups, early)
    early_map = _groups(early_groups, early)

    full_size = Counter(full_map.values())
    early_size = Counter(early_map.values())
    cells = Counter((full_map[a], early_map[a]) for a in early)
    full_pairs = sum(comb(n, 2) for n in full_size.values())
    early_pairs = sum(comb(n, 2) for n in early_size.values())
    shared_pairs = sum(comb(n, 2) for n in cells.values())
    future_added_pairs = full_pairs - shared_pairs
    impacted_addresses = sum(
        1 for address in early if full_size[full_map[address]] > early_size[early_map[address]]
    )

    full_with_late = 0
    early_members_in_full_late_clusters = 0
    for row in all_groups.iter_rows(named=True):
        members = set(row["addresses"])
        has_early = bool(members & early)
        has_late = bool(members - early)
        if has_early and has_late:
            full_with_late += 1
            early_members_in_full_late_clusters += len(members & early)

    return {
        "threshold": threshold,
        "n_early_addresses": len(early),
        "full_capture_non_singleton_clusters": all_groups.height,
        "early_only_non_singleton_clusters": early_groups.height,
        "early_addresses_in_full_clusters_later_grown_by_future_activity": impacted_addresses,
        "full_clusters_spanning_train_and_holdout_addresses": full_with_late,
        "early_addresses_in_spanning_clusters": early_members_in_full_late_clusters,
        "same_group_pairs_among_early_addresses_full_graph": full_pairs,
        "same_group_pairs_using_early_evidence_only": early_pairs,
        "pairs_supported_by_full_graph_but_not_early_evidence": future_added_pairs,
        "future_added_share_of_full_early_pairs": (
            future_added_pairs / full_pairs if full_pairs else 0.0
        ),
    }


def main() -> None:
    target = labels.wallet_labels(RUN, 0.7)
    if target is None:
        raise RuntimeError("training label door unavailable; boundary cannot be resolved")
    tx = pl.read_parquet(ROOT / "normalised/transactions.parquet")
    observed = pl.read_parquet(
        ROOT / "normalised/addresses.parquet", columns=["address", "first_seen_us"]
    )
    edges = pl.read_parquet(
        ROOT / "graph/edges.parquet",
        columns=["src", "dst", "kind", "confidence", "evidence", "ts_us"],
    )
    same_owner = edges.filter(pl.col("kind") == "SAME_OWNER")
    result = {
        "run": RUN,
        "boundary_us": target.boundary_us,
        "protocol_note": (
            "full-capture clusters are compared with clusters rebuilt only from "
            "pre-boundary transactions"
        ),
        "source_hashes": {
            "transactions": digest(ROOT / "normalised/transactions.parquet"),
            "addresses": digest(ROOT / "normalised/addresses.parquet"),
            "graph_edges": digest(ROOT / "graph/edges.parquet"),
        },
        "same_owner_edge_provenance": {
            "n_edges": same_owner.height,
            "n_edges_without_timestamp": same_owner["ts_us"].null_count(),
            "n_edges_without_transaction_id": "transaction_id" not in same_owner.columns,
        },
        "thresholds": [
            _measure(t, tx, observed, same_owner, target.boundary_us) for t in (0.2, 0.3)
        ],
        "interpretation": (
            "Any full-graph early-address pair absent from the early-only partition depends on "
            "at least one post-boundary link. The current BUDDHI stage uses full-capture cluster "
            "membership before assigning its time split, so these links can affect subject IDs, "
            "train labels, and early-window feature aggregation."
        ),
    }
    save(OUT / "buddhi-temporal-topology-audit.json", result)


if __name__ == "__main__":
    main()
