#!/usr/bin/env bash
# S11 shipping check: prove the demo runs from a copy of the repo with the answer key and
# the measurements deleted. If any stage the demo touches secretly reads ground_truth/ or
# measurements/, the copy is missing them and the smoke fails here rather than on stage.
#
# The copy keeps data/generated/s10-demo (the precomputed artifact the demo serves) and
# drops only the two trees the brief names. Third-party deps come from the repo venv; the
# chakravyuh package is imported from the COPY via PYTHONPATH, so this genuinely exercises
# the copied source, not the original tree.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$REPO/.venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="python3"
DEMO_RUN="s10-demo"

DEST="$(mktemp -d "${TMPDIR:-/tmp}/chakravyuh-ship.XXXXXX")"
trap 'rm -rf "$DEST"' EXIT

# Copy only what the demo actually touches: the source it imports, the smoke runner, and the
# precomputed artifact it serves. ground_truth/ and measurements/ are deliberately NOT copied,
# so the copy provably has neither — if a stage the demo exercises reaches for either, it will
# fail here on the stripped copy instead of on a projector's laptop.
cp -a "$REPO/src" "$DEST/src"
cp -a "$REPO/scripts" "$DEST/scripts"
mkdir -p "$DEST/data/generated"
cp -a "$REPO/data/generated/$DEMO_RUN" "$DEST/data/generated/$DEMO_RUN"

if [ -e "$DEST/ground_truth" ] || [ -e "$DEST/measurements" ]; then
  echo "FAIL shipping-check: copy is not stripped — ground_truth/ or measurements/ present" >&2
  exit 1
fi

echo "shipping-check: serving demo from stripped copy at $DEST"
PYTHONPATH="$DEST/src" "$VENV_PY" "$DEST/scripts/demo_smoke.py" "$@"
echo "shipping-check: OK — demo serves with no ground_truth/ or measurements/."
