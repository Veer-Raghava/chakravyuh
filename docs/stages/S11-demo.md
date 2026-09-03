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
