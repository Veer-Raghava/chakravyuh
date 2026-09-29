"""The external-validation leg: absent input is honest, present input produces real numbers.

Two properties, and they are the whole module. When `vendor/elliptic/` is empty the block must
report its absence rather than a zero, because a zero is a claim about a model and this is a
claim about a directory. When files are there, every figure must fall out of them — so the
present-case test builds a small Elliptic-shaped dataset whose signal is known by construction
and checks the model recovered it, not merely that the call returned.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from chakravyuh.eval import external

REPO = Path(__file__).resolve().parent.parent


def _write_elliptic(dir_: Path, n: int = 400, seed: int = 0) -> None:
    """A minimal stand-in: three features, 49 ordinal time steps, class 1 illicit / 2 licit.

    `f0` separates the classes and the others are noise, so a working recipe has to find `f0` and
    a broken one cannot get lucky. The time step is assigned in file order so the time-ordered
    split and a random split would choose visibly different test sets.
    """
    rng = np.random.default_rng(seed)
    rows = ["txId,time,f0,f1,f2"]
    classes = ["txId,class"]
    for i in range(n):
        step = 1 + (i * 49) // n
        x = rng.normal(size=3)
        illicit = i % 2 == 0
        x[0] += 3.0 if illicit else -3.0
        rows.append(f"{i},{step}," + ",".join(f"{v:.4f}" for v in x))
        classes.append(f"{i},{1 if illicit else 2}")
    # A handful of unlabelled rows, which every Elliptic mirror has and no leg may guess at.
    for i in range(n, n + 20):
        rows.append(f"{i},49," + ",".join(f"{v:.4f}" for v in rng.normal(size=3)))
        classes.append(f"{i},unknown")
    (dir_ / "elliptic_txs_features.csv").write_text("\n".join(rows), encoding="utf-8")
    (dir_ / "elliptic_txs_classes.csv").write_text("\n".join(classes), encoding="utf-8")


def test_absent_dataset_is_honest_not_zero(tmp_path: Path) -> None:
    block = external.elliptic_block(tmp_path, train_fraction=0.7, seed=0, coverage_target=0.9)
    assert block == {"available": False, "reason": "dataset_not_vendored"}
    # No figure may be present under any key: a reader must not be able to lift a number out of
    # an absence and quote it.
    assert not any(key in block for key in ("pr_auc", "roc_auc", "f1", "n_test"))


def test_present_dataset_trains_the_shared_recipe(tmp_path: Path) -> None:
    _write_elliptic(tmp_path)
    block = external.elliptic_block(tmp_path, train_fraction=0.7, seed=0, coverage_target=0.9)

    assert block["available"] is True
    assert block["protocol"] == "inductive_time_ordered"
    assert block["dataset"] == "elliptic"
    # The split is the recipe's: every labelled row lands on one side, unlabelled rows in neither.
    assert block["n_train"] + block["n_test"] == 400
    assert block["n_train"] > 0 and block["n_test"] > 0
    # The signal is separable by construction, so a working recipe must beat chance comfortably.
    assert block["pr_auc"] > 0.8, block
    assert block["roc_auc"] > 0.8, block
    assert 0.0 <= block["f1"] <= 1.0
    # Provenance: the hash is of the file that is actually there.
    import hashlib

    expected = hashlib.sha256((tmp_path / "elliptic_txs_features.csv").read_bytes()).hexdigest()
    assert block["source_sha256"] == expected


def test_elliptic_pp_filenames_are_accepted(tmp_path: Path) -> None:
    """The Elliptic++ repository ships the same data under shorter names, and the operator should
    not have to rename what they downloaded. Same run, same numbers, either naming."""
    _write_elliptic(tmp_path)
    for classic, short in (
        ("elliptic_txs_features.csv", "txs_features.csv"),
        ("elliptic_txs_classes.csv", "txs_classes.csv"),
    ):
        (tmp_path / classic).rename(tmp_path / short)
    block = external.elliptic_block(tmp_path, train_fraction=0.7, seed=0, coverage_target=0.9)
    assert block["available"] is True
    assert block["source_name"] == "txs_features.csv"
    assert block["pr_auc"] > 0.8


def test_the_command_line_entry_point_actually_runs() -> None:
    """`python -m chakravyuh.eval.external` must do something, not merely import.

    A module whose `__main__` guard is missing imports cleanly, passes every test that calls its
    functions, and exits 0 in silence — so the Makefile target that calls it would "succeed"
    having measured nothing. `--help` is enough to catch that: it is argparse's, so it needs no
    dataset and writes no run directory, and it is silent exactly when the guard is absent.
    """
    finished = subprocess.run(
        [sys.executable, "-m", "chakravyuh.eval.external", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert finished.returncode == 0, finished.stderr[-2000:]
    # Silence is the failure being guarded against, so assert on the message, not just the code.
    assert "--vendor" in finished.stdout, finished.stdout
