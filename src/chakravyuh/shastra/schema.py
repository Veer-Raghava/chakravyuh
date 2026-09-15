"""Contract section 6, transcribed. Column order and dtype are the contract, not a suggestion.

Transcribed by hand rather than derived from the frames the stage builds, for the reason every
stage in this repo restates its schema: a schema generated from the code that writes it agrees with
that code by construction and so cannot catch the code drifting from the contract.

`features` is a struct whose field order is fixed here too. Contract section 6 names eight fields
it must hold "at minimum"; those eight come first, in the order the contract lists them, and the
extras the prompt asks for follow. A reader diffing this file against the contract should see the
first eight line up without having to search.
"""

from __future__ import annotations

from typing import Final

import polars as pl

STAGE: Final[str] = "shastra"
OUT_DIR: Final[str] = "signals"

# The contract's eight, then the rest. `net_class` stays a string rather than becoming a code:
# the struct is the explanation an analyst reads and a replay input, so it carries the word.
FEATURES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "delta_first_us": pl.Int64(),
    "rank_in_tx": pl.Int32(),
    "n_announcements": pl.Int32(),
    "n_observers_seen": pl.Int32(),
    "peer_frac_rank_one": pl.Float64(),
    "peer_n_txids": pl.Int32(),
    "net_class": pl.String(),
    "announce_spread_us": pl.Int64(),
    "n_observers_blind": pl.Int32(),
    "peer_degree": pl.Int32(),
    "payer_shared": pl.Int32(),
    "n_candidates": pl.Int32(),
    "is_tor_exit": pl.Boolean(),
    "is_hosting": pl.Boolean(),
}

ORIGIN_ESTIMATES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "txid": pl.String(),
    "peer_ip": pl.String(),
    "p_origin": pl.Float64(),
    "rank": pl.Int32(),
    "margin": pl.Float64(),
    "features": pl.Struct(FEATURES_SCHEMA),
    "estimator": pl.String(),
    "abstain": pl.Boolean(),
    "abstain_reason": pl.String(),
}

TYPOLOGY_HITS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "hit_id": pl.String(),
    "typology": pl.String(),
    "subject_id": pl.String(),
    "txids": pl.List(pl.String()),
    "strength": pl.Float64(),
    "params": pl.Struct({"threshold": pl.Float64(), "window_us": pl.Int64()}),
}

ENTITY_TYPES_SCHEMA: Final[dict[str, pl.DataType]] = {
    "subject_id": pl.String(),
    "predicted_type": pl.String(),
    "confidence": pl.Float64(),
    "basis": pl.List(pl.String()),
    "exempt_from_scoring": pl.Boolean(),
}

# The estimator names contract section 6 permits in the `estimator` column. Two are built; the
# other two are names the contract reserves and this stage does not write, which is why the check
# is membership rather than equality.
ESTIMATORS: Final[tuple[str, ...]] = (
    "first_spy",
    "weighted_first_seen",
    "bayes_peer_prior",
    "ensemble",
)

ABSTAIN_REASONS: Final[tuple[str, ...]] = (
    "tor_present",
    "single_observer",
    "margin_below_floor",
    "too_few_announcements",
)

# What the model is allowed to look at. Every one is observable: nothing here is derived from
# the answer key, and the two categoricals arrive as codes rather than strings so a tree cannot
# order them alphabetically by accident.
MODEL_FEATURES: Final[tuple[str, ...]] = (
    "delta_first_us",
    "rank_in_tx",
    "n_announcements",
    "n_observers_seen",
    "n_observers_blind",
    "peer_frac_rank_one",
    "peer_n_txids",
    "peer_degree",
    "announce_spread_us",
    "payer_shared",
    "n_candidates",
    "net_class_code",
    "is_tor_exit",
    "is_hosting",
)

# Fixed so a model trained in one process scores identically in another. Alphabetical, with the
# absent case pinned at zero rather than sorted in, because "vendor/ said nothing" is not a class
# of network and a run with an empty vendor/ must not shift every other code by one.
NET_CLASS_CODES: Final[dict[str, int]] = {
    "hosting": 1,
    "residential": 2,
    "tor_exit": 3,
    "unknown": 4,
    "vpn_suspect": 5,
}
TOR_CLASS: Final[str] = "tor_exit"
HOSTING_CLASSES: Final[frozenset[str]] = frozenset({"hosting", "vpn_suspect"})


def conform(frame: pl.DataFrame, schema: dict[str, pl.DataType]) -> pl.DataFrame:
    """Select in schema order and cast each column, so the contract decides the layout.

    Restated from JAAL rather than imported: no stage imports another stage's internals, and a
    shared helper here would be the first crack in that rule for the sake of six lines.
    """
    return frame.select([pl.col(name).cast(dtype).alias(name) for name, dtype in schema.items()])


def empty(schema: dict[str, pl.DataType]) -> pl.DataFrame:
    """A zero-row frame with exactly this schema."""
    return pl.DataFrame(schema=schema)
