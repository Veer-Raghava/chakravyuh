"""Export aggregate research reports into a run; the serving API never opens eval trees."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def export(run: Path) -> None:
    """Explicit evaluation-side publication of aggregates, without answer-key rows."""
    source_run = run.name
    pipeline = run / "pipeline.json"
    if pipeline.is_file():
        provenance = json.loads(pipeline.read_text())
        parent = Path(provenance["source_run"])
        for name, expected in provenance["input_sha256"].items():
            if (
                hashlib.sha256((parent / "normalised" / f"{name}.parquet").read_bytes()).hexdigest()
                != expected
            ):
                raise ValueError("source capture changed; refusing inherited evaluation summaries")
        source_run = parent.name
    source = Path("measurements") / source_run
    output = run / "presentation"
    output.mkdir(exist_ok=True)
    copied = {}
    for name in ("model_report.json", "origin_accuracy.json", "cluster_metrics.json"):
        if name == "model_report.json" and source_run != run.name:
            continue
        if (source / name).is_file():
            value = (source / name).read_bytes()
            (output / name).write_bytes(value)
            copied[name] = hashlib.sha256(value).hexdigest()
    paths = sorted(Path("measurements").glob("*sweep*/origin_accuracy.json"))
    (output / "origin_curve.json").write_text(
        json.dumps([json.loads(path.read_text()) for path in paths]) + "\n"
    )
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "source_run": source_run,
                "report_sha256": copied,
                "meaning": "aggregate evaluation presentation; not inference inputs",
            },
            indent=2,
        )
        + "\n"
    )
