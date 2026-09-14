"""The two clustering heuristics, and the derived cluster view.

`SAME_OWNER` is an edge with a confidence and a named heuristic. It never merges nodes. The
multi-input heuristic measures 0.36 precision on full clusters in law enforcement settings, so a
hard merge would be wrong roughly two times in three, and an analyst who moved a threshold could
never get the original graph back. Cluster membership is recovered here by running connected
components over the edges above a threshold, which is a read, not a write: delete the
`MEMBER_OF` edges and `clusters.parquet` and the graph is exactly what it was.

Edges within one transaction form a star rather than a clique: every input address is linked to
the lexicographically smallest input address of that transaction. Connected components,
`min_edge_confidence` and the derived clusters are all identical either way, because a clique and
a star over the same vertex set have the same component, and a star is n-1 edges where a clique is
n(n-1)/2. One transaction in a 2000-transaction run already has 38 inputs, which is 703 clique
edges carrying no information the 37 star edges do not.
"""

from __future__ import annotations

from typing import Final

import polars as pl
import rustworkx as rx

from chakravyuh.jaal.build import CLUSTERS_SCHEMA, EDGES_SCHEMA, conform

# The multi-input heuristic's published precision on full clusters in law enforcement settings,
# quoted by contract section 5. Used as the edge confidence so the number an analyst sees on the
# edge is the number the literature measured, not one this project invented.
MULTI_INPUT_CONFIDENCE: Final[float] = 0.36

# The change heuristic is weaker and, in this project, UNMEASURED. SETU's rule is deliberately
# conservative (sole non-round output not paying one of this transaction's own input addresses,
# and only when n_out >= 2), which keeps its recall low but says nothing about its precision. The
# value sits below MULTI_INPUT_CONFIDENCE so a threshold between the two selects multi-input
# alone, which is the comparison an analyst most wants to make. Revisit when S10 measures it.
CHANGE_ADDR_CONFIDENCE: Final[float] = 0.25

# Both heuristics are in at this threshold. The console moves it; the stage records whatever it
# was cut at into every row of clusters.parquet.
DEFAULT_THRESHOLD: Final[float] = 0.2


def _star(frame: pl.DataFrame, members: str, evidence: str, confidence: float) -> pl.DataFrame:
    """Link every address in `members` to that row's lexicographically smallest member.

    `members` is a list column. Rows with fewer than two distinct members produce nothing, which
    is what makes a single-input transaction contribute no edge rather than a self-loop.
    """
    exploded = (
        frame.select(pl.col(members).list.unique().alias("member"))
        .with_columns(pl.col("member").list.min().alias("anchor"))
        .filter(pl.col("member").list.len() >= 2)
        .explode("member")
        .filter(pl.col("member") != pl.col("anchor"))
    )
    return conform(
        exploded.select(
            (pl.lit("addr:") + pl.col("anchor")).alias("src"),
            (pl.lit("addr:") + pl.col("member")).alias("dst"),
            pl.lit("SAME_OWNER").alias("kind"),
            pl.lit(None).cast(pl.Int64()).alias("ts_us"),
            pl.lit(None).cast(pl.Int64()).alias("sats"),
            pl.lit(confidence).alias("confidence"),
            pl.lit(evidence).alias("evidence"),
        ),
        EDGES_SCHEMA,
    )


def common_input_edges(transactions: pl.DataFrame) -> pl.DataFrame:
    """Common input ownership: spending two addresses in one transaction needs both keys.

    CoinJoin-like transactions are excluded, because they are exactly the construction that
    breaks this heuristic: several unrelated parties sign one transaction on purpose. SETU hands
    us `has_equal_outputs` for that, and dropping those transactions is cheaper and more honest
    than emitting edges we already believe are wrong.
    """
    candidates = transactions.filter(
        ~pl.col("is_coinbase") & (pl.col("n_in") >= 2) & ~pl.col("has_equal_outputs")
    )
    return _star(candidates, "input_addresses", "multi_input", MULTI_INPUT_CONFIDENCE)


def change_edges(transactions: pl.DataFrame) -> pl.DataFrame:
    """Change-address detection: the suspected change output belongs to the sender.

    The change index is SETU's, and deliberately weak. This links the change output to the
    transaction's own input addresses, which is the claim the heuristic actually makes: that
    output came back to whoever funded the inputs.
    """
    candidates = (
        transactions.filter(~pl.col("is_coinbase") & (pl.col("change_index") >= 0))
        .with_columns(
            pl.col("output_addresses")
            .list.get(pl.col("change_index"), null_on_oob=True)
            .alias("change_address")
        )
        .filter(pl.col("change_address").is_not_null())
        .select(
            pl.concat_list(pl.col("input_addresses"), pl.col("change_address")).alias("members")
        )
    )
    return _star(candidates, "members", "change_addr", CHANGE_ADDR_CONFIDENCE)


def same_owner_edges(transactions: pl.DataFrame) -> pl.DataFrame:
    """Every candidate `SAME_OWNER` edge from both heuristics, deduplicated.

    Two heuristics can propose the same undirected pair. The stronger claim wins, and the weaker
    duplicate is a drop with a recorded reason rather than a second edge: two edges between one
    pair would let a cluster's `min_edge_confidence` be read off the weaker one and understate
    what holds the cluster together.
    """
    both = pl.concat([common_input_edges(transactions), change_edges(transactions)])
    # Undirected: (a, b) and (b, a) are the same claim. Ordering the pair before deduplicating is
    # what makes that true on disk as well as in the reader's head.
    ordered = both.with_columns(
        pl.min_horizontal("src", "dst").alias("lo"), pl.max_horizontal("src", "dst").alias("hi")
    )
    kept = (
        ordered.sort("lo", "hi", "confidence", descending=[False, False, True])
        .unique(subset=["lo", "hi"], keep="first", maintain_order=True)
        .drop("src", "dst")
        .rename({"lo": "src", "hi": "dst"})
    )
    return conform(kept, EDGES_SCHEMA)


def components(edges: pl.DataFrame, threshold: float) -> list[list[str]]:
    """Connected components of the `SAME_OWNER` edges at or above `threshold`.

    Singletons are excluded: an address nothing links to is not a cluster, and emitting one row
    per unlinked address would make `n_addresses` meaningless and the cluster count a restatement
    of the address count.

    Determinism matters more than it looks. rustworkx returns components as sets, whose iteration
    order is not stable across interpreters, so both the addresses inside a component and the
    components themselves are sorted before anything numbers them. Without that, `cluster:7` would
    name different addresses in two runs of the same seed.
    """
    strong = edges.filter(
        (pl.col("kind") == "SAME_OWNER") & (pl.col("confidence") >= threshold)
    ).select("src", "dst")
    graph: rx.PyGraph[str, None] = rx.PyGraph()
    index: dict[str, int] = {}
    for src, dst in strong.iter_rows():
        for node in (src, dst):
            if node not in index:
                index[node] = graph.add_node(node)
        graph.add_edge(index[src], index[dst], None)
    names = {value: key for key, value in index.items()}
    found = [sorted(names[node] for node in part) for part in rx.connected_components(graph)]
    return sorted((part for part in found if len(part) >= 2), key=lambda part: part[0])


def clusters(edges: pl.DataFrame, threshold: float) -> tuple[pl.DataFrame, pl.DataFrame]:
    """The derived view: `clusters.parquet` and the `MEMBER_OF` edges that point into it.

    Returns `(clusters, member_edges)`. Both are derived, both are deletable, and neither touches
    the address nodes: this is the "cluster membership is a derived view, not a destructive
    operation" rule, implemented as a read over the edge table.
    """
    parts = components(edges, threshold)
    strong = edges.filter((pl.col("kind") == "SAME_OWNER") & (pl.col("confidence") >= threshold))

    rows: list[dict[str, object]] = []
    memberships: list[dict[str, object]] = []
    for number, part in enumerate(parts):
        cluster_id = f"cluster:{number}"
        inside = set(part)
        held = strong.filter(pl.col("src").is_in(inside) & pl.col("dst").is_in(inside))
        weakest = float(held["confidence"].min() or threshold)  # type: ignore[arg-type]
        # The evidence of the weakest link, not of the strongest: MEMBER_OF carries the claim
        # that actually holds this address in the cluster, and that claim is the weakest one.
        weakest_evidence = str(
            held.filter(pl.col("confidence") == weakest)["evidence"].sort().first()
        )
        rows.append(
            {
                "cluster_id": cluster_id,
                # The `addr:` prefix is a node id, not an address. clusters.parquet lists
                # addresses, so the prefix comes off here.
                "addresses": [name.removeprefix("addr:") for name in part],
                "n_addresses": len(part),
                "min_edge_confidence": weakest,
                "heuristics_used": sorted(set(held["evidence"].to_list())),
                "threshold": threshold,
            }
        )
        memberships.extend(
            {
                "src": name,
                "dst": cluster_id,
                "kind": "MEMBER_OF",
                "ts_us": None,
                "sats": None,
                "confidence": weakest,
                "evidence": weakest_evidence,
            }
            for name in part
        )

    cluster_frame = conform(
        pl.DataFrame(rows, schema={name: dtype for name, dtype in CLUSTERS_SCHEMA.items()}),
        CLUSTERS_SCHEMA,
    )
    member_frame = conform(
        pl.DataFrame(memberships, schema={name: dtype for name, dtype in EDGES_SCHEMA.items()}),
        EDGES_SCHEMA,
    )
    return cluster_frame, member_frame


def cluster_nodes(cluster_frame: pl.DataFrame) -> pl.DataFrame:
    """One `cluster:` node per cluster, spanning nothing.

    `first_us` and `last_us` are null: a cluster is an inference about ownership, not something
    the capture observed between two times. Writing the span of its addresses there would invite a
    reader to treat a heuristic's output as an observation.
    """
    from chakravyuh.jaal.build import NODES_SCHEMA

    return conform(
        cluster_frame.select(
            pl.col("cluster_id").alias("node_id"),
            pl.lit("cluster").alias("kind"),
            # Already safe: a cluster id is a counter, and the address count is an aggregate.
            (
                pl.col("cluster_id")
                + pl.lit(" (")
                + pl.col("n_addresses").cast(pl.String())
                + pl.lit(" addrs)")
            ).alias("label"),
            pl.lit(None).cast(pl.Int64()).alias("first_us"),
            pl.lit(None).cast(pl.Int64()).alias("last_us"),
        ),
        NODES_SCHEMA,
    )
