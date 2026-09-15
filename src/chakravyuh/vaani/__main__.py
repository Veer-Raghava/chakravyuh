"""`python -m chakravyuh.vaani --in data/generated/<run> --out data/generated/<run>`.

No eval import, no flag that names a path outside the observable tree. `--in` and `--out`
must both resolve under `data/generated/`, which is the stage guard: the answer key is a
sibling tree and cannot be reached by any invocation of this module.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chakravyuh.vaani.stage import (
    InputPathError,
    build_run,
    resolve_in,
    resolve_out,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chakravyuh.vaani",
        description="Turn risk scores into alerts with evidence and counter-evidence.",
    )
    parser.add_argument(
        "--in",
        dest="run_in",
        type=Path,
        required=True,
        help=(
            "the run directory holding scores/, signals/ and graph/. Must sit under "
            "data/generated/: a stage that can be pointed anywhere can be pointed at the "
            "answer key."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out",
        type=Path,
        required=True,
        help="run directory under data/generated/. alerts/ is written inside it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_in = resolve_in(args.run_in)
        out = resolve_out(args.out)
    except InputPathError as exc:
        # stderr, not stdout: T20 bans print and the contract reserves stdout for peek.py.
        sys.stderr.write(f"vaani: {exc}\n")
        return 2
    try:
        meta = build_run(run_in, out)
    except InputPathError as exc:
        sys.stderr.write(f"vaani: {exc}\n")
        return 2
    sys.stderr.write(f"vaani: alerts written, meta at {meta}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
