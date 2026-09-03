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

.PHONY: help setup fixtures verify verify-contracts verify-determinism verify-replay \
        validate-data peek api demo demo-full demo-reset clean guard-uv \
        verify-s00 verify-s01 verify-s02 verify-s03 verify-s04 verify-s05 \
        verify-s06 verify-s07 verify-s08 verify-s09 verify-s10 verify-s11

help:
	@echo "CHAKRAVYUH targets"
	@echo "  setup              uv sync, create gitignored working directories"
	@echo "  fixtures           regenerate data/fixtures/capture/ (seed 42, deterministic)"
	@echo "  verify             every stage that exists (S00 today)"
	@echo "  verify-s00..s11    one stage each; unbuilt stages fail and name their brief"
	@echo "  verify-contracts   the schema and quarantine guards only"
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
	@mkdir -p data/generated ground_truth keys vendor
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

verify: verify-s00
	@echo "verify: S00 only. Later stages append themselves to this target as they land."

# One rule for all eleven unbuilt stages. The brief path is globbed rather than
# hardcoded so renaming a brief cannot rot the message.
verify-s01 verify-s02 verify-s03 verify-s04 verify-s05 verify-s06 \
verify-s07 verify-s08 verify-s09 verify-s10 verify-s11:
	@n=$(patsubst verify-s%,%,$@); \
	 b=$$(ls docs/stages/S$$n-*.md 2>/dev/null | head -1); \
	 echo "FAIL $@: stage S$$n is not implemented yet."; \
	 echo "  Brief: $${b:-docs/stages/ (missing)}"; \
	 exit 1

verify-determinism:
	@echo "FAIL verify-determinism: needs two full pipeline runs. Arrives with S10."
	@echo "  Brief: docs/stages/S10-scale.md"
	@exit 1

verify-replay:
	@echo "FAIL verify-replay: needs a signed packet to replay. Arrives with S09."
	@echo "  Brief: docs/stages/S09-pramaan.md"
	@exit 1

validate-data:
	@echo "FAIL validate-data: needs the MAYAJAAL validation report. Arrives with S02."
	@echo "  Brief: docs/stages/S02-mayajaal-network.md"
	@exit 1

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
# Never touches data/fixtures/ (committed), ground_truth/, keys/ or vendor/.
clean:
	rm -rf data/generated .pytest_cache .ruff_cache .mypy_cache
	@mkdir -p data/generated
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "clean: data/generated/ and tool caches removed."
