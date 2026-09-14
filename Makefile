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
QUARANTINE_MIN := 11

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

# S03 reads the capture as an outside consumer, so its gate seals two things: the three
# committed fixtures, which is where the awkward cases live, and a real S02 capture directory,
# which is the only input that exercises the staleness link and multi-file row_id ordering.
# Both are sealed twice in two separate interpreters and compared, for the same reason S01
# does it: a dict iteration order that leaked into the output would survive any single-process
# check. Never pin PYTHONHASHSEED here.
S03_ARGS := --txs 2000 --entities 400
S03_CAP := data/generated/_verify-s03-cap
S03_TCAP := ground_truth/_verify-s03-cap
S03_MCAP := measurements/_verify-s03-cap
S03_A := data/generated/_verify-s03-a
S03_B := data/generated/_verify-s03-b

verify-s03: guard-uv verify-quarantine
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest -q tests/test_kavach.py
	@rm -rf $(S03_CAP) $(S03_TCAP) $(S03_MCAP) $(S03_A) $(S03_B)
	@# The three fixtures, each sealed and checked. capture.csv carries the one documented
	@# bad row, so a gate that never rejected anything would be lying about its accounting.
	@for e in csv jsonl xml; do \
	  uv run python -m chakravyuh.kavach --in data/fixtures/capture/capture.$$e \
	    --out $(S03_A)-$$e >/dev/null \
	    || { echo "FAIL verify-s03: sealing capture.$$e failed."; exit 1; }; \
	  $(PY) scripts/check_sealed.py $(S03_A)-$$e \
	    || { echo "FAIL verify-s03: $$e output does not satisfy contract section 3."; exit 1; }; \
	done
	@# All three encodings describe the same announcements, so they must seal to one file.
	@count=$$(sha256sum $(S03_A)-csv/sealed/rows.parquet $(S03_A)-jsonl/sealed/rows.parquet \
	    $(S03_A)-xml/sealed/rows.parquet | awk '{print $$1}' | sort -u | wc -l); \
	  if [ "$$count" -ne 1 ]; then \
	    echo "FAIL verify-s03: the three encodings sealed to $$count distinct files, expected 1."; \
	    exit 1; \
	  fi; \
	  echo "verify-s03: csv, jsonl and xml seal byte-identically."
	@# A real capture: two shards, an upstream _meta.json to link against, 24 thousand rows.
	uv run python -m chakravyuh.mayajaal $(S03_ARGS) --out $(S03_CAP)
	uv run python -m chakravyuh.kavach --in $(S03_CAP)/capture --out $(S03_A)
	uv run python -m chakravyuh.kavach --in $(S03_CAP)/capture --out $(S03_B)
	@$(PY) scripts/check_sealed.py $(S03_A) \
	  || { echo "FAIL verify-s03: the sealed real capture does not satisfy section 3."; exit 1; }
	@# Two interpreters, byte compared. manifest.json is canonicalised on sealed_at_us and
	@# _meta.json on the run id and its two wall clocks; everything else, hashes included, must
	@# match exactly.
	@$(PY) scripts/compare_runs.py $(S03_A)/sealed $(S03_B)/sealed \
	  || { echo "FAIL verify-s03: two seals of one capture produced different bytes."; exit 1; }
	@# The staleness link, made to fail on purpose. Touching the upstream manifest must turn
	@# check_sealed.py red, or the link is decorative.
	@printf '\n' >> $(S03_CAP)/capture/_meta.json
	@if $(PY) scripts/check_sealed.py $(S03_A) >/dev/null 2>&1; then \
	  echo "FAIL verify-s03: the upstream manifest changed and the staleness check passed anyway."; \
	  exit 1; \
	fi
	@echo "verify-s03: staleness is detected when the upstream manifest moves."
	@rm -rf $(S03_CAP) $(S03_TCAP) $(S03_MCAP) $(S03_A) $(S03_B) \
	  $(S03_A)-csv $(S03_A)-jsonl $(S03_A)-xml
	@echo "verify-s03: intake, seal, manifest arithmetic and custody OK."

# S04 splits one table into four, so the gate is mostly arithmetic that must survive the
# split: the announcement count, the txid count, and counts.in == out + dropped. On top of
# that the two paths the brief calls out. `vendor/` is empty in this repo, so a plain run is
# already the no-vendor path and the gate asserts the nulls and the warning are really there;
# the populated path is exercised in tests/test_setu.py against a synthetic CSV tree.
# Both normalisations read one shared seal rather than a copy each, so the only field that
# differs between them is the run id, which compare_runs.py already masks. Two interpreters,
# byte compared, for the same reason S01 and S03 do it. Never pin PYTHONHASHSEED here.
S04_ARGS := --txs 2000 --entities 400
S04_CAP := data/generated/_verify-s04-cap
S04_TCAP := ground_truth/_verify-s04-cap
S04_MCAP := measurements/_verify-s04-cap
S04_SEAL := data/generated/_verify-s04-seal
S04_A := data/generated/_verify-s04-a
S04_B := data/generated/_verify-s04-b

verify-s04: guard-uv verify-quarantine
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest -q tests/test_setu.py
	@rm -rf $(S04_CAP) $(S04_TCAP) $(S04_MCAP) $(S04_SEAL) $(S04_A) $(S04_B)
	uv run python -m chakravyuh.mayajaal $(S04_ARGS) --out $(S04_CAP)
	uv run python -m chakravyuh.kavach --in $(S04_CAP)/capture --out $(S04_SEAL)
	uv run python -m chakravyuh.setu --in $(S04_SEAL)/sealed --out $(S04_A)
	uv run python -m chakravyuh.setu --in $(S04_SEAL)/sealed --out $(S04_B)
	@# Contract section 10, checked from outside the code that wrote it.
	@$(PY) scripts/check_stage.py $(S04_A)/normalised \
	  || { echo "FAIL verify-s04: normalised/ does not satisfy contract section 10."; exit 1; }
	@# The grain split, asserted against the file it came from rather than against itself:
	@# one sealed row is one announcement, and one txid is one transaction row.
	@$(PY) scripts/check_grain.py $(S04_SEAL)/sealed $(S04_A)/normalised \
	  || { echo "FAIL verify-s04: the grain split did not preserve the counts it must."; exit 1; }
	@# Two interpreters, byte compared. _meta.json is canonicalised on the run id and its two
	@# wall clocks; the four Parquet files and their recorded hashes must match exactly.
	@$(PY) scripts/compare_runs.py $(S04_A)/normalised $(S04_B)/normalised \
	  || { echo "FAIL verify-s04: two normalisations of one seal produced different bytes."; exit 1; }
	@# The staleness link, made to fail on purpose. Touching the upstream _meta.json must turn
	@# check_stage.py red, or the link is decorative.
	@printf '\n' >> $(S04_SEAL)/sealed/_meta.json
	@if $(PY) scripts/check_stage.py $(S04_A)/normalised >/dev/null 2>&1; then \
	  echo "FAIL verify-s04: the upstream meta changed and the staleness check passed anyway."; \
	  exit 1; \
	fi
	@echo "verify-s04: staleness is detected when sealed/_meta.json moves."
	@rm -rf $(S04_CAP) $(S04_TCAP) $(S04_MCAP) $(S04_SEAL) $(S04_A) $(S04_B)
	@echo "verify-s04: grain split, enrichment fallback, counts and determinism OK."

# S05 builds the fused graph, so its gate is about three things the earlier gates could not
# test. First, that clustering is non-destructive: check_graph.py asserts one address node per
# normalised address row, which is exactly what a union-find merge would break. Second, that the
# measured clustering precision stays where a heuristic belongs: above 0.8 on synthetic data
# means a label leaked, not that the heuristic got good, so the gate fails on a high number the
# same way it fails on a wrong one. Third, that validate.py's quarantine grep still passes over
# a run whose graph/clusters.parquet legitimately carries a column named in contract section 2.
#
# Unlike S04 this gate keeps capture, seal, normalised and graph in ONE run directory: the run
# id JAAL derives from --out is what eval.metrics uses to find the answer key, so splitting them
# would score against a different run's truth. The second graph is built from the same
# normalised/ into its own tree, which is all the byte compare needs.
S05_ARGS := --txs 2000 --entities 400
S05_RUN := _verify-s05
S05_A := data/generated/$(S05_RUN)
S05_T := ground_truth/$(S05_RUN)
S05_M := measurements/$(S05_RUN)
S05_B := data/generated/_verify-s05-b

verify-s05: guard-uv verify-quarantine
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest -q tests/test_jaal.py
	@rm -rf $(S05_A) $(S05_T) $(S05_M) $(S05_B)
	uv run python -m chakravyuh.mayajaal $(S05_ARGS) --out $(S05_A)
	uv run python -m chakravyuh.kavach --in $(S05_A)/capture --out $(S05_A)
	uv run python -m chakravyuh.setu --in $(S05_A)/sealed --out $(S05_A)
	uv run python -m chakravyuh.jaal --in $(S05_A)/normalised --out $(S05_A) --score
	uv run python -m chakravyuh.jaal --in $(S05_A)/normalised --out $(S05_B)
	@# Contract section 10, checked from outside the code that wrote it.
	@$(PY) scripts/check_stage.py $(S05_A)/graph \
	  || { echo "FAIL verify-s05: graph/ does not satisfy contract section 10."; exit 1; }
	@# Node coverage and edge integrity, asserted against the normalised/ the graph came from
	@# rather than against itself. One address row, one address node, is the union-find trap.
	@$(PY) scripts/check_graph.py $(S05_A)/normalised $(S05_A)/graph \
	  || { echo "FAIL verify-s05: the graph does not cover the tables it was built from."; exit 1; }
	@# Two interpreters, byte compared. Component numbering must not depend on set or dict
	@# iteration order. Never pin PYTHONHASHSEED here: that is what would make this vacuous.
	@$(PY) scripts/compare_runs.py $(S05_A)/graph $(S05_B)/graph \
	  || { echo "FAIL verify-s05: two builds of one normalised/ produced different bytes."; exit 1; }
	@# The brief's sharpest trap, as a gate. A clustering heuristic that scores like an oracle
	@# has seen the answer key; the multi-input heuristic measures 0.36 in the field.
	@$(PY) -c "import json,sys; \
	p = json.load(open('$(S05_M)/cluster_metrics.json'))['pair_precision']; \
	sys.stderr.write('verify-s05: pair precision %.4f\n' % p); \
	sys.exit(0 if p <= 0.8 else 1)" \
	  || { echo "FAIL verify-s05: cluster precision above 0.8 on this data means a leak, not a breakthrough."; exit 1; }
	@# All 48 validator checks over a tree that now holds a section-5 file carrying a column
	@# name section 2 also uses. This is what proves the TRUTH_COLUMNS narrowing is not a hole.
	uv run python -m chakravyuh.eval.validate --run $(S05_RUN)
	@# The staleness link, made to fail on purpose. Touching the upstream _meta.json must turn
	@# check_stage.py red, or the link is decorative.
	@printf '\n' >> $(S05_A)/normalised/_meta.json
	@if $(PY) scripts/check_stage.py $(S05_A)/graph >/dev/null 2>&1; then \
	  echo "FAIL verify-s05: the upstream meta changed and the staleness check passed anyway."; \
	  exit 1; \
	fi
	@echo "verify-s05: staleness is detected when normalised/_meta.json moves."
	@rm -rf $(S05_A) $(S05_T) $(S05_M) $(S05_B)
	@echo "verify-s05: fused graph, non-destructive clustering, scoring and determinism OK."

verify: verify-s00 verify-s01 verify-s02 verify-s03 verify-s04 verify-s05
	@echo "verify: S00 through S05. Later stages append themselves as they land."

# One rule for all six unbuilt stages. The brief path is globbed rather than
# hardcoded so renaming a brief cannot rot the message.
verify-s06 \
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
