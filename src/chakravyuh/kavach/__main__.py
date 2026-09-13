"""`python -m chakravyuh.kavach --in <capture> --out data/generated/<run>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chakravyuh.kavach.schema import CaptureFormatError
from chakravyuh.kavach.seal import InputPathError, resolve_out, seal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chakravyuh.kavach",
        description="Seal a Bitcoin capture into an accountable, typed, hashed intake copy.",
    )
    parser.add_argument(
        "--in",
        dest="capture",
        type=Path,
        required=True,
        help=(
            "capture file or a directory of them, which must sit under data/. An evaluator's "
            "file is copied there first: a stage that can be pointed anywhere is a stage that "
            "can be pointed at the answer key."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out",
        type=Path,
        required=True,
        help="run directory under data/generated/. sealed/ is written inside it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = seal(args.capture, resolve_out(args.out))
    except (InputPathError, CaptureFormatError) as exc:
        # stderr, not stdout: T20 bans print and the contract reserves stdout for peek.py.
        sys.stderr.write(f"kavach: {exc}\n")
        return 2
    sys.stderr.write(f"kavach: sealed, manifest at {manifest}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
