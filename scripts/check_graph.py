"""Check `graph/` against the `normalised/` it was built from, from outside JAAL.

`check_stage.py` checks the manifest's own arithmetic. This checks the thing a manifest cannot:
that the graph covers the tables it came from and that its edges point at nodes that exist.

The first check is the one that matters. One address row, one address node, always. A clustering
implemented as a union-find merge would produce fewer address nodes than there are addresses, and
that is precisely the operation contract section 5 forbids: "SAME_OWNER never merges nodes." The
count is how you catch it from outside, without reading a line of the code that wrote the file.

Writes file names, field names and counts to stderr. Never a row, never an identifier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq  # type: ignore[import-untyped]

# Contract section 5's closed vocabularies, transcribed rather than imported. A checker that
# imports the writer's constants asserts only that a module equals itself.
NODE_KINDS = {"address", "transaction", "peer", "cluster", "asn"}
EDGE_KINDS = {"SPENDS", "RECEIVES", "ANNOUNCED_BY", "SAME_OWNER", "HOSTED_IN", "MEMBER_OF"}
EVIDENCE_KINDS = {"multi_input", "change_addr", "observed", "geoip"}

# Section 5's peel-chain table, transcribed the same way. The stopping reasons are a closed set
# because an analyst reading one needs to know which of four different facts it is reporting.
CHAIN_COLUMNS = (
    "peel_chain_id",
    "transactions",
    "depth",
    "initial_sats",
    "peeled_sats",
    "leak_frac",
    "root_address",
    "first_us",
    "last_us",
    "stop_reason",
)
CHAIN_STOPS = {"no_continuation", "ambiguous_spend", "chain_broken", "cycle"}
CHAIN_MIN_HOPS = 2
# `payment <= 0.35 * total_out`, transcribed as the integer comparison the writer uses. Comparing
# floats from outside could disagree by one satoshi and fail a graph that is right.
PEEL_SHARE_NUM = 7
PEEL_SHARE_DEN = 20

# The mixer rule, transcribed. `has_equal_outputs` is SETU's; the two counts are section 5's.
MIXER_MIN_OUTPUTS = 3
MIXER_MIN_INPUTS = 2

# A v2 graph writes four files. An older graph writes three, and the answer to that is to fail
# here rather than to read a missing peel_chains.parquet as "no chains", which would be the
# checker reporting a clean result for a file it never saw.
GRAPH_FILES = ("nodes.parquet", "edges.parquet", "clusters.parquet", "peel_chains.parquet")

# The four tables SETU writes, which contract section 4 calls the grain split. `counts.in` at
# section 10's grain is every row of every one of them.
ROW_TABLES = (
    "announcements.parquet",
    "transactions.parquet",
    "addresses.parquet",
    "peers.parquet",
)


def _coverage(normalised: Path, nodes: pl.DataFrame) -> list[str]:
    """One node per row of each normalised table, and never fewer."""
    problems: list[str] = []
    expected = {
        "address": pl.read_parquet(normalised / "addresses.parquet").height,
        "transaction": pl.read_parquet(normalised / "transactions.parquet").height,
        "peer": pl.read_parquet(normalised / "peers.parquet").height,
    }
    peers = pl.read_parquet(normalised / "peers.parquet", columns=["asn"])
    expected["asn"] = peers.filter(pl.col("asn").is_not_null())["asn"].n_unique()

    counts = dict(nodes.group_by("kind").len().iter_rows())
    for kind, want in expected.items():
        got = counts.get(kind, 0)
        if got != want:
            detail = (
                " A merge is exactly what section 5 forbids."
                if kind == "address" and got < want
                else ""
            )
            problems.append(f"{got} {kind} nodes, normalised/ holds {want}.{detail}")
    if nodes["node_id"].n_unique() != nodes.height:
        problems.append("node_id is not unique, so an edge endpoint could resolve two ways")
    return problems


def _edges(nodes: pl.DataFrame, edges: pl.DataFrame, clusters: pl.DataFrame) -> list[str]:
    """Every endpoint resolves, and every inferred edge carries what it claims to."""
    problems: list[str] = []
    known = set(nodes["node_id"].to_list())
    for column in ("src", "dst"):
        dangling = edges.filter(~pl.col(column).is_in(known)).height
        if dangling:
            problems.append(f"{dangling} edges have a {column} that is not a node")

    stray = set(edges["kind"].to_list()) - EDGE_KINDS
    if stray:
        problems.append(f"edge kinds outside contract section 5: {sorted(stray)}")
    stray_nodes = set(nodes["kind"].to_list()) - NODE_KINDS
    if stray_nodes:
        problems.append(f"node kinds outside contract section 5: {sorted(stray_nodes)}")
    stray_evidence = set(edges["evidence"].drop_nulls().to_list()) - EVIDENCE_KINDS
    if stray_evidence:
        problems.append(f"evidence values outside contract section 5: {sorted(stray_evidence)}")

    # The requirement in the brief, checked on disk: no SAME_OWNER edge lacks a heuristic and a
    # confidence, and none of them claims to be a fact.
    same_owner = edges.filter(pl.col("kind") == "SAME_OWNER")
    if same_owner.height == 0:
        problems.append("no SAME_OWNER edges at all, so the clustering heuristics produced nothing")
    blank = same_owner.filter(pl.col("evidence").is_null() | pl.col("confidence").is_null()).height
    if blank:
        problems.append(f"{blank} SAME_OWNER edges lack a heuristic name or a confidence")
    certain = same_owner.filter(
        (pl.col("confidence") >= 1.0) | (pl.col("confidence") <= 0.0)
    ).height
    if certain:
        problems.append(
            f"{certain} SAME_OWNER edges sit at or outside 0 and 1. An inferred edge at 1.0 is "
            "rendered as a fact, which a 0.36-precision heuristic has not earned."
        )

    # The same rule, on the other inferred edge kind. A vendored GeoIP table's answer is not a
    # fact the capture observed, so `geoip` at 1.0 would claim more than the table can support.
    # HOSTED_IN built from a capture-carried ASN is `observed` and legitimately 1.0.
    looked_up = edges.filter(pl.col("evidence") == "geoip").filter(pl.col("confidence") >= 1.0)
    if looked_up.height:
        problems.append(
            f"{looked_up.height} geoip edges at confidence 1.0. A lookup is not an observation: "
            "the delegation can have changed between the table being cut and the capture taken."
        )

    structural = edges.filter(pl.col("kind") == "MEMBER_OF")
    dated = structural.filter(pl.col("ts_us").is_not_null() | pl.col("sats").is_not_null()).height
    if dated:
        problems.append(f"{dated} MEMBER_OF edges carry a ts_us or sats, which section 5 nulls")
    if structural.height != int(clusters["n_addresses"].sum() or 0):
        problems.append(
            f"{structural.height} MEMBER_OF edges for {clusters['n_addresses'].sum()} cluster "
            "memberships, so the derived view does not match the clusters it describes"
        )
    return problems


def _clusters(clusters: pl.DataFrame) -> list[str]:
    """`clusters.parquet` self-consistency, and the threshold it claims it was cut at."""
    problems: list[str] = []
    if clusters.height == 0:
        return ["clusters.parquet is empty, so no clustering happened at this threshold"]
    if clusters["threshold"].n_unique() != 1:
        problems.append("clusters.parquet mixes thresholds, so no single cut produced it")
    threshold = float(clusters["threshold"][0])
    wrong = clusters.filter(pl.col("n_addresses") != pl.col("addresses").list.len()).height
    if wrong:
        problems.append(f"{wrong} clusters where n_addresses disagrees with the address list")
    singleton = clusters.filter(pl.col("n_addresses") < 2).height
    if singleton:
        problems.append(f"{singleton} clusters of fewer than two addresses, which are not clusters")
    weak = clusters.filter(pl.col("min_edge_confidence") < threshold).height
    if weak:
        problems.append(f"{weak} clusters held together by an edge below the threshold {threshold}")
    empty = clusters.filter(pl.col("heuristics_used").list.len() == 0).height
    if empty:
        problems.append(f"{empty} clusters name no heuristic, so nothing explains why they exist")
    if clusters["cluster_id"].n_unique() != clusters.height:
        problems.append("cluster_id is not unique")
    return problems


def _accounting(normalised: Path, graph: Path) -> list[str]:
    """`counts` is at row grain, and the rows it names are the rows on disk.

    `check_stage.py` checks the arithmetic; this checks the grain. A stage can satisfy
    `in == out + dropped` at some grain internal to itself while the rows it was handed go
    unaccounted, which is the question contract section 10 exists to answer.
    """
    meta_path = graph / "_meta.json"
    if not meta_path.is_file():
        return []
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    counts = meta.get("counts", {})

    rows = sum(int(pq.ParquetFile(normalised / name).metadata.num_rows) for name in ROW_TABLES)
    problems: list[str] = []
    if counts.get("in") != rows:
        problems.append(
            f"counts.in is {counts.get('in')} and normalised/ holds {rows} rows. Section 10's "
            "grain is rows, so a stage counting something internal leaves its input unaccounted."
        )

    announcements = pl.read_parquet(
        normalised / "announcements.parquet", columns=["txid", "peer_ip"]
    )
    collapsed = announcements.height - announcements.n_unique()
    if counts.get("dropped") != collapsed:
        problems.append(
            f"counts.dropped is {counts.get('dropped')} and {collapsed} announcement rows "
            "describe a (txid, peer_ip) pair another row already described."
        )
    return problems


def _provenance(graph: Path, edges: pl.DataFrame) -> list[str]:
    """`optional_deps.geolite2` and the `evidence` on the HOSTED_IN edges must agree.

    Either both say a vendored lookup ran or neither does. A manifest claiming no GeoIP database
    beside edges labelled `geoip` misstates where the ASN came from, and provenance is the whole
    reason `evidence` is a column rather than a comment.
    """
    meta_path = graph / "_meta.json"
    if not meta_path.is_file():
        return ["graph/ is missing _meta.json, so nothing records what the ASNs came from"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    claimed = bool(meta.get("optional_deps", {}).get("geolite2", False))
    labelled = edges.filter(pl.col("evidence") == "geoip").height
    if labelled and not claimed:
        return [
            f"{labelled} edges are labelled geoip while optional_deps.geolite2 is false. One of "
            "the two is wrong about where the ASN data came from."
        ]
    if claimed and not labelled and edges.filter(pl.col("kind") == "HOSTED_IN").height:
        return [
            "optional_deps.geolite2 is true but no HOSTED_IN edge is labelled geoip, so the "
            "vendored lookup's output is recorded as though the capture had observed it."
        ]
    return []


def _traced(nodes: pl.DataFrame, chains: pl.DataFrame, transactions: pl.DataFrame) -> list[str]:
    """The peel chains describe the nodes, and the transactions they claim to be made of.

    Two checks, and the second is the one worth having. A `peel_chain_id` on a node is a claim that
    this transaction is a hop of that chain and the chain is a claim about which transactions it
    contains, so the two are checked against each other — a writer that marked nodes from one map
    and wrote chains from another would leave them disagreeing and nothing else on disk would
    notice. Then every hop is checked against the peel shape itself, read from `normalised/`: a
    chain of ordinary transactions would be internally consistent and entirely wrong.
    """
    problems: list[str] = []
    if tuple(chains.columns) != CHAIN_COLUMNS:
        return [f"peel_chains.parquet columns are {tuple(chains.columns)}, not section 5's"]

    marked = nodes.filter(pl.col("peel_chain_id").is_not_null())
    if chains.height == 0:
        return (
            [f"{marked.height} nodes carry a peel_chain_id and no chain holds them"]
            if marked.height
            else []
        )

    if chains["peel_chain_id"].n_unique() != chains.height:
        problems.append("peel_chain_id is not unique, so a node could name two chains")

    member: dict[str, str] = {}
    for chain_id, txids in zip(chains["peel_chain_id"], chains["transactions"], strict=True):
        if len(txids) != len(set(txids)):
            problems.append(f"{chain_id} visits a transaction twice")
        for txid in txids:
            member[f"tx:{txid}"] = chain_id

    mislabelled = sum(
        1
        for row in marked.iter_rows(named=True)
        if member.get(row["node_id"]) != row["peel_chain_id"]
    )
    if mislabelled:
        problems.append(
            f"{mislabelled} nodes name a chain that does not list them, so the mark and the chain "
            "came from two different tracings"
        )
    on_graph = set(nodes.filter(pl.col("kind") == "transaction")["node_id"].to_list())
    off_graph = sorted(node for node in member if node not in on_graph)
    if off_graph:
        problems.append(f"{len(off_graph)} chain hops resolve to no transaction node")
    unmarked = sorted(set(member) - set(marked["node_id"].to_list()))
    if unmarked:
        problems.append(
            f"{len(unmarked)} transactions are listed in a chain and carry no peel_chain_id, so "
            "the trace is on disk and not on the graph"
        )

    shallow = chains.filter(pl.col("depth") < CHAIN_MIN_HOPS).height
    if shallow:
        problems.append(f"{shallow} chains are shorter than {CHAIN_MIN_HOPS} hops, which is a peel")
    mismatched = chains.filter(pl.col("depth") != pl.col("transactions").list.len()).height
    if mismatched:
        problems.append(f"{mismatched} chains where depth disagrees with the transactions listed")
    unknown = set(chains["stop_reason"].drop_nulls().to_list()) - CHAIN_STOPS
    if unknown:
        problems.append(f"stop reasons outside section 5's vocabulary: {sorted(unknown)}")
    unrated = chains.filter((pl.col("leak_frac").is_null()) & (pl.col("initial_sats") > 0)).height
    if unrated:
        problems.append(f"{unrated} chains report no leak rate with value entering the chain")
    leaky = chains.filter(pl.col("leak_frac").is_not_null() & (pl.col("initial_sats") <= 0)).height
    if leaky:
        problems.append(f"{leaky} chains report a leak rate with nothing entering the chain")
    wrong_leak = chains.filter(
        pl.col("leak_frac").is_not_null()
        & (pl.col("peeled_sats") / pl.col("initial_sats") != pl.col("leak_frac"))
    ).height
    if wrong_leak:
        problems.append(f"{wrong_leak} chains whose leak_frac is not peeled_sats / initial_sats")
    backwards = chains.filter(
        pl.col("first_us").is_not_null()
        & pl.col("last_us").is_not_null()
        & (pl.col("last_us") < pl.col("first_us"))
    ).height
    if backwards:
        problems.append(f"{backwards} chains end before they start")

    # Every hop, against the shape rather than against the chain's own opinion of it. The writer's
    # hop filter has four more conditions, and this repeats them rather than trusting that a chain
    # labelled a peel is made of peels.
    peelable = set(
        transactions.filter(
            ~pl.col("is_coinbase")
            & (pl.col("n_out") == 2)
            & ~pl.col("has_equal_outputs")
            & (pl.col("output_amounts").list.min() > 0)
            & (
                pl.col("output_amounts").list.min() * PEEL_SHARE_DEN
                <= pl.col("total_out_sats") * PEEL_SHARE_NUM
            )
        )["txid"].to_list()
    )
    not_a_hop = sorted(txid for txid in member if txid.removeprefix("tx:") not in peelable)
    if not_a_hop:
        problems.append(
            f"{len(not_a_hop)} transactions are listed as peel hops and are not two-output "
            "transactions with a thin output, so the chain is not made of peels"
        )
    return problems


def _mixers(nodes: pl.DataFrame, edges: pl.DataFrame, transactions: pl.DataFrame) -> list[str]:
    """The `coinjoin` mark matches the rule, and the set-aside it promises really happened.

    The promise is specific: common-input ownership is not applied across a mixer. The edge table
    cannot say which transaction produced a `SAME_OWNER` edge, so the check goes the other way —
    take each mixer's own input addresses and require that no `multi_input` edge joins any pair of
    them. That is the exclusion, tested from outside rather than read off the manifest.
    """
    problems: list[str] = []
    unset = nodes["coinjoin"].null_count()
    if unset:
        problems.append(
            f"{unset} nodes leave `coinjoin` unset. Section 5 has the column false everywhere it "
            "is not true, so a null is a node nothing decided about."
        )
    marked = nodes.filter(pl.col("coinjoin").fill_null(False))
    not_transaction = marked.filter(pl.col("kind") != "transaction").height
    if not_transaction:
        problems.append(f"{not_transaction} nodes are marked coinjoin and are not transactions")

    shaped = set(
        transactions.filter(
            pl.col("has_equal_outputs")
            & (pl.col("n_out") >= MIXER_MIN_OUTPUTS)
            & (pl.col("n_in") >= MIXER_MIN_INPUTS)
        )["txid"].to_list()
    )
    claimed = {str(node).removeprefix("tx:") for node in marked["node_id"].to_list()}
    if claimed - shaped:
        problems.append(
            f"{len(claimed - shaped)} transactions are marked coinjoin without the shape: "
            "equal outputs, three or more of them, and two or more inputs"
        )
    if shaped - claimed:
        problems.append(
            f"{len(shaped - claimed)} transactions have the mixer shape and are not marked, so a "
            "collaborative transaction went into the clustering heuristics anyway"
        )

    both = marked.filter(pl.col("peel_chain_id").is_not_null()).height
    if both:
        problems.append(
            f"{both} transactions are marked both a mixer and a peel hop. A peel hop is two "
            "outputs with one of them thin; a mixer is three equal ones."
        )

    multi_edges = edges.filter(pl.col("evidence") == "multi_input")
    multi = {
        frozenset((str(src), str(dst)))
        for src, dst in zip(multi_edges["src"], multi_edges["dst"], strict=True)
    }
    inputs = {
        str(txid): [str(one) for one in (addresses if addresses is not None else [])]
        for txid, addresses in zip(
            transactions["txid"], transactions["input_addresses"], strict=True
        )
    }
    joined = 0
    for txid in sorted(claimed):
        addresses = [f"addr:{one}" for one in inputs.get(txid, [])]
        for index, left in enumerate(addresses):
            for right in addresses[index + 1 :]:
                if frozenset((left, right)) in multi:
                    joined += 1
    if joined:
        problems.append(
            f"{joined} multi_input edges join two inputs of a mixer, which is the exclusion "
            "common-input ownership is supposed to make"
        )
    return problems


def check(normalised: Path, graph: Path) -> list[str]:
    """Every way `graph/` fails to describe `normalised/`. Empty means it holds."""
    for name in GRAPH_FILES:
        if not (graph / name).is_file():
            return [f"graph/ is missing {name}"]

    nodes = pl.read_parquet(graph / "nodes.parquet")
    edges = pl.read_parquet(graph / "edges.parquet")
    clusters = pl.read_parquet(graph / "clusters.parquet")
    chains = pl.read_parquet(graph / "peel_chains.parquet")
    transactions = pl.read_parquet(
        normalised / "transactions.parquet",
        columns=[
            "txid",
            "input_addresses",
            "output_amounts",
            "total_out_sats",
            "is_coinbase",
            "has_equal_outputs",
            "n_in",
            "n_out",
        ],
    )
    return (
        _coverage(normalised, nodes)
        + _edges(nodes, edges, clusters)
        + _clusters(clusters)
        + _provenance(graph, edges)
        + _accounting(normalised, graph)
        + _traced(nodes, chains, transactions)
        + _mixers(nodes, edges, transactions)
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        sys.stderr.write("usage: check_graph.py <normalised-dir> <graph-dir>\n")
        return 2
    normalised, graph = Path(args[0]), Path(args[1])
    for one in (normalised, graph):
        if not one.is_dir():
            sys.stderr.write(f"check_graph: {one} is not a directory\n")
            return 2

    problems = check(normalised, graph)
    for line in problems:
        sys.stderr.write(f"  {line}\n")
    if problems:
        sys.stderr.write(f"check_graph: {len(problems)} problems in {graph}\n")
        return 1

    nodes = pl.read_parquet(graph / "nodes.parquet", columns=["kind"])
    edges = pl.read_parquet(graph / "edges.parquet", columns=["kind"])
    clusters = pl.read_parquet(graph / "clusters.parquet", columns=["n_addresses"])
    # Reported, never asserted: the graph is complete with Kuzu absent, so a check that required
    # the Cypher view would invert the optional dependency into a mandatory one.
    meta = json.loads((graph / "_meta.json").read_text(encoding="utf-8"))
    sys.stderr.write(
        f"check_graph: {graph} OK, {nodes.height} nodes, {edges.height} edges, "
        f"{clusters.height} clusters over {clusters['n_addresses'].sum()} addresses, "
        f"kuzu {meta['optional_deps']['kuzu']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
