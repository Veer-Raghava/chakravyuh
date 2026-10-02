"""Inventory reproducible research artifacts and archive current source identities."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import shutil
from pathlib import Path

from common import digest, log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()
    root = Path("research/bitcoin")
    archive = root / "source-snapshots"
    paths = [
        *root.glob("*.py"),
        *(root / "tests").glob("*.py"),
        Path("src/chakravyuh/buddhi/snapshot.py"),
        Path("src/chakravyuh/buddhi/causal_inference.py"),
        Path("src/chakravyuh/buddhi/relational_inference.py"),
        Path("src/chakravyuh/vaani/investigation.py"),
        Path("src/chakravyuh/jaal/provenance.py"),
        Path("src/chakravyuh/shastra/causal.py"),
        Path("src/chakravyuh/mayajaal/config.py"),
        Path("tests/test_buddhi_snapshot.py"),
        Path("tests/test_investigation.py"),
        Path("tests/test_relational_inference.py"),
    ]
    sources = []
    for p in paths:
        h = digest(p)
        target = archive / f"{h}-{p.name}"
        if not target.exists():
            shutil.copyfile(p, target)
        sources.append(dict(path=str(p), sha256=h, snapshot=str(target)))
    artifacts = []
    for p in sorted((root / "results").rglob("*")):
        if p.is_file():
            artifacts.append(dict(path=str(p), bytes=p.stat().st_size, sha256=digest(p)))
    frontend = []
    for p in [
        Path("apps/drishti-v2/src/shell/screens/InvestigationPreview.tsx"),
        Path("apps/drishti-v2/src/shell/screens/ModelIntelligence.tsx"),
        Path("apps/drishti-v2/src/shell/screens/ModelIntelligence.module.css"),
        Path("apps/drishti-v2/src/data/fixtures/research-leads.json"),
        Path("apps/drishti-v2/src/data/fixtures/research-progress.json"),
    ]:
        frontend.append(dict(path=str(p), sha256=digest(p)))
    inputs = []
    for p in [
        *(
            Path(f"data/generated/agency-v2/normalised/{n}.parquet")
            for n in ("transactions", "addresses", "announcements", "peers")
        ),
        Path("data/generated/agency-v2/config.effective.json"),
        *(
            Path(f"ground_truth/agency-v2/{n}.parquet")
            for n in ("entities", "campaigns", "origins")
        ),
    ]:
        inputs.append(dict(path=str(p), bytes=p.stat().st_size, sha256=digest(p)))
    versions = {"python": platform.python_version()}
    for n in ("torch", "numpy", "polars", "sklearn", "xgboost", "lightgbm", "joblib"):
        versions[n] = importlib.import_module(n).__version__
    report = dict(
        checkpoint=args.checkpoint,
        current_sources=sources,
        artifacts=artifacts,
        frontend=frontend,
        canonical_inputs=inputs,
        versions=versions,
        artifact_bytes=sum(a["bytes"] for a in artifacts),
        scope="Hashes identify artifacts; historical executed versions retained separately.",
        default_backend_replaced=False,
        full_release_verified=False,
    )
    path = archive / f"{args.checkpoint}-manifest.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log(
        "checkpoint_manifest_written",
        path=str(path),
        artifacts=len(artifacts),
        bytes=report["artifact_bytes"],
    )


if __name__ == "__main__":
    main()
