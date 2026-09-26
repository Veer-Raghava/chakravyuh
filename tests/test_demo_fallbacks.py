"""S11 fallback gate: prove every optional dependency degrades exactly one feature.

The pipeline names four optional dependencies — kuzu (the Cypher view), GeoLite2 (ASN/geo
enrichment), a GPU (nothing in this tree needs one), and a trained LightGBM model (scoring
confidence) — plus the quarantined answer key. The contract is that any one of them being
absent degrades its own feature and nothing else: the stage still writes its contract output,
and it records the absence rather than crashing on it.

Most of that is already proven per-stage (kuzu in ``test_jaal``, vendored enrichment in
``test_setu``/``test_jaal``, the untrained-model path in ``test_buddhi``, and the answer key
in the ten quarantine tests). This module does the part none of those do: it asserts the
optional-dependency contract holds *across every stage at once*, on the committed demo
artifact the projector will actually serve — and that no optional import can crash a stage
merely by being absent. It reads artifacts; it regenerates nothing.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import polars as pl
import pytest

REPO = Path(__file__).resolve().parent.parent
DEMO_RUN = REPO / "data" / "generated" / "s10-demo"
OPTIONAL_DEPS = {"kuzu", "geolite2", "gpu"}
# Distribution names of the dependencies whose absence must degrade, never crash on import.
# A stage may import these only inside a function, behind an availability check.
GUARDED_IMPORTS = {"kuzu", "lightgbm", "geoip2", "shap", "mapie"}

pytestmark = pytest.mark.skipif(
    not DEMO_RUN.is_dir(),
    reason="demo run s10-demo absent; build once with `make demo-full`",
)


def _stage_metas() -> dict[str, Any]:
    return {
        meta.parent.name: json.loads(meta.read_text())
        for meta in sorted(DEMO_RUN.glob("*/_meta.json"))
    }


def test_every_stage_records_the_optional_dependency_flags() -> None:
    """The demo cannot claim a feature it never had. Every stage records which optional
    dependencies were present, as booleans, so a degraded run is legible after the fact."""
    metas = _stage_metas()
    assert metas, "demo run has no stage metadata"
    for stage, meta in metas.items():
        deps = meta.get("optional_deps")
        assert deps is not None, f"{stage} recorded no optional_deps block"
        assert set(deps) >= OPTIONAL_DEPS, f"{stage} optional_deps missing keys: {deps}"
        for name in OPTIONAL_DEPS:
            assert isinstance(deps[name], bool), f"{stage}.{name} is not a bool: {deps[name]!r}"


def test_kuzu_absent_degraded_only_the_cypher_view() -> None:
    """kuzu is not installed here, so the demo was built without it. The graph stage must
    still have written its contract output — the degradation is the view, not the graph."""
    graph_meta = json.loads((DEMO_RUN / "graph" / "_meta.json").read_text())
    assert graph_meta["optional_deps"]["kuzu"] is False
    assert "kuzu_absent_cypher_view_unavailable" in graph_meta["warnings"]

    # The feature that must NOT be degraded: the fused graph itself is complete.
    edges = pl.read_parquet(DEMO_RUN / "graph" / "edges.parquet")
    nodes = pl.read_parquet(DEMO_RUN / "graph" / "nodes.parquet")
    assert edges.height > 0 and nodes.height > 0


def test_no_gpu_was_required_and_none_was_used() -> None:
    """Nothing in this tree needs a GPU; the demo laptop has none. Every stage records the
    GPU as absent and completed anyway — the CPU path is the only path."""
    for stage, meta in _stage_metas().items():
        assert meta["optional_deps"]["gpu"] is False, f"{stage} claims a GPU it should not use"


def test_no_stage_hard_imports_an_optional_dependency() -> None:
    """An optional dependency imported at module top crashes the whole stage the instant it
    is missing — the opposite of degrading one feature. Assert every optional import lives
    inside a function, where an availability guard can catch its absence."""
    offenders: list[str] = []
    for path in (REPO / "src" / "chakravyuh").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in tree.body:  # module-level statements only
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in GUARDED_IMPORTS:
                    offenders.append(f"{path.relative_to(REPO)}: top-level import {name}")
    assert not offenders, "optional dependency imported at module top:\n" + "\n".join(offenders)
