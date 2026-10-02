"""Evaluate JAAL's existing peel-hop output rule against synthetic answer keys."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import polars as pl

from chakravyuh.jaal import trace
from common import digest, log, save


def run(run_id: str, out: Path):
    start = time.perf_counter()
    root = Path("data/generated") / run_id
    tx_path = root / "normalised/transactions.parquet"
    gt_path = Path("ground_truth") / run_id / "chain_txs.parquet"
    tx = pl.read_parquet(tx_path)
    gt = pl.read_parquet(gt_path)
    # Rename the answer-key column to prevent accidentally comparing JAAL's own
    # inferred `change_index` with itself after a same-name join.
    truth = gt.select(
        "txid", "entity_id", pl.col("change_index").alias("true_change_index")
    )
    observed = tx.select("txid", "output_addresses").join(truth, on="txid", how="inner")
    true_by_tx = {r["txid"]: r for r in observed.iter_rows(named=True)}
    sender_by_tx = dict(truth.select("txid", "entity_id").iter_rows())

    hops = trace.hops(tx)
    records = []
    for r in hops.iter_rows(named=True):
        answer = true_by_tx[r["txid"]]
        true_idx = answer["true_change_index"]
        true_address = (answer["output_addresses"][true_idx]
                        if true_idx is not None and true_idx >= 0 else None)
        records.append({
            "txid": r["txid"], "predicted_change_address": r["change_address"],
            "true_change_address": true_address,
            "correct": bool(true_address is not None and
                             r["change_address"] == true_address),
        })
    predicted_by_tx = {r["txid"]: r for r in records}
    tp = sum(r["correct"] for r in records)
    n_true_change_two_output = observed.join(
        tx.select("txid", "n_out"), on="txid", how="left"
    ).filter((pl.col("n_out") == 2) & (pl.col("true_change_index") >= 0)).height

    spenders = trace._spenders(tx, hops["change_address"])
    successors, _, stopped = trace._links(hops, spenders)
    chain_tp = 0
    for current, following in successors.items():
        record = predicted_by_tx.get(current)
        if (record is not None and record["correct"] and
                sender_by_tx.get(current) == sender_by_tx.get(following)):
            chain_tp += 1
    n_links = len(successors)

    result = {
        "run": run_id,
        "target": "exact synthetic change output address and same synthetic sender across a tracer successor",
        "rule": "two outputs, non-equal, smaller output <=35% of total; largest output selected as change; follow only unique spends to another hop",
        "transactions_with_true_change_and_two_outputs": n_true_change_two_output,
        "predicted_hops": hops.height,
        "correct_predicted_change_addresses": tp,
        "candidate_precision": tp / hops.height if hops.height else None,
        "recall_within_true_change_two_output_transactions": tp / n_true_change_two_output if n_true_change_two_output else None,
        "successor_links": n_links,
        "correct_same_sender_successor_links": chain_tp,
        "successor_precision": chain_tp / n_links if n_links else None,
        "coverage_of_all_true_change_two_output_transactions": chain_tp / n_true_change_two_output if n_true_change_two_output else None,
        "stopped_hops": len(stopped),
        "hashes": {str(p): digest(p) for p in [tx_path, gt_path]},
        "elapsed_seconds": time.perf_counter() - start,
        "limitations": [
            "Retrospective full-run diagnostic; not a fixed historical snapshot.",
            "Synthetic answer-key behavior; not external wallet ground truth.",
            "Point estimates treat correlated transactions as independent counts.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    save(out / "peel-audit.json", result)
    log("jaal_peel_audit_complete", run=run_id, out=str(out), seconds=result["elapsed_seconds"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="agency-v2")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.run, args.out)
