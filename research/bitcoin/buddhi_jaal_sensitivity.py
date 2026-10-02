"""Research-only BUDDHI sensitivity to JAAL's measured confidence threshold.

Rebuilds the operational subject clusters from the same immutable evidence graph at 0.20
(current CIOH + change) and 0.30 (CIOH only), then reruns the same BUDDHI recipe. Labels enter
training through the eval label door and enter this script's output only as aggregate metrics.
No production artifact is written or overwritten.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import polars as pl
from common import digest, partition_metrics, save

from chakravyuh.buddhi import features, model
from chakravyuh.eval import labels, metrics
from chakravyuh.jaal import cluster

RUN = "agency-v2"
ROOT = Path("data/generated") / RUN
TRUTH = Path("ground_truth") / RUN / "entities.parquet"
OUT = Path("research/bitcoin/results/buddhi-jaal-sensitivity")
InputData = tuple[
    pl.DataFrame,
    pl.DataFrame,
    pl.DataFrame,
    pl.DataFrame,
    pl.DataFrame | None,
    pl.DataFrame,
    pl.DataFrame,
    dict[str, str],
    dict[str, int],
]


def _load_inputs() -> InputData:
    tx = pl.read_parquet(
        ROOT / "normalised/transactions.parquet", columns=list(features.TRANSACTION_COLUMNS)
    )
    addresses = pl.read_parquet(
        ROOT / "normalised/addresses.parquet",
        columns=list(features.ADDRESS_COLUMNS) + ["first_seen_us"],
    )
    edges = pl.read_parquet(ROOT / "graph/edges.parquet", columns=list(features.EDGE_COLUMNS))
    origins = pl.read_parquet(
        ROOT / "signals/origin_estimates.parquet",
        columns=list(features.ORIGIN_ESTIMATE_COLUMNS) + ["estimator"],
    )
    l1_path = ROOT / "signals/origin_l1.parquet"
    l1 = (
        pl.read_parquet(l1_path, columns=list(features.ORIGIN_L1_COLUMNS))
        if l1_path.exists()
        else None
    )
    hits = pl.read_parquet(
        ROOT / "signals/typology_hits.parquet", columns=["subject_id", "typology", "txids"]
    )
    truth = pl.read_parquet(TRUTH, columns=["entity_id", "is_illicit", "addresses"])
    owner_by_address = {
        a: row["entity_id"] for row in truth.iter_rows(named=True) for a in row["addresses"]
    }
    illicit_by_address = {
        a: int(row["is_illicit"]) for row in truth.iter_rows(named=True) for a in row["addresses"]
    }
    return tx, addresses, edges, origins, l1, hits, truth, owner_by_address, illicit_by_address


def _run_threshold(threshold: float, data: InputData) -> dict[str, Any]:
    started = time.perf_counter()
    tx, addresses, edges, origins, l1, hits, truth, owner_by_address, illicit_by_address = data
    model_edges = edges.filter(
        (pl.col("kind") != "SAME_OWNER") | (pl.col("confidence") >= threshold)
    )
    clusters, _ = cluster.clusters(model_edges, threshold)
    partition = [row for row in clusters["addresses"].to_list()]
    # Include all observed singletons as the operational partition metric does.
    owners_seen = set(addresses["address"].to_list()) & set(owner_by_address)
    part_stats = partition_metrics(partition, owner_by_address, owners_seen)

    # Cluster-label contamination describes how many predicted subjects collapse distinct
    # synthetic controllers or both licit and illicit controllers. It is diagnostic only.
    multi_owner = 0
    mixed_risk = 0
    sizes = []
    for members in partition:
        owners = {owner_by_address[a] for a in members if a in owner_by_address}
        risk = {illicit_by_address[a] for a in members if a in illicit_by_address}
        multi_owner += int(len(owners) > 1)
        mixed_risk += int(len(risk) > 1)
        sizes.append(len(members))

    setting = json.loads((ROOT / "config.effective.json").read_text())
    train_fraction = float(setting.get("eval", {}).get("train_fraction", 0.7))
    coverage = float(setting.get("eval", {}).get("coverage_target", 0.9))
    seed = int(setting.get("seed", 42))
    target = labels.wallet_labels(RUN, train_fraction)
    if target is None:
        raise RuntimeError("training labels unavailable through eval label door")
    boundary = target.boundary_us

    subject_table = features.build(
        tx, clusters, addresses, model_edges, origins, boundary, typology_hits=hits, origin_l1=l1
    )
    members = features.subjects(clusters, addresses)
    subject_addresses = members.group_by("subject_id", maintain_order=True).agg(
        pl.col("address").sort().alias("addresses")
    )
    order_map = (
        members.join(addresses.select("address", "first_seen_us"), on="address", how="inner")
        .group_by("subject_id")
        .agg(pl.col("first_seen_us").min().alias("_order"))
    )
    label_map = dict(
        zip(
            target.frame["address"].to_list(),
            target.frame["is_illicit"].cast(pl.Int64).to_list(),
            strict=True,
        )
    )
    train_subjects = (
        subject_table.filter(pl.col("is_train"))
        .join(order_map, on="subject_id", how="left")
        .with_columns(pl.col("_order").fill_null(0))
    )
    labelled = members.join(
        pl.DataFrame({"address": list(label_map), "y": list(label_map.values())}),
        on="address",
        how="inner",
    )
    subject_y = labelled.group_by("subject_id", maintain_order=True).agg(
        (2 * pl.col("y").sum() > pl.len()).cast(pl.Int64).alias("y")
    )
    train_frame = train_subjects.join(subject_y, on="subject_id", how="inner").select(
        "_order", "y", *features.MODEL_FEATURES
    )

    bundle, calibrated = model.fit(train_frame, seed=seed, coverage_target=coverage)
    scored = subject_table.select("subject_id", "is_train", *features.MODEL_FEATURES)
    risk = model.risk_scores(bundle, scored)
    sets = model.predict_sets(bundle, scored)
    pred = pl.DataFrame(
        {
            "subject_id": scored["subject_id"],
            "is_train": scored["is_train"],
            "risk_score": risk,
            "in_set_0": sets["in_set_0"],
            "in_set_1": sets["in_set_1"],
        }
    )
    pred = pred.join(subject_addresses, on="subject_id", how="left").filter(~pl.col("is_train"))
    pred = pred.drop("is_train")
    pred = pred.with_columns((~(pl.col("in_set_0") | pl.col("in_set_1"))).alias("abstain"))
    report = metrics.score_wallets(
        RUN,
        predictions=pred,
        boundary_us=boundary,
        coverage_target=coverage,
        params={"research_threshold": threshold},
        write=False,
    )
    wm = report["wallet_model"]
    held = (
        truth.select("entity_id", "is_illicit", pl.col("addresses").alias("address"))
        .explode("address")
        .join(addresses.select("address", "first_seen_us"), on="address", how="inner")
        .filter(pl.col("first_seen_us") >= boundary)
    )
    flagged_addresses = set(
        pred.filter(pl.col("in_set_1"))
        .select("addresses")
        .explode("addresses")["addresses"]
        .to_list()
    )
    campaign_status = held.group_by("entity_id").agg(
        pl.col("is_illicit").first().alias("is_illicit"),
        pl.col("address").is_in(flagged_addresses).any().alias("flagged"),
    )
    flagged_campaigns = campaign_status.filter(pl.col("flagged"))
    true_flagged = int(flagged_campaigns.filter(pl.col("is_illicit")).height)
    false_flagged = int(flagged_campaigns.filter(~pl.col("is_illicit")).height)
    true_campaigns = int(campaign_status.filter(pl.col("is_illicit")).height)
    holdout_subjects = pred.height
    output = {
        "threshold": threshold,
        "jaal_partition": {
            **part_stats,
            "n_clusters": len(partition),
            "clusters_with_multiple_true_owners": multi_owner,
            "clusters_mixing_licit_and_illicit": mixed_risk,
            "largest_cluster": max(sizes, default=1),
        },
        "buddhi": {
            "n_train_subjects_with_labels": train_frame.height,
            "n_holdout_subjects": holdout_subjects,
            "actor_pr_auc": wm["actor_level"]["pr_auc"],
            "actor_roc_auc": wm["actor_level"]["roc_auc"],
            "precision_at_20": wm["actor_level"]["precision_at_20"],
            "recall_at_20": wm["actor_level"]["recall_at_20"],
            "tx_pr_auc": wm["tx_level"]["pr_auc"],
            "tx_precision_at_20": wm["tx_level"]["precision_at_20"],
            "campaign_recall": wm["campaign_level"]["campaign_recall"],
            "campaigns": wm["campaign_level"]["n_campaigns"],
            "campaigns_caught": wm["campaign_level"]["n_caught"],
            "campaign_precision": true_flagged / flagged_campaigns.height
            if flagged_campaigns.height
            else 0.0,
            "campaigns_flagged_total": flagged_campaigns.height,
            "licit_campaigns_flagged": false_flagged,
            "illicit_campaign_recall_recomputed": true_flagged / true_campaigns
            if true_campaigns
            else 0.0,
            "abstain_rate": wm["abstain_rate"],
            "calibration": {
                "trained": calibrated.trained,
                "mondrian": calibrated.mondrian,
                "n_fit": calibrated.n_train,
                "n_calibration": calibrated.n_calibration,
                "reason": calibrated.reason,
            },
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    return output


def main() -> None:
    data = _load_inputs()
    output = {
        "run": RUN,
        "protocol": (
            "identical agency-v2 time-ordered split; only the JAAL confidence threshold changes"
        ),
        "input_hashes": {
            "transactions": digest(ROOT / "normalised/transactions.parquet"),
            "addresses": digest(ROOT / "normalised/addresses.parquet"),
            "graph_edges": digest(ROOT / "graph/edges.parquet"),
            "origin_estimates": digest(ROOT / "signals/origin_estimates.parquet"),
            "origin_l1": digest(ROOT / "signals/origin_l1.parquet"),
            "typology_hits": digest(ROOT / "signals/typology_hits.parquet"),
            "truth_entities": digest(TRUTH),
        },
        "scenarios": [_run_threshold(t, data) for t in (0.2, 0.3)],
        "limitations": [
            "One synthetic seed and one generator; this is sensitivity, not external validity.",
            "Threshold 0.30 removes measured 0.25 change edges but retains 0.36 CIOH edges.",
            "The same hidden entity truth is used only for training labels through the eval door "
            "and aggregate evaluation.",
            "BUDDHI is retrained under each partition; this measures end-to-end JAAL "
            "sensitivity, not isolated feature attribution.",
        ],
    }
    save(OUT / "buddhi-jaal-sensitivity.json", output)
    sys.stdout.write(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
