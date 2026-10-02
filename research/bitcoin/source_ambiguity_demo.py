"""Two toy propagation histories with identical capture and different source presence.

This is a constructive observability example, not a reproduction of Bitcoin Core relay.
Only observer-visible events enter the actual causal candidate extraction API.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from common import digest, log
from polars.testing import assert_frame_equal

from chakravyuh.shastra import causal

TXID = "a" * 64
RELAY, HIDDEN, OBSERVER = "192.0.2.1", "198.51.100.2", "203.0.113.3"


def history(source: str) -> tuple[list[dict[str, object]], pl.DataFrame]:
    # Every link delay is one second. Observer only monitors RELAY -> OBSERVER.
    events: list[dict[str, object]] = []
    if source == HIDDEN:
        events.append({"src": HIDDEN, "dst": RELAY, "seen_us": 100_000_000})
    events.append({"src": RELAY, "dst": OBSERVER, "seen_us": 101_000_000})
    visible = [event for event in events if event["dst"] == OBSERVER]
    capture = pl.DataFrame(
        {
            "row_id": range(len(visible)),
            "txid": [TXID] * len(visible),
            "peer_ip": [event["src"] for event in visible],
            "observer_ip": [event["dst"] for event in visible],
            "seen_us": [event["seen_us"] for event in visible],
        }
    )
    return events, capture


def main():
    first_events, first_capture = history(RELAY)
    second_events, second_capture = history(HIDDEN)
    assert_frame_equal(first_capture, second_capture)
    peers = pl.DataFrame({"peer_ip": [RELAY], "asn": [65001], "net_class": ["residential"]})
    tx = pl.DataFrame({"txid": [TXID], "input_addresses": [["wallet-input"]]})
    first = causal.candidates(first_capture, peers, tx, n_observers=1)
    second = causal.candidates(second_capture, peers, tx, n_observers=1)
    assert_frame_equal(first, second)
    output = Path("research/bitcoin/results/source-ambiguity-demo.json")
    report = {
        "worlds": [
            {
                "source": RELAY,
                "source_asn": 65001,
                "created_us": 100_000_000,
                "source_present_in_capture": True,
                "events": first_events,
            },
            {
                "source": HIDDEN,
                "source_asn": 65002,
                "created_us": 99_000_000,
                "source_present_in_capture": False,
                "events": second_events,
            },
        ],
        "capture_equal": True,
        "causal_candidate_features_equal": True,
        "candidate_count": first.height,
        "source_sha256": digest(__file__),
        "candidate_api_sha256": digest(causal.__file__),
        "interpretation": [
            "Identical observations/features do not uniquely determine source host or its presence.",
            "A deterministic model of these inputs gives the same answer in both histories.",
            "Additional observations/assumptions can distinguish cases; more compute alone cannot.",
            "AML evidence remains the same because the observed transaction/money flow is unchanged.",
        ],
        "limitations": [
            "Toy positive-delay announcement process; not complete Bitcoin Core protocol simulation.",
            "Not an empirical estimate of ambiguity frequency, Bayes error or real-world coverage.",
            "Documentation-only IP ranges and private-use ASNs; no real host attribution.",
        ],
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    log("source_ambiguity_demo_verified", candidate_rows=first.height)


if __name__ == "__main__":
    main()
