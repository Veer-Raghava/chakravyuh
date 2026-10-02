"""Research-only, same-capture SHASTRA feature-family ablation.

Uses the canonical MAYAJAAL answer key only through the eval label door for training, then uses
the held-out origins solely for aggregate metrics. It never writes production signals or metrics.
The intentionally global candidate aggregates mirror the current stage; this experiment measures
feature-family contribution under the existing protocol, not causal/forward-time validity.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import polars as pl

from chakravyuh.eval.labels import origin_labels
from chakravyuh.eval.split import boundary_us
from chakravyuh.shastra import estimate, features, schema

RUN = "agency-v2"
OUT = Path("research/bitcoin/results/shastra-feature-ablation/shastra-feature-ablation.json")
VARIANTS = {
    "full": schema.MODEL_FEATURES,
    "without_global_peer_payer": tuple(
        name
        for name in schema.MODEL_FEATURES
        if name not in {"peer_frac_rank_one", "peer_n_txids", "peer_degree", "payer_shared"}
    ),
    "timing_and_local_observation": (
        "delta_first_us",
        "rank_in_tx",
        "n_announcements",
        "n_observers_seen",
        "n_observers_blind",
        "announce_spread_us",
        "n_candidates",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metrics(
    scored: pl.DataFrame,
    truth: pl.DataFrame,
    peers: pl.DataFrame,
    asn_prior: pl.DataFrame,
    floors: tuple[float, ...],
) -> dict[str, object]:
    truth = truth.select("txid", "origin_peer_ip", "true_origin_asn")
    holdout = scored.join(truth, on="txid", how="inner")
    l0_first = holdout.sort(["txid", "p_origin", "peer_ip"], descending=[False, True, False])
    l0_top = l0_first.group_by("txid", maintain_order=True).first()
    txs = l0_top.select(
        "txid",
        (pl.col("peer_ip") == pl.col("origin_peer_ip")).alias("l0_hit"),
        "abstain",
    )
    l0_top1 = float(txs["l0_hit"].mean()) if txs.height else 0.0
    l0_top3_rows = l0_first.group_by("txid", maintain_order=True).head(3)
    l0_top3 = (
        l0_top3_rows.group_by("txid")
        .agg(pl.col("origin_peer_ip").first().is_in(pl.col("peer_ip")).alias("hit"))["hit"]
        .mean()
    )
    l1 = estimate.asn_rollup(
        scored,
        peers,
        asn_prior,
        margin_floor=0.04,
        estimator="ablation",
    )
    l1_eval = l1.join(truth, on="txid", how="inner").with_columns(
        (pl.col("origin_asn") == pl.col("true_origin_asn")).alias("hit")
    )
    acted = l1_eval.filter(~pl.col("abstain"))
    policy_curve = []
    for floor in floors:
        thresholded = (
            estimate.asn_rollup(scored, peers, asn_prior, margin_floor=floor, estimator="ablation")
            .join(truth, on="txid", how="inner")
            .with_columns((pl.col("origin_asn") == pl.col("true_origin_asn")).alias("hit"))
        )
        answered = thresholded.filter(~pl.col("abstain"))
        policy_curve.append(
            {
                "margin_floor": floor,
                "acted": answered.height,
                "coverage": float((~thresholded["abstain"]).mean()) if thresholded.height else 0.0,
                "precision_when_acted": float(answered["hit"].mean()) if answered.height else 0.0,
            }
        )
    asn_ranked = (
        scored.select("txid", "peer_ip", "p_origin")
        .join(peers.select("peer_ip", "asn"), on="peer_ip", how="left")
        .group_by("txid", "asn")
        .agg(pl.col("p_origin").sum().alias("mass"))
        .join(asn_prior.select("asn", pl.col("frac_rank_one").alias("prior")), on="asn", how="left")
        .with_columns((pl.col("mass") * pl.col("prior").fill_null(0.0)).alias("score"))
        .join(truth.select("txid", "true_origin_asn"), on="txid", how="inner")
        .sort(["txid", "score", "asn"], descending=[False, True, False])
    )
    l1_top3 = (
        asn_ranked.group_by("txid", maintain_order=True)
        .head(3)
        .group_by("txid")
        .agg(pl.col("true_origin_asn").first().is_in(pl.col("asn")).alias("hit"))["hit"]
        .mean()
    )
    return {
        "n_holdout_observed_transactions": txs.height,
        "l0_top1": l0_top1,
        "l0_top3": float(l0_top3 or 0.0),
        "l1_top1": float(l1_eval["hit"].mean()) if l1_eval.height else 0.0,
        "l1_top3": float(l1_top3 or 0.0),
        "l1_margin_policy_curve": policy_curve,
        "l1_coverage": float((~l1_eval["abstain"]).mean()) if l1_eval.height else 0.0,
        "l1_precision_when_acted": float(acted["hit"].mean()) if acted.height else 0.0,
        "l1_acted": acted.height,
    }


def main() -> None:
    started = time.perf_counter()
    run_dir = Path("data/generated") / RUN
    normalised = run_dir / "normalised"
    announcements = pl.read_parquet(
        normalised / "announcements.parquet", columns=list(features.ANNOUNCEMENT_COLUMNS)
    )
    peers = pl.read_parquet(
        normalised / "peers.parquet",
        columns=[*features.PEER_COLUMNS, "asn", "as_org", "net_class", "geo_country"],
    )
    transactions = pl.read_parquet(
        normalised / "transactions.parquet", columns=list(features.TRANSACTION_COLUMNS)
    )
    edges = pl.read_parquet(run_dir / "graph" / "edges.parquet", columns=["src", "dst"])
    arrival = pl.read_parquet(normalised / "arrival.parquet")
    prior = pl.read_parquet(normalised / "asn_rollup.parquet")
    labels = origin_labels(RUN, 0.7)
    if labels is None:
        raise RuntimeError("research answer key unavailable")
    candidates = features.candidates(announcements, peers, transactions, edges)
    candidates = estimate.attach_mle(candidates, arrival, relay_delay_us=2_000_000.0)
    truth = pl.read_parquet(
        Path("ground_truth") / RUN / "origins.parquet",
        columns=["txid", "true_origin_ip", "true_origin_asn"],
    ).rename({"true_origin_ip": "origin_peer_ip"})
    seen = announcements.group_by("txid").agg(pl.col("seen_us").min().alias("first_seen_us"))
    first_us = int(seen["first_seen_us"].min())
    last_us = int(seen["first_seen_us"].max())
    fit_boundary = boundary_us(first_us, last_us, 0.60)
    validation_ids = seen.filter(
        (pl.col("first_seen_us") >= fit_boundary) & (pl.col("first_seen_us") < labels.boundary_us)
    )["txid"]
    test_ids = seen.filter(pl.col("first_seen_us") >= labels.boundary_us)["txid"]
    validation_truth = truth.filter(pl.col("txid").is_in(validation_ids))
    test_truth = truth.filter(pl.col("txid").is_in(test_ids))
    fit_labels = (
        labels.frame.join(seen, on="txid", how="inner")
        .filter(pl.col("first_seen_us") < fit_boundary)
        .select("txid", "origin_peer_ip")
    )
    floors = (0.0, 0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.04, 0.08, 0.15)

    results: dict[str, object] = {}
    original_estimator_features = estimate.MODEL_FEATURES
    original_schema_features = schema.MODEL_FEATURES
    try:
        for name, columns in VARIANTS.items():
            estimate.MODEL_FEATURES = columns
            schema.MODEL_FEATURES = columns
            scored, fit = estimate.ensemble(
                candidates,
                fit_labels,
                boundary_us=fit_boundary,
                margin_floor=0.04,
                min_announcements=2,
                seed=42,
            )
            validation_metrics = metrics(scored, validation_truth, peers, prior, floors)
            eligible = [
                row
                for row in validation_metrics["l1_margin_policy_curve"]
                if row["acted"] >= 100 and row["precision_when_acted"] >= 0.90
            ]
            selected_floor = (
                max(eligible, key=lambda row: (row["acted"], -row["margin_floor"]))["margin_floor"]
                if eligible
                else None
            )
            test_metrics = metrics(
                scored,
                test_truth,
                peers,
                prior,
                floors if selected_floor is None else (*floors, selected_floor),
            )
            selected_test = next(
                (
                    row
                    for row in test_metrics["l1_margin_policy_curve"]
                    if row["margin_floor"] == selected_floor
                ),
                None,
            )
            results[name] = {
                "features": list(columns),
                "fit": fit.__dict__,
                "validation": validation_metrics,
                "selected_margin_floor": selected_floor,
                "selection_rule": (
                    "maximum validation coverage among floors with >=100 answers and "
                    ">=0.90 precision"
                ),
                "test": test_metrics,
                "selected_policy_test_result": selected_test,
            }
    finally:
        estimate.MODEL_FEATURES = original_estimator_features
        schema.MODEL_FEATURES = original_schema_features

    result = {
        "run_id": RUN,
        "seed": 42,
        "protocol": (
            "train/calibration first 60%, validation next 10%, test final 30%; "
            "features retain current full-capture aggregates"
        ),
        "boundaries_us": {"fit_validation": fit_boundary, "validation_test": labels.boundary_us},
        "inputs": {
            str(path): sha256(path)
            for path in (
                normalised / "announcements.parquet",
                normalised / "transactions.parquet",
                normalised / "peers.parquet",
                normalised / "arrival.parquet",
                normalised / "asn_rollup.parquet",
                run_dir / "graph" / "edges.parquet",
                Path("ground_truth") / RUN / "origins.parquet",
            )
        },
        "variants": results,
        "elapsed_seconds": time.perf_counter() - started,
        "limitations": [
            "one synthetic world/seed; no transfer claim",
            (
                "current global peer, payer, and graph aggregates remain in variants unless "
                "explicitly ablated"
            ),
            "holdout has transactions observed by at least one candidate peer; not all broadcasts",
            (
                "candidate rows are correlated within transaction; inference should use "
                "transaction-block uncertainty"
            ),
            (
                "this ablation is a research diagnostic and does not rewrite production signals "
                "or metrics"
            ),
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
