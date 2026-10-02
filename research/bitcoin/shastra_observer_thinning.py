"""Paired capture-thinning stress: frozen source model, nested active observer subsets."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import joblib
import polars as pl
from causal_origin_benchmark import transaction_results
from common import digest, log
from shastra_world_transfer import label, predict

from chakravyuh.shastra import causal


def main():
    out = Path("research/bitcoin/results/shastra-observer-thinning")
    out.mkdir(parents=True, exist_ok=False)
    root = Path("data/generated/agency-v2/normalised")
    ann = pl.read_parquet(root / "announcements.parquet")
    peers = pl.read_parquet(root / "peers.parquet")
    transactions = pl.read_parquet(root / "transactions.parquet")
    truth = pl.read_parquet("ground_truth/agency-v2/origins.parquet").select(
        "txid", pl.col("true_origin_ip").alias("origin_peer_ip"), "true_origin_asn"
    )
    bundle_path = Path(
        "research/bitcoin/results/shastra-world-transfer/frozen-canonical-lightgbm.joblib"
    )
    bundle = joblib.load(bundle_path)
    observers = sorted(
        ann["observer_ip"].unique().to_list(), key=lambda x: hashlib.sha256(x.encode()).hexdigest()
    )
    assert len(observers) == 48
    full_times = ann.group_by("txid").agg(pl.col("seen_us").min().alias("first_seen_us"))
    boundary = int(full_times["first_seen_us"].min()) + int(
        (int(full_times["first_seen_us"].max()) - int(full_times["first_seen_us"].min())) * 0.7
    )
    baseline_ids = set(full_times.filter(pl.col("first_seen_us") >= boundary)["txid"].to_list())
    log(
        "observer_thinning_preregistered",
        active_observers=[48, 24, 8],
        subset="nested SHA256 order of IP strings",
        frozen_policy=bundle["threshold"],
        boundary_us=boundary,
        consumed_canonical_capture=True,
    )
    results = []
    for n in (48, 24, 8):
        start = time.perf_counter()
        capture = ann.filter(pl.col("observer_ip").is_in(observers[:n]))
        observed = causal.candidates(capture, peers, transactions, n_observers=n)
        # No original-capture histories are supplied to the causal feature routine.
        frame = label(observed, truth)
        tx = transaction_results(frame, predict(frame, bundle)).filter(
            pl.col("txid").is_in(baseline_ids)
        )
        answered = tx.filter(
            (pl.col("legacy_separation") >= bundle["threshold"])
            & (pl.col("n_observers_in_tx") >= 2)
            & ~pl.col("any_tor")
        )
        absent = answered.filter(pl.col("source_present") == 0)
        present = answered.filter(pl.col("source_present") == 1)
        report = dict(
            active_observers=n,
            capture_rows=capture.height,
            full_capture_test_transactions=len(baseline_ids),
            observed_test_transactions=tx.height,
            lost_test_transactions=len(baseline_ids) - tx.height,
            source_present_fraction=float(tx["source_present"].mean()),
            policy_answers=answered.height,
            policy_correct=int(answered["weighted_hit"].sum()),
            policy_precision=float(answered["weighted_hit"].mean()) if answered.height else None,
            coverage_of_full_capture_test=answered.height / len(baseline_ids),
            absent_source_answers=absent.height,
            absent_source_correct=int(absent["weighted_hit"].sum()),
            present_source_answers=present.height,
            present_source_correct=int(present["weighted_hit"].sum()),
            seconds=time.perf_counter() - start,
        )
        tx.write_parquet(out / f"observers{n}-tx-scores.parquet", compression="zstd")
        (out / f"observers{n}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        results.append(report)
        log("observer_thinning_case_complete", **report)
    assert results[0]["policy_answers"] == 486 and results[0]["policy_correct"] == 459
    report = dict(
        results=results,
        source_sha256=digest(__file__),
        bundle_sha256=digest(bundle_path),
        selected_observers=observers,
        limitations=[
            "Post-capture thinning, not new propagation or placement simulation.",
            "Canonical consumed world; not independent generalization evidence.",
            "Baseline uses captured test transactions, not all generated transactions.",
            "Peer metadata stays available as supplied registry facts.",
            "Source absence truth is used only for diagnostic evaluation, never policy decisions.",
            "Full-capture membership fixes evaluation cohort; selection remains causal.",
        ],
    )
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
