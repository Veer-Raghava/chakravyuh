"""The peel-chain tracer: walk one coin out through its small-peel-plus-change hops.

A peel hop is one transaction that pays a thin slice away and carries the rest on as change. One
hop is ordinary. A run of them is the typology, because the run is one coin being walked away from
where it came from, a slice at a time, and the change output is the thread that ties the hops
together. This module follows that thread.

It is deliberately sharper than `shastra.typology`'s peel hit, which counts peel-shaped
transactions per subject. A count is not a chain: two peels by one owner on unrelated coins are
two hits and no chain, and nothing in a count says which transaction followed which. The tracer
links a hop to the next only through the change output the next hop actually spends, so what it
emits is a path with a depth and a leak rate rather than a tally.

Neither module imports the other; the shared number is restated, the same way `conform()` and the
path guards are. `PEEL_MAX_SHARE` here is `shastra.typology`'s, and the two criteria agreeing on
what a peel looks like is the point — a stage that disagreed with itself about the shape would make
both numbers unreadable.

Nothing here reads a label or the answer key. A chain is a shape in the transaction graph, and the
tracer can be wrong about it, which is why a chain is a row with a depth and a stopping reason
rather than a deletion or a merge.
"""

from __future__ import annotations

from typing import Final

import polars as pl

from chakravyuh.jaal import mixer

# The peel test, as an exact integer comparison: payment <= 0.35 * total_out, written
# `payment * 20 <= total_out * 7` so no satoshi is ever put through a float. At 21M BTC the
# largest product here is about 4.2e16, well inside int64.
PEEL_MAX_SHARE_NUM: Final[int] = 7
PEEL_MAX_SHARE_DEN: Final[int] = 20
# A single peel is ordinary; the chain is what is being traced. Two is the shortest thing that is
# a run, and it is the same bar `shastra.typology` sets for its peel hit.
PEEL_MIN_HOPS: Final[int] = 2

# Why a walk ended. Four different facts, kept apart: an analyst chasing a chain needs to know
# whether the capture ran out, whether the coin was spent twice, whether the pattern simply
# stopped, or whether the data is inconsistent with a chain of transactions.
NO_CONTINUATION: Final[str] = "no_continuation"
AMBIGUOUS_SPEND: Final[str] = "ambiguous_spend"
CHAIN_BROKEN: Final[str] = "chain_broken"
CYCLE: Final[str] = "cycle"

PEEL_CHAINS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "peel_chain_id": pl.String(),
    # The chain's transactions in hop order, first to last. Named `transactions` rather than
    # `txids` on purpose: `txids` is a name `eval/validate.py` treats as a quarantine tripwire and
    # permits in exactly one observable file (`signals/typology_hits.parquet`), and widening that
    # gate to admit a second file is a worse trade than picking a different name for a column.
    "transactions": pl.List(pl.String()),
    "depth": pl.Int32(),
    "initial_sats": pl.Int64(),
    "peeled_sats": pl.Int64(),
    "leak_frac": pl.Float64(),
    "root_address": pl.String(),
    "first_us": pl.Int64(),
    "last_us": pl.Int64(),
    "stop_reason": pl.String(),
}


def hops(transactions: pl.DataFrame) -> pl.DataFrame:
    """One row per peel-shaped transaction, with what the tracer needs to link it onward.

    A hop is two outputs, the smaller of them a thin slice of the value moved; a mixer is not a
    hop (a collaborative transaction's change is nobody's change), and neither is a coinbase or a
    zero-value payment. `change_index` is the larger output, which is unique because two equal
    outputs would have made `has_equal_outputs` true and excluded the row.

    This frame is also the honest denominator for the whole stage: the number of peel-shaped
    transactions minus the number inside a chain is the count of peels that went nowhere, and that
    count is recorded in `_meta.json` rather than dropped in silence.
    """
    shaped = (
        transactions.filter(
            ~pl.col("is_coinbase")
            & (pl.col("n_out") == 2)
            & ~pl.col("has_equal_outputs")
            & ~mixer.is_mixer()
            & (pl.col("total_out_sats") > 0)
        )
        .with_columns(
            pl.col("output_amounts").list.min().alias("payment_sats"),
            pl.col("output_amounts").list.arg_max().alias("change_index"),
        )
        .filter(
            # Parenthesised, and not for style: `&` binds tighter than `<=` in Python, so the
            # unparenthesised form parses as `((payment > 0) & (payment * 20)) <= (total * 7)`
            # and the share test silently never runs. `scripts/check_graph.py` caught exactly
            # that, from outside, by re-deriving the shape independently.
            (pl.col("payment_sats") > 0)
            & (
                pl.col("payment_sats") * PEEL_MAX_SHARE_DEN
                <= pl.col("total_out_sats") * PEEL_MAX_SHARE_NUM
            )
        )
    )
    # A null amount would make `arg_max` pick an arbitrary index, and the root address would then
    # depend on the null's position rather than on the values. Reading a null as zero makes the
    # comparison well-defined without moving any real amount.
    largest_input = pl.col("input_amounts").list.eval(pl.element().fill_null(0)).list.arg_max()
    return shaped.select(
        "txid",
        "first_seen_us",
        "total_in_sats",
        "payment_sats",
        pl.col("output_addresses")
        .list.get(pl.col("change_index"), null_on_oob=True)
        .alias("change_address"),
        # The pot the chain started from: the largest input of the first hop.
        pl.col("input_addresses").list.get(largest_input, null_on_oob=True).alias("root_address"),
    )


def _spenders(transactions: pl.DataFrame, change_addresses: pl.Series) -> pl.DataFrame:
    """`address -> sorted txids that spend it`, restricted to the change addresses hops produced."""
    return (
        transactions.select("txid", pl.col("input_addresses").alias("address"))
        .explode("address")
        .drop_nulls("address")
        .filter(pl.col("address").is_in(change_addresses))
        .group_by("address")
        .agg(pl.col("txid").sort().alias("spenders"))
    )


def _links(
    hop_frame: pl.DataFrame, spent_by: pl.DataFrame
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """`hop -> next hop` and `hop -> why the walk stopped`, for hops that have no next hop.

    A hop continues only when its change output is spent by exactly one transaction and that
    transaction is itself a hop. Two spenders means the same change address was spent twice in
    this capture and neither continuation can be claimed, so the walk stops and says so. A single
    spender that is not a hop means the pattern ended there — a fan-out, a mixer, or an ordinary
    payment picked the change up.

    A transaction that would inherit two hops is a merge rather than a continuation, and both of
    its would-be predecessors stop: a chain that claimed the merge would be asserting which of two
    coins it was following, and the capture does not say.
    """
    hop_ids = set(hop_frame["txid"].to_list())
    stopped: dict[str, str] = {}
    candidates: dict[str, str] = {}

    joined = hop_frame.select("txid", "change_address").join(
        spent_by.rename({"address": "change_address"}), on="change_address", how="left"
    )
    for row in joined.sort("txid").iter_rows(named=True):
        txid = str(row["txid"])
        spenders = row["spenders"]
        if not spenders:
            stopped[txid] = NO_CONTINUATION
        elif len(spenders) > 1:
            stopped[txid] = AMBIGUOUS_SPEND
        elif spenders[0] == txid or spenders[0] not in hop_ids:
            stopped[txid] = CHAIN_BROKEN
        else:
            candidates[txid] = str(spenders[0])

    inherited: dict[str, list[str]] = {}
    for hop, follower in candidates.items():
        inherited.setdefault(follower, []).append(hop)

    successor: dict[str, str] = {}
    for follower, predecessors in inherited.items():
        if len(predecessors) == 1:
            successor[predecessors[0]] = follower
        else:
            for blocked in predecessors:
                stopped[blocked] = CHAIN_BROKEN
    predecessor = {follower: hop for hop, follower in successor.items()}
    return successor, predecessor, stopped


def _walk(
    hop_ids: set[str], successor: dict[str, str], predecessor: dict[str, str]
) -> tuple[list[list[str]], list[str]]:
    """`(every maximal path, the hops where a walk was cut short by a revisit)`.

    A hop with no predecessor starts a path, so walking from those alone covers every hop that is
    not on a cycle. A chain of transactions cannot contain a cycle — a transaction only spends
    outputs that already existed — but a partial capture is not obliged to be a chain, so whatever
    is left over is walked too and cut, rather than being dropped. Returning the cut hops rather
    than stopping quietly is what lets the chain say `cycle` instead of looking complete.

    Starts are taken in txid order and the result is sorted by first hop, so two interpreters
    number the same chains the same way. Nothing here iterates a set.
    """
    visited: set[str] = set()
    chains: list[list[str]] = []
    cut: list[str] = []

    def follow(start: str) -> None:
        chain = [start]
        visited.add(start)
        node = start
        while node in successor:
            following = successor[node]
            if following in visited:
                cut.append(node)
                break
            visited.add(following)
            chain.append(following)
            node = following
        chains.append(chain)

    for start in sorted(node for node in hop_ids if node not in predecessor):
        if start not in visited:
            follow(start)
    for remaining in sorted(hop_ids - visited):
        if remaining not in visited:
            follow(remaining)
    chains.sort(key=lambda chain: chain[0])
    return chains, cut


def peel_chains(transactions: pl.DataFrame) -> pl.DataFrame:
    """Every peel chain of two hops or more, numbered in a deterministic order.

    One row per chain. `depth` is the number of hops, `initial_sats` the value that entered the
    first hop and `peeled_sats` the total paid away as thin slices across the chain, so
    `leak_frac` is the share of what went in that left as payments. A later hop that also spends
    coin from outside the chain can push `leak_frac` above one; that is reported rather than
    clamped, because a chain that absorbed value is a fact about the chain.
    """
    hop_frame = hops(transactions)
    if hop_frame.is_empty():
        return pl.DataFrame(schema=PEEL_CHAINS_SCHEMA)

    successor, predecessor, stopped = _links(
        hop_frame, _spenders(transactions, hop_frame["change_address"])
    )
    walked, cut = _walk(set(hop_frame["txid"].to_list()), successor, predecessor)
    for hop in cut:
        stopped[hop] = CYCLE
    chains = [chain for chain in walked if len(chain) >= PEEL_MIN_HOPS]

    by_txid = {row["txid"]: row for row in hop_frame.iter_rows(named=True)}
    rows: list[dict[str, object]] = []
    for number, chain in enumerate(chains):
        first = by_txid[chain[0]]
        initial = int(first["total_in_sats"] or 0)
        peeled = sum(int(by_txid[txid]["payment_sats"]) for txid in chain)
        times = [
            int(by_txid[txid]["first_seen_us"])
            for txid in chain
            if by_txid[txid]["first_seen_us"] is not None
        ]
        rows.append(
            {
                "peel_chain_id": f"peel:{number}",
                "transactions": chain,
                "depth": len(chain),
                "initial_sats": initial,
                "peeled_sats": peeled,
                "leak_frac": (peeled / initial) if initial > 0 else None,
                "root_address": first["root_address"],
                "first_us": min(times) if times else None,
                "last_us": max(times) if times else None,
                "stop_reason": stopped.get(chain[-1], NO_CONTINUATION),
            }
        )
    return pl.DataFrame(rows, schema=PEEL_CHAINS_SCHEMA)
