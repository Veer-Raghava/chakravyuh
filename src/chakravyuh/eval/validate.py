"""Does this run measure what it claims to measure?

This module lives in `chakravyuh.eval` rather than in `chakravyuh.mayajaal` for one reason: it
opens `ground_truth/<run>/`, and CLAUDE.md permits exactly one package to do that. The generator
cannot check its own leakage, because checking leakage means holding the answer key next to the
capture and asking how much of the key the capture gives away.

Three groups of checks, and a run has to pass all three:

  invariants    Facts that are either true or the run is corrupt: a txid is sixty-four lowercase
                hex characters, an address list is as long as its amount list, the rows sharing a
                txid agree on that transaction's chain columns, inputs cover outputs, every
                announced txid exists on the chain and was announced before it was confirmed, no
                coinbase is announced at all, every announced transaction has exactly one true
                originator, no address has two owners, each observer answers to one address, and
                `counts.in == counts.out + counts.dropped` in every manifest.
  distributions Shape checks against `run_config.json`'s `validation` block. A generator that
                emits the right columns full of the wrong numbers passes every invariant above
                and is still useless: a uniform value distribution, a fixed relay delay or a
                metronomic block interval each erase a signal a later stage is supposed to find.
  leakage       How much of the answer key the capture leaks. Both directions are failures. Too
                much and the benchmark is trivial: if `first announcement seen` names the true
                originator nine times in ten, S03 has nothing to estimate. Too little and the
                problem is unwinnable, which is the same as unmeasurable.

Every number in the report is a count, a ratio or a row index. Nothing here writes an IP, an
address or a txid into `report.json`, `report.md` or a log line: the report is the one artifact of
this stage that a human reads, and CLAUDE.md's rule against emitting a complete identifier applies
hardest to the file most likely to be pasted into a chat window. Row indices are safe and are what
makes a failure findable with `scripts/peek.py`.

`report.md` deliberately omits the run id, so two runs of one seed produce byte-identical reports
and `make verify-determinism` can compare them directly.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import polars as pl

from chakravyuh.mayajaal import config, export, writers

LOG = logging.getLogger("validate")

GENERATED_ROOT = writers.REPO_ROOT / "data" / "generated"
CONFIG_NAME = "config.effective.json"
# Named here rather than imported, the same way `scripts/compare_runs.py` names it: this module
# may read a manifest and nothing else about how the writer works.
MANIFEST = "_meta.json"

_TXID = re.compile(r"^[0-9a-f]{64}$")
# Section 1's timestamp, in the one form the exporter writes: six fractional digits, explicit
# offset. The loose forms section 1 also permits are KAVACH's problem, not this run's.
_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$")
_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%S%.f%:z"

# A column name that exists only in the answer key. If one of these ever appears in a header
# under `data/generated/`, a label has crossed the line, and no distribution check matters after
# that. `tests/test_network.py` greps the same list.
#
# Every column of all four quarantined files is named, except the two that are public chain facts
# and legitimately appear in the capture: `txid` and `block_height`. A partial list is worse than
# no list, because it reports "none" while a label walks past it.
TRUTH_COLUMNS: tuple[str, ...] = (
    "true_origin_ip",
    "true_origin_entity_id",
    "broadcast_us",
    "used_tor",
    "used_vpn",
    "observed_by_n",
    "entity_id",
    "entity_type",
    "input_entity_ids",
    "is_illicit",
    "typologies",
    "addresses",
    "ips",
    "behind_cgnat",
    "change_index",
    "heuristic_violation",
    "campaign_id",
    "typology",
    "entity_ids",
    "txids",
    "start_us",
    "end_us",
    "total_sats",
)

_LIST_COLUMNS = (
    "input_addresses",
    "input_amounts",
    "output_addresses",
    "output_amounts",
    "script_types",
)
_INT_COLUMNS = ("src_port", "dst_port", "asn", "fee_sats", "vsize", "block_height")


@dataclass(frozen=True, slots=True)
class Check:
    """One line of the report: what was measured, what it had to be, and whether it was.

    `value` and `bound` are formatted for a human and are never an identifier. `note` is where a
    failure says which row to look at, because a report that says only "false" sends the reader
    back to a million rows with no starting point.
    """

    group: str
    name: str
    ok: bool
    value: str
    bound: str
    note: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "value": self.value,
            "bound": self.bound,
            "note": self.note,
        }


def _num(value: float) -> str:
    """Format a measurement. Six digits, because two runs of one seed must agree exactly and a
    float rendered shorter than it is hides a real difference between them."""
    return f"{value:.6f}"


def _capture(observable: Path) -> pl.DataFrame:
    """Every CSV shard, read as text and concatenated in shard order.

    Read with `infer_schema_length=0` so every column arrives as a string and this module, not
    polars, decides what a field means. That matters for the invariants: a column parsed to
    integers before it is checked has already thrown away the malformed value the check exists to
    catch, and an empty field has to stay distinguishable from a zero.

    ponytail: the whole capture is read into memory as one frame, the same ceiling the generator
    already accepts for `network.Capture`. The upgrade is `pl.scan_csv` and per-shard reductions,
    which costs the row-index column that makes a failure locatable.
    """
    shards = sorted((observable / export.CSV_DIR).glob("part-*.csv"))
    if not shards:
        raise SystemExit(f"validate: no capture shards under {observable / export.CSV_DIR}")
    frame = pl.concat([pl.read_csv(shard, infer_schema_length=0) for shard in shards])
    return frame.with_row_index("row").with_columns(
        *(pl.col(name).cast(pl.Int64, strict=False) for name in _INT_COLUMNS),
        *(
            pl.col(name).str.split("|").list.len().fill_null(0).alias(f"n_{name}")
            for name in _LIST_COLUMNS
        ),
        *(
            pl.col(name)
            .str.split("|")
            .list.eval(pl.element().cast(pl.Int64, strict=False))
            .list.sum()
            .fill_null(0)
            .alias(f"sum_{name}")
            for name in ("input_amounts", "output_amounts")
        ),
        pl.col("timestamp")
        .str.to_datetime(_STAMP_FORMAT, time_unit="us", strict=False)
        .dt.timestamp("us")
        .alias("time_us"),
    )


def _delays(cap: pl.DataFrame, origins: pl.DataFrame) -> pl.DataFrame:
    """The capture with each row's delay since its transaction was broadcast, in microseconds.

    This is the one place the answer key is joined onto the capture, and it is why this module is
    quarantined: `broadcast_us` is the moment the originating node first sent the transaction,
    which no observer can see. Two checks need it, the relay-delay dispersion and the ordering
    invariant that no announcement predates the broadcast it announces, so it is computed once.
    """
    return cap.join(origins.select("txid", "broadcast_us"), on="txid", how="left").with_columns(
        (pl.col("time_us") - pl.col("broadcast_us")).alias("delay_us")
    )


def _rows(frame: pl.DataFrame, predicate: pl.Expr) -> tuple[int, str]:
    """Count the rows that break a rule and locate the first, so a failure is actionable.

    A row index is not an identifier, so naming one is safe and is the only pointer the report can
    legally give: `python scripts/peek.py` on the shard that holds it shows the row redacted.
    """
    hits = frame.filter(predicate)
    if hits.height == 0:
        return 0, ""
    return hits.height, f"first at capture row {hits['row'][0]}"


def _invariants(
    cap: pl.DataFrame,
    txs: pl.DataFrame,
    origins: pl.DataFrame,
    delays: pl.DataFrame,
    entities: pl.DataFrame,
    endowment: pl.DataFrame,
) -> list[Check]:
    """The checks whose failure means the run is broken rather than badly tuned.

    Six of these are section 1's own load invariants, restated here because KAVACH will apply them
    at S03 and a generated capture that cannot pass its own intake is not worth shipping. The rest
    are the joins that only the answer key makes possible.
    """
    out: list[Check] = []

    def rule(name: str, predicate: pl.Expr, frame: pl.DataFrame | None = None) -> None:
        bad, note = _rows(cap if frame is None else frame, predicate)
        out.append(Check("invariants", name, bad == 0, f"{bad} rows", "0 rows", note))

    def count(name: str, bad: int, unit: str, note: str = "") -> None:
        out.append(Check("invariants", name, bad == 0, f"{bad} {unit}", f"0 {unit}", note))

    rule("txid is 64 lowercase hex", ~pl.col("txid").str.contains(_TXID.pattern))
    rule(
        "timestamp is ISO 8601 with six fractional digits and an explicit offset",
        ~pl.col("timestamp").str.contains(_STAMP.pattern) | pl.col("time_us").is_null(),
    )
    rule(
        "input addresses and input amounts are the same length",
        pl.col("n_input_addresses") != pl.col("n_input_amounts"),
    )
    rule(
        "output addresses and output amounts are the same length",
        pl.col("n_output_addresses") != pl.col("n_output_amounts"),
    )
    rule(
        "script types name every output",
        pl.col("n_script_types") != pl.col("n_output_addresses"),
    )
    rule("every announced transaction has an output", pl.col("n_output_addresses") < 1)
    rule(
        "inputs cover outputs on a payment",
        (pl.col("n_input_addresses") > 0)
        & (pl.col("sum_input_amounts") < pl.col("sum_output_amounts")),
    )
    rule(
        "vsize is positive and fee is not negative",
        (pl.col("vsize") <= 0) | (pl.col("fee_sats") < 0),
    )
    rule(
        "ports are inside the 16-bit range",
        ~pl.col("src_port").is_between(1, 65535) | ~pl.col("dst_port").is_between(1, 65535),
    )
    rule("msg_type is inv or tx", ~pl.col("msg_type").is_in(["inv", "tx"]))
    # Ascending time is what makes sharding on the row index a sharding on time, which every
    # later stage assumes when it reads one shard and calls the window it covers an interval.
    rule("the capture never goes backwards in time", pl.col("time_us").diff() < 0)

    # One transaction announced by many peers means the chain columns repeat, and section 1 asks
    # that the repeats agree. They cannot disagree by construction, since the exporter joins them
    # in from one transaction, so this check is really guarding against a future exporter that
    # rebuilds them per row.
    repeated = (
        "input_addresses",
        "input_amounts",
        "output_addresses",
        "output_amounts",
        "script_types",
        "fee_sats",
        "vsize",
        "block_height",
    )
    disagreeing = (
        cap.group_by("txid")
        .agg(*(pl.col(name).n_unique().alias(name) for name in repeated))
        .filter(pl.any_horizontal(*(pl.col(name) > 1 for name in repeated)))
        .height
    )
    count("rows sharing a txid agree on the chain columns", disagreeing, "txids")
    count(
        "every announced txid exists on the chain",
        cap.join(txs.select("txid"), on="txid", how="anti")["txid"].n_unique(),
        "txids",
    )

    # Two rules about what a node may announce, both answered by the transaction's own row.
    # `is_coinbase` and `block_time_us` are public chain facts, so this join needs no answer key.
    chained = cap.join(txs.select("txid", "is_coinbase", "block_time_us"), on="txid", how="left")
    rule(
        "no coinbase transaction is announced",
        pl.col("is_coinbase").fill_null(False),
        chained,
    )
    # A node that already holds the block relays the block, not the loose transaction inside it.
    # An announcement at or after the confirming block's timestamp is therefore an event no
    # observer could have recorded, and it would hand S03 arrival times that cannot occur.
    rule(
        "no announcement lands at or after its confirming block",
        pl.col("time_us") >= pl.col("block_time_us"),
        chained,
    )

    spends = txs.filter(~pl.col("is_coinbase"))
    count(
        "exactly one true originator per announced txid",
        spends.join(origins, on="txid", how="anti").height
        + origins.join(spends, on="txid", how="anti").height
        + (origins.height - origins["txid"].n_unique())
        # The row counts, not only the sets. The txid column of origins.parquet is built by
        # filtering `run.txs` while every other column is built by walking the network layer's
        # own origin list, so the two are aligned by position and nothing in the writer proves
        # it. A duplicate txid on the chain side slips past all three set terms above and would
        # shift every column of origins.parquet by one row against its own txid.
        + abs(origins.height - spends.height),
        "txids",
    )
    # Two observers sharing one dst_ip is not a corrupt row, which is why nothing above catches
    # it: every field is well formed. It is worse than that. Any group-by on dst_ip silently
    # merges the two vantage points into one, and the merge is invisible in the output.
    pairs = cap.select("observer_id", "dst_ip").unique().height
    count(
        "observer id and dst_ip are one to one",
        (pairs - cap["observer_id"].n_unique()) + (pairs - cap["dst_ip"].n_unique()),
        "surplus pairings",
    )
    # Address ownership, at zero tolerance, because both of these break the S04 clustering answer
    # key rather than any single row: an address owned twice merges two entities, and a coinbase
    # paying into the endowment makes a pool and a wallet look like one cluster.
    owners = (
        entities.select("entity_id", "addresses")
        .explode("addresses")
        .group_by("addresses")
        .agg(pl.col("entity_id").n_unique().alias("owners"))
    )
    count(
        "no address is owned by two entities",
        owners.filter(pl.col("owners") > 1).height,
        "addresses",
    )
    count(
        "no coinbase output address is also an endowment address",
        txs.filter(pl.col("is_coinbase"))
        .select(pl.col("output_addresses").explode().alias("address"))
        .join(endowment.select("address"), on="address", how="semi")["address"]
        .n_unique(),
        "addresses",
    )
    seen = cap.group_by("txid").agg(pl.col("observer_id").n_unique().alias("seen"))
    count(
        "observed_by_n equals the observers that recorded the transaction",
        origins.join(seen, on="txid", how="left")
        .with_columns(pl.col("seen").fill_null(0))
        .filter(pl.col("observed_by_n") != pl.col("seen"))
        .height,
        "txids",
    )
    # An announcement that predates the broadcast it announces is a clock the propagation model
    # built backwards, and it would hand S03 a negative feature it could learn from.
    rule("no announcement predates its broadcast", pl.col("delay_us") < 0, delays)
    return out


def _manifests(observable: Path) -> list[Check]:
    """Section 10's arithmetic, once per output directory.

    `counts.in == counts.out + counts.dropped` is the whole point: a stage that quietly loses rows
    is indistinguishable from one that had fewer rows to begin with unless the shortfall is
    declared. The XML sample declares its own, which is why it passes while carrying 500 rows of a
    million-row capture.
    """
    out: list[Check] = []
    for path in sorted(observable.rglob(MANIFEST)):
        where = path.parent.name
        payload = json.loads(path.read_text(encoding="utf-8"))
        counts = payload.get("counts", {})
        got, made, lost = counts.get("in"), counts.get("out"), counts.get("dropped")
        ok = isinstance(got, int) and isinstance(made, int) and isinstance(lost, int)
        out.append(
            Check(
                "manifests",
                f"{where}: counts.in == counts.out + counts.dropped",
                ok and got == made + lost,
                f"{got} == {made} + {lost}" if ok else "missing counts",
                "equal",
            )
        )
        files = payload.get("outputs", [])
        out.append(
            Check("manifests", f"{where}: names its outputs", bool(files), f"{len(files)}", ">= 1")
        )
    return out


def _xml_columns(path: Path) -> Sequence[str]:
    """The child tags of the sample's first row. A column is an element name in this encoding, so
    checking the tags is checking the header."""
    tree = ElementTree.parse(path)
    first = tree.getroot().find("row")
    return () if first is None else [child.tag for child in first]


def _headers(observable: Path) -> list[Check]:
    """No ground-truth column name anywhere under `data/generated/`.

    Names, not values: a leaked label arrives as a column, and a column arrives with a name. The
    capture is checked in all three encodings because they are three separate writers, and the one
    that regresses will be the one nothing looked at. `tests/test_network.py` asserts the same
    thing on a fresh run; this repeats it here so `make validate-data` on an old run still fails.
    """
    found: dict[str, None] = {}
    checked = 0
    for path in sorted(observable.rglob("*")):
        names: Sequence[str] = ()
        if path.suffix == ".csv":
            with path.open(encoding="utf-8") as handle:
                names = (handle.readline().strip() or "").split(",")
        elif path.suffix == ".jsonl":
            with path.open(encoding="utf-8") as handle:
                first = handle.readline()
            names = list(json.loads(first)) if first.strip() else ()
        elif path.suffix == ".parquet":
            names = pl.scan_parquet(path).collect_schema().names()
        elif path.suffix == ".xml":
            names = _xml_columns(path)
        else:
            continue
        checked += 1
        for name in set(names) & set(TRUTH_COLUMNS):
            found[name] = None
    return [
        Check(
            "quarantine",
            "no ground-truth column name appears in an observable header",
            not found,
            ", ".join(found) if found else "none",
            "none",
            f"{checked} files checked",
        )
    ]


def _cv(values: pl.Series) -> float:
    """Coefficient of variation, standard deviation over mean.

    Scale free on purpose: the thresholds in `run_config.json` have to hold whether a delay is
    measured in seconds or microseconds, and a run at a different mean relay delay should not move
    the bar. A zero or absent mean means there is nothing to disperse, and `inf` fails every
    check it appears in rather than passing quietly.
    """
    mean, deviation = values.mean(), values.std()
    if not isinstance(mean, float) or not isinstance(deviation, float) or mean <= 0.0:
        return math.inf
    return deviation / mean


def _band(
    group: str, name: str, value: float, low: float | None, high: float | None, note: str = ""
) -> Check:
    ok = (low is None or value >= low) and (high is None or value <= high)
    if low is not None and high is not None:
        bound = f"{_num(low)} to {_num(high)}"
    elif low is not None:
        bound = f">= {_num(low)}"
    else:
        bound = f"<= {_num(high)}" if high is not None else "any"
    return Check(group, name, ok, _num(value), bound, note)


def _distributions(
    cfg: config.Config,
    cap: pl.DataFrame,
    txs: pl.DataFrame,
    blocks: pl.DataFrame,
    delays: pl.DataFrame,
) -> list[Check]:
    """Shape, not correctness. Every bound comes from `run_config.json`'s `validation` block, so
    retuning the generator moves the bar in one file rather than in this module."""
    limits = cfg.validation
    out: list[Check] = []

    values = txs.filter(~pl.col("is_coinbase"))["output_amounts"].explode()
    p50, p99, p999 = (values.quantile(q) or 0.0 for q in (0.5, 0.99, 0.999))
    ratio99 = p99 / p50 if p50 else 0.0
    ratio999 = p999 / p50 if p50 else 0.0
    out.append(
        _band("distributions", "value p99 / p50", ratio99, limits.value_p99_over_p50_min, None)
    )
    out.append(
        _band("distributions", "value p999 / p50", ratio999, limits.value_p999_over_p50_min, None)
    )

    spends = txs.filter(~pl.col("is_coinbase"))
    measured = spends.filter(pl.col("input_txids").list.len() > 1).height / max(spends.height, 1)
    target = cfg.chain.multi_input_rate
    slack = target * limits.multi_input_rate_tolerance
    out.append(_band("distributions", "multi-input rate", measured, target - slack, target + slack))

    # Against the transactions that are actually gossiped. Coinbase is never announced, so
    # counting it in the denominator would report a per-transaction rate for a population that
    # includes transactions no peer can ever announce.
    per_tx = cap.height / max(spends.height, 1)
    wanted = float(cfg.mean_announcements_per_tx)
    room = wanted * limits.announcements_per_tx_tolerance
    out.append(
        _band(
            "distributions", "announcements per transaction", per_tx, wanted - room, wanted + room
        )
    )

    # Dispersion, not the mean. A constant relay delay would still produce the right average and
    # would hand S03 a network where the first announcement is always the closest peer.
    out.append(
        _band(
            "distributions",
            "relay delay coefficient of variation",
            _cv(delays["delay_us"].cast(pl.Float64)),
            limits.delay_cv_min,
            None,
        )
    )
    intervals = blocks["time_us"].diff().drop_nulls().cast(pl.Float64)
    out.append(
        _band(
            "distributions",
            "block interval coefficient of variation",
            _cv(intervals),
            limits.block_interval_cv_min,
            limits.block_interval_cv_max,
        )
    )
    return out


# Everything a rule or a model is allowed to look at, and nothing that is not in the capture.
FEATURES: tuple[str, ...] = (
    "arrival",
    "since_first",
    "n_rows",
    "is_inv",
    "src_port",
    "asn_known",
)


def _labelled(cap: pl.DataFrame, origins: pl.DataFrame) -> pl.DataFrame:
    """The capture with the answer key attached and the features a trivial attacker would use.

    `is_origin` is true for every row whose announcing peer is the one that actually broadcast the
    transaction, so several rows of one transaction can carry it: the originating node announces to
    each of its peers, and more than one of them may be an observer. That is the honest labelling.
    Marking only the earliest such row would flatter any rule that guesses early.
    """
    return (
        cap.join(origins.select("txid", "true_origin_ip"), on="txid", how="left")
        .with_columns((pl.col("src_ip") == pl.col("true_origin_ip")).alias("is_origin"))
        .with_columns(
            (pl.col("row").rank("ordinal").over("txid") - 1).alias("arrival"),
            (pl.col("time_us") - pl.col("time_us").min().over("txid")).alias("since_first"),
            pl.len().over("txid").alias("n_rows"),
            (pl.col("msg_type") == "inv").alias("is_inv"),
            pl.col("asn").is_not_null().alias("asn_known"),
        )
    )


def _accuracy(
    frame: pl.DataFrame, by: Sequence[str], descending: Sequence[bool], total: int
) -> float:
    """Accuracy of a rule that sorts the rows of a transaction and guesses the first one.

    `total` is every transaction that was broadcast, not every transaction some observer recorded.
    The two differ: a transaction can reach no observer at all, and dividing by the observed count
    would score a rule only on the transactions it was given a chance at. That is the denominator
    S03 has to report on, so it is the denominator here.

    Ties break on `row`, the position in the capture, which every caller appends: a rule whose
    ordering is ambiguous must still be deterministic, or two runs of one seed disagree here.
    """
    chosen = frame.sort(by, descending=list(descending)).unique(
        subset="txid", keep="first", maintain_order=True
    )
    return float(chosen["is_origin"].sum()) / total if total else 0.0


def _tree(frame: pl.DataFrame, total: int) -> float:
    """How well a depth-two decision tree over the observable columns picks the originating row.

    Fitted and scored on the same rows on purpose. This is not a model anyone would ship: it is an
    upper bound on what a shallow, purely local rule can extract, and an upper bound is exactly
    what a leakage gate wants. Depth two because the question is whether the answer is sitting in
    one or two thresholds, not whether a large model can eventually find it.

    `scikit-learn` arrives with `mapie`, pinned in `uv.lock`, so importing it adds no dependency.
    Imported here rather than at module scope so the invariants still run if it ever goes missing.
    """
    from sklearn.tree import DecisionTreeClassifier

    if frame["is_origin"].n_unique() < 2:
        return 0.0
    model = DecisionTreeClassifier(max_depth=2, random_state=0)
    features = frame.select(FEATURES).to_numpy().astype("float64")
    model.fit(features, frame["is_origin"].to_numpy())
    scored = frame.with_columns(
        pl.Series("score", model.predict_proba(features)[:, 1], dtype=pl.Float64)
    )
    return _accuracy(scored, ["score", "row"], [True, False], total)


def _leakage(cfg: config.Config, frame: pl.DataFrame, broadcast: int) -> list[Check]:
    """The checks that decide whether the benchmark is worth running at all.

    Every score here is a share of `broadcast`, every transaction that was put on the wire, which
    is the same denominator S03 will report its accuracy on. That denominator has a ceiling below
    1: a transaction's originator is only in the candidate set when it announced to an observer and
    was the first to reach it, and a transaction can reach no observer at all. For the rest no rule
    and no model can ever be right. The ceiling is measured and reported first, because a leakage
    number read without it looks like far more headroom than the capture has.

    The first-seen score is banded rather than capped. Above the ceiling the answer is in the
    capture and S03 has nothing to estimate; below the floor the network has hidden the originator
    so thoroughly that no method could ever score, which is not a hard problem but an unmeasurable
    one. The remaining rules are capped: each is something an investigator could try in one line of
    SQL, and any of them working is the benchmark answering itself.
    """
    limits = cfg.validation
    found = frame.group_by("txid").agg(pl.col("is_origin").any().alias("found"))["found"].sum()
    recoverable = float(found) / broadcast if broadcast else 0.0
    first_seen = _accuracy(frame, ["time_us", "row"], [False, False], broadcast)
    out = [
        _band(
            "leakage",
            "the originator is in the capture at all",
            recoverable,
            limits.origin_recoverable_min,
            None,
            "the ceiling on every score below, and on S03's accuracy",
        ),
        _band(
            "leakage",
            "first announcement seen names the originator",
            first_seen,
            limits.first_seen_leakage_min,
            limits.first_seen_leakage_max,
            f"{_num(first_seen / recoverable if recoverable else 0.0)} of the reachable share",
        ),
    ]

    peers = frame.group_by("txid", "src_ip").agg(
        pl.len().alias("announcements"),
        pl.col("row").min().alias("row"),
        pl.col("is_origin").first(),
    )
    busiest = frame.group_by("src_ip").agg(pl.len().alias("announcements"), pl.col("row").min())
    top = busiest.sort(["announcements", "row"], descending=[True, False])["src_ip"][0]
    everywhere = (
        frame.filter(pl.col("true_origin_ip") == top)["txid"].n_unique() / broadcast
        if broadcast
        else 0.0
    )

    # The only rule here that is not a one-column sort: link transactions by their first input
    # address, then name the peer that shows up across most of that payer's transactions. Address
    # reuse is the strongest observable signal in the capture, and this is the shape S03 is
    # supposed to discover, so it is the rule most worth knowing the score of before S03 exists.
    payer = frame.with_columns(pl.col("input_addresses").str.split("|").list.first().alias("payer"))
    shared = (
        payer.unique(subset=["txid", "payer", "src_ip"])
        .group_by("payer", "src_ip")
        .agg(pl.col("txid").n_unique().alias("shared"))
    )
    linked = payer.join(shared, on=["payer", "src_ip"], how="left")

    trivial = {
        "the peer announcing it most often": _accuracy(
            peers, ["announcements", "row"], [True, False], broadcast
        ),
        "the first full tx message rather than an inv": _accuracy(
            frame, ["is_inv", "time_us", "row"], [False, False, False], broadcast
        ),
        "the lowest source port": _accuracy(frame, ["src_port", "row"], [False, False], broadcast),
        "the busiest peer in the whole capture": everywhere,
        "the peer seen across most of that payer's transactions": _accuracy(
            linked, ["shared", "row"], [True, False], broadcast
        ),
    }
    out += [
        _band("leakage", f"trivial rule: {name}", value, None, limits.trivial_rule_max)
        for name, value in trivial.items()
    ]
    out.append(
        _band(
            "leakage",
            "depth-2 decision tree over the observable columns",
            _tree(frame, broadcast),
            None,
            limits.tree_leakage_max,
            "the same six features, combined instead of tried one at a time",
        )
    )
    return out


def _config(observable: Path) -> config.Config:
    """Reload the config the run recorded, not the one on disk at the repository root.

    `n_transactions` is handed back in because `config.load` would otherwise recompute it from
    `target_rows`, and the effective copy preserves the operator's original target rather than the
    count this run actually used. `anchor` is the repository root because that copy names
    `regions.yaml` exactly as `run_config.json` did, and that file is a neighbour of the original.
    """
    path = observable / CONFIG_NAME
    baked = json.loads(path.read_text(encoding="utf-8"))
    return config.load(path, n_txs=int(baked["n_transactions"]), anchor=writers.REPO_ROOT)


def _share(frame: pl.DataFrame, column: str) -> float:
    total = frame.height
    return round(frame[column].sum() / total, 6) if total else 0.0


def _summary(
    cap: pl.DataFrame, txs: pl.DataFrame, blocks: pl.DataFrame, truth: Path
) -> dict[str, Any]:
    """Aggregates only, and every one of them a count or a ratio.

    This is what a human reads first, and it is the reason the rule against printing data is not
    the same as a rule against reporting: `11694 rows from 5000 peers` describes the run without
    naming one peer.
    """
    origins = pl.read_parquet(truth / "origins.parquet")
    entities = pl.read_parquet(truth / "entities.parquet")
    campaigns = pl.read_parquet(truth / "campaigns.parquet")
    seen = cap["txid"].n_unique()
    # Coinbase is counted on its own line rather than folded into the shortfall below it. A
    # coinbase is never gossiped as a loose transaction, so counting it as a transaction no
    # observer saw would report a deliberate property of Bitcoin as a gap in the capture.
    coinbase = int(txs["is_coinbase"].sum())
    broadcast = txs.height - coinbase
    return {
        "capture_rows": cap.height,
        "transactions": txs.height,
        "coinbase_transactions_never_gossiped": coinbase,
        "transactions_broadcast": broadcast,
        "transactions_announced": seen,
        "broadcast_transactions_no_observer_saw": broadcast - seen,
        "blocks": blocks.height,
        "announcing_peers": cap["src_ip"].n_unique(),
        "observers": cap["observer_id"].n_unique(),
        "tor_share": _share(origins, "used_tor"),
        "vpn_share": _share(origins, "used_vpn"),
        "unresolved_asn_share": round(cap["asn"].null_count() / max(cap.height, 1), 6),
        "unresolved_geo_share": round(cap["geo_country"].null_count() / max(cap.height, 1), 6),
        "entities": entities.height,
        "illicit_entities": int(entities["is_illicit"].sum()),
        "entities_in_a_campaign": entities.filter(pl.col("typologies").list.len() > 0).height,
        "campaigns": campaigns.height,
    }


GROUPS = ("invariants", "manifests", "quarantine", "distributions", "leakage")


def _markdown(checks: Sequence[Check], summary: dict[str, Any], failed: int) -> str:
    """The report a human reads. No run id, so two runs of one seed produce identical bytes and
    `make verify-determinism` can compare these files as it compares everything else."""
    lines = [
        "# MAYAJAAL validation",
        "",
        f"**{'PASS' if not failed else 'FAIL'}** — {len(checks) - failed} of {len(checks)} "
        "checks passed.",
        "",
        "## Run",
        "",
    ]
    lines += [f"- {name.replace('_', ' ')}: {value}" for name, value in summary.items()]
    for group in GROUPS:
        rows = [check for check in checks if check.group == group]
        if not rows:
            continue
        # The note column carries what a bare number cannot: on a failing row, which row to look
        # at; on a passing one, what the number has to be read against. A note only a failure
        # renders is a note nobody sees, because the report is read when it passes.
        lines += [
            "",
            f"## {group.title()}",
            "",
            "| | check | measured | required | note |",
            "|-|-|-|-|-|",
        ]
        lines += [
            f"| {'ok' if one.ok else '**FAIL**'} | {one.name} | {one.value} | {one.bound} "
            f"| {one.note} |"
            for one in rows
        ]
    notes = [one for one in checks if one.note and not one.ok]
    if notes:
        lines += ["", "## Where to look", ""]
        lines += [f"- {one.name}: {one.note}" for one in notes]
    return "\n".join(lines) + "\n"


def _json(checks: Sequence[Check], summary: dict[str, Any], failed: int) -> str:
    payload = {
        "verdict": "PASS" if not failed else "FAIL",
        "checks_run": len(checks),
        "checks_failed": failed,
        "summary": summary,
        "checks": {
            group: [one.as_json() for one in checks if one.group == group] for group in GROUPS
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    parser = argparse.ArgumentParser(
        prog="validate", description="Check one MAYAJAAL run against its own answer key."
    )
    # A run id, never a path. The answer key and the measurements directory are derived from it,
    # exactly as the generator derives them, so no argument can point the reader at another tree.
    parser.add_argument("--run", required=True, help="run id under data/generated/")
    args = parser.parse_args(argv)

    roots = writers.run_roots(GENERATED_ROOT / args.run)
    for tree in (roots.observable, roots.truth):
        if not tree.is_dir():
            raise SystemExit(f"validate: no run named {args.run!r}: {tree} does not exist")

    cfg = _config(roots.observable)
    cap = _capture(roots.observable)
    chain = roots.observable / "chain"
    txs = pl.read_parquet(chain / "transactions.parquet")
    blocks = pl.read_parquet(chain / "blocks.parquet")
    endowment = pl.read_parquet(chain / "endowment.parquet")
    origins = pl.read_parquet(roots.truth / "origins.parquet")
    entities = pl.read_parquet(roots.truth / "entities.parquet")
    delays = _delays(cap, origins)
    frame = _labelled(cap, origins)
    # Every leakage score is a share of this, not of the transactions that reached an observer.
    broadcast = txs.height - int(txs["is_coinbase"].sum())

    checks = (
        _invariants(cap, txs, origins, delays, entities, endowment)
        + _manifests(roots.observable)
        + _headers(roots.observable)
        + _distributions(cfg, cap, txs, blocks, delays)
        + _leakage(cfg, frame, broadcast)
    )
    failed = [one for one in checks if not one.ok]
    summary = _summary(cap, txs, blocks, roots.truth)

    out = roots.measurements / "validation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(_json(checks, summary, len(failed)), encoding="utf-8")
    (out / "report.md").write_text(_markdown(checks, summary, len(failed)), encoding="utf-8")

    for one in failed:
        LOG.error(
            "FAIL %s: %s, measured %s, required %s", one.group, one.name, one.value, one.bound
        )
    LOG.info(
        "validate: %d checks, %d failed, %d capture rows, %d transactions, report %s",
        len(checks),
        len(failed),
        cap.height,
        txs.height,
        out / "report.md",
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
