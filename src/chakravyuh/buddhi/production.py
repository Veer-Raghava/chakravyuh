"""Frozen graph-context detection adapted to the existing Leads and Proof contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.buddhi import relational_inference
from chakravyuh.vaani import counters, evidence, investigation

ENGINE = "causal-relational-xgboost"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_meta(run: Path, directory: str, stage: str, params: dict[str, Any]) -> None:
    now = int(datetime.now(UTC).timestamp() * 1_000_000)
    files = sorted(p for p in (run / directory).iterdir() if p.name != "_meta.json")
    meta = {
        "stage": stage,
        "run_id": run.name,
        "started_at_us": now,
        "finished_at_us": now,
        "code_version": buildinfo.code_version(),
        "seed": 0,
        "params": params,
        "inputs": [
            {
                "path": f"normalised/{name}.parquet",
                "sha256": _hash(run / "normalised" / f"{name}.parquet"),
                "rows": 0,
            }
            for name in ("transactions", "addresses", "announcements", "peers")
        ],
        "outputs": [
            {"path": f"{directory}/{p.name}", "sha256": _hash(p), "rows": 0} for p in files
        ],
        "counts": {
            "in": params.get("scored", 0),
            "out": params.get("scored", 0) if stage == "buddhi" else params.get("selected", 0),
            "dropped": 0
            if stage == "buddhi"
            else params.get("scored", 0) - params.get("selected", 0),
            "drop_reasons": {}
            if stage == "buddhi"
            else {
                "review_budget_or_evidence_overlap": params.get("scored", 0)
                - params.get("selected", 0)
            },
        },
        "warnings": ["ranking_only_no_confidence_interval"],
        "optional_deps": {"gpu": False},
    }
    (run / directory / "_meta.json").write_text(json.dumps(meta, indent=2) + "\n")


def build_run(
    run: Path,
    model: Path,
    *,
    start_us: int,
    end_us: int,
    k: int = 20,
) -> dict[str, Any]:
    """Score an explicit window, diversify its queue, and write standard stage artifacts.

    No training labels or model fitting. The selected model must use singleton addresses.
    Legacy score/proof directories are refused rather than overwritten.
    """
    if start_us > end_us or not 1 <= k <= 200:
        raise ValueError("ordered window and 1–200 leads required")
    if any((run / name).exists() for name in ("scores", "alerts", "packets")):
        raise ValueError("use a fresh run; existing detection/cases must not be overwritten")
    manifest = json.loads((model / "manifest.json").read_text())
    if manifest.get("partition_mode") != "address":
        raise ValueError("production graph engine requires address-mode model")
    scores, view, provenance = relational_inference.score(
        run / "normalised",
        model,
        start_us=start_us,
        end_us=end_us,
    )
    transactions = pl.read_parquet(run / "normalised/transactions.parquet")
    queue = investigation.packet(
        scores,
        view,
        transactions,
        pl.read_parquet(run / "normalised/announcements.parquet"),
        pl.read_parquet(run / "normalised/peers.parquet"),
        k=k,
        overlap=0.25,
    )
    refs = {
        "subject:" + hashlib.sha256(s.encode()).hexdigest()[:24]: s
        for s in scores["subject_id"].to_list()
    }
    top_features = []
    for row in scores.iter_rows(named=True):
        pairs = sorted(
            ((name, float(row[f"shap_{name}"])) for name in relational_inference.FEATURES),
            key=lambda pair: (-abs(pair[1]), pair[0]),
        )
        top_features.append([{"name": name, "value": value} for name, value in pairs[:8]])
    wallet = scores.select("subject_id", "risk_score").with_columns(
        pl.lit("UNCLEAR").alias("label"),
        pl.lit(0.0).alias("conf_low"),
        pl.lit(1.0).alias("conf_high"),
        pl.lit(0.0).alias("coverage_target"),
        pl.lit(ENGINE).alias("model"),
        pl.lit(False).alias("abstain"),
        pl.Series(
            "top_features",
            top_features,
            dtype=pl.List(pl.Struct({"name": pl.String, "value": pl.Float64})),
        ),
    )
    (run / "scores").mkdir()
    wallet.write_parquet(run / "scores/wallet_scores.parquet")
    scores.write_parquet(run / "scores/relational_scores.parquet")
    pl.DataFrame(schema={"class": pl.String, "method": pl.String}).write_parquet(
        run / "scores/calibration.parquet"
    )
    provenance.update(
        model_manifest_sha256=_hash(model / "manifest.json"),
        interval_available=False,
        selection=queue["selection"],
        calibration="Platt mapping fitted on synthetic history; ranking use only",
    )
    (run / "scores/engine.json").write_text(json.dumps(provenance, indent=2) + "\n")
    alerts, reasons, mitigations = [], [], []
    for lead in queue["leads"]:
        subject = refs[lead["subject_ref"]]
        aid = (
            "alr-"
            + hashlib.sha256(
                f"{subject}:{start_us}:{end_us}:{provenance['model_sha256']}".encode()
            ).hexdigest()[:20]
        )
        related = transactions.filter(
            pl.col("first_seen_us").is_between(start_us, end_us)
            & (
                pl.col("input_addresses").list.contains(subject[5:])
                | pl.col("output_addresses").list.contains(subject[5:])
            )
        ).sort(["first_seen_us", "txid"], descending=[True, False])
        lead.update(
            alert_id=aid,
            subject_id=subject,
            representative_txid=str(related["txid"][0]) if related.height else None,
        )
        rank = lead["rank"]
        # Priority is review order, not a calibrated illicit-class threshold.
        alerts.append(
            dict(
                alert_id=aid,
                subject_id=subject,
                rank=rank,
                severity="high" if rank <= 5 else "medium" if rank <= 15 else "low",
                conf_low=0.0,
                conf_high=1.0,
                headline=(
                    f"Graph-context review lead · {lead['supporting_transaction_count']} "
                    "supporting transactions"
                ),
                origin_txid=None,
                origin_peer_ip=None,
                origin_p=None,
                attribution_ready=False,
            )
        )
        for reason in lead["reasons"]:
            reasons.append(
                dict(
                    alert_id=aid,
                    kind="model_feature",
                    statement=reason["description"],
                    weight=reason["shap_margin"],
                    source_ref=f"model:{provenance['model_sha256']}#{reason['feature']}",
                )
            )
        reasons.append(
            dict(
                alert_id=aid,
                kind="observed_graph",
                statement=(
                    f"{lead['displayed_transaction_count']} transaction graphs retained "
                    "with complete inputs and outputs; "
                    f"{lead['network_observation_count']} captured peer observations."
                ),
                weight=0.0,
                source_ref="alerts/lead_queue.json#" + aid,
            )
        )
        for negative in lead["mitigating_contributions"]:
            mitigations.append(
                dict(
                    alert_id=aid,
                    kind="model_mitigation",
                    statement=negative["feature"].replace("_", " ") + " lowered the model margin",
                    strength=abs(negative["shap_margin"]),
                    would_clear=False,
                )
            )
        mitigations.append(
            dict(
                alert_id=aid,
                kind="interpretation_limit",
                statement=(
                    "This is an activity review lead. Ownership and originating peer are "
                    "unresolved; ordinary services can exhibit similar activity."
                ),
                strength=0.0,
                would_clear=False,
            )
        )
    (run / "alerts").mkdir()
    for name, rows, schema in [
        ("alerts", alerts, evidence.ALERTS_SCHEMA),
        ("evidence", reasons, evidence.EVIDENCE_SCHEMA),
        ("counter", mitigations, counters.COUNTER_SCHEMA),
    ]:
        pl.DataFrame(rows, schema=schema).write_parquet(run / "alerts" / f"{name}.parquet")
    queue["engine"] = provenance
    (run / "alerts/lead_queue.json").write_text(json.dumps(queue, indent=2, allow_nan=False) + "\n")
    params = dict(
        engine=ENGINE,
        feature_count=329,
        scored=scores.height,
        selected=len(alerts),
        window=queue["window"],
        model_sha256=provenance["model_sha256"],
        score_meaning=provenance["score_meaning"],
        interval_available=False,
        priority_meaning="review rank; not a class-confidence threshold",
    )
    _write_meta(run, "scores", "buddhi", params)
    params["upstream_meta"] = {
        "path": str(run / "scores/_meta.json"),
        "sha256": _hash(run / "scores/_meta.json"),
    }
    _write_meta(run, "alerts", "vaani", params)
    return provenance | {"scored": scores.height, "selected": len(alerts)}
