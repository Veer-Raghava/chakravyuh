"""Write `data/fixtures/ui/` — the eight adapter payloads as committed JSON.

One exporter, calling `chakravyuh.api.serialize` directly. That is the whole point: the
console's fixtures and the API's responses are produced by the same code, so "the shapes
match" is true by construction rather than by someone remembering to keep two files in step.

S10 note, recorded here because it is a fact about the project's history: Track B had not
started when these fixtures were first generated, so the payload shapes were authored from
`docs/DATA-CONTRACTS.md` and the reference run rather than from a Track B client. The adapter
surface itself is fixed by `docs/DRISHTI-SPEC.md` and did not change.

Usage: uv run python scripts/export_ui_fixtures.py --run _sweep-0.10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chakravyuh.api import serialize  # noqa: E402

UI_DIR = Path("data/fixtures/ui")


def _write(name: str, payload: object) -> None:
    path = UI_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stderr.write(f"fixtures-ui: {path}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", required=True, help="run id under data/generated/")
    args = parser.parse_args(argv)

    run_dir = Path("data/generated") / args.run
    if not run_dir.is_dir():
        sys.stderr.write(f"fixtures-ui: no run directory {run_dir}\n")
        return 2
    UI_DIR.mkdir(parents=True, exist_ok=True)

    _write("manifest", serialize.manifest(run_dir))
    _write("collapse", serialize.collapse(run_dir))
    _write("transactions", serialize.transactions(run_dir, limit=200, offset=0))
    _write("alerts", serialize.alerts(run_dir, limit=200, offset=0, severity=None))

    # One confident origin case and one abstain case, so the console's abstain state has a
    # real payload. Chosen deterministically: first txid with 8+ lanes, first abstained txid
    # announced by a Tor exit (asn 64510 in this world), both from the run's own tables.
    import polars as pl

    txs = pl.read_parquet(
        run_dir / "normalised" / "transactions.parquet",
        columns=["txid", "n_announcements", "is_coinbase"],
    )
    confident = txs.filter(~pl.col("is_coinbase") & (pl.col("n_announcements") >= 8)).sort("txid")[
        "txid"
    ][0]
    _write("origin", serialize.origin_estimate(run_dir, str(confident)))

    peers = pl.read_parquet(run_dir / "normalised" / "peers.parquet", columns=["peer_ip", "asn"])
    tor_peers = set(peers.filter(pl.col("asn") == 64510)["peer_ip"].to_list())
    announcements = pl.read_parquet(
        run_dir / "normalised" / "announcements.parquet", columns=["txid", "peer_ip"]
    )
    estimates = pl.read_parquet(
        run_dir / "signals" / "origin_estimates.parquet",
        columns=["txid", "estimator", "rank", "abstain"],
    )
    abstained = set(
        estimates.filter((pl.col("estimator") == "ensemble") & pl.col("abstain"))["txid"]
        .unique()
        .to_list()
    )
    tor_txids = set(
        announcements.filter(pl.col("peer_ip").is_in(tor_peers))["txid"].unique().to_list()
    )
    abstain_case = sorted(abstained & tor_txids)
    if abstain_case:
        _write("origin-abstain", serialize.origin_estimate(run_dir, abstain_case[0]))
    else:
        sys.stderr.write("fixtures-ui: no tor-abstain case in this run; fixture omitted\n")

    _write("graph", serialize.graph(run_dir, detail="cluster", focus=None, cap=2000))
    _write("graph-address", serialize.graph(run_dir, detail="address", focus=None, cap=500))

    top = pl.read_parquet(run_dir / "alerts" / "alerts.parquet", columns=["alert_id", "rank"]).sort(
        "rank"
    )["alert_id"][0]
    _write("alert", serialize.alert(run_dir, str(top)))

    packet_path = run_dir / "packets" / str(top) / "packet.json"
    if packet_path.is_file():
        _write("packet", serialize.packet(run_dir, str(top)))
    else:
        sys.stderr.write(
            f"fixtures-ui: no packet for {top}; run pramaan --case {top} on this run first\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
