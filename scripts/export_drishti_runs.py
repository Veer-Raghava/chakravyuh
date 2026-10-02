"""Export the local run inventory, preserving missing stages instead of borrowing a case."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import polars as pl

from chakravyuh.api import serialize

OUT = Path("apps/drishti-v2/src/data/fixtures/runs")
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--runs", nargs="+", help="Refresh only named runs; retain other catalog entries"
)
args = parser.parse_args()
CATALOG = (
    json.loads((OUT / "catalog.json").read_text())
    if args.runs and (OUT / "catalog.json").exists()
    else []
)
for run in sorted(Path("data/generated").iterdir()):
    if not run.is_dir():
        continue
    if args.runs and run.name not in args.runs:
        continue
    CATALOG = [r for r in CATALOG if r["id"] != run.name]
    # Evaluation-side aggregate export is explicit and outside the serving API.
    from chakravyuh.eval.presentation import export as export_presentation

    if (Path("measurements") / run.name).is_dir() or (run / "pipeline.json").is_file():
        export_presentation(run)
    payload = {}
    errors = {}

    def capture(key, operation, payload=payload, errors=errors):
        try:
            payload[key] = operation()
        except (
            FileNotFoundError,
            KeyError,
            IndexError,
            pl.exceptions.PolarsError,
            ValueError,
        ) as error:
            errors[key] = str(error)

    if (run / "sealed/manifest.json").exists():
        capture("manifest", lambda run=run: serialize.manifest(run))
    if (run / "normalised/transactions.parquet").exists():
        capture("collapse", lambda run=run: serialize.collapse(run))
        capture("transactions", lambda run=run: serialize.transactions(run, 200, 0))
        capture("world", lambda run=run: serialize.world(run))
    if (run / "graph/nodes.parquet").exists():
        capture("graph", lambda run=run: serialize.graph(run, "cluster", None, 500))
        capture("graphAddress", lambda run=run: serialize.graph(run, "address", None, 500))
        capture("graphActor", lambda run=run: serialize.graph(run, "actor", None, 500))
    estimates = run / "signals/origin_estimates.parquet"
    if estimates.exists():
        frame = pl.read_parquet(estimates)
        ensemble = frame.filter(pl.col("estimator") == "ensemble").sort(["txid", "rank"])
        for key, abstain in [("origin", False), ("originAbstain", True)]:
            choices = ensemble.filter(pl.col("abstain") == abstain)["txid"].unique().sort()
            if len(choices):
                capture(
                    key, lambda run=run, txid=str(choices[0]): serialize.origin_estimate(run, txid)
                )
    if (run / "alerts/alerts.parquet").exists():
        capture("alerts", lambda run=run: serialize.alerts(run, 200, 0, None))
        top = pl.read_parquet(run / "alerts/alerts.parquet").sort("rank")
        if top.height:
            case = str(top["alert_id"][0])
            capture("alert", lambda run=run, case=case: serialize.alert(run, case))
            payload["alertDetails"] = {}
            payload["packets"] = {}
            case_ids = set(top.head(20)["alert_id"].to_list())
            case_ids.update(path.parent.name for path in (run / "packets").glob("*/packet.json"))
            for aid in sorted(case_ids):
                try:
                    payload["alertDetails"][aid] = serialize.alert(run, aid)
                    if (run / "packets" / aid / "packet.json").exists():
                        payload["packets"][aid] = serialize.packet(run, aid)
                except (
                    FileNotFoundError,
                    KeyError,
                    IndexError,
                    ValueError,
                    pl.exceptions.PolarsError,
                ) as error:
                    errors["case:" + aid] = str(error)
            if (run / "packets" / case / "packet.json").exists():
                capture("packet", lambda run=run, case=case: serialize.packet(run, case))
    if "graphAddress" in payload and estimates.exists():
        payload["originDetails"] = {}
        known = set(ensemble["txid"].to_list())
        for node in payload["graphAddress"]["nodes"]:
            txid = node["node_id"].removeprefix("tx:")
            if node["kind"] == "transaction" and txid in known:
                try:
                    payload["originDetails"][txid] = serialize.origin_estimate(run, txid)
                except (
                    FileNotFoundError,
                    KeyError,
                    IndexError,
                    ValueError,
                    pl.exceptions.PolarsError,
                ) as error:
                    errors["origin:" + txid] = str(error)
    # The global scene is capped. Focused traces keep every captured money
    # endpoint and announcing peer for the selected transaction.
    if "graphAddress" in payload:
        nodes = pl.read_parquet(run / "graph/nodes.parquet")
        edges = pl.read_parquet(run / "graph/edges.parquet")
        focuses = {
            n["node_id"] for n in payload["graphAddress"]["nodes"] if n["kind"] == "transaction"
        }
        focuses.update(
            "tx:" + o["txid"] for o in [payload.get("origin"), payload.get("originAbstain")] if o
        )
        focuses.update(
            "tx:" + a["origin"]["txid"]
            for a in payload.get("alertDetails", {}).values()
            if a.get("origin")
        )
        focuses.update(
            "tx:" + a["representative_txid"]
            for a in payload.get("alertDetails", {}).values()
            if a.get("representative_txid")
        )
        payload["focusedGraphs"] = {}
        for focus in sorted(focuses):
            incident = edges.filter((pl.col("src") == focus) | (pl.col("dst") == focus))
            ids = set(incident["src"].to_list()) | set(incident["dst"].to_list()) | {focus}
            # ASN belongs to each announcing peer; ownership ties remain local hypotheses.
            hosted = edges.filter((pl.col("kind") == "HOSTED_IN") & pl.col("src").is_in(ids))
            ids.update(hosted["dst"].to_list())
            local_edges = edges.filter(pl.col("src").is_in(ids) & pl.col("dst").is_in(ids))
            local_nodes = nodes.filter(pl.col("node_id").is_in(ids))
            payload["focusedGraphs"][focus] = dict(
                detail="address",
                node_cap=local_nodes.height,
                aggregated=None,
                nodes=[
                    dict(
                        node_id=row["node_id"],
                        kind=serialize._node_kind(row["node_id"]),
                        label=serialize._redacted_address(row["label"])
                        if row["node_id"].startswith(("addr:", "cluster:"))
                        else row["label"],
                        first_us=row["first_us"],
                        last_us=row["last_us"],
                    )
                    for row in local_nodes.iter_rows(named=True)
                ],
                edges=[
                    dict(
                        src=row["src"],
                        dst=row["dst"],
                        kind=row["kind"],
                        ts_us=row["ts_us"],
                        sats=row["sats"],
                        confidence=float(row["confidence"]),
                        evidence=row["evidence"],
                    )
                    for row in local_edges.iter_rows(named=True)
                ],
            )
            txid = focus.removeprefix("tx:")
            if estimates.exists() and txid in known and txid not in payload["originDetails"]:
                capture(
                    "_focusOrigin", lambda run=run, txid=txid: serialize.origin_estimate(run, txid)
                )
                if "_focusOrigin" in payload:
                    payload["originDetails"][txid] = payload.pop("_focusOrigin")
    text = json.dumps(payload, separators=(",", ":")) + "\n"
    (OUT / f"{run.name}.json").write_text(text)
    curated = run.name in [
        "agency-graph",
        "agency-v2",
        "_sweep-0.10",
        "_sweep-0.02",
        "s12-canonical",
    ]
    CATALOG.append(
        dict(
            id=run.name,
            curated=curated,
            available=list(payload),
            stages=sorted(p.name for p in run.iterdir() if p.is_dir()),
            sha256=hashlib.sha256(text.encode()).hexdigest(),
            observer_fraction=payload.get("world", {}).get("observer_fraction"),
            alert_count=len(payload.get("alerts", {}).get("alerts", [])),
            errors=errors,
        )
    )
    sys.stderr.write(f"drishti-export: {run.name} {list(payload)}\n")
(OUT / "catalog.json").write_text(
    json.dumps(sorted(CATALOG, key=lambda r: r["id"]), indent=2) + "\n"
)
