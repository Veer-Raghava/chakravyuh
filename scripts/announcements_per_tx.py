"""Print the realized announcements-per-transaction ratio of a run, for rider 0a.

The S10 brief says the scale arithmetic must not be hardcoded: MAYAJAAL's `n_txs` default is
`target_rows // mean_announcements_per_tx`, but the realized ratio depends on the observer
fraction, the deadline drop, and which transactions reached any observer at all. This script
prints the measured number the way the validator computes it — capture rows over gossiped
(non-coinbase) transactions — so docs/PERF.md quotes what the run did, never what the config
hoped. Stdlib only. Prints one ratio, never a row of data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: announcements_per_tx.py <run-dir>", file=sys.stderr)
        return 2
    run = Path(args[0])
    meta = json.loads((run / "capture" / "_meta.json").read_text(encoding="utf-8"))
    counts = meta["counts"]
    rows = counts["in"] + counts["out"]
    if rows <= 0:
        print("announcements_per_tx: the capture is empty", file=sys.stderr)
        return 1
    tx_meta = json.loads((run / "chain" / "_meta.json").read_text(encoding="utf-8"))
    gossiped = tx_meta["params"]["n_transactions"] - tx_meta["params"]["n_blocks"]
    if gossiped <= 0:
        print("announcements_per_tx: no gossiped transactions", file=sys.stderr)
        return 1
    config = json.loads((run / "config.effective.json").read_text(encoding="utf-8"))
    wanted = config["mean_announcements_per_tx"]
    ratio = rows / gossiped
    print(
        f"announcements_per_tx: {rows} capture rows / {gossiped} gossiped transactions = "
        f"{ratio:.3f} (config target {wanted})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
