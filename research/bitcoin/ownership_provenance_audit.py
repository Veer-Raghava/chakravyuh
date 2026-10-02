"""Compare event-ledger snapshots against true prefix rebuilds on the canonical world."""

from __future__ import annotations

import time
from pathlib import Path

import polars as pl
from common import digest, log, save
from polars.testing import assert_frame_equal

from chakravyuh.jaal import cluster, provenance


def main() -> None:
    started = time.perf_counter()
    source = Path("data/generated/agency-v2/normalised/transactions.parquet")
    transactions = pl.read_parquet(source)
    ledger = provenance.ownership_evidence(transactions)
    first = int(transactions["first_seen_us"].min())
    last = int(transactions["first_seen_us"].max())
    results = []
    for fraction in (0.25, 0.45, 0.60, 0.70, 1.0):
        cutoff = first + int((last - first) * fraction)
        snapshot = provenance.snapshot_edges(ledger, cutoff)
        prefix = cluster.same_owner_edges(transactions.filter(pl.col("first_seen_us") <= cutoff))
        columns = [name for name in prefix.columns if name != "ts_us"]
        assert_frame_equal(
            snapshot.select(columns).sort("src", "dst"),
            prefix.select(columns).sort("src", "dst"),
        )
        partitions = {}
        for threshold in (0.2, 0.3):
            parts = cluster.components(snapshot, threshold)
            assert parts == cluster.components(prefix, threshold)
            partitions[str(threshold)] = {
                "clusters": len(parts),
                "linked_addresses": sum(map(len, parts)),
            }
        results.append(
            {
                "fraction": fraction,
                "cutoff_us": cutoff,
                "claims_available": ledger.filter(pl.col("available_us") <= cutoff).height,
                "deduplicated_edges": snapshot.height,
                "prefix_claim_parity": True,
                "partitions": partitions,
            }
        )
    result = {
        "run": "agency-v2",
        "ledger_rows": ledger.height,
        "unique_pairs": ledger.select("src", "dst").unique().height,
        "repeated_pair_claims": ledger.height - ledger.select("src", "dst").unique().height,
        "missing_timestamps": ledger["available_us"].null_count(),
        "missing_txids": ledger["txid"].null_count(),
        "snapshots": results,
        "seconds": time.perf_counter() - started,
        "hashes": {
            str(path): digest(path)
            for path in (source, Path(__file__), Path(provenance.__file__), Path(cluster.__file__))
        },
        "limitations": [
            "first_seen_us assumes the full transaction body is available at first observation",
            "heuristic weights remain uncalibrated; provenance does not correct false links",
            "stage defaults unchanged; BUDDHI still requires explicit snapshot integration",
        ],
    }
    output = Path("research/bitcoin/results/ownership-provenance-audit.json")
    save(output, result)
    log("ownership_provenance_audit_complete", output=str(output), production_changes=True)


if __name__ == "__main__":
    main()
