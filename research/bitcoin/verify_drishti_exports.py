"""Check exported run identity and complete focused transaction evidence against stored graphs."""

import hashlib
import json
import sys
from pathlib import Path

import polars as pl

root = Path("apps/drishti-v2/src/data/fixtures/runs")
checks = []


def edge_key(row):
    return tuple(
        row.get(k) for k in ["src", "dst", "kind", "ts_us", "sats", "confidence", "evidence"]
    )


for item in json.loads((root / "catalog.json").read_text()):
    if item["id"] != "agency-v2" and not item["id"].startswith("_sweep-"):
        continue
    path = root / (item["id"] + ".json")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    payload = json.loads(path.read_text())
    assert payload["world"]["run_id"] == item["id"]
    assert set(item["available"]) == set(payload)
    if item["id"].startswith("_sweep-"):
        assert not {"alerts", "alert", "packet", "packets"}.intersection(payload)
    source = pl.read_parquet(Path("data/generated") / item["id"] / "graph/edges.parquet")
    for focus, graph in payload["focusedGraphs"].items():
        ids = {n["node_id"] for n in graph["nodes"]}
        assert focus in ids
        assert all(e["src"] in ids and e["dst"] in ids for e in graph["edges"])
        expected = source.filter(
            ((pl.col("src") == focus) | (pl.col("dst") == focus))
            & pl.col("kind").is_in(["SPENDS", "RECEIVES", "ANNOUNCED_BY"])
        )
        got = [
            e
            for e in graph["edges"]
            if (e["src"] == focus or e["dst"] == focus)
            and e["kind"] in ["SPENDS", "RECEIVES", "ANNOUNCED_BY"]
        ]
        assert sorted(map(edge_key, got), key=str) == sorted(
            map(edge_key, expected.iter_rows(named=True)), key=str
        ), focus
    for origin in [payload["origin"], payload.get("originAbstain")]:
        if origin:
            assert "tx:" + origin["txid"] in payload["focusedGraphs"]
            assert origin["txid"] in payload["originDetails"]
    checks.append(
        {
            "run": item["id"],
            "complete_focused_traces": len(payload["focusedGraphs"]),
            "packets": len(payload.get("packets", {})),
        }
    )
output = Path("research/bitcoin/results/drishti-redesign/export-report.json")
output.write_text(json.dumps(checks, indent=2) + "\n")
sys.stdout.write(json.dumps(checks, indent=2) + "\n")
