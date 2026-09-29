#!/usr/bin/env python3
"""Rewrite the alert headlines in `data/fixtures/ui/alerts.json` as analyst prose.

WHY THIS EXISTS. VAANI writes one headline per alert from the top two SHAP features through a
single template (`vaani/evidence.py:137`), so 200 alerts collapse onto 30 strings and ~62% of
them open with the same coinjoin clause. The facts are right; the presentation reads as
template garbage on the VAANI and PRAMAAN screens.

WHAT THIS IS NOT. Not an LLM, not a network call, not a new scoring path. It is pattern
matching over facts the run already produced, plus a hand-written phrase bank: offline,
deterministic (seeded 42 per alert id), and re-runnable byte for byte.

SOURCE OF TRUTH, in order:
  1. `<run>/alerts/evidence.parquet` — the run's real SHAP rows, 5 per alert, with weights.
     Preferred: the fixture headline is truncated to 96 characters, which loses features 3-5
     and leaves ~4% of headlines genuinely ambiguous (one truncated clause covers both
     `mean_sent_sats` and `mean_p_origin`).
  2. The existing headline — the fallback when no run directory is present. LOSSY by
     construction; see `PINS`, which pins the truncated clauses whose longest-phrase guess is
     known to be wrong. Running the fallback prints how many alerts took it.

Prose rules carried over from CLAUDE.md: no raw feature name ever reaches the screen, no
identifier is rendered (counts only), "cluster" is avoided because AlertCard renders the
headline raw and does not scrub it, and every claim is traceable to a feature that fired.

Usage:
    python3 scripts/generate_headlines.py                     # rewrite in place
    python3 scripts/generate_headlines.py --dry-run           # report, write nothing
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
GLOSS_TABLE = REPO / "docs" / "FEATURES.md"
ALERTS_PATH = REPO / "data" / "fixtures" / "ui" / "alerts.json"
EVIDENCE_PATH = REPO / "data" / "generated" / "agency-v2" / "alerts" / "evidence.parquet"
SEED = 42
MAX_LEN = 200  # Two sentences that still fit three lines of AlertCard; LeadsScreen clamps to one.

_GLOSS_ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(.+?)\s*\|\s*$")

# ── the phrase bank ───────────────────────────────────────────────────────────────────────
# One entry per feature that actually fires as a top-3 signal in the canonical run, per
# direction. `high`/`low` is the sign of the SHAP weight, so a `low` clause must be the true
# inverse of its `high` twin, never a weaker restatement. "*" means direction-blind.
CLAUSES: dict[str, dict[str, list[str]]] = {
    "frac_equal_outputs": {
        "high": [
            "most of its transactions settle to equal-value outputs, the on-chain "
            "fingerprint of a CoinJoin",
            "equal-value outputs dominate its transaction mix, the classic mixer footprint",
            "it keeps paying out in matched, same-sized outputs, which is what mixing produces",
        ],
        "low": [
            "equal-value outputs are rare across its history, so mixing is not what flagged it"
        ],
    },
    "fan_in_ratio": {
        "high": [
            "it sweeps wide sets of input addresses into single transactions",
            "many separate addresses are consolidated into one transaction at a time",
            "scattered inputs are gathered up in bulk rather than spent where they sit",
        ],
        "low": ["its transactions draw on very few input addresses at once"],
    },
    "max_fan_out": {
        "high": [
            "single transactions pay out to a wide fan of addresses",
            "its sends split into a broad fan of outputs instead of one recipient",
        ],
        "low": ["its sends stay with a narrow set of recipients"],
    },
    "peel_leak_frac": {
        "high": [
            "its peel chains leak an unusually large share of value out as the payment, "
            "not the change",
            "each peel moves most of the value out and leaves only a thin change trail behind",
        ],
        "low": ["its peels hold most of the value back in the change leg"],
    },
    "median_dwell_us": {
        "high": [
            "funds sit for an unusually long stretch between arriving and being sent on",
            "receipts linger before the next send, and that slow dwell is itself the anomaly",
        ],
        "low": [
            "funds are forwarded minutes after arriving, with almost no dwell time",
            "receipts and sends are near-simultaneous, the shape of automated pass-through",
        ],
    },
    "n_addresses": {
        "high": ["a large set of addresses stays active inside its window"],
        "low": ["only a few of its addresses are active"],
    },
    "total_sent_sats": {
        "high": ["it pushes a large volume of satoshis outbound inside its window"],
        "low": ["the volume it sends out is small"],
    },
    "total_received_sats": {
        "high": ["large sums flow in from elsewhere"],
        "low": ["incoming value is thin"],
    },
    "mean_sent_sats": {
        "high": ["its individual sends are large, not dribbled out in small pieces"],
        "low": ["its sends are individually small"],
    },
    "mean_received_sats": {
        "high": ["individual receipts are unusually large"],
        "low": ["its receipts are individually small"],
    },
    "n_tx_received": {
        "high": ["many separate payments land on it"],
        "low": ["almost nothing pays it inside its window"],
    },
    "n_tx_sent": {
        "high": ["it sends often enough that the frequency itself stands out"],
        "low": ["it sends rarely"],
    },
    "balance_sats": {
        "high": ["receipts outrun sends and the surplus is left to sit"],
        "low": ["sends outrun receipts and the balance is draining away"],
    },
    "n_counterparties": {
        "high": ["it deals with a wide spread of distinct counterparties"],
        "low": ["its counterparties are few"],
    },
    "n_coinbase_received": {
        "high": ["block rewards land on it, which is what mining pools look like"],
    },
    "n_typologies": {
        "high": ["several distinct laundering morphologies fire on its sends"],
    },
    "n_typology_txns": {
        "high": ["a run of its sends feeds a flagged laundering pattern"],
    },
    "structuring_frac": {
        "high": [
            "its send amounts sit just under round-number thresholds, the shape of "
            "deliberate structuring",
            "amounts stop just beneath the round figures a reporting rule would latch onto",
        ],
    },
    "burstiness": {
        "high": ["its sends bunch into tight bursts rather than a steady flow"],
    },
    "peel_chain_depth": {
        "high": ["its peel runs are long, not a one-off"],
    },
    "fee_anomaly": {
        "high": ["its fee rate sits well clear of the going rate for its window"],
        "low": ["its fees are unremarkable for its window"],
    },
    "mean_asn_margin": {
        "high": ["the leading network operator stands clearly ahead of the runner-up"],
        "low": ["the operator estimate is too close to call"],
    },
    "mean_origin_margin": {
        "high": ["the top origin candidate separates cleanly from the runner-up"],
    },
    "mean_p_origin": {
        "high": ["the origin estimate lands with real confidence on its sends"],
    },
    "mean_p_asn": {
        "high": ["the operator estimate is unusually confident on its sends"],
    },
    "frac_origin_abstained": {
        "high": ["the origin estimator refused to answer on a large share of its sends"],
    },
    "frac_l1_abstained": {
        "high": ["no single operator could be named for a large share of its sends"],
    },
    "frac_top1_tor": {
        "high": ["its leading origin candidate is a Tor exit"],
    },
    "mean_n_announcements": {
        "high": ["its sends are gossiped unusually widely across announcing peers"],
    },
    "min_edge_confidence": {
        "high": ["even the weakest link holding its owner group together is a strong one"],
        "low": ["the links holding its owner group together are weak"],
    },
    "n_heuristics": {
        "high": ["several independent on-chain patterns agree on who owns it"],
    },
    "n_script_types": {
        "high": ["its addresses span several script formats"],
    },
}

# Reached only by a feature this bank has never seen (a new run, a new model). Kept honest and
# deliberately vague rather than inventing a pattern; the run below counts how often it fires.
GENERIC = ["the model's strongest signal on this wallet is far from the peer norm"]

LABELS_BY_TYPOLOGY: dict[tuple[str, ...], list[str]] = {
    ("coinjoin_like", "fan_out"): [
        "Mixer then fan-out",
        "CoinJoin plus fan-out",
        "Mix and distribute",
    ],
    ("coinjoin_like",): ["CoinJoin footprint", "Mixer footprint"],
    ("fan_out",): ["Fan-out payout", "Wide distribution"],
    ("peel_chain",): ["Peel chain", "Peel and move"],
    ("structuring",): ["Structured sends", "Threshold hugging"],
}
LABELS_BY_FEATURE: dict[str, str] = {
    "frac_equal_outputs": "Mixer footprint",
    "fan_in_ratio": "Consolidation sweep",
    "max_fan_out": "Fan-out payout",
    "peel_leak_frac": "Peel chain",
    "structuring_frac": "Structured sends",
    "median_dwell_us": "Timing anomaly",
    "balance_sats": "Flow imbalance",
    "fee_anomaly": "Fee anomaly",
    "n_addresses": "Address sprawl",
    "total_sent_sats": "Outbound volume",
    "total_received_sats": "Inbound volume",
    "mean_asn_margin": "Operator lead",
    "n_tx_received": "Inbound stream",
}
LEADS = [
    "Nothing subtle here",
    "The shape is familiar",
    "Read the flow of funds",
    "Start with the money",
    "The pattern is too clean to be organic",
    "This is not background noise",
    "Strip away the noise",
    "Look at the shape of the wallet",
    "The signals line up",
    "Taken together",
    "The behaviour is consistent throughout",
    "Two facts point the same way",
]

NET_PHRASES: dict[str, str] = {
    "vpn_suspect": "the leading origin candidate sits in a VPN range",
    "mobile": "the leading origin candidate is a mobile carrier rather than a fixed line",
    "hosting": "the leading origin candidate sits in a hosting range",
    "residential": "the leading origin candidate is a residential line",
}

# The truncated clause texts whose longest-phrase guess is known wrong, pinned from the
# canonical run's own SHAP rows. Only the fallback path reads this.
PINS: dict[str, str] = {
    "how far": "mean_asn_margin",  # longest-phrase would pick fee_anomaly
    "average size of it": "mean_received_sats",
    "average": "peel_leak_frac",
    "most add": "fan_in_ratio",
    "distinct": "n_counterparties",
    "hig": "median_dwell_us",  # a clause truncated mid-word leaves nothing to match on
}


# ── reading the facts ─────────────────────────────────────────────────────────────────────
def load_glosses() -> dict[str, str]:
    """Feature name -> its gloss phrase, from the same table the alerts gate validates against."""
    table = {}
    for line in GLOSS_TABLE.read_text(encoding="utf-8").splitlines():
        if match := _GLOSS_ROW.match(line):
            table[match.group(1)] = match.group(2)
    if not table:
        raise SystemExit(f"no feature glosses in {GLOSS_TABLE}; cannot name features in prose")
    return table


def features_from_evidence(
    path: Path, ids: set[str], glosses: dict[str, str]
) -> dict[str, list[tuple[str, float]]]:
    """The run's real SHAP rows per alert, strongest first. Empty when the run is absent."""
    if not path.is_file():
        return {}
    try:
        import polars as pl
    except ImportError:
        return {}
    rows = pl.read_parquet(path, columns=["alert_id", "kind", "statement", "weight"]).filter(
        (pl.col("kind") == "model_feature") & pl.col("alert_id").is_in(ids)
    )
    out: dict[str, list[tuple[str, float]]] = {}
    for row in rows.iter_rows(named=True):
        statement = str(row["statement"])
        # The statement embeds the gloss verbatim, so the gloss table maps it back to a name.
        key = next((k for k, phrase in glosses.items() if phrase in statement), None)
        if key is not None:
            out.setdefault(str(row["alert_id"]), []).append((key, float(row["weight"])))
    for rows_out in out.values():
        rows_out.sort(key=lambda pair: -abs(pair[1]))
    return out


def features_from_headline(headline: str, glosses: dict[str, str]) -> list[tuple[str, str]]:
    """Top clauses of an existing headline as (feature, direction). Lossy: the text is truncated."""
    body = headline.split(": ", 1)[1] if ": " in headline else headline
    out: list[tuple[str, str]] = []
    for clause in body.split("; "):
        clause = clause.strip().rstrip(".")
        direction = "high"
        for word in ("high", "low"):
            if clause.startswith(word + " "):
                direction, clause = word, clause[len(word) + 1 :]
        clause = clause.rstrip(".").strip()
        if clause in PINS:
            out.append((PINS[clause], direction))
            continue
        candidates = [
            key
            for key, phrase in glosses.items()
            if phrase.startswith(clause) or clause.startswith(phrase)
        ]
        # Longest phrase wins: a truncated clause is a prefix of its own gloss, and of shorter
        # glosses that share an opening, so the longest match is the only defensible guess.
        candidates.sort(key=lambda key: -len(glosses[key]))
        out.append((candidates[0] if candidates else "unknown", direction))
    return out


# ── writing the prose ─────────────────────────────────────────────────────────────────────
def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _clause(key: str, direction: str) -> str:
    bank = CLAUSES.get(key, {})
    options = bank.get(direction) or bank.get("*") or []
    return options[0] if options else GENERIC[0]


def _clause_options(key: str, direction: str) -> list[str]:
    bank = CLAUSES.get(key, {})
    return bank.get(direction) or bank.get("*") or GENERIC


def _owner_phrases(cluster_size: int) -> list[str]:
    if cluster_size > 1:
        return [
            f"the group holds {cluster_size} addresses that move under one owner",
            f"those {cluster_size} addresses move together as one owner",
        ]
    return [
        "nothing on-chain ties it to another address",
        "no on-chain link joins it to another address",
    ]


def _labels(typologies: list[str], first_feature: str) -> list[str]:
    key = tuple(sorted(typologies))
    if key in LABELS_BY_TYPOLOGY:
        return LABELS_BY_TYPOLOGY[key]
    for typology in sorted(typologies):
        if (typology,) in LABELS_BY_TYPOLOGY:
            return LABELS_BY_TYPOLOGY[(typology,)]
    return [LABELS_BY_FEATURE.get(first_feature, "Laundering shape")]


def _prefix(text: str) -> str:
    return " ".join(text.split()[:4]).lower()


def build(
    alert: dict[str, Any],
    features: list[tuple[str, str]],
    rng: random.Random,
    used_opening: dict[str, int],
    used_tail: dict[str, int],
) -> list[tuple[str, str, str]]:
    """Every headline this alert could carry, best first, as (headline, opening key, tail key).

    Ranked by how little its opening has been used in the file so far, then its tail — that
    spread is the whole defence against 200 alerts that read as one template — then by length,
    with the RNG breaking ties so two alerts with identical facts still read differently.
    """
    f1, d1 = features[0]
    labels = _labels(list(alert.get("typologies") or []), f1)
    clause_options = _clause_options(f1, d1)

    openings: list[str] = []
    for clause in clause_options:
        openings.append(f"{_cap(clause)}.")
    for label in labels:
        for clause in clause_options:
            openings.append(f"{label}: {clause}.")
    for lead in LEADS:
        for clause in clause_options:
            openings.append(f"{lead}: {clause}.")

    tails: list[tuple[str, str, str]] = [("", "", "")]  # (sentence form, usage key, clause stated)
    if len(features) > 1:
        tail = _clause(features[1][0], features[1][1])
        owner = _owner_phrases(int(alert.get("cluster_size") or 1))
        net = NET_PHRASES.get(str(alert.get("origin_net_class") or ""))
        forms = [
            f"{_cap(tail)}.",
            f"{_cap(tail)}, and {owner[0]}.",
            f"{_cap(tail)} — {owner[1]}.",
            f"{_cap(tail)}, and {owner[1]}.",
            f"{_cap(tail)}; {owner[0]}.",
        ]
        if net:
            # A semicolon, not "and": the origin leg is a separate claim from the wallet's shape.
            forms += [f"{_cap(tail)}; {net}."]
        if len(features) > 2:
            # The third signal, when the run gave one, is what stops the tails colliding. Joined
            # with a semicolon: several clauses carry their own commas, so "and"/"while" would
            # build a run-on where the semicolon stays grammatical.
            third = _clause(features[2][0], features[2][1])
            if third != tail and "," not in third:
                forms += [f"{_cap(tail)}; {third}."]
        # The usage key counts the wording as well as the shape, so one clause does not front
        # every tail even while its shapes keep rotating.
        tails = [(form, _prefix(form), tail) for form in forms]

    combos: list[tuple[str, str, str]] = []
    for opening in openings:
        # The same clause twice would read as a template, which is the defect being fixed.
        fitting = [
            (form, key)
            for form, key, clause in tails
            if clause not in opening and (not form or len(opening) + len(form) + 1 <= MAX_LEN)
        ]
        # A long opening still gets a lone sentence rather than nothing: dropping the tail costs
        # detail, dropping the opening costs the alert its whole distinctive opening.
        for form, key in fitting or [("", "")]:
            combos.append((opening + (" " + form if form else ""), _prefix(opening), key))
    shuffled = combos[:]
    rng.shuffle(shuffled)
    # Least-used opening first, then least-used tail; among equals the longer string, because the
    # tail is detail the second sentence exists to carry.
    return sorted(
        shuffled,
        key=lambda row: (used_opening.get(row[1], 0), used_tail.get(row[2], 0), -len(row[0])),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--alerts", type=Path, default=ALERTS_PATH)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE_PATH)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = parser.parse_args()

    payload = json.loads(args.alerts.read_text(encoding="utf-8"))
    alerts = payload["alerts"]
    glosses = load_glosses()

    evidence = features_from_evidence(args.evidence, {a["alert_id"] for a in alerts}, glosses)
    source = f"evidence ({args.evidence})" if evidence else "the existing headlines"
    print(f"{len(alerts)} alerts; features from {source}")

    before: dict[str, int] = {}
    for alert in alerts:
        before[alert["headline"]] = before.get(alert["headline"], 0) + 1

    used_opening: dict[str, int] = {}
    used_tail: dict[str, int] = {}
    seen: set[str] = set()
    unknown = 0
    for alert in alerts:
        rows = evidence.get(alert["alert_id"])
        if rows:
            features = [(key, "high" if weight >= 0 else "low") for key, weight in rows[:3]]
        else:
            features = features_from_headline(alert["headline"], glosses)[:2]
        unknown += sum(1 for key, _ in features if key == "unknown")
        rng = random.Random(f"{args.seed}:{alert['alert_id']}")
        options = build(alert, features, rng, used_opening, used_tail)
        # The first candidate whose opening and tail are least-used AND whose string no alert
        # carries yet; a repeat is the exact defect this script exists to fix, so it is checked,
        # not hoped for.
        headline, opening_key, tail_key = next(
            (row for row in options if row[0] not in seen), options[0]
        )
        used_opening[opening_key] = used_opening.get(opening_key, 0) + 1
        # The empty tail is counted too, or dropping the second sentence would always look like
        # the cheapest option and half the file would lose its detail.
        used_tail[tail_key] = used_tail.get(tail_key, 0) + 1
        seen.add(headline)
        alert["headline"] = headline

    after: dict[str, int] = {}
    for alert in alerts:
        after[alert["headline"]] = after.get(alert["headline"], 0) + 1

    top_before = max(before.values())
    top_after = max(after.values())
    print(
        f"unique headlines {len(before)} -> {len(after)} "
        f"(most-repeated {top_before} -> {top_after})"
    )
    if unknown:
        print(
            f"WARNING: {unknown} features are not in the phrase bank; the generic clause was used"
        )
    if len(after) < len(alerts):
        print(
            f"WARNING: {len(alerts) - len(after)} alerts repeated a headline. Expected only on the "
            f"headline-parse fallback, where a truncated source leaves two facts to work with."
        )
    _self_check(alerts)

    if args.dry_run:
        for alert in alerts[:8]:
            print(f"  {alert['rank']:>3}  {alert['headline']}")
        return 0

    args.alerts.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.alerts}")
    return 0


def _self_check(alerts: list[dict[str, Any]]) -> None:
    """The definition-of-done scan, over the strings this run just produced."""
    banned = (
        "cluster",
        "src_ip",
        "peer_ip",
        "p_origin",
        "p_asn",
        "ABSTAIN",
        "conformal",
        "LightGBM",
    )
    raw_names = [key for key in CLAUSES if key in " ".join(a["headline"] for a in alerts)]
    for alert in alerts:
        headline = alert["headline"]
        assert headline, f"alert {alert['alert_id']} has no headline"
        assert len(headline) <= MAX_LEN, f"{headline!r} is {len(headline)} chars, over {MAX_LEN}"
        assert headline.count(".") <= 2, f"{headline!r} is more than two sentences"
        for word in banned:
            assert (
                word.lower() not in headline.lower()
            ), f"{word!r} reached the screen: {headline!r}"
    assert not raw_names, f"raw feature names in prose: {raw_names}"


if __name__ == "__main__":
    sys.exit(main())
