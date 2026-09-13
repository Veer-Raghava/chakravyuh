## S11 · Demo hardening

**Goal.** One command starts everything from precomputed artifacts, every optional dependency has a
tested fallback, and the five beats run cold and offline.

**Reads.** `docs/DEMO-RUN.md`, `docs/DEMO-CASES.md`, `docs/DRISHTI-SPEC.md`.

**Writes.** `make demo`, `make demo-reset`, fallback tests for Kùzu absent, GeoLite2 absent, no GPU
and no model file, an airplane-mode test wired into `verify`, and `docs/DEMO-SCRIPT.md` with the
five beats, the exact keystrokes, the three demo txids and the one line spoken per beat.

**Definition of done.** `make demo` from a cold start with networking disabled, and every fallback
test passing.

**Known traps.** A demo that needs the network for a font, which is why the fonts are vendored. A
layout that breaks at 1366x768, which is what venue projectors often are. A demo that can only be
run once because there is no reset. Beats that only work in one order. A fallback that is described
in a document rather than proven by a test.

**Runbook note, added at S03.** An evaluator's own capture file has to be copied under `data/`
before it can be sealed. KAVACH's `--in` is allowlisted to that directory, so a file sitting on a
USB stick or in `~/Downloads` is refused by design rather than by accident. The demo script's
"seal the evaluator's file" beat is therefore two commands, not one:

```
cp /path/to/their/capture.csv data/incoming/
uv run python -m chakravyuh.kavach --in data/incoming/capture.csv --out data/generated/<run>
```

Reasoning is in `docs/DECISIONS.md` under the `--in` allowlist entry. Do not present the copy as
a workaround: it is the point at which an outside file enters the tree the tool is permitted to
read, and it is also what makes `sealed/INPUT.sha256` a hash of a file that is still on disk to
re-hash later.
