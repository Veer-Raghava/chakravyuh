"""`python -m chakravyuh.mayajaal` — the command line for the generator.

MAYAJAAL-SPEC's own example is `mayajaal --txs 100000 --seed 42`, and those two plus the entity
count are the only parameters this CLI may override. Everything else comes from
run_config.json, whose effective form is copied into the run directory so a run always carries
the numbers that produced it.

One program, one process, one run: the chain, the campaigns that compete inside it, the peer
network that carries it and the capture an observer would have recorded are all built here in
sequence. Nothing reads back what an earlier layer wrote, because a layer that reloads its own
output is a layer that can disagree with it.

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

from chakravyuh.mayajaal import adversary, chain, config, network, writers

LOG = logging.getLogger("mayajaal")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mayajaal", description="Generate the MAYAJAAL chain.")
    parser.add_argument("--config", type=Path, default=Path("run_config.json"))
    parser.add_argument("--out", type=Path, required=True, help="run directory to write")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--txs", type=int, default=None, help="payments, excluding coinbase")
    parser.add_argument("--entities", type=int, default=None)
    # The chain layer alone, for S01's gate. Without this, S01's verify target runs the whole
    # generator, so a change to the network layer reddens S01 as well as S02 and the failure
    # names the wrong stage. `writers.write_run` already treats `net=None` as a chain-only run.
    parser.add_argument(
        "--chain-only",
        action="store_true",
        help="build the chain and campaigns only, skipping the peer network and the capture",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    args = _parser().parse_args(argv)
    cfg = config.load(args.config, seed=args.seed, n_txs=args.txs, n_entities=args.entities)

    # The only clock read in the stage. Section 10 requires wall-clock start and finish, which
    # is why scripts/compare_runs.py masks exactly those two fields plus the run id when it
    # compares two runs: they are the one part of a run that cannot be reproducible.
    started_at_us = time.time_ns() // 1000

    # One generator per layer, each seeded from `cfg.seed` alone. Separate streams rather than
    # one shared one, so a change to the chain's number of draws cannot silently reshape the
    # peer graph, and a run stays reproducible from the seed in `config.effective.json`.
    adv = adversary.Adversary(cfg=cfg, rng=random.Random(cfg.seed + 1))
    run = chain.generate(cfg, random.Random(cfg.seed), adv.plan)
    adv.apply_typologies(run.population)
    net = None if args.chain_only else network.build(cfg, run, random.Random(cfg.seed + 2))
    writers.write_run(
        run,
        cfg,
        args.out,
        started_at_us=started_at_us,
        finished_at_us=time.time_ns() // 1000,
        net=net,
        campaigns=adv.records(),
    )
    carried = (
        "chain only"
        if net is None
        else f"{len(net.topology.nodes)} nodes, {len(net.capture)} announcements"
    )
    LOG.info(
        "mayajaal: %d transactions in %d blocks, %d entities, multi-input rate %.3f, "
        "%d campaigns, %s, out %s",
        len(run.txs),
        len(run.blocks),
        cfg.world.n_entities,
        run.multi_input_rate,
        len(adv.records()),
        carried,
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
