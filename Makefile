# CHAKRAVYUH orchestrator. There is no workflow engine; this file is it.
#
# A stage is finished when its verify-sNN target exits zero. Every stage that does
# not exist yet has a target that exits NON-zero and names its own brief, because a
# stub that exits zero lets a later session declare a stage done before it is built.

.DEFAULT_GOAL := help
SHELL := /bin/bash

# Use the project venv when uv sync has built it, otherwise the system interpreter.
# peek.py's CSV path and the fixture builder are stdlib-only, so they work either way.
PY := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: help setup fixtures verify verify-contracts verify-quarantine verify-determinism \
        verify-replay validate-data peek api demo demo-full demo-reset clean guard-uv \
        verify-s00 verify-s01 verify-s02 verify-s03 verify-s04 verify-s05 \
        verify-s06 verify-s07 verify-s08 verify-s09 verify-s10 verify-s11

help:
	@echo "CHAKRAVYUH targets"
	@echo "  setup              uv sync, create gitignored working directories"
	@echo "  fixtures           regenerate data/fixtures/capture/ (seed 42, deterministic)"
	@echo "  verify             every stage that exists (S00, S01, S02 today)"
	@echo "  verify-s00..s11    one stage each; unbuilt stages fail and name their brief"
	@echo "  verify-contracts   the schema and quarantine guards only"
	@echo "  verify-quarantine  the leakage gates alone; every stage calls this one"
	@echo "  validate-data      invariants, distributions and leakage for RUN=<run-id>"
	@echo "  verify-determinism one seed, two interpreters, all three trees compared"
	@echo "  peek P=<path>      inspect a parquet or csv file, identifiers truncated"
	@echo "  api                serve the read-only API on 127.0.0.1:8000"
	@echo "  clean              delete data/generated/ and tool caches, nothing else"

guard-uv:
	@command -v uv >/dev/null || { \
	  echo "ERROR: uv is not installed, so ruff/mypy/pytest cannot run."; \
	  echo "  Arch:  sudo pacman -S uv       then: make setup"; \
	  echo "  Brief: docs/stages/S00-skeleton.md"; \
	  exit 1; }

setup: guard-uv
	@mkdir -p data/generated ground_truth measurements keys vendor
	uv sync
	@echo "setup: dependencies synced, working directories created."

fixtures:
	python3 scripts/make_fixtures.py --seed 42 --out data/fixtures/capture

verify-s00: guard-uv
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest -q

verify-contracts: guard-uv
	uv run pytest -q tests/test_contracts.py

# Law 2's gate, kept as its own target because every later stage has to run it unchanged.
# The floor is the whole point: `pytest -m` exits zero when everything is deselected, so a
# renamed marker or an emptied registry would turn this green while testing nothing, and every
# stage that calls it would inherit the free pass.
# `-o addopts=` in the counting pass only: pyproject already puts -q in addopts, and a second
# -q makes pytest print per-file totals instead of one test id per line, which the count needs.
QUARANTINE_MIN := 5

verify-quarantine: guard-uv
	@count=$$(uv run pytest -o addopts= --collect-only -q --strict-markers -m quarantine \
	    2>/dev/null | grep -c '::') ; \
	  if [ "$$count" -lt $(QUARANTINE_MIN) ]; then \
	    echo "FAIL verify-quarantine: collected $$count marked tests, expected at least $(QUARANTINE_MIN)."; \
	    echo "  A dropped marker or a renamed test would otherwise pass this gate vacuously."; \
	    echo "  Registry: tests/conftest.py"; \
	    exit 1; \
	  fi ; \
	  echo "verify-quarantine: $$count leakage tests selected."
	uv run pytest -q --strict-markers -m quarantine

# Chain-only runs used by the determinism check below. Under data/generated/, so
# `make clean` removes them and git never sees them.
# --chain-only is what keeps this target about S01: without it the S01 gate builds the peer
# network too, so any S02 change reddens S01 as well and the failure names the wrong stage.
S01_A := data/generated/_verify-s01-a
S01_B := data/generated/_verify-s01-b
S01_ARGS := --txs 2000 --entities 400 --chain-only
# Ground truth lands in a sibling directory per run, named after the run. Both halves are
# compared: a generator could agree on every observable byte and still disagree on the
# answer key, and an answer key that is not reproducible cannot score anything.
S01_TA := ground_truth/_verify-s01-a
S01_TB := ground_truth/_verify-s01-b

verify-s01: guard-uv verify-quarantine
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest -q tests/test_chain.py
	@rm -rf $(S01_A) $(S01_B) $(S01_TA) $(S01_TB)
	uv run python -m chakravyuh.mayajaal $(S01_ARGS) --out $(S01_A)
	uv run python -m chakravyuh.mayajaal $(S01_ARGS) --out $(S01_B)
	@# Two separate interpreters, deliberately. tests/test_chain.py also generates the
	@# same run twice with one seed, but that happens inside one process and therefore
	@# under one PYTHONHASHSEED, so it cannot catch output that depends on set or dict
	@# hash ordering. Only a second process can. Never pin PYTHONHASHSEED here: doing so
	@# is exactly what would make this check vacuous.
	@# compare_runs.py rather than `diff -r -x _meta.json`: excluding the manifest would
	@# drop every hash, row count and drop reason from the comparison. It masks the run id
	@# and the two wall-clock timestamps section 10 requires, and compares the rest.
	@$(PY) scripts/compare_runs.py $(S01_A) $(S01_B) \
	  || { echo "FAIL verify-s01: two runs with seed 42 produced different bytes."; exit 1; }
	@$(PY) scripts/compare_runs.py $(S01_TA) $(S01_TB) \
	  || { echo "FAIL verify-s01: two runs with seed 42 produced different ground truth."; exit 1; }
	@rm -rf $(S01_A) $(S01_B) $(S01_TA) $(S01_TB)
	@echo "verify-s01: chain layer OK, and two same-seed runs agree byte for byte."

# S02 adds the network layer, the adversary and the export to the same run, so an S02 run
# is what validate-data measures and what verify-determinism runs twice. --txs is a
# transaction count, and 20000 of them fan out into roughly 370 thousand announcements.
# The size is chosen by what it exercises rather than by speed: campaigns are bounded by
# illicit_tx_share, so a 2000-transaction run generates none and every campaign assertion
# in the validator and the tests would pass by being vacuous. 20000 yields five. Cost is
# about 30s to generate and 2s to validate.
S02_ARGS := --txs 20000 --entities 4000
S02_RUN_A := _verify-s02-a
S02_RUN_B := _verify-s02-b
S02_A := data/generated/$(S02_RUN_A)
S02_B := data/generated/$(S02_RUN_B)
S02_TA := ground_truth/$(S02_RUN_A)
S02_TB := ground_truth/$(S02_RUN_B)
S02_MA := measurements/$(S02_RUN_A)
S02_MB := measurements/$(S02_RUN_B)

# validate.py exits non-zero when any hard invariant fails or any leakage rule lands outside
# its acceptance band, so the report is the gate rather than something to read afterwards.
verify-s02: guard-uv verify-quarantine
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest -q tests/test_network.py
	@rm -rf $(S02_A) $(S02_TA) $(S02_MA)
	uv run python -m chakravyuh.mayajaal $(S02_ARGS) --out $(S02_A)
	uv run python -m chakravyuh.eval.validate --run $(S02_RUN_A)
	@rm -rf $(S02_A) $(S02_TA) $(S02_MA)
	@echo "verify-s02: network, adversary and export OK, validation report clean."

verify: verify-s00 verify-s01 verify-s02
	@echo "verify: S00, S01 and S02. Later stages append themselves as they land."

# One rule for all eight unbuilt stages. The brief path is globbed rather than
# hardcoded so renaming a brief cannot rot the message.
verify-s03 verify-s04 verify-s05 verify-s06 \
verify-s07 verify-s08 verify-s09 verify-s10 verify-s11:
	@n=$(patsubst verify-s%,%,$@); \
	 b=$$(ls docs/stages/S$$n-*.md 2>/dev/null | head -1); \
	 echo "FAIL $@: stage S$$n is not implemented yet."; \
	 echo "  Brief: $${b:-docs/stages/ (missing)}"; \
	 exit 1

# The same seed twice, in two interpreters, compared across all three trees. The
# measurements tree is compared too: a report is a number we will publish, and a number
# that moves between runs of the same seed is not a measurement.
verify-determinism: guard-uv
	@rm -rf $(S02_A) $(S02_B) $(S02_TA) $(S02_TB) $(S02_MA) $(S02_MB)
	uv run python -m chakravyuh.mayajaal $(S02_ARGS) --out $(S02_A)
	uv run python -m chakravyuh.mayajaal $(S02_ARGS) --out $(S02_B)
	uv run python -m chakravyuh.eval.validate --run $(S02_RUN_A)
	uv run python -m chakravyuh.eval.validate --run $(S02_RUN_B)
	@# Never pin PYTHONHASHSEED here: two separate interpreters is the entire point, and
	@# pinning is exactly what would make this check vacuous.
	@$(PY) scripts/compare_runs.py $(S02_A) $(S02_B) \
	  || { echo "FAIL verify-determinism: two runs with one seed produced different bytes."; exit 1; }
	@$(PY) scripts/compare_runs.py $(S02_TA) $(S02_TB) \
	  || { echo "FAIL verify-determinism: two runs with one seed produced different ground truth."; exit 1; }
	@$(PY) scripts/compare_runs.py $(S02_MA) $(S02_MB) \
	  || { echo "FAIL verify-determinism: two runs with one seed measured differently."; exit 1; }
	@rm -rf $(S02_A) $(S02_B) $(S02_TA) $(S02_TB) $(S02_MA) $(S02_MB)
	@echo "verify-determinism: observable, ground truth and measurements all reproduced."

verify-replay:
	@echo "FAIL verify-replay: needs a signed packet to replay. Arrives with S09."
	@echo "  Brief: docs/stages/S09-pramaan.md"
	@exit 1

# RUN is a run id, never a path, because the answer key and the measurements directory are
# derived from it. There is deliberately no flag anywhere that could point validation at a
# ground truth belonging to a different run.
RUN ?= run-a

validate-data: guard-uv
	@test -d data/generated/$(RUN) || { \
	  echo "FAIL validate-data: no run named '$(RUN)' under data/generated/."; \
	  echo "  Generate one:  uv run python -m chakravyuh.mayajaal --out data/generated/$(RUN)"; \
	  echo "  Or name another:  make validate-data RUN=<run-id>"; \
	  exit 1; }
	uv run python -m chakravyuh.eval.validate --run $(RUN)
	@echo "validate-data: measurements/$(RUN)/validation/report.md"

demo demo-full demo-reset:
	@echo "FAIL $@: needs precomputed artifacts. Arrives with S10 and S11."
	@echo "  Briefs: docs/stages/S10-scale.md, docs/stages/S11-demo.md"
	@exit 1

peek:
	@test -n "$(P)" || { echo "usage: make peek P=<path.csv|path.parquet>"; exit 1; }
	@$(PY) scripts/peek.py "$(P)"

api:
	@$(PY) -c "import chakravyuh.api.app" 2>/dev/null || { \
	  echo "FAIL api: chakravyuh.api.app does not exist yet. Arrives with L7."; exit 1; }
	uv run uvicorn chakravyuh.api.app:app --host 127.0.0.1 --port 8000

# Deletes only regenerable pipeline output and tool caches.
# Never touches data/fixtures/ (committed), ground_truth/, measurements/, keys/ or vendor/.
clean:
	rm -rf data/generated .pytest_cache .ruff_cache .mypy_cache
	@mkdir -p data/generated
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "clean: data/generated/ and tool caches removed."
