"""Which revision of the code produced an artifact.

`docs/DATA-CONTRACTS.md` asks for `code_version` as a git sha and `tool_version` as the
package version, and the two are not the same fact. A packet that cites a seal has to be
traceable to the commit that produced it, or a replay cannot show it re-ran the same code.
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

UNKNOWN: str = "unknown"
"""What `code_version` says when git cannot answer. Honest, unlike a package version."""

_TIMEOUT_S: int = 10


def _git(args: list[str], root: Path) -> str | None:
    """Run a git subcommand. Returns stdout stripped, or None if git could not answer.

    Local only: no network, and none of the subcommands here contact a remote.
    """
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


@lru_cache(maxsize=1)
def code_version() -> str:
    """The revision this code ran from, as `<12 hex>` or `<12 hex>-dirty`.

    The `-dirty` suffix matters: a seal produced from a modified tree is not reproducible from
    the commit it names, and silently claiming otherwise is the failure mode this field exists
    to prevent. Only tracked modifications count — an untracked scratch file cannot change a
    sealed byte, and counting it would make the value flap between runs.

    The repository root is taken from this file's location rather than the current directory,
    so the value describes the code that ran and not wherever the caller happened to stand.
    """
    root = Path(__file__).resolve().parents[2]
    head = _git(["rev-parse", "HEAD"], root)
    if head is None:
        return UNKNOWN
    changed = _git(["status", "--porcelain", "--untracked-files=no"], root)
    return f"{head[:12]}{'-dirty' if changed else ''}"
