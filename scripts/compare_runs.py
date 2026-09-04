"""Compare two runs of the same generator with only the unreproducible fields masked.

`diff -r -x _meta.json` would be shorter and would be wrong. Excluding the manifest drops
every sha256, every row count and every drop reason from the comparison, which is most of what
a determinism gate exists to check, and no per-run self-assertion ever compares run A to run B.

So every file is compared as bytes, except one named `_meta.json`, which is compared after
exactly three fields are removed: `run_id`, which is the directory name and therefore differs
by construction, and the two wall-clock timestamps section 10 requires. Everything else in the
manifest is compared, hashes and counts included.

Used by `make verify-s01` and imported by `tests/test_chain.py`, so the byte gate and the
in-process gate cannot drift apart. Stdlib only, like `peek.py`, so it runs under the system
interpreter. Prints paths and field names, never a row of data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MASKED = ("run_id", "started_at_us", "finished_at_us")
MANIFEST = "_meta.json"


def canonical_meta(payload: bytes) -> str:
    """A manifest with the three unreproducible fields removed, key-sorted so order cannot lie."""
    node = json.loads(payload.decode("utf-8"))
    if not isinstance(node, dict):
        raise TypeError(f"a {MANIFEST} must hold a JSON object, got {type(node).__name__}")
    for field in MASKED:
        node.pop(field, None)
    return json.dumps(node, indent=2, sort_keys=True)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def differences(left: Path, right: Path) -> list[str]:
    """Every way the two trees disagree. Empty means identical for determinism purposes."""
    here, there = _files(left), _files(right)
    out = [f"only in {left}: {name}" for name in sorted(set(here) - set(there))]
    out += [f"only in {right}: {name}" for name in sorted(set(there) - set(here))]
    for name in sorted(set(here) & set(there)):
        mine, yours = here[name].read_bytes(), there[name].read_bytes()
        if Path(name).name == MANIFEST:
            if canonical_meta(mine) != canonical_meta(yours):
                out.append(f"{name}: differs in a field other than {', '.join(MASKED)}")
        elif mine != yours:
            out.append(f"{name}: differs, {len(mine)} bytes against {len(yours)}")
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: compare_runs.py <tree-a> <tree-b>", file=sys.stderr)
        return 2
    left, right = Path(args[0]), Path(args[1])
    for root in (left, right):
        if not root.is_dir():
            print(f"compare_runs: {root} is not a directory", file=sys.stderr)
            return 2
    found = differences(left, right)
    for line in found:
        print(f"  {line}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
