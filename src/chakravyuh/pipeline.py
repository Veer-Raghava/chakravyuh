"""Integrated offline graph-context scoring → leads → signed case pipeline.

Starts from the sealed, normalized observation run produced by KAVACH/SETU.
The legacy stage entry points remain available; this versioned route uses frozen CPU inference.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from chakravyuh.buddhi import production
from chakravyuh.pramaan import stage as proof


def run(
    source: Path,
    output: Path,
    model: Path,
    *,
    start_us: int,
    end_us: int,
    k: int = 20,
    keys_root: Path | None = None,
) -> dict[str, Any]:
    """Preserve source run, freeze observations/model, and produce new signed cases."""
    base = (Path.cwd() / "data/generated").resolve()
    source, output = source.resolve(), output.resolve()
    if base not in source.parents or base not in output.parents:
        raise ValueError("input and output must be named runs under data/generated")
    if output.exists() or source == output or source in output.parents:
        raise ValueError("output must be a fresh independent run")
    if not (source / "sealed/manifest.json").is_file():
        raise ValueError("a KAVACH-sealed observation run is required")
    for name in ("transactions", "addresses", "announcements", "peers"):
        if not (source / "normalised" / f"{name}.parquet").is_file():
            raise ValueError(f"missing normalized {name}")
    # Freeze only observation artifacts, never legacy scores or signed packets.
    output.mkdir(parents=True)
    for name in ("sealed", "normalised", "graph", "signals", "chain"):
        if (source / name).is_dir():
            shutil.copytree(source / name, output / name)
    for name in ("config.effective.json",):
        if (source / name).is_file():
            shutil.copy2(source / name, output / name)
    shutil.copytree(model, output / "detector")
    summary = production.build_run(
        output, output / "detector", start_us=start_us, end_us=end_us, k=k
    )
    keys_root = keys_root or Path.cwd()
    keys = proof.load_or_create_keys(keys_root)
    cases = proof.build_run(output, output, None, keys, keys_root)
    if not all(
        proof.verify_signature(case, keys_root / "keys")
        and proof.verify_replay(output, output, case.name, keys_root)
        for case in cases
    ):
        raise ValueError("new case signature or replay verification failed")
    summary.update(source_run=str(source), output_run=str(output), signed_cases=len(cases))
    (output / "pipeline.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="source", type=Path, required=True)
    parser.add_argument("--out", dest="output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--start-us", type=int, required=True)
    parser.add_argument("--end-us", type=int, required=True)
    parser.add_argument("--leads", type=int, default=20)
    args = parser.parse_args()
    try:
        summary = run(
            args.source,
            args.output,
            args.model,
            start_us=args.start_us,
            end_us=args.end_us,
            k=args.leads,
        )
    except (ValueError, FileNotFoundError) as exc:
        sys.stderr.write(f"pipeline: {exc}\n")
        return 2
    sys.stderr.write(
        f"pipeline: {summary['selected']} review leads, "
        f"{summary['signed_cases']} verified signed cases\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
