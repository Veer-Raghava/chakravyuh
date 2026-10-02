"""Actually execute the offline CLI in a temporary copy containing only observations/model."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import polars as pl
from buddhi_world_transfer import windows
from common import digest, log


def main():
    workspace = Path.cwd()
    normalised = workspace / "data/generated/agency-v2/normalised"
    model = workspace / "research/bitcoin/results/causal-inference-artifact"
    _, start, end = windows(pl.read_parquet(normalised / "transactions.parquet"))[7]
    with tempfile.TemporaryDirectory(prefix="causal-offline-smoke-") as directory:
        stripped = Path(directory)
        (stripped / "normalised").mkdir()
        for name in ("transactions.parquet", "addresses.parquet"):
            shutil.copyfile(normalised / name, stripped / "normalised" / name)
        (stripped / "model").mkdir()
        for name in ("model.json", "manifest.json"):
            shutil.copyfile(model / name, stripped / "model" / name)
        command = [
            sys.executable,
            "-m",
            "chakravyuh.buddhi.causal_inference",
            "--normalised",
            "normalised",
            "--model",
            "model",
            "--output",
            "output",
            "--start-us",
            str(start),
            "--end-us",
            str(end),
        ]
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(workspace / "src")
        completed = subprocess.run(
            command,
            cwd=stripped,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
            check=True,
        )
        assert not completed.stdout
        scores = pl.read_parquet(stripped / "output/scores.parquet")
        assert scores.height > 0 and "y" not in scores.columns and "owner" not in scores.columns
        manifest = json.loads((stripped / "output/manifest.json").read_text())
        report = {
            "rows": scores.height,
            "columns": scores.columns,
            "returncode": completed.returncode,
            "temporary_input_files": [
                "normalised/transactions.parquet",
                "normalised/addresses.parquet",
                "model/model.json",
                "model/manifest.json",
            ],
            "stdout_empty": True,
            "score_sha256": digest(stripped / "output/scores.parquet"),
            "source_sha256": digest(__file__),
            "inference_manifest": manifest,
            "limitations": [
                "Exercises one frozen model/window and installed optional dependencies.",
                "Not an independent predictive evaluation or complete dashboard shipping check.",
            ],
        }
    output = workspace / "research/bitcoin/results/causal-inference-stripped-smoke.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    log("causal_inference_stripped_smoke_passed", rows=scores.height)


if __name__ == "__main__":
    main()
