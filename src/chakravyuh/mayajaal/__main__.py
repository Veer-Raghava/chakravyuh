"""`python -m chakravyuh.mayajaal` — the command line for the chain generator.

MAYAJAAL-SPEC's own example is `mayajaal --txs 100000 --seed 42`, and those two plus the entity
count are the only parameters this CLI may override. Everything else comes from
run_config.json, whose effective form is copied into the run directory so a run always carries
the numbers that produced it.

`--out` is the only path argument in the whole stage. The answer key directory is derived from
it, never passed in, which is what keeps every label inside one quarantined tree.

Progress goes to the log, never to stdout, and never contains a row of data.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from pathlib import Path

from chakravyuh.mayajaal import chain, config, writers

LOG = logging.getLogger("mayajaal")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mayajaal", description="Generate the MAYAJAAL chain.")
    parser.add_argument("--config", type=Path, default=Path("run_config.json"))
    parser.add_argument("--out", type=Path, required=True, help="run directory to write")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--txs", type=int, default=None, help="payments, excluding coinbase")
    parser.add_argument("--entities", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    args = _parser().parse_args(argv)
    cfg = config.load(args.config, seed=args.seed, n_txs=args.txs, n_entities=args.entities)

    # The only clock read in the stage. Section 10 requires wall-clock start and finish, which
    # is why scripts/compare_runs.py masks exactly those two fields plus the run id when it
    # compares two runs: they are the one part of a run that cannot be reproducible.
    started_at_us = time.time_ns() // 1000
    run = chain.generate(cfg, random.Random(cfg.seed))
    writers.write_run(
        run,
        cfg,
        args.out,
        started_at_us=started_at_us,
        finished_at_us=time.time_ns() // 1000,
    )
    LOG.info(
        "mayajaal: %d transactions in %d blocks, %d entities, multi-input rate %.3f, out %s",
        len(run.txs),
        len(run.blocks),
        cfg.world.n_entities,
        run.multi_input_rate,
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
