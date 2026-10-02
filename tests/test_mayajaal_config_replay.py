"""Saved effective configuration must reproduce a world, not just parameter values."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from chakravyuh.mayajaal import adversary, chain, config, network

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("seed", [42, 1337])
def test_sorted_effective_config_replays_chain_and_campaigns(tmp_path: Path, seed: int) -> None:
    original = config.load(REPO / "run_config.json", seed=seed, n_txs=1200, n_entities=300)
    saved = tmp_path / "config.effective.json"
    saved.write_text(json.dumps(original.effective, sort_keys=True), encoding="utf-8")
    # The saved file already records transaction count. No repeat CLI override is necessary.
    restored = config.load(saved, anchor=REPO)
    assert restored.n_txs == original.n_txs
    assert restored.effective == original.effective

    left_adversary = adversary.Adversary(original, random.Random(seed + 1))
    right_adversary = adversary.Adversary(restored, random.Random(seed + 1))
    left = chain.generate(original, random.Random(seed), left_adversary.plan)
    right = chain.generate(restored, random.Random(seed), right_adversary.plan)
    assert left.txs == right.txs
    assert left_adversary.records() == right_adversary.records()
    assert left.population.entities == right.population.entities
    assert network.build(original, left, random.Random(seed + 2)) == network.build(
        restored, right, random.Random(seed + 2)
    )


def test_explicit_transaction_override_wins_over_saved_count(tmp_path: Path) -> None:
    original = config.load(REPO / "run_config.json", n_txs=1200, n_entities=300)
    saved = tmp_path / "config.effective.json"
    saved.write_text(json.dumps(original.effective, sort_keys=True), encoding="utf-8")
    restored = config.load(saved, n_txs=900, anchor=REPO)
    assert restored.n_txs == 900
    assert restored.effective["n_transactions"] == 900
