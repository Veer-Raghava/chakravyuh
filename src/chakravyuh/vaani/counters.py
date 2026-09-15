"""The reasons against each alert, in the same pass that builds the alert.

Counter-evidence generated here is never optional enrichment: the caller builds one row
list per alert in the same loop that writes the alert row, and `build` raises if any alert
ends with zero counters, which is the contract's "the pipeline fails if any alert has none".

The kinds are contract section 8's closed vocabulary. Two of them — `entity_type_conflict`
and `pool_payout_pattern` — fire from `signals/entity_types.parquet`, which is zero-row on
every run written so far (S06 rider); those paths stay dormant on real data and are
exercised by the named mining-pool test. A benign explanation for a typology hit rides
`entity_type_conflict`: it is the same claim, that something innocent about this subject
explains the pattern the model saw.

`would_clear` is reserved for the one decisive case: an entity whose own type explains the
behaviour — a mining pool with coinbase origination and a regular payout cadence above all.
A tool that marks which single doubt closes the lead is one an investigator can use.
"""

from __future__ import annotations

from typing import Final

import polars as pl

COUNTER_SCHEMA: Final[dict[str, pl.DataType]] = {
    "alert_id": pl.String(),
    "kind": pl.String(),
    "statement": pl.String(),
    "strength": pl.Float64(),
    "would_clear": pl.Boolean(),
}

# A cluster whose weakest holding link sits below this is a guess, not a finding: JAAL cuts
# clusters at 0.2 and the multi-input heuristic's honest confidence lands near 0.36, so a
# link that barely clears the threshold holds the cluster together on a coin flip.
CLUSTER_CONFIDENCE_FLOOR: Final[float] = 0.5

# The estimator already refuses transactions whose top-two margin is under its own floor, so
# any rank-1 row cleared that bar. Counter-evidence holds the analyst to a stricter one: a
# lead whose winning margin is under twice the estimator's floor is not something to act on.
LOW_MARGIN_FACTOR: Final[float] = 2.0

# One honest benign explanation per typology in contract section 6's vocabulary. These are
# reasons a pattern can exist without laundering, not verdicts.
BENIGN_EXPLANATIONS: Final[dict[str, str]] = {
    "peel_chain": "long chains also arise from consolidation and exchange batching",
    "structuring": "many small payments are ordinary retail or payroll behaviour",
    "fan_out": "a wide fan also matches marketplace payouts and wage batches",
    "pass_through": "processors and custodians pass value through as their job",
    "coinjoin_like": "equal-value outputs also come from privacy wallets used for anonymity alone",
    "rapid_hop": "automated services relay funds quickly without any attempt to hide",
}


def _entity_counters(
    subject_id: str,
    alert_id: str,
    types_row: dict[str, object] | None,
    has_typology_hit: bool,
) -> list[dict[str, object]]:
    """Entity-type counters for one alert, including the decisive mining-pool case."""
    del subject_id
    if types_row is None:
        return []
    kind = str(types_row["predicted_type"])
    raw_basis = types_row["basis"]
    if isinstance(raw_basis, list | tuple | set):
        basis: set[str] = {str(one) for one in raw_basis}
    else:
        basis = set()
    confidence = float(str(types_row["confidence"]))
    out: list[dict[str, object]] = []
    if kind == "mining_pool" and {"coinbase_origination", "payout_cadence"} <= basis:
        out.append(
            {
                "alert_id": alert_id,
                "kind": "pool_payout_pattern",
                "statement": (
                    "this cluster originated coinbase transactions and pays out on a regular "
                    "cadence, which is what a mining pool does"
                ),
                "strength": confidence,
                "would_clear": not has_typology_hit,
            }
        )
        return out
    if bool(types_row["exempt_from_scoring"]) and not has_typology_hit:
        out.append(
            {
                "alert_id": alert_id,
                "kind": "entity_type_conflict",
                "statement": (
                    f"the subject is recognised as a {kind.replace('_', ' ')}, whose ordinary "
                    f"activity explains volume like this"
                ),
                "strength": confidence,
                "would_clear": True,
            }
        )
    elif kind:
        out.append(
            {
                "alert_id": alert_id,
                "kind": "entity_type_conflict",
                "statement": (
                    f"the subject is recognised as a {kind.replace('_', ' ')}, which may explain "
                    f"the pattern without any illicit intent"
                ),
                "strength": confidence * 0.5,
                "would_clear": False,
            }
        )
    return out


def build(
    alerts: pl.DataFrame,
    origin_top1: pl.DataFrame,
    entity_types: pl.DataFrame,
    typology_hits: pl.DataFrame,
    clusters: pl.DataFrame,
    peer_subjects: pl.DataFrame,
    abstain_frac: pl.DataFrame,
    margin_floor: float,
    origin_mass: pl.DataFrame,
) -> pl.DataFrame:
    """One or more counter rows per alert, every kind decided from observable data alone.

    `alerts` is the internal frame with `origin_margin` and `subject_id` still on it; the
    contract columns are selected by the caller afterwards. `origin_top1` holds the ensemble's
    rank-1 rows (`txid`, `peer_ip`, `margin`); `abstain_frac` holds one row per subject with
    the share of its sent transactions the estimator refused. `peer_subjects` counts the
    distinct subjects sharing each anchor peer. `origin_mass` holds one row per txid with the
    sum of ensemble `p_origin` over its candidates: the un-renormalised shortfall is the
    probability the true originator was never observed, and it is the counter-evidence every
    anchored alert carries.
    """
    rows: list[dict[str, object]] = []
    types_by_id = (
        {str(r["subject_id"]): r for r in entity_types.iter_rows(named=True)}
        if entity_types.height
        else {}
    )
    hit_ids = set(typology_hits["subject_id"].to_list()) if typology_hits.height else set()
    conf_by_id = dict(zip(clusters["cluster_id"], clusters["min_edge_confidence"], strict=True))
    abstain_by_id = dict(zip(abstain_frac["subject_id"], abstain_frac["frac"], strict=True))
    peers_by_subject = dict(zip(alerts["subject_id"], alerts["origin_peer_ip"], strict=True))
    subjects_by_peer: dict[str, int] = {}
    if peer_subjects.height:
        subjects_by_peer = dict(
            zip(peer_subjects["peer_ip"], peer_subjects["n_subjects"], strict=True)
        )
    mass_by_tx = (
        dict(zip(origin_mass["txid"], origin_mass["mass"], strict=True))
        if origin_mass.height
        else {}
    )

    for alert in alerts.iter_rows(named=True):
        alert_id = str(alert["alert_id"])
        subject = str(alert["subject_id"])
        anchor_peer = peers_by_subject[subject]

        # Origin leg. No rank-1 row anywhere on the subject's sends, or the estimator refused
        # on a share of them, is the "we simply did not observe it" state made explicit.
        if alert["origin_txid"] is None:
            rows.append(
                {
                    "alert_id": alert_id,
                    "kind": "insufficient_observation",
                    "statement": (
                        "no origin estimate is available for this subject's transactions, so "
                        "the network side of this alert rests on nothing observable"
                    ),
                    "strength": 1.0,
                    "would_clear": False,
                }
            )
        else:
            if subject in abstain_by_id and float(str(abstain_by_id[subject])) > 0.0:
                share = float(str(abstain_by_id[subject]))
                rows.append(
                    {
                        "alert_id": alert_id,
                        "kind": "insufficient_observation",
                        "statement": (
                            f"the origin estimator declined to answer on "
                            f"{round(share * 100)}% of this subject's sends, "
                            f"usually a Tor exit or too few announcing peers"
                        ),
                        "strength": round(share, 4),
                        "would_clear": False,
                    }
                )
            # The probabilities are deliberately never renormalised to one, so their shortfall
            # is a measurable doubt: the true originator may not be among the peers we saw.
            mass = float(str(mass_by_tx.get(str(alert["origin_txid"]), 0.0)))
            if mass < 1.0:
                rows.append(
                    {
                        "alert_id": alert_id,
                        "kind": "insufficient_observation",
                        "statement": (
                            f"all observed announcing peers together account for only "
                            f"{round(mass * 100)}% of the estimated origin probability, so the "
                            f"true originator may not have been observed at all"
                        ),
                        "strength": round(1.0 - mass, 4),
                        "would_clear": False,
                    }
                )
        if alert["origin_margin"] is not None and float(str(alert["origin_margin"])) < (
            LOW_MARGIN_FACTOR * margin_floor
        ):
            rows.append(
                {
                    "alert_id": alert_id,
                    "kind": "low_origin_margin",
                    "statement": (
                        "the leading origin candidate is only narrowly ahead of the runner-up, "
                        "which is too thin a margin to act on"
                    ),
                    "strength": max(
                        0.0,
                        round(
                            1.0
                            - float(alert["origin_margin"]) / (LOW_MARGIN_FACTOR * margin_floor),
                            4,
                        ),
                    ),
                    "would_clear": False,
                }
            )

        # Cluster leg. A weak holding link means the subject itself may be a stitching error.
        confidence = conf_by_id.get(subject)
        if confidence is not None and float(str(confidence)) < CLUSTER_CONFIDENCE_FLOOR:
            conf = float(str(confidence))
            rows.append(
                {
                    "alert_id": alert_id,
                    "kind": "weak_cluster_link",
                    "statement": (
                        f"the weakest link holding this cluster together has confidence "
                        f"{conf:.2f}, so some of these addresses may not share an owner"
                    ),
                    "strength": round(1.0 - conf, 4),
                    "would_clear": False,
                }
            )

        # Shared infrastructure leg. One peer announcing for several subjects is a relay, a
        # CGNAT, or a busy host, and only one of those is the originator.
        if anchor_peer is not None:
            shared = subjects_by_peer.get(str(anchor_peer), 1)
            if shared > 1:
                rows.append(
                    {
                        "alert_id": alert_id,
                        "kind": "shared_ip",
                        "statement": (
                            f"the same network address announces traffic for {shared} distinct "
                            f"subjects, so it may be a shared relay rather than an owner"
                        ),
                        "strength": round(1.0 - 1.0 / shared, 4),
                        "would_clear": False,
                    }
                )

        # Entity and typology leg.
        rows += _entity_counters(subject, alert_id, types_by_id.get(subject), subject in hit_ids)
        for hit in typology_hits.filter(pl.col("subject_id") == subject).iter_rows(named=True):
            benign = BENIGN_EXPLANATIONS.get(str(hit["typology"]))
            if benign:
                rows.append(
                    {
                        "alert_id": alert_id,
                        "kind": "entity_type_conflict",
                        "statement": (
                            f"the {str(hit['typology']).replace('_', ' ')} pattern this alert "
                            f"rests on has a benign reading: {benign}"
                        ),
                        "strength": round(float(hit["strength"]) * 0.5, 4),
                        "would_clear": False,
                    }
                )

    frame = (
        pl.DataFrame(rows, schema=COUNTER_SCHEMA) if rows else pl.DataFrame(schema=COUNTER_SCHEMA)
    )
    counts = frame.group_by("alert_id").len()
    empty = alerts.filter(~pl.col("alert_id").is_in(counts["alert_id"]))
    if empty.height:
        # Contract section 8: the pipeline fails rather than publishing an alert with no
        # counter-evidence. Names ids, never rows.
        raise AssertionError(
            f"{empty.height} alerts carry no counter-evidence, starting with "
            f"{empty['alert_id'][0]}; counter-evidence is mandatory for every alert"
        )
    return frame.sort("alert_id", "kind")
