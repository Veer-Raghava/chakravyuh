"""`python -m chakravyuh.pramaan --in data/generated/<run> --out data/generated/<run>`.

Read-only over the run, writes only `packets/` inside it, signs with the key pair in
`keys/` (gitignored). The Merkle head goes to stdout; everything else goes to stderr.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chakravyuh.pramaan.stage import (
    InputPathError,
    build_run,
    git_root,
    load_or_create_keys,
    resolve_in,
    resolve_out,
    verify_replay,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chakravyuh.pramaan",
        description="Sign one alert into a replayable evidence packet with a BNSS notice.",
    )
    parser.add_argument(
        "--in",
        dest="run_in",
        type=Path,
        required=True,
        help="the run directory holding the upstream stages' outputs. Must sit under "
        "data/generated/: a stage that can be pointed anywhere can be pointed at the "
        "answer key.",
    )
    parser.add_argument(
        "--out",
        dest="out",
        type=Path,
        required=True,
        help="run directory under data/generated/. packets/ is written inside it.",
    )
    parser.add_argument(
        "--case",
        dest="case",
        type=str,
        default=None,
        help="one alert id to packet. Without it, every alert is packeted.",
    )
    parser.add_argument(
        "--generate-keys",
        dest="generate_keys",
        action="store_true",
        help="create keys/ed25519.seed and keys/ed25519.pub if absent, then exit.",
    )
    parser.add_argument(
        "--verify-replay",
        dest="verify_replay",
        action="store_true",
        help="do not write; regenerate the packet for --case and assert byte-identity.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    keys = load_or_create_keys(git_root())
    if args.generate_keys:
        sys.stderr.write("pramaan: keys present under keys/ (created if absent)\n")
        return 0
    try:
        run_in = resolve_in(args.run_in)
        out = resolve_out(args.out)
    except InputPathError as exc:
        sys.stderr.write(f"pramaan: {exc}\n")
        return 2
    try:
        if args.verify_replay:
            if not args.case:
                sys.stderr.write("pramaan: --verify-replay needs --case\n")
                return 2
            if verify_replay(run_in, out, args.case, git_root()):
                sys.stdout.write("pramaan: replay verified, byte-identical\n")
                return 0
            sys.stderr.write("pramaan: replay MISMATCH, the packet is not reproducible\n")
            return 1
        written = build_run(run_in, out, args.case, keys, git_root())
        sys.stderr.write(f"pramaan: {len(written)} packet(s) written under {out / 'packets'}\n")
        return 0
    except InputPathError as exc:
        sys.stderr.write(f"pramaan: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
