"""Research-only AML comparisons on separately built temporal subject snapshots.

Includes a explicitly truth-derived ownership oracle for error-localization, never deployment.
Labels attach only after observable feature construction (except that named oracle control).
"""

from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
from common import digest, log, ranking
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from chakravyuh.buddhi import snapshot
from chakravyuh.jaal import provenance

ROOT = Path("data/generated/agency-v2")
OUT = Path("research/bitcoin/results/buddhi-snapshot-benchmark.json")
PARAMS = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 40,
    "lambda_l2": 1.0,
    "num_threads": 4,
    "deterministic": True,
    "force_col_wise": True,
    "verbosity": -1,
    "seed": 42,
}


def truth_ledger(addresses, labels):
    # Deliberate oracle: owner IDs determine partition, not detector features directly.
    known = (
        addresses.select("address", "first_seen_us")
        .join(labels, on="address")
        .sort("first_seen_us", "address")
    )
    anchors = known.group_by("owner", maintain_order=True).agg(
        pl.col("address").first().alias("anchor"),
        pl.col("first_seen_us").first().alias("anchor_us"),
    )
    return (
        known.join(anchors, on="owner")
        .filter(pl.col("address") != pl.col("anchor"))
        .select(
            ("addr:" + pl.col("anchor")).alias("src"),
            ("addr:" + pl.col("address")).alias("dst"),
            ("oracle:" + pl.col("owner")).alias("txid"),
            pl.max_horizontal("first_seen_us", "anchor_us").alias("available_us"),
            pl.lit(1.0).alias("confidence"),
            pl.lit("multi_input").alias("evidence"),
        )
    )


def labelled_snapshots(tx, addresses, ledger, labels, threshold, cuts):
    frames = []
    owners_seen = set()
    for window_id, (phase, start, end) in enumerate(cuts):
        s = snapshot.build(tx, addresses, ledger, start_us=start, end_us=end, threshold=threshold)
        active_owners = (
            ACTIVITY.filter((pl.col("first_seen_us") >= start) & (pl.col("first_seen_us") <= end))[
                "owner"
            ]
            .unique()
            .to_list()
        )
        window_labels = labels.with_columns(
            pl.col("owner").is_in(active_owners).cast(pl.Int8).alias("y")
        )
        target = (
            s.members.join(window_labels, on="address")
            .group_by("subject_id")
            .agg(
                pl.col("y").max().alias("y"),
                pl.col("y").mean().alias("illicit_fraction"),
                pl.col("owner").unique().sort().alias("owners"),
                pl.col("y").n_unique().alias("risk_classes"),
            )
        )
        f = (
            s.table.join(target, on="subject_id")
            .with_columns(pl.lit(phase).alias("phase"), pl.lit(window_id).alias("window_id"))
            .sort("subject_id")
        )
        if phase == "fit":
            owners_seen.update(f["owners"].explode().to_list())
        f = f.with_columns(
            pl.col("owners")
            .map_elements(
                lambda owners: not any(o in owners_seen for o in owners), return_dtype=pl.Boolean
            )
            .alias("unseen_owner")
        )
        frames.append(f)
        log(
            "buddhi_snapshot_built",
            phase=phase,
            threshold=threshold,
            subjects=f.height,
            ownership_edges=s.edges.height,
            production_changes=False,
        )
    return pl.concat(frames)


def assess(frame, raw, key):
    masks = {p: frame["phase"].to_numpy() == p for p in ("fit", "cal", "val", "test")}
    y = frame["y"].to_numpy()
    clipped = np.clip(raw, 1e-6, 1 - 1e-6)
    logits = np.log(clipped / (1 - clipped))
    cal = LogisticRegression(max_iter=1000, random_state=42).fit(
        logits[masks["cal"], None], y[masks["cal"]]
    )
    scores = cal.predict_proba(logits[:, None])[:, 1]
    test = masks["test"]
    result = {
        "validation_subjects": ranking(y[masks["val"]], scores[masks["val"]]),
        "subjects": ranking(y[test], scores[test]),
        "unseen_owner_subjects": ranking(
            y[test & frame["unseen_owner"].to_numpy()],
            scores[test & frame["unseen_owner"].to_numpy()],
        ),
        "mixed_risk_subjects": int(
            (frame.filter(pl.col("phase") == "test")["risk_classes"] > 1).sum()
        ),
        "n_fit": int(masks["fit"].sum()),
        "fit_positives": int(y[masks["fit"]].sum()),
    }
    test_ids = np.flatnonzero(test)
    ranked = test_ids[np.argsort(-scores[test], kind="stable")]
    for k in (20, 50):
        result[f"avg_illicit_address_fraction_top{k}"] = float(
            frame["illicit_fraction"].to_numpy()[ranked[:k]].mean()
        )
    # Score every latent true controller by max score of any subject containing its address.
    # This is a research diagnostic; mixed subject scores also contaminate licit controllers.
    actor = (
        frame.filter(pl.col("phase") == "test")
        .with_columns(pl.Series("score", scores[test]))
        .select("owners", "score")
        .explode("owners")
        .group_by("owners")
        .agg(pl.col("score").max())
    )
    actor = (
        actor.join(ACTOR_Y, left_on="owners", right_on="owner")
        .filter(pl.col("owners").is_in(ACTIVE_TEST_OWNERS))
        .sort("owners")
    )
    result["true_controller_diagnostic"] = ranking(actor["y"].to_numpy(), actor["score"].to_numpy())
    score_path = OUT.parent / f"{OUT.stem}-scores" / f"{key}.parquet"
    score_path.parent.mkdir(parents=True, exist_ok=True)
    frame.select(
        "subject_id", "window_id", "phase", "y", "owners", "illicit_fraction", "unseen_owner"
    ).with_columns(pl.Series("score", scores)).write_parquet(score_path, compression="zstd")
    result["research_score_artifact"] = str(score_path)
    result["research_score_sha256"] = digest(score_path)
    result["test_by_window"] = {
        str(window): ranking(
            y[test & (frame["window_id"].to_numpy() == window)],
            scores[test & (frame["window_id"].to_numpy() == window)],
        )
        for window in frame.filter(pl.col("phase") == "test")["window_id"].unique().sort()
    }
    return result


def main(matched=False):
    global LABELS, ACTIVITY, ACTOR_Y, ACTIVE_TEST_OWNERS, OUT
    started = time.perf_counter()
    tx = pl.read_parquet(ROOT / "normalised/transactions.parquet")
    addresses = pl.read_parquet(ROOT / "normalised/addresses.parquet")
    truth_path = Path("ground_truth/agency-v2/entities.parquet")
    truth = pl.read_parquet(truth_path)
    LABELS = truth.select(
        pl.col("entity_id").alias("owner"),
        pl.col("is_illicit").cast(pl.Int8).alias("y"),
        pl.col("addresses").alias("address"),
    ).explode("address")
    first, last = int(tx["first_seen_us"].min()), int(tx["first_seen_us"].max())
    boundaries = [first + int((last - first) * p) for p in (0.45, 0.6, 0.7, 1.0)]
    cuts = [
        ("fit", first, boundaries[0]),
        ("cal", boundaries[0] + 1, boundaries[1]),
        ("val", boundaries[1] + 1, boundaries[2]),
        ("test", boundaries[2] + 1, boundaries[3]),
    ]
    if matched:
        OUT = OUT.with_name("buddhi-matched-window-benchmark.json")
        endpoints = [first + int((last - first) * i / 10) for i in range(11)]
        cuts = [
            (
                "fit" if i < 4 else "cal" if i < 6 else "val" if i == 6 else "test",
                endpoints[i] if i == 0 else endpoints[i] + 1,
                endpoints[i + 1],
            )
            for i in range(10)
        ]
    campaign_path = Path("ground_truth/agency-v2/campaigns.parquet")
    campaigns = (
        pl.read_parquet(campaign_path)
        .select("entity_ids", "txids")
        .explode("txids")
        .rename({"txids": "txid"})
    )
    observed_owners = (
        tx.select(
            "txid",
            "first_seen_us",
            pl.concat_list("input_addresses", "output_addresses").alias("address"),
        )
        .explode("address")
        .join(LABELS.select("owner", "address"), on="address")
    )
    ACTIVITY = (
        observed_owners.join(campaigns, on="txid")
        .filter(pl.col("entity_ids").list.contains(pl.col("owner")))
        .select("owner", "txid", "first_seen_us")
        .unique()
    )
    test_activity = ACTIVITY.filter(pl.col("first_seen_us") > boundaries[2])["owner"].unique()
    ACTOR_Y = (
        LABELS.select("owner")
        .unique()
        .with_columns(pl.col("owner").is_in(test_activity).cast(pl.Int8).alias("y"))
    )
    ACTIVE_TEST_OWNERS = (
        observed_owners.filter(pl.col("first_seen_us") > boundaries[2])["owner"].unique().to_list()
    )
    real_ledger = provenance.ownership_evidence(tx)
    result = {}
    for policy, ledger, threshold in [
        ("singleton", real_ledger, 1.01),
        ("cioh", real_ledger, 0.3),
        ("cioh_change", real_ledger, 0.2),
        ("oracle_ownership", truth_ledger(addresses, LABELS), 0.3),
    ]:
        frame = labelled_snapshots(tx, addresses, ledger, LABELS, threshold, cuts)
        fit = frame["phase"].to_numpy() == "fit"
        x = frame.select(snapshot.SNAPSHOT_FEATURES).to_numpy().astype(np.float64)
        x = np.nan_to_num(x, nan=0.0)
        x = np.sign(x) * np.log1p(np.abs(x))
        x = StandardScaler().fit(x[fit]).transform(x).astype(np.float32)
        y = frame["y"].to_numpy()
        models = {"lightgbm": None}
        if policy == "cioh":
            models.update(
                {
                    "logistic": LogisticRegression(max_iter=1000, random_state=42),
                    "random_forest": RandomForestClassifier(
                        n_estimators=150,
                        max_depth=18,
                        min_samples_leaf=10,
                        n_jobs=4,
                        random_state=42,
                    ),
                    "extra_trees": ExtraTreesClassifier(
                        n_estimators=150,
                        max_depth=18,
                        min_samples_leaf=10,
                        n_jobs=4,
                        random_state=42,
                    ),
                    "xgboost": XGBClassifier(
                        n_estimators=300,
                        max_depth=5,
                        learning_rate=0.05,
                        min_child_weight=10,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        n_jobs=4,
                        tree_method="hist",
                        random_state=42,
                    ),
                }
            )
        output = {}
        for name, model in models.items():
            begin = time.perf_counter()
            if name == "lightgbm":
                model = lgb.train(PARAMS, lgb.Dataset(x[fit], label=y[fit]), num_boost_round=300)
                p = model.predict(x)
            else:
                model.fit(x[fit], y[fit])
                p = model.predict_proba(x)[:, 1]
            output[name] = {
                **assess(frame, p, f"{policy}-{name}"),
                "fit_and_predict_seconds": time.perf_counter() - begin,
            }
            log(
                "buddhi_snapshot_model_complete",
                policy=policy,
                model=name,
                test_ap=output[name]["subjects"]["ap"],
                production_changes=False,
            )
        result[policy] = output
    report = {
        "run": "agency-v2",
        "cuts_us": cuts,
        "features": snapshot.SNAPSHOT_FEATURES,
        "feature_version": (
            "snapshot_v3_exact_gross_flows_subject_counterparties_unique_sends_sorted"
        ),
        "target_version": "observed_campaign_participation_in_decision_window",
        "campaign_activity_owners_by_window": {
            f"{phase}:{end}": ACTIVITY.filter(
                (pl.col("first_seen_us") >= start) & (pl.col("first_seen_us") <= end)
            )["owner"].n_unique()
            for phase, start, end in cuts
        },
        "common_test_controller_universe": len(ACTIVE_TEST_OWNERS),
        "models": result,
        "seconds": time.perf_counter() - started,
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "validation_selected_cioh_model": max(
            result["cioh"],
            key=lambda name: (
                result["cioh"][name]["validation_subjects"]["p_at_20"],
                result["cioh"][name]["validation_subjects"]["ap"],
            ),
        ),
        "selection_rule": "CIOH model: maximum validation Precision@20, then validation AP",
        "lightgbm_params": PARAMS,
        "limitations": [
            "reused synthetic world and time periods; not confirmatory",
            "target is observed campaign participation in window; not guilt or every tx illicit",
            "snapshot decisions at window end; recurring owners are evaluated separately",
            "any illicit member yields positive subject; "
            "mixed ownership requires purity diagnostics",
            "oracle ownership is deliberately truth-derived and unavailable in deployment",
            "global source/ASN scores and typology hits excluded, 23-feature version",
            "unequal window lengths may shift activity features; compare matched durations next",
        ],
        "hashes": {
            str(p): digest(p)
            for p in [
                ROOT / "normalised/transactions.parquet",
                ROOT / "normalised/addresses.parquet",
                truth_path,
                campaign_path,
                Path(__file__),
                Path(snapshot.__file__),
                Path(provenance.__file__),
            ]
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    log("buddhi_snapshot_benchmark_complete", output=str(OUT), production_changes=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--matched", action="store_true")
    main(parser.parse_args().matched)
