"""Run one pipeline stage under wall-clock and peak-RSS measurement, for docs/PERF.md.

Wraps a command, reads its exit code, elapsed seconds and peak resident set (via
`resource.getrusage(RUSAGE_CHILDREN)`, which reports the child's maximum RSS in KiB on
Linux), and prints one `STAGE_RESULT ...` line to stderr. Nothing else about the stage's
output is reprinted. Usage:

    uv run python scripts/stage_time.py --run s10-canonical --stage kavach -- \
        python -m chakravyuh.kavach --in data/generated/s10-canonical/capture ...

The `--` separates the measured command. Stdlib only.
"""

from __future__ import annotations

import argparse
import resource
import subprocess
import sys
import time


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command after `--`")
    args = parser.parse_args(argv)
    command = [part for part in args.command if part != "--"]
    if not command:
        print("stage_time: no command after `--`", file=sys.stderr)
        return 2

    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    started = time.monotonic()
    finished = subprocess.run(command, check=False)
    elapsed = time.monotonic() - started
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    print(
        f"STAGE_RESULT run={args.run} stage={args.stage} exit={finished.returncode} "
        f"seconds={elapsed:.1f} peak_kib={max(peak, before)}",
        file=sys.stderr,
    )
    return finished.returncode


if __name__ == "__main__":
    raise SystemExit(main())
