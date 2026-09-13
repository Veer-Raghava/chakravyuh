"""`python -m chakravyuh.setu --in data/generated/<run>/sealed --out data/generated/<run>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chakravyuh.setu.schema import SealedInputError
from chakravyuh.setu.stage import InputPathError, normalise_run, resolve_in, resolve_out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chakravyuh.setu",
        description="Split the announcement grain from the transaction grain, and enrich peers.",
    )
    parser.add_argument(
        "--in",
        dest="sealed",
        type=Path,
        required=True,
        help=(
            "the sealed/ directory written by KAVACH, which must sit under data/. A stage that "
            "can be pointed anywhere is a stage that can be pointed at the answer key."
        ),
    )
    parser.add_argument(
        "--out",
        dest="out",
        type=Path,
        required=True,
        help="run directory under data/generated/. normalised/ is written inside it.",
    )
    parser.add_argument(
        "--vendor",
        dest="vendor",
        type=Path,
        default=None,
        help=(
            "override the offline enrichment root, default vendor/. Absent or empty means the "
            "geo, ASN and net_class columns are null and the run completes anyway."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        meta = normalise_run(resolve_in(args.sealed), resolve_out(args.out), args.vendor)
    except (InputPathError, SealedInputError) as exc:
        # stderr, not stdout: T20 bans print and the contract reserves stdout for peek.py.
        sys.stderr.write(f"setu: {exc}\n")
        return 2
    sys.stderr.write(f"setu: normalised, meta at {meta}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
