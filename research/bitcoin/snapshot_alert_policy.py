"""Validation-only response thresholds, evaluated from preserved snapshot scores."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from common import digest, log


def counts(frame):
    n = frame.height
    hits = int(frame["y"].sum()) if n else 0
    return {
        "answered": n,
        "correct": hits,
        "false_alerts": n - hits,
        "precision": hits / n if n else None,
    }


def main():
    root = Path("research/bitcoin/results")
    report_path = root / "buddhi-matched-window-benchmark.json"
    report = json.loads(report_path.read_text())
    name = report["validation_selected_cioh_model"]
    paths = {
        "validation_selected": report["models"]["cioh"][name]["research_score_artifact"],
        "oracle_control": report["models"]["oracle_ownership"]["lightgbm"][
            "research_score_artifact"
        ],
    }
    results = {}
    for key, path in paths.items():
        data = pl.read_parquet(path)
        val = data.filter(pl.col("phase") == "val")
        test = data.filter(pl.col("phase") == "test")
        cumulative = (
            val.group_by("score")
            .agg(pl.len().alias("n"), pl.col("y").sum().alias("hits"))
            .sort("score", descending=True)
            .with_columns(pl.col("n").cum_sum(), pl.col("hits").cum_sum())
        )
        policies = []
        for target in (0.8, 0.9):
            eligible = cumulative.filter(
                (pl.col("n") >= 10) & (pl.col("hits") / pl.col("n") >= target)
            ).sort("n", descending=True)
            threshold = float(eligible["score"][0]) if eligible.height else None
            answered = (
                test.filter(pl.col("score") >= threshold) if threshold is not None else test.head(0)
            )
            total_positives = int(test["y"].sum())
            policies.append(
                {
                    "validation_precision_target": target,
                    "threshold": threshold,
                    "validation": counts(val.filter(pl.col("score") >= threshold))
                    if threshold is not None
                    else counts(val.head(0)),
                    "test": {
                        **counts(answered),
                        "coverage": answered.height / test.height,
                        "recall": float(answered["y"].sum()) / total_positives
                        if total_positives
                        else None,
                    },
                    "test_by_window": {
                        str(w): counts(answered.filter(pl.col("window_id") == w))
                        for w in test["window_id"].unique().sort()
                    },
                }
            )
        results[key] = {
            "model": name if key == "validation_selected" else "oracle_lightgbm",
            "score_artifact": path,
            "score_sha256": digest(path),
            "policies": policies,
        }
    out = root / "snapshot-alert-policy.json"
    out.write_text(
        json.dumps(
            {
                "results": results,
                "rule": "max validation coverage at >=10 decisions and specified precision; "
                "keep tied scores together",
                "limitations": [
                    "post-benchmark exploratory policy analysis; fresh-world confirmation required",
                    "observed validation precision is not a confidence lower bound "
                    "or future guarantee",
                    "oracle ownership is deliberately unavailable in deployment",
                    "repeat subject decisions may share controllers; independence not assumed",
                ],
                "hashes": {str(p): digest(p) for p in (report_path, Path(__file__))},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    log("snapshot_alert_policy_complete", output=str(out), production_changes=False)


if __name__ == "__main__":
    main()
