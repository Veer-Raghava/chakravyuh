## S00 · Skeleton and contracts

**Goal.** The full directory tree, dependency pinning, the Makefile, `scripts/peek.py`, the
fixture set, the contract tests, and this file split into per-stage briefs. No pipeline logic.

**Reads.** `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/DATA-CONTRACTS.md`, `docs/STAGE-BRIEFS.md`.

**Writes.** The tree with `__init__.py` and a one-line ownership docstring per package.
`pyproject.toml` with exact pins. `Makefile` with `setup`, `fixtures`, `verify`, `verify-s00`
through `verify-s11`, `verify-determinism`, `verify-contracts`, `verify-replay`, `validate-data`,
`peek`, `api`, `demo`, `demo-full`, `demo-reset`, `clean`. `scripts/peek.py`. `data/fixtures/`
with the ~200 row capture in CSV, JSONL and XML at seed 42 plus `fixtures/README.md`.
`tests/test_contracts.py`. `docs/stages/*.md`. Empty `docs/EXPLAIN.md` and `docs/DECISIONS.md`.

**Definition of done.** `make verify-s00`

**Known traps.** Missing `__init__.py`, so nothing imports. Fixtures containing only the happy
path, which silently poisons every later stage. A `verify-sNN` stub that exits zero instead of
failing with a clear message, which lets a stage pass before it exists. `peek.py` printing a full
identifier.

---
