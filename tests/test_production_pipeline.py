"""Native frozen inference reaches newly signed, replayable cases without labels."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl
import pytest
from test_buddhi_snapshot import _data

from chakravyuh import pipeline
from chakravyuh.pramaan import packet, stage

MODEL = (
    Path(__file__).resolve().parents[1]
    / "research/bitcoin/results/relational-inference-artifacts/address"
)


def test_frozen_pipeline_signs_its_own_cases_and_preserves_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "data/generated/capture"
    normalised = source / "normalised"
    normalised.mkdir(parents=True)
    tx, addresses = _data()
    tx.write_parquet(normalised / "transactions.parquet")
    addresses.write_parquet(normalised / "addresses.parquet")
    pl.DataFrame(
        {
            "row_id": [1, 2],
            "txid": ["early", "future"],
            "peer_ip": ["192.0.2.1", "198.51.100.1"],
            "observer_ip": ["203.0.113.1", "203.0.113.2"],
            "seen_us": [101, 301],
        }
    ).write_parquet(normalised / "announcements.parquet")
    pl.DataFrame(
        {
            "peer_ip": ["192.0.2.1", "198.51.100.1"],
            "net_class": ["hosting", "residential"],
            "asn": [65001, 65002],
        }
    ).write_parquet(normalised / "peers.parquet")
    (source / "sealed").mkdir()
    (source / "sealed/manifest.json").write_text(json.dumps({"input_files": [], "rows_sealed": 2}))
    before = {
        str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in source.rglob("*")
        if p.is_file()
    }
    output = tmp_path / "data/generated/new-cases"
    result = pipeline.run(source, output, MODEL, start_us=0, end_us=200, k=2)
    assert result["selected"] > 0 and result["signed_cases"] == result["selected"]
    for case in (output / "packets").iterdir():
        if not case.is_dir():
            continue
        payload = json.loads((case / "packet.json").read_bytes())
        assert stage.verify_signature(case, tmp_path / "keys")
        assert stage.verify_replay(output, output, case.name, tmp_path)
        assert payload["confidence"]["method"] == "ranking_only"
        assert payload["confidence"]["interval_available"] is False
        assert payload["detection"]["engine"]["feature_count"] == 329
        assert payload["detection"]["lead"]["representative_txid"] == "early"
        assert all(
            n.get("time_us", 0) <= 200
            for n in payload["detection"]["lead"]["evidence_graph"]["nodes"]
        )
        assert payload["counter_findings"]
        corrupted = dict(payload)
        corrupted["confidence"] = dict(payload["confidence"], risk_score=0.999)
        assert not packet.verify_replay_field(corrupted)
    after = {
        str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in source.rglob("*")
        if p.is_file()
    }
    assert before == after
    observed = output / "normalised/announcements.parquet"
    original = observed.read_bytes()
    observed.write_bytes(original + b"tampered")
    with pytest.raises(packet.CaseError, match="scored snapshot"):
        packet.build(output, payload["case_id"], seed=0, replay_command="verify")
    observed.write_bytes(original)
    with pytest.raises(ValueError, match="fresh"):
        pipeline.run(source, output, MODEL, start_us=0, end_us=200)
