## S10 · Scale

**Goal.** One million capture rows end to end, resumable, with recorded timings.

**Reads.** Everything. **Writes.** A full run under `data/generated/`, `docs/PERF.md` with
per-stage wall clock and peak memory plus the machine specs, `docs/DEMO-RUN.md` naming the
precomputed artifact paths.

**Definition of done.** `make demo-full` from an empty data directory, and `docs/PERF.md` exists
with per-stage timings.

**Known traps.** Optimising before profiling. A run that is not resumable, which turns any failure
into a full restart. Validation checks only ever run at fixture scale, when distribution checks fail
differently at a million rows. Losing determinism at scale through parallelism with unordered
reduction. Making live regeneration the demo path.

---
