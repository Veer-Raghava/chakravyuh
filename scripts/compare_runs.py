"""Compare two runs of the same generator with only the unreproducible fields masked.

`diff -r -x _meta.json` would be shorter and would be wrong. Excluding the manifest drops
every sha256, every row count and every drop reason from the comparison, which is most of what
a determinism gate exists to check, and no per-run self-assertion ever compares run A to run B.

So every file is compared as bytes, except the two that carry a wall clock, which are compared
after exactly the unreproducible fields are removed: `_meta.json` loses `run_id`, the directory
name and therefore different by construction, and the two timestamps section 10 requires;
`sealed/manifest.json` loses `sealed_at_us`. Everything else in both is compared, hashes and
counts included.

Used by `make verify-s01` and `make verify-s03`, and imported by `tests/test_chain.py`, so the
byte gate and the in-process gate cannot drift apart. Stdlib only, like `peek.py`, so it runs
under the system interpreter. Prints paths and field names, never a row of data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Field name to the file it is stripped from. A wall clock is excluded from every hash and
# every comparison, never from the diff alone: KAVACH records the masked hash of
# `sealed/manifest.json` rather than its raw one for the same reason.
MASKED_BY_FILE = {
    "_meta.json": ("run_id", "started_at_us", "finished_at_us"),
    "manifest.json": ("sealed_at_us",),
}
MASKED = MASKED_BY_FILE["_meta.json"]
MANIFEST = "_meta.json"


def canonical_meta(payload: bytes, name: str = MANIFEST) -> str:
    """A manifest with its unreproducible fields removed, key-sorted so order cannot lie."""
    node = json.loads(payload.decode("utf-8"))
    if not isinstance(node, dict):
        raise TypeError(f"a {name} must hold a JSON object, got {type(node).__name__}")
    for field in MASKED_BY_FILE[name]:
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
        base = Path(name).name
        if base in MASKED_BY_FILE:
            if canonical_meta(mine, base) != canonical_meta(yours, base):
                masked = ", ".join(MASKED_BY_FILE[base])
                out.append(f"{name}: differs in a field other than {masked}")
        elif mine != yours:
            out.append(f"{name}: differs, {len(mine)} bytes against {len(yours)}")
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    except_names: list[str] = []
    if args and args[0] == "--except":
        except_names, args = args[1].split(","), args[2:]
    if len(args) != 2:
        print("usage: compare_runs.py [--except file,file] <tree-a> <tree-b>", file=sys.stderr)
        return 2
    left, right = Path(args[0]), Path(args[1])
    for root in (left, right):
        if not root.is_dir():
            print(f"compare_runs: {root} is not a directory", file=sys.stderr)
            return 2
    skipped = [
        f"except {name}"
        for name in except_names
        if (left / name).is_file() or (right / name).is_file()
    ]
    found = [line for line in differences(left, right) if _name_of(line) not in except_names]
    for line in skipped:
        print(f"  {line}", file=sys.stderr)
    for line in found:
        print(f"  {line}", file=sys.stderr)
    return 1 if found else 0


def _name_of(line: str) -> str:
    """The file name a difference line names, for `--except` filtering.

    Difference lines come in two shapes: `only in <dir>: <name>` and
    `<name>: differs...`. The colon split cannot tell them apart, so an
    "only in" line is taken by its last whitespace token instead.
    """
    if line.startswith("only in "):
        return line.rsplit(" ", 1)[-1]
    for token in line.split(":"):
        token = token.strip()
        if "/" in token or token.endswith(".json") or token.endswith(".parquet"):
            return token.rsplit("/", 1)[-1]
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
