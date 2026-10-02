"""Compare saved ownership sensitivity scores on identical observable controller windows."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from common import digest, log, ranking
from typed_graph_transfer import NAMES

OUT = Path("research/bitcoin/results/partition-error-propagation")
KEYS = ["owner", "window_id"]


def main():
    frames = {
        (threshold, name): pl.read_parquet(OUT / f"threshold-{threshold}-{name}.parquet")
        for threshold in (0.3, 0.2)
        for name in NAMES
    }
    common = (
        frames[0.3, NAMES[0]]
        .select(*KEYS, "y")
        .join(frames[0.2, NAMES[0]].select(*KEYS, pl.col("y").alias("other_y")), on=KEYS)
    )
    assert common.select(pl.col("y") == pl.col("other_y")).to_series().all()
    assert common.unique(KEYS).height == common.height
    results = {}
    for (threshold, name), frame in frames.items():
        aligned = frame.join(common.select(KEYS), on=KEYS).sort(KEYS)
        assert aligned.height == common.height
        results.setdefault(str(threshold), {})[name] = ranking(
            aligned["y"].to_numpy(), aligned["score"].to_numpy()
        )
    report = {
        "common_controller_windows": common.height,
        "common_positives": int(common["y"].sum()),
        "models": results,
        "hashes": {
            str(p): digest(p) for p in [Path(__file__), OUT / "report.json", *OUT.glob("*.parquet")]
        },
        "limitations": [
            "Intersection conditions on being represented by both partitions.",
            "Hidden controller keys are diagnostic only; not analyst deduplication.",
            "Same frozen models, consumed canonical world; no retraining confirmation.",
        ],
    }
    (OUT / "common-universe-report.json").write_text(json.dumps(report, indent=2) + "\n")
    log("partition_common_universe_complete", common_rows=common.height)


if __name__ == "__main__":
    main()
