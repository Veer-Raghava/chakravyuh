"""Record the sources, exports and observed graph inputs of the R46 UI checkpoint."""

import hashlib
import json
import platform
import subprocess
from pathlib import Path

base = Path("research/bitcoin/results/drishti-redesign")
source_archive = Path("research/bitcoin/source-snapshots/R46-final")
paths = set(Path("apps/drishti-v2/src").rglob("*"))
paths.update(Path("apps/drishti-v2/dist").rglob("*"))
paths.update(base.rglob("*"))
paths.update(Path("research/bitcoin/source-snapshots/R46-initial").rglob("*"))
paths.update(
    Path(p)
    for p in [
        "scripts/export_drishti_runs.py",
        "src/chakravyuh/api/serialize.py",
        "research/bitcoin/verify_drishti_exports.py",
        "research/bitcoin/verify_drishti_redesign.py",
        "research/bitcoin/project_drishti_nodes.cjs",
        "docs/research/DRISHTI-INVESTIGATION-WORKSPACE.md",
        "docs/research/EXPERIMENT-JOURNAL.md",
        "docs/research/events.jsonl",
        "PROGRESS.md",
        "apps/drishti-v2/package.json",
        "apps/drishti-v2/package-lock.json",
    ]
)
for run in [
    "agency-v2",
    "_sweep-0.02",
    "_sweep-0.05",
    "_sweep-0.10",
    "_sweep-0.25",
    "_sweep-0.50",
    "_sweep-0.60",
    "_sweep-0.70",
]:
    paths.update(Path("data/generated", run, "graph").glob("*.parquet"))
records = []
for path in sorted(paths):
    if not path.is_file() or path == base / "manifest.json":
        continue
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    records.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    if str(path).startswith("apps/drishti-v2/src/") and path.suffix in {".tsx", ".ts", ".css"}:
        dest = source_archive / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
report = {
    "checkpoint": "R46",
    "python": platform.python_version(),
    "node": subprocess.check_output(["node", "--version"], text=True).strip(),
    "artifacts": records,
}
(base / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
