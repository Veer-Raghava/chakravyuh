"""Evidence rows: the reasons for an alert, and the language that states them.

Every statement is a template over observable quantities; no LLM call, no network, no clock
in the text path, which is what makes the same input render the same three sentences in a
second process. Identifiers are truncated here, at write time, so the parquet itself is
safe to open on a projector — a raw column name never appears because every feature name
passes through the gloss table first.

The three-sentence reason string is assembled from the evidence and counter rows by
`reason_string`, at read time, by PRAMAAN or the console. `alerts.parquet` stays
contract-exact; the reason is derived, never stored.
"""

from __future__ import annotations

from typing import Final

import polars as pl

from chakravyuh.vaani import gloss, redact

EVIDENCE_SCHEMA: Final[dict[str, pl.DataType]] = {
    "alert_id": pl.String(),
    "kind": pl.String(),
    "statement": pl.String(),
    "weight": pl.Float64(),
    "source_ref": pl.String(),
}

ALERTS_SCHEMA: Final[dict[str, pl.DataType]] = {
    "alert_id": pl.String(),
    "subject_id": pl.String(),
    "rank": pl.Int32(),
    "severity": pl.String(),
    "conf_low": pl.Float64(),
    "conf_high": pl.Float64(),
    "headline": pl.String(),
    "origin_txid": pl.String(),
    "origin_peer_ip": pl.String(),
    "origin_p": pl.Float64(),
    "attribution_ready": pl.Boolean(),
}

SEVERITY: Final[dict[str, str]] = {
    "LIKELY_ILICIT": "high",
    "UNCLEAR": "medium",
    "ABSTAIN": "low",
}


def _anchor(
    subject_id: str,
    addresses: list[str],
    receives: pl.DataFrame,
    origin_top1: pl.DataFrame,
) -> dict[str, object]:
    """The single transaction whose origin estimate anchors this alert.

    Candidates are the subject's RECEIVES edges joined to the ensemble's rank-1 rows; the
    anchor is the highest-probability one, ties broken by margin then txid, so the choice is
    deterministic. All-null when the estimator answered nothing for this subject.
    """
    candidates = (
        receives.filter(pl.col("address").is_in(set(addresses)))
        .select("txid")
        .unique()
        .join(origin_top1, on="txid", how="inner")
    )
    if candidates.is_empty():
        return {
            "origin_txid": None,
            "origin_peer_ip": None,
            "origin_p": None,
            "origin_margin": None,
        }
    best = candidates.sort(["p_origin", "margin", "txid"], descending=[True, True, False]).head(1)
    row = best.iter_rows(named=True).__next__()
    return {
        "origin_txid": row["txid"],
        "origin_peer_ip": row["peer_ip"],
        "origin_p": float(row["p_origin"]),
        "origin_margin": float(row["margin"]),
    }


def alerts_frame(
    scores: pl.DataFrame,
    clusters: pl.DataFrame,
    receives: pl.DataFrame,
    origin_top1: pl.DataFrame,
    glosses: dict[str, str],
) -> pl.DataFrame:
    """The contract section 8 alerts table, one row per scored subject that is not licit.

    Rank is 1..N by risk score, ties broken by subject id, so the ordering is a property of
    the data rather than of a hash seed. Identifiers in the two contract fields are carried
    whole: the contract's evidence packet (section 9) quotes `origin_txid` and
    `origin_peer_ip`, and truncation in a machine field would force S09 to re-derive what
    the pipeline already had. Prose renders truncated copies.
    """
    keep = scores.filter(pl.col("label") != "LIKELY_LICIT")
    addr_of = (
        clusters.select("cluster_id", "addresses")
        .explode("addresses")
        .rename({"cluster_id": "subject_id", "addresses": "address"})
    )
    rows: list[dict[str, object]] = []
    for subject in keep["subject_id"].to_list():
        row = keep.filter(pl.col("subject_id") == subject).iter_rows(named=True).__next__()
        addresses = (
            addr_of.filter(pl.col("subject_id") == subject)["address"].to_list()
            if subject in set(clusters["cluster_id"])
            else [subject.removeprefix("addr:")]
        )
        anchor = _anchor(subject, addresses, receives, origin_top1)
        rows.append(
            {
                "subject_id": subject,
                "risk_score": float(row["risk_score"]),
                "conf_low": float(row["conf_low"]),
                "conf_high": float(row["conf_high"]),
                "label": str(row["label"]),
                "top_features": row["top_features"],
                **anchor,
            }
        )
    internal = pl.DataFrame(rows).sort("risk_score", "subject_id", descending=[True, False])
    ordered = internal.with_row_index("rank", offset=1).with_columns(
        pl.col("rank").cast(pl.Int32()),
        pl.col("label")
        .replace_strict(SEVERITY, default="medium", return_dtype=pl.String())
        .alias("severity"),
    )
    # The headline, one sentence under 100 characters, generated from the top two features
    # rather than written free. Feature names pass the gloss table, never raw columns.
    headlines: list[str] = []
    for row in ordered.iter_rows(named=True):
        parts = [
            _short_gloss(glosses, feature["name"], float(feature["value"]))
            for feature in row["top_features"][:2]
        ]
        label = str(row["label"]).replace("LIKELY_", "").replace("ILICIT", "illicit")
        label = label.replace("_", " ").lower()
        headline = f"{label}: " + "; ".join(parts)
        # Under 100, not at most 100: the contract's words, so 96 plus the ellipsis is the cap.
        headlines.append(headline[:96] + "..." if len(headline) >= 100 else headline)
    return ordered.with_columns(
        pl.Series("headline", headlines, dtype=pl.String()),
        # Section 8's ready flag: true only when a peer, a port and a precise time all exist.
        # Every observed announcement row carries a non-null port and timestamp, and a rank-1
        # estimate exists only for an observed announcement, so an anchor implies all three.
        pl.col("origin_txid").is_not_null().alias("attribution_ready"),
    )


def _short_gloss(glosses: dict[str, str], name: str, value: float) -> str:
    """A compact clause for one feature: gloss plus direction, no number to crowd the line."""
    phrase = gloss.gloss(glosses, name)
    direction = "high" if value >= 0 else "low"
    return f"{direction} {phrase}"


def evidence_rows(
    internal: pl.DataFrame,
    glosses: dict[str, str],
    announcements: pl.DataFrame,
    clusters: pl.DataFrame,
) -> pl.DataFrame:
    """The reasons for, one row per reason per alert, identifiers truncated in the prose."""
    rows: list[dict[str, object]] = []
    for alert in internal.iter_rows(named=True):
        alert_id = alert["alert_id"]
        subject = str(alert["subject_id"])
        # One model_feature row per top SHAP feature, prose from the gloss table.
        for feature in alert["top_features"]:
            name = str(feature["name"])
            value = float(feature["value"])
            phrase = gloss.gloss(glosses, name)
            direction = "raised" if value >= 0 else "lowered"
            emphasis = " substantially" if abs(value) > 0.5 else ""
            rows.append(
                {
                    "alert_id": alert_id,
                    "kind": "model_feature",
                    "statement": f"this wallet's {phrase} {direction} its risk score{emphasis}",
                    "weight": value,
                    "source_ref": f"scores/wallet_scores.parquet#subject_id={subject}",
                }
            )
        # The origin leg, stated with truncated identifiers in the prose.
        if alert["origin_txid"] is not None:
            tx = redact.redact_txid(str(alert["origin_txid"]))
            ip = redact.redact_ip(str(alert["origin_peer_ip"]))
            p = float(alert["origin_p"])
            rows.append(
                {
                    "alert_id": alert_id,
                    "kind": "origin_estimate",
                    "statement": (
                        f"transaction {tx} is estimated to have originated from network "
                        f"address {ip} with probability {p:.3f}"
                    ),
                    "weight": p,
                    "source_ref": (f"signals/origin_estimates.parquet#tx_prefix={tx[:8]}"),
                }
            )
            earliest = (
                announcements.filter(
                    (pl.col("txid") == alert["origin_txid"])
                    & (pl.col("peer_ip") == alert["origin_peer_ip"])
                )
                .sort("seen_us")
                .head(1)
            )
            if earliest.height:
                seen = int(earliest["seen_us"][0])
                observed_row = int(earliest["row_id"][0])
                rows.append(
                    {
                        "alert_id": alert_id,
                        "kind": "network_context",
                        "statement": (
                            f"the network address was first observed announcing that "
                            f"transaction at {_utc(seen)}, observation row {observed_row}"
                        ),
                        "weight": p,
                        "source_ref": (f"normalised/announcements.parquet#row_id={observed_row}"),
                    }
                )
        # The cluster leg: how firmly the addresses are held together.
        confidence = (
            clusters.filter(pl.col("cluster_id") == subject)["min_edge_confidence"]
            if subject in set(clusters["cluster_id"])
            else None
        )
        if confidence is not None and len(confidence):
            conf = float(confidence[0])
            rows.append(
                {
                    "alert_id": alert_id,
                    "kind": "cluster_edge",
                    "statement": (
                        f"the addresses share this wallet because clustering edges hold them "
                        f"together, the weakest at confidence {conf:.2f}"
                    ),
                    "weight": round(conf, 4),
                    "source_ref": f"graph/clusters.parquet#cluster_id={subject}",
                }
            )
        else:
            rows.append(
                {
                    "alert_id": alert_id,
                    "kind": "cluster_edge",
                    "statement": (
                        "the subject is a single address that no clustering heuristic linked "
                        "to anything else"
                    ),
                    "weight": 0.0,
                    "source_ref": f"scores/wallet_scores.parquet#subject_id={subject}",
                }
            )
    return pl.DataFrame(rows, schema=EVIDENCE_SCHEMA)


def _utc(us: int) -> str:
    """UTC string of a microsecond timestamp, for a sentence an analyst reads."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(us / 1_000_000, tz=UTC).strftime("%Y-%m-%d %H:%M:%SZ")


def reason_string(
    alert: dict[str, object],
    evidence: pl.DataFrame,
    counters: pl.DataFrame,
) -> str:
    """Three sentences, maximum, assembled from the rows this alert already carries.

    Derived at read time from `evidence.parquet` and `counter.parquet`, never stored, so
    `alerts.parquet` stays column-exact with the contract. Deterministic: same rows in,
    same string out, in any process. The subject is never interpolated: the string may be
    rendered anywhere, and a subject id can be a bare Bitcoin address.
    """
    features = evidence.filter(
        (pl.col("alert_id") == alert["alert_id"]) & (pl.col("kind") == "model_feature")
    ).sort("weight", descending=True)
    parts: list[str] = []
    if features.height:
        top = features.head(1).iter_rows(named=True).__next__()
        parts.append(f"subject: {top['statement']} more than any other signal")
    if alert["origin_txid"] is not None:
        peer_ip = str(alert["origin_peer_ip"])
        origin_p = float(str(alert["origin_p"]))
        parts.append(
            f"the best attribution points to network address "
            f"{redact.redact_ip(peer_ip)} with probability {origin_p:.3f}"
        )
    else:
        parts.append("no origin attribution is available for this subject")
    decisive = counters.filter((pl.col("alert_id") == alert["alert_id"]) & pl.col("would_clear"))
    if decisive.height:
        parts.append(f"counter-evidence clears this lead: {decisive['statement'][0]}")
    else:
        low = float(str(alert["conf_low"]))
        high = float(str(alert["conf_high"]))
        parts.append(
            f"the calibrated interval is [{low:.2f}, {high:.2f}]; read it with the "
            f"counter-evidence before acting"
        )
    return ". ".join(parts[:3]) + "."
