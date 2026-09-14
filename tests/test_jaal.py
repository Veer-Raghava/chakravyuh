"""JAAL: what must hold when two layers become one graph.

Two tests here are marked `quarantine` and registered in `tests/conftest.py`: the one that builds
the whole graph in a working directory where the answer key does not exist, and the one that greps
the three written files for the quarantined names. They are Law 2 rules that only a real run can
demonstrate, so `make verify-quarantine` collects them as well as the stage gate.

Everything that writes does so under `tmp_path` and changes directory into it first, because
JAAL's path guard is relative to the working directory: running from `tmp_path` exercises the
guard rather than stepping around it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from chakravyuh.jaal import build, cluster, view
from chakravyuh.jaal.stage import InputPathError, build_run, resolve_in, resolve_out
from chakravyuh.kavach.seal import resolve_out as kavach_out
from chakravyuh.kavach.seal import seal
from chakravyuh.setu.stage import normalise_run
from chakravyuh.setu.stage import resolve_in as setu_in
from chakravyuh.setu.stage import resolve_out as setu_out

REPO = Path(__file__).resolve().parent.parent
FIXTURE_CAPTURE = REPO / "data" / "fixtures" / "capture" / "capture.csv"

# Transcribed from docs/DATA-CONTRACTS.md section 5 by hand, not imported from
# chakravyuh.jaal.build. A contract test that reads the same constant the code writes from
# asserts only that a module equals itself.
CONTRACT_SECTION_5: dict[str, list[tuple[str, str]]] = {
    "nodes.parquet": [
        ("node_id", "String"),
        ("kind", "String"),
        ("label", "String"),
        ("first_us", "Int64"),
        ("last_us", "Int64"),
    ],
    "edges.parquet": [
        ("src", "String"),
        ("dst", "String"),
        ("kind", "String"),
        ("ts_us", "Int64"),
        ("sats", "Int64"),
        ("confidence", "Float64"),
        ("evidence", "String"),
    ],
    "clusters.parquet": [
        ("cluster_id", "String"),
        ("addresses", "List(String)"),
        ("n_addresses", "Int32"),
        ("min_edge_confidence", "Float64"),
        ("heuristics_used", "List(String)"),
        ("threshold", "Float64"),
    ],
}

# Section 5's closed vocabularies, also transcribed.
CONTRACT_NODE_KINDS = {"address", "transaction", "peer", "cluster", "asn"}
CONTRACT_EDGE_KINDS = {"SPENDS", "RECEIVES", "ANNOUNCED_BY", "SAME_OWNER", "HOSTED_IN", "MEMBER_OF"}
CONTRACT_EVIDENCE = {"multi_input", "change_addr", "observed", "geoip"}


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repo root holding `data/` and nothing else, with the process moved into it."""
    (tmp_path / "data" / "generated").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _normalise_fixture(workspace: Path, name: str = "run") -> Path:
    """Seal and normalise the committed capture into `<workspace>/data/generated/<name>/`.

    The committed fixture rather than a generated capture: it is small enough to reason about, it
    is the same input the S03 and S04 gates use, and it carries the documented bad row, so the
    graph is built over a post-rejection table like every real run's is.
    """
    target = workspace / "data" / "capture.csv"
    target.write_bytes(FIXTURE_CAPTURE.read_bytes())
    seal(target, kavach_out(Path("data/generated") / name))
    run = workspace / "data" / "generated" / name
    normalise_run(setu_in(run / "sealed"), setu_out(run))
    return run


def _build(
    workspace: Path, name: str = "run", threshold: float = cluster.DEFAULT_THRESHOLD
) -> Path:
    """Normalise the fixture and build a graph from it. Returns the `graph/` directory."""
    run = _normalise_fixture(workspace, name)
    build_run(resolve_in(run / "normalised"), resolve_out(run), threshold)
    return run / "graph"


def _frames(graph: Path) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    return (
        pl.read_parquet(graph / "nodes.parquet"),
        pl.read_parquet(graph / "edges.parquet"),
        pl.read_parquet(graph / "clusters.parquet"),
    )


def _same_owner(pairs: list[tuple[str, str, float, str]]) -> pl.DataFrame:
    """A hand-built `SAME_OWNER` edge table, for the tests that compute the answer themselves."""
    return build.conform(
        pl.DataFrame(
            {
                "src": [f"addr:{src}" for src, _, _, _ in pairs],
                "dst": [f"addr:{dst}" for _, dst, _, _ in pairs],
                "kind": ["SAME_OWNER"] * len(pairs),
                "ts_us": [None] * len(pairs),
                "sats": [None] * len(pairs),
                "confidence": [confidence for _, _, confidence, _ in pairs],
                "evidence": [evidence for _, _, _, evidence in pairs],
            },
            schema={
                "src": pl.String(),
                "dst": pl.String(),
                "kind": pl.String(),
                "ts_us": pl.Int64(),
                "sats": pl.Int64(),
                "confidence": pl.Float64(),
                "evidence": pl.String(),
            },
        ),
        build.EDGES_SCHEMA,
    )


# --- contract -------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(CONTRACT_SECTION_5))
def test_each_output_matches_contract_section_5(workspace: Path, name: str) -> None:
    """Column names, order and dtypes, against the document rather than against the writer."""
    graph = _build(workspace)
    schema = pl.read_parquet_schema(graph / name)
    assert [(key, str(value)) for key, value in schema.items()] == CONTRACT_SECTION_5[name]


def test_every_kind_is_inside_the_contract_vocabulary(workspace: Path) -> None:
    """Section 5 closes three vocabularies. A value outside one is a contract violation."""
    nodes, edges, _ = _frames(_build(workspace))
    assert set(nodes["kind"].to_list()) <= CONTRACT_NODE_KINDS
    assert set(edges["kind"].to_list()) <= CONTRACT_EDGE_KINDS
    assert set(edges["evidence"].drop_nulls().to_list()) <= CONTRACT_EVIDENCE
    # Anti-vacuity: the fixture must actually exercise the kinds this test claims to check.
    assert {"address", "transaction", "peer", "cluster"} <= set(nodes["kind"].to_list())
    assert {"SPENDS", "RECEIVES", "ANNOUNCED_BY", "SAME_OWNER", "MEMBER_OF"} <= set(
        edges["kind"].to_list()
    )


def test_meta_satisfies_section_10_and_links_upstream(workspace: Path) -> None:
    """The staleness link and the counts identity, on a real run."""
    graph = _build(workspace)
    meta = json.loads((graph / "_meta.json").read_text(encoding="utf-8"))

    assert meta["stage"] == "jaal"
    assert meta["counts"]["in"] == meta["counts"]["out"] + meta["counts"]["dropped"]
    assert sum(meta["counts"]["drop_reasons"].values()) == meta["counts"]["dropped"]
    assert meta["params"]["upstream_meta"]["path"].endswith("normalised/_meta.json")
    assert len(meta["params"]["upstream_meta"]["sha256"]) == 64
    assert {entry["path"] for entry in meta["outputs"]} == {
        f"graph/{name}" for name in CONTRACT_SECTION_5
    }


def test_no_label_carries_a_complete_identifier(workspace: Path) -> None:
    """`label` is a display column, so a full identifier here is a full identifier on a screen."""
    nodes, _, _ = _frames(_build(workspace))
    addresses = pl.read_parquet(
        workspace / "data" / "generated" / "run" / "normalised" / "addresses.parquet"
    )["address"].to_list()
    transactions = pl.read_parquet(
        workspace / "data" / "generated" / "run" / "normalised" / "transactions.parquet"
    )["txid"].to_list()
    peers = pl.read_parquet(
        workspace / "data" / "generated" / "run" / "normalised" / "peers.parquet"
    )["peer_ip"].to_list()

    labels = set(nodes["label"].to_list())
    for full in addresses + transactions + peers:
        assert f"addr:{full}" not in labels
        assert f"tx:{full}" not in labels
        assert f"peer:{full}" not in labels
    # Anti-vacuity: the walk must have had something to check.
    assert len(addresses) > 10 and len(transactions) > 10 and len(peers) > 5
    # And the truncation must really be truncation rather than a rename.
    address_labels = nodes.filter(pl.col("kind") == "address")["label"].to_list()
    assert all("…" in one for one in address_labels)
    peer_labels = nodes.filter(pl.col("kind") == "peer")["label"].to_list()
    assert all(one.endswith(".x.x") or ":x:x" in one for one in peer_labels)


# --- the heuristics -------------------------------------------------------------------------


def test_no_same_owner_edge_lacks_a_heuristic_and_a_confidence(workspace: Path) -> None:
    """The brief's first requirement, on every written edge.

    An inferred edge at confidence 1.0 would be rendered as a fact by the console, which a
    0.36-precision heuristic has not earned, so the bound is strict at both ends.
    """
    _, edges, _ = _frames(_build(workspace))
    same_owner = edges.filter(pl.col("kind") == "SAME_OWNER")
    assert same_owner.height > 0, "the fixture produced no clustering edges, so this proved nothing"

    assert same_owner["evidence"].null_count() == 0
    assert same_owner["confidence"].null_count() == 0
    assert set(same_owner["evidence"].to_list()) <= {"multi_input", "change_addr"}
    assert same_owner["confidence"].min() > 0.0  # type: ignore[operator]
    assert same_owner["confidence"].max() < 1.0  # type: ignore[operator]

    # The observed edges are the mirror image: confidence exactly 1.0, because the capture saw
    # them. HOSTED_IN is deliberately not in this list — it is 1.0 only when the capture carried
    # the ASN itself, and below 1.0 when a vendored table supplied it, which is the case the
    # next test pins.
    facts = edges.filter(pl.col("kind").is_in(["SPENDS", "RECEIVES", "ANNOUNCED_BY"]))
    assert facts["confidence"].min() == 1.0
    assert facts["confidence"].max() == 1.0


def test_a_looked_up_asn_is_not_a_fact(workspace: Path) -> None:
    """Section 5 reserves 1.0 for facts, and a GeoIP table's answer is not one.

    The same peers, built twice: once told the upstream ran a vendored lookup and once not. The
    edges are structurally identical and only the provenance columns move, which is the point —
    a delegation can change between a table being cut and a capture being taken, so a console
    filtering on confidence has to be able to tell the two apart.
    """
    peers = pl.read_parquet(_normalise_fixture(workspace) / "normalised" / "peers.parquet")
    if peers["asn"].null_count() == peers.height:
        pytest.skip("no ASN resolved in this fixture, so there is nothing hosted anywhere")

    looked_up = build.hosting_edges(peers, from_lookup=True)
    observed = build.hosting_edges(peers, from_lookup=False)
    assert looked_up.height == observed.height > 0
    assert looked_up.drop("confidence", "evidence").equals(observed.drop("confidence", "evidence"))

    assert set(looked_up["evidence"].to_list()) == {"geoip"}
    assert looked_up["confidence"].max() < 1.0  # type: ignore[operator]
    assert set(observed["evidence"].to_list()) == {"observed"}
    assert observed["confidence"].min() == 1.0


def test_same_owner_never_merges_nodes(workspace: Path) -> None:
    """Contract section 5's hard rule, asserted as a count and as an invariance.

    One address row, one address node, at every threshold. A union-find implementation would
    collapse addresses into representatives and the first assertion would drop; an implementation
    that rebuilt nodes per threshold would break the second.
    """
    run = _normalise_fixture(workspace)
    addresses = pl.read_parquet(run / "normalised" / "addresses.parquet").height

    seen = []
    for threshold in (0.2, 0.9):
        build_run(resolve_in(run / "normalised"), resolve_out(run), threshold)
        nodes, _, clusters = _frames(run / "graph")
        assert nodes.filter(pl.col("kind") == "address").height == addresses
        seen.append(
            (
                nodes.filter(pl.col("kind") == "address").sort("node_id").to_dicts(),
                clusters.height,
            )
        )

    # The address nodes are identical across the two cuts; only the derived view moved.
    assert seen[0][0] == seen[1][0]
    assert seen[0][1] > 0, "the low threshold produced no clusters, so nothing was compared"
    assert seen[1][1] == 0, "0.9 is above both heuristic confidences, so no cluster survives it"


def test_the_threshold_selects_heuristics_by_hand() -> None:
    """Four addresses, three edges, three cuts. The answer is computed here, not by the code.

    Edges: a-b and b-c at 0.36 from multi_input, c-d at 0.25 from change_addr.

    At 0.2 all three hold, so one cluster of four whose weakest link is 0.25 and which names both
    heuristics. At 0.3 the change edge drops, leaving a-b-c: three addresses, weakest 0.36, one
    heuristic. At 0.5 nothing holds and there is no cluster at all.
    """
    edges = _same_owner(
        [
            ("a", "b", 0.36, "multi_input"),
            ("b", "c", 0.36, "multi_input"),
            ("c", "d", 0.25, "change_addr"),
        ]
    )

    low, low_members = cluster.clusters(edges, 0.2)
    assert low.height == 1
    assert low["addresses"].to_list() == [["a", "b", "c", "d"]]
    assert low["n_addresses"].to_list() == [4]
    assert low["min_edge_confidence"].to_list() == [0.25]
    assert low["heuristics_used"].to_list() == [["change_addr", "multi_input"]]
    assert low["threshold"].to_list() == [0.2]
    assert low_members.height == 4
    assert set(low_members["dst"].to_list()) == {"cluster:0"}
    # MEMBER_OF is structural, so section 5 nulls its time and its value.
    assert low_members["ts_us"].null_count() == 4
    assert low_members["sats"].null_count() == 4

    middle, middle_members = cluster.clusters(edges, 0.3)
    assert middle["addresses"].to_list() == [["a", "b", "c"]]
    assert middle["min_edge_confidence"].to_list() == [0.36]
    assert middle["heuristics_used"].to_list() == [["multi_input"]]
    assert middle_members.height == 3

    high, high_members = cluster.clusters(edges, 0.5)
    assert high.height == 0
    assert high_members.height == 0


def test_a_star_and_a_clique_cluster_the_same(workspace: Path) -> None:
    """The shape choice, justified as a test rather than as a comment.

    JAAL emits n-1 star edges per transaction where a clique would emit n(n-1)/2. The derived
    clusters must be identical either way, or the saving would have cost information.
    """
    star = _same_owner(
        [
            ("a", "b", 0.36, "multi_input"),
            ("a", "c", 0.36, "multi_input"),
            ("a", "d", 0.36, "multi_input"),
        ]
    )
    clique = _same_owner(
        [
            ("a", "b", 0.36, "multi_input"),
            ("a", "c", 0.36, "multi_input"),
            ("a", "d", 0.36, "multi_input"),
            ("b", "c", 0.36, "multi_input"),
            ("b", "d", 0.36, "multi_input"),
            ("c", "d", 0.36, "multi_input"),
        ]
    )
    assert star.height == 3 and clique.height == 6
    assert cluster.clusters(star, 0.2)[0].to_dicts() == cluster.clusters(clique, 0.2)[0].to_dicts()


def test_coinjoin_like_transactions_produce_no_multi_input_edge() -> None:
    """The heuristic's known failure mode, excluded rather than emitted and regretted.

    Two transactions, identical except that the second has two outputs of equal value. Several
    unrelated parties signing one transaction is exactly what equal outputs signal, so the second
    contributes nothing.
    """
    frame = pl.DataFrame(
        {
            "txid": ["plain", "coinjoin"],
            "is_coinbase": [False, False],
            "n_in": [2, 2],
            "has_equal_outputs": [False, True],
            "input_addresses": [["a", "b"], ["c", "d"]],
        }
    )
    edges = cluster.common_input_edges(frame)
    assert edges.height == 1
    assert edges["src"].to_list() == ["addr:a"]
    assert edges["dst"].to_list() == ["addr:b"]
    assert edges["confidence"].to_list() == [cluster.MULTI_INPUT_CONFIDENCE]


def test_the_stronger_heuristic_wins_a_duplicate_pair() -> None:
    """Both heuristics can propose one pair. Two edges would understate what holds the cluster."""
    frame = pl.DataFrame(
        {
            "txid": ["one"],
            "is_coinbase": [False],
            "n_in": [2],
            "n_out": [2],
            "has_equal_outputs": [False],
            "change_index": [0],
            "input_addresses": [["a", "b"]],
            "output_addresses": [["a", "z"]],
        }
    )
    # multi_input proposes a-b; change_addr proposes a-b too, because the change output pays an
    # input address back.
    assert cluster.common_input_edges(frame).height == 1
    assert cluster.change_edges(frame).height >= 1

    merged = cluster.same_owner_edges(frame)
    pairs = list(zip(merged["src"].to_list(), merged["dst"].to_list(), strict=True))
    assert len(pairs) == len(set(pairs)), "a pair was written twice"
    assert merged.filter((pl.col("src") == "addr:a") & (pl.col("dst") == "addr:b"))[
        "confidence"
    ].to_list() == [cluster.MULTI_INPUT_CONFIDENCE]


def test_the_degree_distribution_is_heavy_tailed(workspace: Path) -> None:
    """A real graph has hubs. A blob or a pile of pairs has neither, and both are bugs.

    Two ratios rather than a fitted power law: the mean pulled well above the median, and a p99
    an order of magnitude above it. Measured on a 2000-transaction run at 3.84 and 27.7, so the
    bounds below have room, and a graph that had collapsed or shattered fails both.
    """
    _, edges, _ = _frames(_build(workspace))
    degree = (
        pl.concat(
            [edges.select(pl.col("src").alias("node")), edges.select(pl.col("dst").alias("node"))]
        )
        .group_by("node")
        .len()
        .sort("len")
    )
    counts = degree["len"].to_list()
    assert len(counts) > 100, "too few nodes for a distribution to mean anything"

    median = counts[len(counts) // 2]
    mean = sum(counts) / len(counts)
    p99 = counts[int(len(counts) * 0.99)]
    assert median >= 1
    assert mean / median >= 2.0, f"mean {mean:.2f} over median {median} is not a tail"
    assert p99 / median >= 10.0, f"p99 {p99} over median {median} is not a tail"


# --- optional dependencies and paths --------------------------------------------------------


def test_the_graph_is_complete_without_kuzu(workspace: Path) -> None:
    """Requirement 5. Kùzu missing costs the Cypher view and nothing else."""
    graph = _build(workspace)
    meta = json.loads((graph / "_meta.json").read_text(encoding="utf-8"))

    assert meta["optional_deps"]["kuzu"] == view.available()
    nodes, edges, clusters = _frames(graph)
    assert nodes.height > 0 and edges.height > 0 and clusters.height > 0

    if view.available():  # pragma: no cover - kuzu is not installed in this repo
        pytest.skip("kuzu is installed, so the absent path cannot be exercised here")
    assert "kuzu_absent_cypher_view_unavailable" in meta["warnings"]
    assert view.cypher_view(graph) is None


def test_the_input_path_guard_refuses_a_sibling_tree(workspace: Path) -> None:
    """`--in` is allowlisted to `data/`, which is what makes the quarantine structural."""
    outside = workspace / "ground" / "truth"
    outside.mkdir(parents=True)
    with pytest.raises(InputPathError):
        resolve_in(outside)
    with pytest.raises(InputPathError):
        resolve_out(workspace / "data" / "generated")


def test_two_builds_of_one_normalised_agree(workspace: Path) -> None:
    """Determinism inside one process. The gate repeats it across two, which is the real test."""
    run = _normalise_fixture(workspace)
    build_run(resolve_in(run / "normalised"), resolve_out(run))
    first = {name: (run / "graph" / name).read_bytes() for name in CONTRACT_SECTION_5}
    build_run(resolve_in(run / "normalised"), resolve_out(run))
    second = {name: (run / "graph" / name).read_bytes() for name in CONTRACT_SECTION_5}
    assert first == second


# --- quarantine -----------------------------------------------------------------------------


def test_jaal_builds_with_the_answer_key_absent(workspace: Path) -> None:
    """Law 2 rule 6, run rather than asserted.

    A subprocess whose working directory holds only `data/`. The answer key is not merely unread
    here, it does not exist on any path the process could construct, so a stage that had quietly
    grown a dependency on it cannot complete. Run twice: once plain, and once with --score, which
    must degrade to a warning rather than die.
    """
    _normalise_fixture(workspace, "isolated")
    script = (
        "import sys; from pathlib import Path;"
        f"sys.path.insert(0, {str(REPO / 'src')!r});"
        "from chakravyuh.jaal.stage import build_run, resolve_in, resolve_out;"
        "build_run(resolve_in(Path('data/generated/isolated/normalised')),"
        " resolve_out(Path('data/generated/isolated')))"
    )
    finished = subprocess.run(
        [sys.executable, "-c", script],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-2000:]

    meta = json.loads(
        (workspace / "data" / "generated" / "isolated" / "graph" / "_meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert meta["counts"]["in"] == meta["counts"]["out"] + meta["counts"]["dropped"]
    assert meta["counts"]["out"] > 0

    scored = subprocess.run(
        [
            sys.executable,
            "-m",
            "chakravyuh.jaal",
            "--in",
            "data/generated/isolated/normalised",
            "--out",
            "data/generated/isolated",
            "--score",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert scored.returncode == 0, scored.stderr[-2000:]
    assert "not scored" in scored.stderr
    # And nothing was created outside data/, because there was nothing to write a measurement to.
    assert sorted(one.name for one in workspace.iterdir()) == ["data"]


def test_no_graph_artifact_names_the_quarantine(workspace: Path) -> None:
    """Law 2 rule 4: no observable file may contain either quarantined path, as a name or a value.

    The literals are reconstructed rather than written, so this file does not itself hold the two
    strings the source-tree grep looks for.
    """
    forbidden = ("ground" + "_truth", "measure" + "ments")
    graph = _build(workspace)

    checked = 0
    for path in sorted(graph.rglob("*")):
        if not path.is_file():
            continue
        checked += 1
        if path.suffix == ".json":
            text = path.read_text(encoding="utf-8")
            assert not any(one in text for one in forbidden), f"{path.name} names the quarantine"
            continue
        frame = pl.read_parquet(path)
        assert not set(frame.columns) & set(forbidden)
        for column in frame.columns:
            if frame.schema[column] != pl.String():
                continue
            values = frame[column].drop_nulls()
            for one in forbidden:
                assert (
                    values.str.contains(one, literal=True).sum() == 0
                ), f"{path.name}.{column} carries {one!r}"
    assert checked >= 4, "the walk found fewer files than one graph writes, so it proved nothing"

    # The source side of the same rule: no JAAL module may name either path.
    for module in sorted((REPO / "src" / "chakravyuh" / "jaal").rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        assert not any(one in text for one in forbidden), f"{module.name} names the quarantine"
