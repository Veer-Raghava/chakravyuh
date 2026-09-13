"""Check a `sealed/` directory against contract section 3, from outside the code that wrote it.

The tests assert what KAVACH intended. This asserts what is on disk, using nothing KAVACH
imports, so a bug that lives in a shared helper cannot hide from both at once. Stdlib plus
pyarrow for the Parquet footer, like `peek.py`.

Five things, in the order they would bite:

1. the four expected files exist
2. `rows_read == rows_sealed + rows_rejected`, and both Parquet row counts match the manifest
3. `INPUT.sha256` re-hashes to the same digest the manifest recorded for every input
4. the masked hash of `manifest.json` recomputes to what `_meta.json` recorded
5. the staleness link resolves, or is explicitly null

Writes file names, field names and counts to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EXPECTED_FILES = ("rows.parquet", "rejected.parquet", "INPUT.sha256", "manifest.json", "_meta.json")
MANIFEST_MASKED = ("sealed_at_us",)


def _row_count(path: Path) -> int:
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    return int(pq.ParquetFile(path).metadata.num_rows)


def _masked_manifest_sha256(manifest: dict[str, object]) -> str:
    masked = {key: value for key, value in manifest.items() if key not in MANIFEST_MASKED}
    return hashlib.sha256(json.dumps(masked, indent=2, sort_keys=True).encode("utf-8")).hexdigest()


def check(sealed: Path) -> list[str]:
    """Every way `sealed/` fails the contract. Empty means it holds."""
    problems: list[str] = []

    missing = [name for name in EXPECTED_FILES if not (sealed / name).is_file()]
    if missing:
        return [f"missing: {', '.join(missing)}"]

    manifest = json.loads((sealed / "manifest.json").read_text(encoding="utf-8"))
    meta = json.loads((sealed / "_meta.json").read_text(encoding="utf-8"))

    read = manifest["rows_read"]
    kept = manifest["rows_sealed"]
    dropped = manifest["rows_rejected"]
    if read != kept + dropped:
        problems.append(f"manifest arithmetic: {read} != {kept} + {dropped}")

    actual_kept = _row_count(sealed / "rows.parquet")
    actual_dropped = _row_count(sealed / "rejected.parquet")
    if actual_kept != kept:
        problems.append(f"rows.parquet holds {actual_kept} rows, manifest claims {kept}")
    if actual_dropped != dropped:
        problems.append(f"rejected.parquet holds {actual_dropped} rows, manifest claims {dropped}")

    counts = meta.get("counts", {})
    if (counts.get("in"), counts.get("out"), counts.get("dropped")) != (read, kept, dropped):
        problems.append("_meta.json counts disagree with manifest.json")

    # Per-input row counts must add up to what was read, and every one must be an integer. This
    # is the check that catches a shard read short: the totals can still reconcile against the
    # outputs while one input silently contributed fewer rows than it held.
    inputs = meta.get("inputs", [])
    if not inputs:
        problems.append("_meta.json lists no inputs")
    if any(not isinstance(entry.get("rows"), int) for entry in inputs):
        problems.append("a _meta.json input has a non-integer row count, so it cannot be summed")
    elif sum(entry["rows"] for entry in inputs) != counts.get("in"):
        problems.append(
            f"_meta.json input rows sum to {sum(e['rows'] for e in inputs)}, counts.in is "
            f"{counts.get('in')}"
        )
    # The same files, in the same order, as manifest.input_files. If these two lists disagree the
    # custody record and the input digest describe different runs.
    if [entry.get("path") for entry in inputs] != [
        entry.get("path") for entry in manifest["input_files"]
    ]:
        problems.append("_meta.json inputs and manifest.input_files are not the same files")

    recorded = {
        line.split("  ", 1)[1]: line.split("  ", 1)[0]
        for line in (sealed / "INPUT.sha256").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    for entry in manifest["input_files"]:
        name = Path(entry["path"]).name
        if recorded.get(name) != entry["sha256"]:
            problems.append(f"INPUT.sha256 disagrees with the manifest for {name}")
            continue
        source = Path(entry["path"])
        if source.is_file():
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                problems.append(f"{name} on disk no longer hashes to what was sealed")

    declared = meta.get("params", {}).get("manifest", {})
    if declared.get("sha256_masked") != _masked_manifest_sha256(manifest):
        problems.append("manifest.json does not match the masked hash recorded in _meta.json")
    if "sealed_at_us" not in manifest:
        problems.append("manifest.json has no sealed_at_us")
    for output in meta.get("outputs", []):
        if Path(output["path"]).name == "manifest.json":
            problems.append(
                "manifest.json is hashed raw in _meta.json outputs. It carries a wall clock, so "
                "that hash cannot reproduce; record the masked hash instead."
            )

    upstream = meta.get("params", {}).get("upstream_meta")
    if upstream is None:
        problems.append("_meta.json has no upstream_meta, so nothing can check staleness")
    elif upstream.get("path") is not None:
        source = Path(upstream["path"])
        if not source.is_file():
            problems.append(f"upstream {upstream['path']} no longer exists")
        elif hashlib.sha256(source.read_bytes()).hexdigest() != upstream["sha256"]:
            problems.append(
                f"stale: {upstream['path']} has changed since this seal. Re-run KAVACH."
            )

    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.stderr.write("usage: check_sealed.py <run-dir-or-sealed-dir>\n")
        return 2
    target = Path(args[0])
    sealed = target if target.name == "sealed" else target / "sealed"
    if not sealed.is_dir():
        sys.stderr.write(f"check_sealed: {sealed} is not a directory\n")
        return 2

    problems = check(sealed)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_sealed: {len(problems)} problems in {sealed}\n")
        return 1
    manifest = json.loads((sealed / "manifest.json").read_text(encoding="utf-8"))
    sys.stderr.write(
        f"check_sealed: {sealed} OK, {manifest['rows_read']} read = "
        f"{manifest['rows_sealed']} sealed + {manifest['rows_rejected']} rejected\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
