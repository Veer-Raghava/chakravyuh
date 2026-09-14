"""The optional Kùzu Cypher view over `graph/`.

Kùzu is a demo convenience: it lets an analyst ask a Cypher question about a graph that already
exists as three Parquet files. It is never a hard dependency, so the import lives inside the
function rather than at module scope. With Kùzu absent the graph is complete and only this view
is unavailable, which is the path this repo actually runs: `import kuzu` fails here.
"""

from __future__ import annotations

import sys
from pathlib import Path

NODE_TABLE = """
CREATE NODE TABLE IF NOT EXISTS GraphNode(
  node_id STRING, kind STRING, label STRING, first_us INT64, last_us INT64,
  PRIMARY KEY (node_id))
"""

EDGE_TABLE = """
CREATE REL TABLE IF NOT EXISTS GraphEdge(
  FROM GraphNode TO GraphNode,
  kind STRING, ts_us INT64, sats INT64, confidence DOUBLE, evidence STRING)
"""


def available() -> bool:
    """Whether Kùzu can be imported at all. Recorded in `_meta.json` under `optional_deps`."""
    try:
        # Not added to mypy's ignore_missing_imports: kuzu is the one dependency that is genuinely
        # absent, and an override there would also silence a typo in some future optional import.
        import kuzu  # type: ignore[import-not-found] # noqa: F401
    except ImportError:
        return False
    return True


def cypher_view(graph_dir: Path, database: Path | None = None) -> Path | None:
    """Load `graph/` into a Kùzu database beside it. None when Kùzu is not installed.

    Returns the database path on success. A warning on stderr and None otherwise, never an
    exception: a missing optional dependency is not a stage failure.
    """
    try:
        import kuzu
    except ImportError:
        sys.stderr.write(
            "jaal: kuzu is not installed, so the Cypher view was skipped. The graph itself is "
            "complete: nodes.parquet, edges.parquet and clusters.parquet are all written.\n"
        )
        return None

    target = database if database is not None else graph_dir / "cypher.kuzu"
    connection = kuzu.Connection(kuzu.Database(str(target)))
    connection.execute(NODE_TABLE)
    connection.execute(EDGE_TABLE)
    connection.execute(f'COPY GraphNode FROM "{graph_dir / "nodes.parquet"}"')
    connection.execute(f'COPY GraphEdge FROM "{graph_dir / "edges.parquet"}"')
    return target
