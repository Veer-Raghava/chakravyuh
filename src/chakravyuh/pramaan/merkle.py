"""The append-only hash chain across packets.

One line per generated packet: `index  leaf  prev_root`. The leaf is the SHA-256 of the
packet's canonical serialisation; the root after line n chains every leaf before it, so
removing, replacing or reordering any line breaks the recomputed chain from that point
on — which is what "append-only" is checkable to mean.

The log lives at `packets/merkle.log` and is shared by every case in the run. Regenerating
a case appends a duplicate leaf rather than rewriting the line it would have produced,
because rewriting history is the one thing this file must never survive.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

GENESIS: Final[str] = "0" * 64


def canonical(payload: dict[str, object]) -> bytes:
    """The canonical serialisation a hash or signature is computed over.

    Key-sorted, no whitespace, `ensure_ascii` on: the same dict in any process produces
    the same bytes, which is the property the signature and the replay both lean on.
    """
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def leaf(packet_bytes: bytes) -> str:
    """The log's leaf for one packet: the SHA-256 of its canonical serialisation."""
    return hashlib.sha256(packet_bytes).hexdigest()


def root_of(leaves: list[str]) -> str:
    """The Merkle root over the leaves so far, duplicated-padded to a power of two."""
    if not leaves:
        return GENESIS
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(f"{level[i]}{level[i + 1]}".encode()).hexdigest()
            for i in range(0, len(level), 2)
        ]
    return level[0]


def append(log_path: Path, packet_bytes: bytes) -> str:
    """Append one leaf and return the new head. Prints nothing; the caller owns stdout."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    leaves, _ = read(log_path)
    new_leaf = leaf(packet_bytes)
    prev = root_of(leaves)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{len(leaves)}  {new_leaf}  {prev}\n")
    return root_of(leaves + [new_leaf])


def read(log_path: Path) -> tuple[list[str], list[str]]:
    """Parse the log into (leaves, prev_roots). Raises on a malformed line, because a log
    that cannot be parsed is a log someone edited by hand."""
    if not log_path.is_file():
        return [], []
    leaves: list[str] = []
    prevs: list[str] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"merkle log line is malformed: {line[:32]}…")
        leaves.append(parts[1])
        prevs.append(parts[2])
    return leaves, prevs


def verify(log_path: Path) -> tuple[bool, str]:
    """Recompute the chain. Returns (ok, head). A log that fails here was rewritten."""
    try:
        leaves, prevs = read(log_path)
    except ValueError as exc:
        return False, str(exc)
    expected_prev = GENESIS
    for i, (_leaf, prev) in enumerate(zip(leaves, prevs, strict=True)):
        if prev != expected_prev:
            return False, f"chain breaks at line {i}"
        expected_prev = root_of(leaves[: i + 1])
    return True, root_of(leaves)
