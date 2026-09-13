"""Check any stage's `_meta.json` from outside the code that wrote it.

`check_sealed.py` knows what a `sealed/` directory is. This one knows only what contract
section 10 says every stage writes, so S05 onwards can point it at their own output directory
without a new script each time. Stdlib plus pyarrow for the Parquet footer, like `peek.py`.

Four things, in the order they would bite:

1. every `outputs` entry exists and re-hashes to the digest recorded for it
2. every `outputs` entry's Parquet row count matches the `rows` recorded for it
3. `counts.in == counts.out + counts.dropped`, and `drop_reasons` sums to `dropped`
4. the staleness link resolves: `params.upstream_meta.sha256` still matches the file it names

Writes file names, field names and counts to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REQUIRED_KEYS = ("stage", "run_id", "code_version", "params", "inputs", "outputs", "counts")


def _row_count(path: Path) -> int | None:
    """Rows in a Parquet file, or None for an output that is not Parquet."""
    if path.suffix != ".parquet":
        return None
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    return int(pq.ParquetFile(path).metadata.num_rows)


def check(stage_dir: Path) -> list[str]:
    """Every way `<stage_dir>/_meta.json` fails contract section 10. Empty means it holds."""
    meta_path = stage_dir / "_meta.json"
    if not meta_path.is_file():
        return [f"no _meta.json in {stage_dir}"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    problems: list[str] = []
    missing = [key for key in REQUIRED_KEYS if key not in meta]
    if missing:
        return [f"_meta.json is missing {', '.join(missing)}"]

    outputs = meta["outputs"]
    if not outputs:
        problems.append("_meta.json lists no outputs")
    # Paths are recorded relative to the run directory, which is the parent of the stage
    # directory. Resolving them from here is what makes the hash check a check on the files an
    # investigator would actually open.
    run_dir = stage_dir.parent
    for entry in outputs:
        target = run_dir / entry["path"]
        if not target.is_file():
            problems.append(f"output {entry['path']} does not exist")
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != entry.get("sha256"):
            problems.append(f"{entry['path']} no longer hashes to what _meta.json recorded")
            continue
        rows = _row_count(target)
        if rows is not None and "rows" in entry and rows != entry["rows"]:
            problems.append(f"{entry['path']} holds {rows} rows, _meta.json claims {entry['rows']}")

    counts = meta["counts"]
    read, kept, dropped = counts.get("in"), counts.get("out"), counts.get("dropped")
    if not all(isinstance(value, int) for value in (read, kept, dropped)):
        problems.append("counts.in, counts.out and counts.dropped must all be integers")
    elif read != kept + dropped:
        problems.append(f"counts do not account for every row: {read} != {kept} + {dropped}")
    reasons = counts.get("drop_reasons", {})
    if isinstance(reasons, dict) and isinstance(dropped, int) and sum(reasons.values()) != dropped:
        problems.append(
            f"drop_reasons sum to {sum(reasons.values())}, counts.dropped is {dropped}. A row "
            "dropped for no recorded reason is a row nobody can defend in court."
        )

    inputs = meta["inputs"]
    for entry in inputs:
        source = Path(entry["path"])
        if not source.is_file():
            problems.append(f"input {entry['path']} no longer exists")
        elif hashlib.sha256(source.read_bytes()).hexdigest() != entry.get("sha256"):
            problems.append(f"input {entry['path']} has changed since this stage ran")

    upstream = meta["params"].get("upstream_meta")
    if upstream is None:
        problems.append("params.upstream_meta is absent, so nothing can check staleness")
    elif upstream.get("path") is not None:
        source = Path(upstream["path"])
        if not source.is_file():
            problems.append(f"upstream {upstream['path']} no longer exists")
        elif hashlib.sha256(source.read_bytes()).hexdigest() != upstream["sha256"]:
            problems.append(
                f"stale: {upstream['path']} has changed since {meta['stage']} ran. Re-run it."
            )

    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: check_stage.py <stage-output-dir>\n")
        return 2
    stage_dir = Path(args[0])
    if not stage_dir.is_dir():
        sys.stderr.write(f"check_stage: {stage_dir} is not a directory\n")
        return 2

    problems = check(stage_dir)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_stage: {len(problems)} problems in {stage_dir}\n")
        return 1
    meta = json.loads((stage_dir / "_meta.json").read_text(encoding="utf-8"))
    counts = meta["counts"]
    sys.stderr.write(
        f"check_stage: {stage_dir} OK, stage {meta['stage']}, {len(meta['outputs'])} outputs, "
        f"{counts['in']} in = {counts['out']} out + {counts['dropped']} dropped\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
