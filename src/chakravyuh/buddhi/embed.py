"""Label-free structural embeddings of the JAAL dual graph, as extra BUDDHI columns.

REMODEL-PLAN section 7 asks for "self-supervised graph embeddings (Deep-Graph-Infomax /
GraphSAGE-style) over the JAAL dual graph, fed as extra columns into the GBM". This module is
that signal, built the one way the air-gap allows.

**Why not a trained GNN.** The box is offline: `torch` cannot be installed and `uv.lock` cannot
be regenerated here (P0-a hit the same wall). A dependency-free linearisation of the same family
is therefore what ships — K-hop mean aggregation over the confidence-weighted adjacency,
`H = A_hat^K X` (Wu et al. 2019, *Simplifying Graph Convolutional Networks*: a linear GCN is
exactly this), reduced by an exact SVD to at most `DIM` columns. It reads no labels and learns no
weights, so it is named for what it is — **label-free structural embedding**, not
self-supervised — and the deviation from the plan's wording is recorded rather than hidden
behind the acronym. Upgrade path: if the box ever gets `torch`, a trained encoder swaps in behind
`subject_embeddings` and nothing else changes.

**The window rule, which is the same one `features.cluster_shape` applies.** An edge belongs to a
subject's window when no endpoint carries a timestamp outside it. A node's timestamp is when it
first appeared — an address's `first_seen_us`, a transaction's. An edge whose endpoints have no
timestamp at all (`HOSTED_IN`, peer-to-ASN) is infrastructure metadata, the same kind of static
lookup `GeoLite2` is, so it is in both windows: it is not a fact about the capture's timeline and
cannot leak one.

**What this module must not do.** It never reads a label, never reads outside `edges`,
`transactions` and `addresses`, and returns null — never zero — for a subject with no node in its
window's graph. That null is load-bearing: `stage.py` reads it to decide which booster scored the
row, which is what the per-row `model` flag reports.
"""

from __future__ import annotations

from typing import Final, Literal

import numpy as np
import polars as pl

# The embedding width handed to the GBM, and the propagation depth. Two hops is the SGC default
# and the point where the dual graph's layers actually meet: address -> transaction -> peer, so the
# wire layer reaches the money layer without either being flattened into the other. A window whose
# node design has fewer than `DIM` columns yields fewer (see `_reduce`); the caller fills the rest
# with null, because padding a basis direction that does not exist with zeros would be a fact this
# module made up.
DIM: Final[int] = 8
HOPS: Final[int] = 2

Half = Literal["train", "holdout"]

# Node ids are `<kind>:<value>`; the kind is the prefix. Extracted rather than split so a value
# that contains a colon cannot shift the prefix.
_KIND_RE: Final[str] = r"^([^:]+):"

SUBJECT_ONLY: Final[dict[str, pl.DataType]] = {"subject_id": pl.String()}


def _node_times(transactions: pl.DataFrame, addresses: pl.DataFrame) -> pl.DataFrame:
    """When each timestamped node first appeared. Only addresses and transactions carry a time.

    Peers, ASNs and clusters are structural: the capture says nothing about when they began, and
    inventing a timestamp for them would turn "always present" into a fabricated fact.
    """
    return pl.concat(
        [
            addresses.select(("addr:" + pl.col("address")).alias("node"), "first_seen_us"),
            transactions.select(("tx:" + pl.col("txid")).alias("node"), "first_seen_us"),
        ]
    )


def _window(tagged: pl.DataFrame, half: Half, boundary_us: int) -> pl.DataFrame:
    """The edges visible to one window's subjects.

    `half="train"` keeps edges with no endpoint at or after the boundary; `half="holdout"` keeps
    the ones with no endpoint before it. An edge with no timestamped endpoint is kept by both —
    see the module docstring. With no boundary derived (`boundary_us <= 0`) nothing can be called
    train, so no window exists and the whole graph is the only honest answer.
    """
    if boundary_us <= 0:
        return tagged
    at_or_after = (pl.col("ts_src") >= boundary_us).fill_null(False) | (
        pl.col("ts_dst") >= boundary_us
    ).fill_null(False)
    before = (pl.col("ts_src") < boundary_us).fill_null(False) | (
        pl.col("ts_dst") < boundary_us
    ).fill_null(False)
    return tagged.filter(~at_or_after if half == "train" else ~before)


def _design(window: pl.DataFrame, node_ids: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """`(X, (src, dst, weight))` for this window, over `node_ids` in the order given.

    X's columns are, in an order derived from the data rather than hardcoded so that a new edge
    kind cannot silently vanish: out- and in-degree per edge kind, confidence-weighted degree both
    ways, the log of satoshis moved both ways, and a one-hot of the node's kind.
    """
    kinds = sorted(window["kind"].unique().to_list())
    n = len(node_ids)
    index = pl.DataFrame({"node": node_ids, "i": np.arange(n, dtype=np.int64)})
    placed = (
        window.select("src", "dst", "kind", "sats", "confidence")
        .with_columns(pl.col("confidence").fill_null(0.0), pl.col("sats").fill_null(0))
        .join(index.rename({"node": "src", "i": "src_i"}), on="src", how="left")
        .join(index.rename({"node": "dst", "i": "dst_i"}), on="dst", how="left")
    )
    src = np.asarray(placed["src_i"].to_numpy(), dtype="int64")
    dst = np.asarray(placed["dst_i"].to_numpy(), dtype="int64")
    weight = np.asarray(placed["confidence"].to_numpy(), dtype="float64")
    sats = np.log1p(np.asarray(placed["sats"].to_numpy(), dtype="float64"))
    kind = np.asarray(placed["kind"].to_numpy(), dtype=object)
    node_kind = np.asarray([node.split(":", 1)[0] for node in node_ids], dtype=object)

    columns = [np.bincount(src[kind == k], minlength=n).astype("float64") for k in kinds]
    columns += [np.bincount(dst[kind == k], minlength=n).astype("float64") for k in kinds]
    columns += [
        np.bincount(src, weights=weight, minlength=n),
        np.bincount(dst, weights=weight, minlength=n),
        np.bincount(src, weights=sats, minlength=n),
        np.bincount(dst, weights=sats, minlength=n),
    ]
    columns += [(node_kind == prefix).astype("float64") for prefix in sorted(set(node_kind))]
    return np.column_stack(columns), np.column_stack([src, dst, weight])


def _propagate(x: np.ndarray, coo: np.ndarray, hops: int) -> np.ndarray:
    """`A_hat^hops @ X`, with self-loops and row-normalised (SGC's mean aggregation).

    `scipy.sparse` is imported here rather than at module scope so this leg stays droppable: a run
    that does not ask for embeddings never pays for the import, and deleting this file takes
    nothing with it but the GNN columns. `scipy` arrives with `mapie`'s scikit-learn, like the
    `sklearn` that `model.py` already imports directly.
    """
    from scipy import sparse

    n = x.shape[0]
    src, dst, weight = coo[:, 0].astype("int64"), coo[:, 1].astype("int64"), coo[:, 2]
    adjacency = sparse.csr_matrix((weight, (src, dst)), shape=(n, n)) + sparse.eye(n, format="csr")
    # Every node keeps its self-loop, so no row sums to zero and the division below cannot produce
    # a NaN that would travel into the model as a feature.
    scale = sparse.diags(1.0 / np.asarray(adjacency.sum(axis=1)).ravel())
    normalised = scale @ adjacency
    hidden = x
    for _ in range(hops):
        hidden = normalised @ hidden
    return np.asarray(hidden, dtype="float64")


def _standardise(x: np.ndarray) -> np.ndarray:
    """Per-column zero-mean unit-variance, so one window's embedding is comparable to another's.

    Not cosmetic: the two windows are two different graphs, so an unstandardised design lets the
    window's own scale (chiefly how many satoshis moved inside it) dominate the leading singular
    direction. A model trained on the early window would then read the late window's embeddings as
    a distribution shift rather than as structure. A constant column spreads nothing and is left
    alone rather than divided by zero.
    """
    spread = np.asarray(x.std(axis=0), dtype="float64")
    spread[spread == 0] = 1.0
    return np.asarray((x - x.mean(axis=0)) / spread, dtype="float64")


def _reduce(hidden: np.ndarray, dim: int) -> np.ndarray:
    """Exact SVD reduction to at most `dim` columns, with the singular vectors' sign pinned.

    An SVD is unique only up to the sign of each singular vector. LAPACK is deterministic for a
    fixed input on a fixed machine, which is what `make verify-s07`'s two-interpreter compare
    exercises, but pinning the sign costs two lines and removes the whole class of risk: the
    largest-magnitude entry of each column is made positive, a rule that reads only the output.
    """
    dim = min(dim, hidden.shape[1])
    _, _, right = np.linalg.svd(hidden, full_matrices=False)
    reduced = np.asarray(hidden @ right[:dim].T, dtype="float64")
    for column in range(reduced.shape[1]):
        vector = reduced[:, column]
        if vector[int(np.argmax(np.abs(vector)))] < 0:
            reduced[:, column] = -vector
    return reduced


def subject_embeddings(
    edges: pl.DataFrame,
    transactions: pl.DataFrame,
    addresses: pl.DataFrame,
    members: pl.DataFrame,
    *,
    half: Half,
    boundary_us: int,
    dim: int = DIM,
    hops: int = HOPS,
) -> pl.DataFrame:
    """One embedding row per subject in `members` that has a node in this window's graph.

    `members` is the `(subject_id, address)` map for the half being embedded — the caller hands
    train members with `half="train"` and holdout members with `half="holdout"`, exactly as it
    already calls `cluster_shape` twice. A subject's embedding is the mean of its member addresses'
    node embeddings; a subject whose members have no node here is absent from the result, and the
    caller's left join turns that into null rather than zero.
    """
    empty = pl.DataFrame(schema=SUBJECT_ONLY)
    if members.height == 0:
        return empty

    times = _node_times(transactions, addresses)
    tagged = (
        edges.select("src", "dst", "kind", "sats", "confidence")
        .join(times.rename({"node": "src", "first_seen_us": "ts_src"}), on="src", how="left")
        .join(times.rename({"node": "dst", "first_seen_us": "ts_dst"}), on="dst", how="left")
    )
    window = _window(tagged, half, boundary_us)
    if window.height == 0:
        return empty

    node_ids = sorted(set(window["src"].to_list()) | set(window["dst"].to_list()))
    x, coo = _design(window, node_ids)
    reduced = _reduce(_propagate(_standardise(x), coo, hops), dim)

    subjects = members["subject_id"].unique().sort()
    placed = (
        members.select("subject_id", ("addr:" + pl.col("address")).alias("node"))
        .join(
            pl.DataFrame({"node": node_ids, "row": np.arange(len(node_ids), dtype=np.int64)}),
            on="node",
            how="inner",
        )
        .join(
            pl.DataFrame({"subject_id": subjects, "s": np.arange(subjects.len(), dtype=np.int64)}),
            on="subject_id",
            how="inner",
        )
    )
    if placed.height == 0:
        return empty

    totals = np.zeros((subjects.len(), reduced.shape[1]), dtype="float64")
    counts = np.zeros(subjects.len(), dtype="float64")
    np.add.at(totals, placed["s"].to_numpy(), reduced[placed["row"].to_numpy()])
    np.add.at(counts, placed["s"].to_numpy(), 1.0)
    present = counts > 0
    mean = totals[present] / counts[present][:, None]
    return pl.DataFrame(
        {
            "subject_id": subjects.filter(pl.Series(present)),
            **{f"embed_{i:02d}": mean[:, i] for i in range(mean.shape[1])},
        }
    )
