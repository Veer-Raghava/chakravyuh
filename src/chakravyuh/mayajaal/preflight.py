"""The pre-write guard: refuse to write a run over the bytes of a different run.

`writers.py` cannot do this itself. It is the one file allowed to name the quarantine
directory, and it pays for that permission with a test proving it never opens a file except
to write, so it cannot compare what is already on disk. This module can, and it stays
outside the quarantine by never naming it: both directories arrive as arguments.

The only file this module ever opens is one named `_meta.json`. Law 2 rule 5 forbids a
manifest from carrying a label, which makes a manifest the one file in either tree that a
non-quarantined module can safely look at.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Slot:
    """One directory a run owns, and the manifest that says which run wrote it."""

    directory: Path
    manifest: Path


def _recorded_hash(manifest: Path) -> str | None:
    """The config hash a previous run left behind, or None if there is nothing to trust."""
    if not manifest.is_file():
        return None
    try:
        node = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(node, dict):
        return None
    found = node.get("config_sha256")
    return found if isinstance(found, str) else None


def refuse_to_clobber(slots: Sequence[Slot], *, config_sha256: str) -> None:
    """Raise unless every directory that already exists was written by this same config.

    Decided on content, never on mtime. An identical config hash means the same run being
    regenerated, and a run is deterministic, so overwriting rewrites the same bytes. Anything
    else is two different runs sharing one name, which passes every schema check downstream
    and quietly makes the answer key disagree with the data it answers for.

    A directory that exists with no readable manifest is the crashed-midway case and is
    refused too: the write that would have recorded which run owns those bytes is exactly the
    write that did not happen.
    """
    stale = [(slot, _recorded_hash(slot.manifest)) for slot in slots if slot.directory.exists()]
    stale = [(slot, found) for slot, found in stale if found != config_sha256]
    if not stale:
        return

    lines = [
        "refusing to write over a different run.",
        f"  this run's config sha256:  {config_sha256}",
    ]
    for slot, found in stale:
        lines.append(f"  {slot.directory}: {found or '(no manifest, so a half-written run)'}")
    lines.append("  Pick another --out, or delete both directories by hand:")
    lines.extend(f"    rm -rf {slot.directory}" for slot in slots)
    raise FileExistsError("\n".join(lines))
