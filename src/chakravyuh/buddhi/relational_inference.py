"""Offline graph-context tree inference; portable artifacts, no Torch or research imports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import numpy as np
import polars as pl
from numpy.typing import NDArray
from scipy.special import expit

from chakravyuh.buddhi import snapshot
from chakravyuh.jaal import provenance
from chakravyuh.shastra.schema import NET_CLASS_CODES

TX_FEATURES = (
    "n_in",
    "n_out",
    "total_out_sats",
    "fee_sats",
    "fee_rate_sat_vb",
    "has_equal_outputs",
)
IP_FEATURES = ("observations", "transactions", "observers", *(f"class_{i}" for i in range(6)))
CONTEXT = (
    *TX_FEATURES,
    *(f"announcer_mean_{n}" for n in IP_FEATURES),
    *(f"funder_mean_{n}" for n in snapshot.SNAPSHOT_FEATURES),
)
FEATURES = (
    *snapshot.SNAPSHOT_FEATURES,
    *(
        n
        for relation in ("received", "spent")
        for n in (
            f"{relation}_log_degree",
            *(
                f"{relation}_{stat}_{field}"
                for stat in ("mean", "std", "min", "max")
                for field in CONTEXT
            ),
        )
    ),
)


def _scale(values: NDArray[Any], parameters: dict[str, Any]) -> NDArray[np.float32]:
    mean = np.asarray(parameters["mean"], dtype=np.float64)
    scale = np.asarray(parameters["scale"], dtype=np.float64)
    if mean.shape != (values.shape[1],) or scale.shape != mean.shape:
        raise ValueError("scaler width mismatch")
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("invalid frozen scaler")
    return ((values - mean) / scale).astype(np.float32)


def _indices(frame: pl.DataFrame, source: str, target: str) -> NDArray[np.int64]:
    return frame.select(source, target).unique().sort(source, target).to_numpy().astype(np.int64).T


def _pool(values: NDArray[np.float32], edges: NDArray[np.int64], size: int) -> NDArray[np.float32]:
    total = np.zeros((size, values.shape[1]), dtype=np.float32)
    count = np.zeros((size, 1), dtype=np.float32)
    np.add.at(total, edges[1], values[edges[0]])
    np.add.at(count, edges[1], 1)
    return (total / np.maximum(count, 1)).astype(np.float32)


def _summaries(
    context: NDArray[np.float32], edges: NDArray[np.int64], size: int
) -> NDArray[np.float32]:
    source, target = edges
    values = context[source].astype(np.float64)
    count = np.bincount(target, minlength=size)
    total = np.zeros((size, context.shape[1]))
    squares = np.zeros_like(total)
    low, high = np.full_like(total, np.inf), np.full_like(total, -np.inf)
    np.add.at(total, target, values)
    np.add.at(squares, target, values**2)
    np.minimum.at(low, target, values)
    np.maximum.at(high, target, values)
    mean = total / np.maximum(count[:, None], 1)
    std = np.sqrt(np.maximum(squares / np.maximum(count[:, None], 1) - mean**2, 0))
    low[count == 0], high[count == 0] = 0, 0
    return np.column_stack([np.log1p(count), mean, std, low, high]).astype(np.float32)


def build(
    tx: pl.DataFrame,
    addresses: pl.DataFrame,
    announcements: pl.DataFrame,
    peers: pl.DataFrame,
    scalers: dict[str, Any],
    *,
    start_us: int,
    end_us: int,
    partition_mode: Literal["heuristic", "address"],
) -> tuple[NDArray[np.float32], snapshot.Snapshot]:
    """329 causal features over explicit decision windows, never neighbor labels."""
    ledger = (
        pl.DataFrame(schema=provenance.LEDGER_SCHEMA)
        if partition_mode == "address"
        else provenance.ownership_evidence(tx)
    )
    view = snapshot.build(
        tx,
        addresses,
        ledger,
        start_us=start_us,
        end_us=end_us,
        threshold=0.3,
        partition_mode=partition_mode,
    )
    subjects = view.table.sort("subject_id").with_row_index("si")
    members = view.members.join(subjects.select("subject_id", "si"), on="subject_id")
    transactions = (
        tx.filter(pl.col("first_seen_us").is_between(start_us, end_us))
        .sort("txid")
        .with_row_index("ti")
    )
    observed = announcements.filter(pl.col("seen_us").is_between(start_us, end_us)).join(
        transactions.select("txid", "ti"), on="txid"
    )
    ips = (
        observed.group_by("peer_ip")
        .agg(
            pl.len().alias("observations"),
            pl.col("txid").n_unique().alias("transactions"),
            pl.col("observer_ip").n_unique().alias("observers"),
        )
        .join(peers.select("peer_ip", "net_class"), on="peer_ip", how="left")
        .sort("peer_ip")
        .with_row_index("pi")
    )

    def links(field: str) -> pl.DataFrame:
        return (
            transactions.select("ti", pl.col(field).alias("address"))
            .explode("address")
            .drop_nulls("address")
            .join(members, on="address")
        )

    funds = _indices(links("input_addresses"), "si", "ti")
    receives = _indices(links("output_addresses"), "ti", "si")
    announces = _indices(observed.join(ips.select("peer_ip", "pi"), on="peer_ip"), "pi", "ti")
    local = np.nan_to_num(
        subjects.select(snapshot.SNAPSHOT_FEATURES).to_numpy().astype(np.float64), nan=0.0
    )
    local = _scale(np.sign(local) * np.log1p(np.abs(local)), scalers["subject"])
    tx_values = np.nan_to_num(
        transactions.select(TX_FEATURES).to_numpy().astype(np.float64), nan=0.0
    )
    tx_values = _scale(np.log1p(np.maximum(tx_values, 0)), scalers["transaction"])
    ip_counts = (
        ips.select("observations", "transactions", "observers").to_numpy().astype(np.float32)
    )
    codes = ips["net_class"].replace_strict(NET_CLASS_CODES, default=0).to_numpy().astype(int)
    ip_values = _scale(np.column_stack([np.log1p(ip_counts), np.eye(6)[codes]]), scalers["ip"])
    context = np.column_stack(
        [
            tx_values,
            _pool(ip_values, announces, len(tx_values)),
            _pool(local, funds, len(tx_values)),
        ]
    ).astype(np.float32)
    result = np.column_stack(
        [
            local,
            _summaries(context, receives, len(local)),
            _summaries(context, funds[::-1], len(local)),
        ]
    ).astype(np.float32)
    if result.shape[1] != len(FEATURES) or not np.isfinite(result).all():
        raise ValueError("invalid relational feature matrix")
    return result, view


def score(
    normalised: Path, model_dir: Path, *, start_us: int, end_us: int
) -> tuple[pl.DataFrame, snapshot.Snapshot, dict[str, Any]]:
    """Native CPU tree predictions and exact raw-margin TreeSHAP explanations."""
    import xgboost as xgb

    metadata = json.loads((model_dir / "manifest.json").read_text())
    if metadata.get("features") != list(FEATURES) or metadata.get("schema_version") != 1:
        raise ValueError("unsupported relational artifact schema")
    mode = metadata.get("partition_mode")
    if mode not in ("address", "heuristic"):
        raise ValueError("unsupported partition mode")
    model_path = model_dir / "model.json"
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if digest != metadata["model_sha256"]:
        raise ValueError("model digest mismatch")
    names = ("transactions", "addresses", "announcements", "peers")
    frames = {n: pl.read_parquet(normalised / f"{n}.parquet") for n in names}
    values, view = build(
        frames["transactions"],
        frames["addresses"],
        frames["announcements"],
        frames["peers"],
        metadata["scalers"],
        start_us=start_us,
        end_us=end_us,
        partition_mode=mode,
    )
    model = xgb.Booster(params={"nthread": 4})
    model.load_model(model_path)
    if len(values):
        matrix = xgb.DMatrix(values)
        raw = model.predict(matrix)
        shap = model.predict(matrix, pred_contribs=True)
        margin = model.predict(matrix, output_margin=True)
    else:
        raw = np.empty(0, dtype=np.float32)
        margin = raw
        shap = np.empty((0, len(FEATURES) + 1), dtype=np.float32)
    if not np.allclose(shap.sum(axis=1), margin, atol=1e-4, rtol=1e-4):
        raise ValueError("TreeSHAP margin reconstruction failed")
    clipped = np.clip(raw, 1e-6, 1 - 1e-6)
    dtype = metadata["platt_dtype"]
    if dtype not in ("float32", "float64"):
        raise ValueError("unsupported calibration dtype")
    logits = np.log(clipped / (1 - clipped)).astype(dtype)
    probability = expit(
        logits * np.asarray(metadata["platt_coefficient"], dtype=dtype)
        + np.asarray(metadata["platt_intercept"], dtype=dtype)
    )
    result = view.table.select("subject_id").with_columns(
        pl.Series("risk_score", probability),
        pl.Series("raw_score", raw),
        *(pl.Series(f"shap_{n}", shap[:, i]) for i, n in enumerate(FEATURES)),
        pl.Series("shap_bias", shap[:, -1]),
    )
    run = {
        "engine": "causal-relational-xgboost",
        "feature_count": len(FEATURES),
        "partition_mode": mode,
        "start_us": start_us,
        "end_us": end_us,
        "model_sha256": digest,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_sha256": {
            n: hashlib.sha256((normalised / f"{n}.parquet").read_bytes()).hexdigest() for n in names
        },
        "score_meaning": "historically calibrated synthetic activity ranking; no guilt probability",
    }
    return result.sort(["risk_score", "subject_id"], descending=[True, False]), view, run
