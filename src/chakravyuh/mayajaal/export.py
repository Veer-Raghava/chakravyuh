"""MAYAJAAL-SPEC Layer 5: the capture, in the three shapes a real one arrives in.

Section 1 of `docs/DATA-CONTRACTS.md` is the only schema in this project we did not choose, so
this module implements it and nothing else. One row is one announcement of one transaction by
one peer, the chain columns repeat across every row announcing the same txid, and the eighteen
column names here are exactly section 1's names in section 1's order.

Three directories, because a file from NTRO could be any of them and a stage that has only ever
seen our CSV will break on the day it is handed XML:

  capture/       CSV shards of `export.shard_rows` rows. Lists are pipe separated, a null is
                 the empty field.
  capture_json/  the same rows as JSONL. Lists stay lists and a null stays null, so this is the
                 encoding that loses nothing.
  capture_xml/   a small sample, `export.xml_sample_rows` rows, because the format is verbose
                 and its purpose is to prove the reader handles it, not to carry the run.

Nothing here writes to disk. Every part is built in memory and handed to `writers.py`, which is
the one module in the stage that opens a file, and which hashes the bytes it is given before
writing them. Nothing here reads a clock: a row's timestamp comes from the run's own microsecond
clock, and the epoch it is measured from is `chain.genesis_us`.

No column in this file is a ground-truth column. The answer key knows which peer of the many
announcing a transaction was the one that created it; a capture row cannot, or the whole problem
would be a lookup.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree

from chakravyuh.mayajaal import network
from chakravyuh.mayajaal.chain import Run
from chakravyuh.mayajaal.config import Config
from chakravyuh.mayajaal.network import Network

# Section 1, required columns first and then our optional extensions, in the document's order.
# `tests/test_contracts.py` holds the same two lists and the golden fixture is written in this
# order, so a real capture and a generated one present their columns identically.
COLUMNS: tuple[str, ...] = (
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "txid",
    "input_addresses",
    "input_amounts",
    "output_addresses",
    "output_amounts",
    "geo_country",
    "asn",
    "fee_sats",
    "vsize",
    "script_types",
    "block_height",
    "msg_type",
    "observer_id",
)

# The Unix epoch, because `chain.genesis_us` is measured from it. Not a clock read: the only
# thing this module does with `datetime` is arithmetic on a number the run already fixed.
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

CSV_DIR = "capture"
JSON_DIR = "capture_json"
XML_DIR = "capture_xml"


def _stamp(time_us: int) -> str:
    """ISO 8601 with exactly six fractional digits and an explicit `+00:00`.

    Section 1 permits epoch seconds and epoch milliseconds too, and KAVACH detects all three.
    We write the unambiguous one. `timedelta` rather than `fromtimestamp`, because dividing a
    microsecond epoch by a million to get a float would round somewhere past the year 2112.
    """
    return (EPOCH + timedelta(microseconds=time_us)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "+00:00"


@dataclass(frozen=True, slots=True)
class Part:
    """One file of one export directory: where it goes, its bytes, and the rows it carries.

    `rows` counts announcements, not lines: a CSV header is not a row. `writers.py` sums these
    per directory to fill section 10's `counts.out`, and the difference against the rows offered
    is `counts.dropped`, which is how the XML sample accounts for what it left behind.
    """

    directory: str
    name: str
    text: str
    rows: int

    @property
    def rel(self) -> str:
        return f"{self.directory}/{self.name}"


def _cell(value: object) -> str:
    """One CSV field. A list becomes pipe separated, a null becomes the empty field."""
    if value is None:
        return ""
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


def rows(cfg: Config, run: Run, net: Network, start: int, stop: int) -> Iterator[dict[str, object]]:
    """Announcements `start` up to `stop`, expanded into section 1's columns.

    The capture holds one index per row rather than a copy of the transaction, so the repeated
    chain columns are joined in here, at write time. Iterating a slice rather than the whole
    capture is what keeps one shard, not the entire run, in memory as text.

    Every key is inserted in `COLUMNS` order and the CSV, JSONL and XML writers all rely on
    that, so `tests/test_network.py` asserts the two agree.
    """
    capture = net.capture
    nodes = net.topology.nodes
    observers = net.topology.observers
    dst_port = cfg.network.listen_port
    for index in range(start, stop):
        tx = run.txs[capture.tx_index[index]]
        node = nodes[capture.src_node[index]]
        watcher = capture.observer[index]
        yield {
            "timestamp": _stamp(capture.time_us[index]),
            "src_ip": node.ip,
            "dst_ip": observers[watcher].ip,
            # The announcing side's ephemeral port. Load bearing for CGNAT attribution: it is
            # the only thing distinguishing two wallets behind one carrier address.
            "src_port": node.port,
            "dst_port": dst_port,
            "txid": tx.txid,
            "input_addresses": list(tx.input_addresses),
            "input_amounts": list(tx.input_sats),
            "output_addresses": list(tx.output_addresses),
            "output_amounts": list(tx.output_sats),
            "geo_country": node.country,
            "asn": node.asn,
            "fee_sats": tx.fee_sats,
            "vsize": tx.vsize_vb,
            "script_types": list(tx.output_kinds),
            "block_height": tx.height,
            "msg_type": "inv" if capture.is_inv[index] else "tx",
            "observer_id": network.observer_id(watcher),
        }


def _csv(batch: Iterator[dict[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for row in batch:
        writer.writerow([_cell(value) for value in row.values()])
    return buffer.getvalue()


def _jsonl(batch: Iterator[dict[str, object]]) -> str:
    return "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in batch)


def _xml(batch: Iterator[dict[str, object]], seed: int) -> tuple[str, int]:
    """The sample as XML, and how many rows it holds.

    A list column becomes repeated `<item>` children, and a null becomes an empty element, so
    an empty list and a null look the same here. That is a property of the format rather than a
    defect to paper over: which columns are lists is fixed by section 1, and a reader keyed on
    the column name recovers the difference. `data/fixtures/capture/capture.xml` is deliberately
    the same shape, down to the root's attributes.
    """
    root = ElementTree.Element("capture", seed=str(seed), rows="0")
    written = 0
    for row in batch:
        element = ElementTree.SubElement(root, "row")
        for column, value in row.items():
            child = ElementTree.SubElement(element, column)
            if isinstance(value, list):
                for item in value:
                    ElementTree.SubElement(child, "item").text = str(item)
            elif value is not None:
                child.text = str(value)
        written += 1
    root.set("rows", str(written))
    ElementTree.indent(root, space="  ")
    return ElementTree.tostring(root, encoding="unicode", xml_declaration=True) + "\n", written


def _spans(total: int, size: int) -> list[tuple[int, int]]:
    """Contiguous row ranges of at most `size` rows, and one empty range for an empty capture.

    The capture is sorted by time, so a contiguous range of rows is a contiguous interval of
    time and sharding on the row index is sharding on time. An empty capture still gets one
    part, because a header with no rows says "no announcements" and a missing directory says
    "the exporter did not run".
    """
    return [(start, min(start + size, total)) for start in range(0, max(total, 1), size)]


def parts(cfg: Config, run: Run, net: Network) -> Iterator[Part]:
    """Every file of every export directory, one at a time.

    A generator rather than a list: the caller writes each part and drops it, so the peak cost
    is one shard of text rather than the whole capture three times over.

    ponytail: one shard is buffered in memory before it is hashed and written. The ceiling is
    `export.shard_rows` rows of text, a few hundred megabytes at the default; the upgrade is an
    incremental hash over a stream, which costs `writers.py` its buffer-then-write guarantee.
    """
    total = len(net.capture)
    size = max(1, cfg.export.shard_rows)
    spans = _spans(total, size)
    if "csv" in cfg.export.formats:
        for index, (start, stop) in enumerate(spans):
            text = _csv(rows(cfg, run, net, start, stop))
            yield Part(CSV_DIR, f"part-{index:04d}.csv", text, stop - start)
    if "jsonl" in cfg.export.formats:
        for index, (start, stop) in enumerate(spans):
            text = _jsonl(rows(cfg, run, net, start, stop))
            yield Part(JSON_DIR, f"part-{index:04d}.jsonl", text, stop - start)
    sample = min(total, cfg.export.xml_sample_rows)
    text, written = _xml(rows(cfg, run, net, 0, sample), cfg.seed)
    yield Part(XML_DIR, "sample.xml", text, written)


def offered(net: Network) -> int:
    """Announcements handed to the exporter, which is `counts.in` for every export directory."""
    return len(net.capture)
