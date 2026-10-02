"""Run the portable engine and real evidence queues, then evaluate held-out lead yield."""

import json
import time
from pathlib import Path

import polars as pl
from buddhi_world_transfer import windows
from common import digest, log

from chakravyuh.vaani.investigation import run, select


def main():
    start = time.perf_counter()
    normalised = Path("data/generated/agency-v2/normalised")
    tx = pl.read_parquet(normalised / "transactions.parquet")
    root = Path("research/bitcoin/results/investigation-demo-v2")
    model = Path("research/bitcoin/results/relational-inference-artifacts/address")
    labels = (
        pl.read_parquet("ground_truth/agency-v2/entities.parquet")
        .select(pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address"))
        .explode("address")
    )
    owner_by_address = dict(labels.select("address", "owner").iter_rows())
    reference = pl.read_parquet(
        "research/bitcoin/results/relational-summary-controls/address/xgboost_distribution_features-scores.parquet"
    )
    metrics = []
    log(
        "investigation_demo_started",
        engine="address-rich-xgboost",
        windows=[7, 8, 9],
        selection_overlap=0.25,
        demo_preview_window=8,
        no_model_refit=True,
    )
    for i, (phase, left, right) in enumerate(windows(tx)):
        if phase != "test":
            continue
        queue = run(normalised, model, root / f"window{i}", start_us=left, end_us=right)
        scores = pl.read_parquet(root / f"window{i}/scores.parquet")
        # Reconstruct exact observable support for evaluation of identical policies.
        supports = {}
        for row in tx.filter(pl.col("first_seen_us").is_between(left, right)).iter_rows(named=True):
            for address in (*row["input_addresses"], *row["output_addresses"]):
                supports.setdefault("addr:" + address, set()).add(row["txid"])
        ranked = scores["subject_id"].head(2000).to_list()
        y = dict(reference.filter(pl.col("window_id") == i).select("subject_id", "y").iter_rows())
        for policy, overlap in [("score_only", None), ("evidence_diverse", 0.25)]:
            chosen = select(ranked, supports, k=20, overlap=overlap)
            owners = {owner_by_address[s.removeprefix("addr:")] for s in chosen if y[s]}
            metrics.append(
                dict(
                    window=i,
                    policy=policy,
                    returned=len(chosen),
                    positive_addresses=sum(y[s] for s in chosen),
                    distinct_positive_controllers=len(owners),
                )
            )
        # A fixed earlier-planned illustrative window, not chosen using new labels.
        if i == 8:
            fixture = dict(
                queue,
                preview=dict(
                    kind="synthetic research prototype",
                    window_id=8,
                    engine="329-feature graph-context XGBoost",
                    active_run_metrics=False,
                ),
            )
            dest = Path("apps/drishti-v2/src/data/fixtures/research-leads.json")
            dest.write_text(json.dumps(fixture, separators=(",", ":"), allow_nan=False) + "\n")
    report = dict(
        metrics=metrics,
        seconds=time.perf_counter() - start,
        source_sha256=digest(__file__),
        limitations=[
            "Consumed test windows; implementation replay, not new confirmation.",
            "Truth used after queue construction for evaluation only.",
            "Evidence diversity does not establish controller identity.",
            "UI preview is a fixed synthetic window, not the selected active application run.",
        ],
    )
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    log("investigation_demo_complete", report=str(root / "report.json"))


if __name__ == "__main__":
    main()
