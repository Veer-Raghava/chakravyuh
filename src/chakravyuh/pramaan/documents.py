"""The two rendered documents: `packet.pdf` and `notice.pdf`.

`packet.pdf` is the case file an analyst reads. `notice.pdf` is a production requisition
under section 94 of the Bharatiya Nagarik Suraksha Sanhita, 2023, addressed to the entity
that operates the infrastructure the attribution points at, listing the records requested.
The statutory grounding is the one the project claims: disclosure of the hash value is
required by section 63(4) of the Bharatiya Sakshya Adhiniyam, 2023, read with Schedule
Part A, and the packet discloses it — which is the whole point of the hash chain.

Both are document typography — serif body, generous margins, no UI furniture — and both
truncate every identifier through `vaani.redact` before a character reaches a page. A
complete address, IP or txid on a page is a leak, not evidence.
"""

from __future__ import annotations

from typing import Any

from chakravyuh.pramaan import pdflib
from chakravyuh.vaani import redact

MARGIN: float = 72.0  # one inch, document style
BODY_WIDTH: float = pdflib.A4[0] - 2 * MARGIN
LINE: float = 14.0

AS_ORG_FALLBACK = "the operator of the network named below"


def _redact_ip(ip: str) -> str:
    return redact.redact_ip(ip) if ip else "(no address attributed)"


def _redact_txid(txid: str) -> str:
    return redact.redact_txid(txid) if txid else "(not attributed)"


class _Cursor:
    """A y-coordinate walking down one page. Adds a page when the block runs out."""

    def __init__(self, doc: pdflib.Document, top: float, bottom: float) -> None:
        self.doc = doc
        self.page = doc.page()
        self.y = top
        self.top = top
        self.bottom = bottom

    def next_page(self) -> None:
        self.page = self.doc.page()
        self.y = self.top

    def space(self, height: float) -> None:
        self.y += height
        if self.y > self.bottom:
            self.next_page()

    def heading(self, text: str) -> None:
        self.space(LINE * 1.5)
        self.page.text(MARGIN, self.y, "serif-bold", 13, text)
        self.space(LINE)
        self.page.rule(MARGIN, self.y + 3, BODY_WIDTH)
        self.space(LINE)

    def para(self, text: str, font: str = "serif", size: float = 10.5) -> None:
        for line in pdflib.wrap(text, font, size, BODY_WIDTH):
            self.page.text(MARGIN, self.y, font, size, line)
            self.space(size * 1.35)

    def field(self, label: str, value: str) -> None:
        self.page.text(MARGIN, self.y, "serif-bold", 10.5, label)
        self.page.text(MARGIN + 160, self.y, "serif", 10.5, value)
        self.space(LINE)


def packet_pdf(packet: dict[str, Any]) -> bytes:
    """The evidence packet as a document: the case, the custody, the doubts."""
    doc = pdflib.Document(f"Evidence packet {packet['case_id']}")
    cur = _Cursor(doc, top=MARGIN, bottom=pdflib.A4[1] - MARGIN)

    cur.heading("EVIDENCE PACKET")
    cur.field("Case", str(packet["case_id"]))
    cur.field("Generated", _utc_iso(int(packet["generated_at_us"])))
    cur.field("Code version", str(packet["code_version"]))
    cur.field("Tool version", str(packet["tool_version"]))

    cur.heading("SUBJECT")
    subject = packet["subject"]
    cur.field("Subject", str(subject["subject_id"]))
    cur.field("Cluster", str(subject["cluster_id"]) or "(single address)")
    for one in subject["addresses_redacted"][:12]:
        cur.para(one, font="mono", size=10)
    if len(subject["addresses_redacted"]) > 12:
        cur.para(
            f"(and {len(subject['addresses_redacted']) - 12} further addresses in the "
            "packet's JSON, omitted here for space)"
        )

    attribution = packet["attribution"]
    cur.heading("ATTRIBUTION")
    if packet.get("attribution_ready") and attribution.get("asn") is not None:
        cur.field(
            "Network operator (ASN)",
            f"AS{attribution['asn']} {attribution['as_org']}".strip(),
        )
        cur.field("Network class", str(attribution["net_class"]) or "-")
        cur.field("Region", str(attribution["geo_country"]) or "-")
        cur.field("Operator probability", f"{float(attribution['p_asn']):.3f}")
        cur.field("Margin to runner-up", f"{float(attribution['margin']):.3f}")
        if attribution.get("observed_at_utc"):
            cur.field("Observed at", str(attribution["observed_at_utc"]))
        # The exact host is officer-only: rendered only in the redacted first-octet form, and
        # only when present. The full IP/port never leave the packet's JSON.
        if attribution.get("peer_ip"):
            cur.field("Host address (officer-only)", _redact_ip(str(attribution["peer_ip"])))
            cur.field("Source port (officer-only)", str(attribution["peer_port"]))
        cur.para(
            "The probability is the estimator's own mass on this operator, not a share of "
            "certainty: the mass does not sum to one, because the operator that broadcast the "
            "transaction may not have been observed at all."
        )
    else:
        cur.para(
            "No origin attribution is stated for this subject. The operator, network class "
            "and a precise observation time are not all present, so the packet records no "
            "attribution rather than an unready one."
        )

    cur.heading("CONFIDENCE")
    conf = packet["confidence"]
    cur.para(
        f"The calibrated interval for this subject's risk is [{float(conf['low']):.2f}, "
        f"{float(conf['high']):.2f}], built at coverage target "
        f"{float(conf['coverage_target']):.2f} "
        f"by the {conf['method']} method. The claim is that the interval covers the true "
        "risk the stated fraction of the time; it is not a probability of guilt."
    )

    cur.heading("FINDINGS")
    for one in packet["findings"]:
        cur.para(f"· [{one['kind']}] {one['statement']}")

    cur.heading("COUNTER-EVIDENCE, THE CASE AGAINST THIS LEAD")
    for one in packet["counter_findings"]:
        marker = "WOULD CLEAR" if one["would_clear"] else "considered"
        cur.para(f"· [{one['kind']}] ({marker}) {one['statement']}")

    cur.heading("CHAIN OF CUSTODY")
    cur.field("Sealed input rows", str(packet["input"]["rows_sealed"]))
    for entry in packet["input"]["files"]:
        cur.para(f"{entry['path']}\nsha256 {entry['sha256']}", font="mono", size=9)
    for link in packet["chain_of_custody"]:
        cur.para(
            f"{link['stage']}  finished {_utc_iso(int(link['at_us']))}\n"
            f"  meta sha256 {link['sha256']}\n"
            f"  inputs {len(link['inputs'])} file(s), outputs {len(link['outputs'])} file(s)",
            font="mono",
            size=9,
        )

    cur.heading("REPLAY AND LEGAL BASIS")
    replay = packet["replay"]
    cur.para(
        "The packet can be regenerated from the sealed inputs with the recorded seed. The "
        "replay digest is computed over the canonical serialisation of this packet with "
        "the digest field blanked; the verifying command recomputes it and compares.",
    )
    cur.para(str(replay["command"]), font="mono", size=9)
    cur.para(f"replay digest {replay['expected_packet_sha256']}", font="mono", size=9)
    cur.para("merkle log leaf and head are recorded in the run's packets/merkle.log")
    legal = packet["legal"]
    cur.para(
        f"Legal basis: {legal['basis']}. Hash disclosure: {legal['hash_disclosure']}. The "
        "hash values in this packet are disclosed as required for electronic records, so "
        "that the court may verify the integrity of the evidence by recomputing them."
    )
    return doc.render()


def notice_pdf(packet: dict[str, Any]) -> bytes:
    """A section 94 production requisition, pre-filled from the packet.

    Addressed to the operator of the attributed peer's network — on the current runs an
    exchange or ISP would be filled by the officer — it enumerates the records wanted, in
    the language of the records themselves, with every identifier truncated.
    """
    doc = pdflib.Document(f"Production notice {packet['case_id']}")
    cur = _Cursor(doc, top=MARGIN, bottom=pdflib.A4[1] - MARGIN)

    cur.heading("REQUISITION TO PRODUCE DOCUMENTS")
    cur.para(
        "Under section 94 of the Bharatiya Nagarik Suraksha Sanhita, 2023, an officer "
        "conducting an investigation may require the person in possession of a document "
        "to produce it. You are accordingly required to produce the records enumerated "
        "below, which the accompanying evidence packet identifies as material to the "
        "investigation.",
        size=11,
    )
    attribution = packet["attribution"]
    subject = packet["subject"]

    cur.heading("TO")
    org = attribution.get("as_org") or AS_ORG_FALLBACK
    cur.para(
        f"The operator of the network service identified as {org} (autonomous system "
        f"{attribution.get('asn') or '___'}), being the person in possession of the "
        "records described below.",
        size=11,
    )

    cur.heading("CASE REFERENCE")
    cur.field("Case", str(packet["case_id"]))
    cur.para(f"digest {packet['replay']['expected_packet_sha256']}", font="mono", size=9)

    cur.heading("RECORDS REQUIRED")
    items: list[str] = []
    if attribution["peer_ip"]:
        when = str(attribution["observed_at_utc"])
        peer = _redact_ip(str(attribution["peer_ip"]))
        items.append(
            f"1. Subscriber and session records for the network address {peer} "
            f"in use at or around {when}, including the source port {attribution['peer_port']} "
            "and the account to which that session was assigned."
        )
        items.append(
            "2. The network address translation or address-sharing logs from which the "
            "identity of the subscriber behind that address at that time can be "
            "established, where the address was shared."
        )
    for one in subject["addresses_redacted"][:4]:
        items.append(
            f"3. Know-your-customer records and transaction statements for the Bitcoin "
            f"address {one}, and for any address you control that received funds from or "
            f"sent funds to it during the period covered by the sealed capture."
        )
    if attribution["peer_ip"]:
        items.append(
            "4. Any record of the peer's connection to the Bitcoin network from that "
            "address, sufficient to corroborate or refute its having announced the "
            f"transaction {_redact_txid(str(attribution.get('origin_txid', '')))}."
        )
    if not items:
        items.append(
            "1. Records sufficient to identify the operator of the subject described in "
            "the accompanying evidence packet."
        )
    for line in items:
        cur.para(line, size=11)
        cur.space(LINE)

    cur.heading("MANNER OF PRODUCTION")
    cur.para(
        "Produce the documents at the office of the issuing officer within the time the "
        "requisition states. Where a record is electronic, produce it with the hash value "
        "required by section 63(4) of the Bharatiya Sakshya Adhiniyam, 2023, read with "
        "Part A of the Schedule, disclosing the hash so that the record's integrity can be "
        "verified. The accompanying evidence packet discloses its own hash values in the "
        "same manner and may be verified by recomputation.",
        size=11,
    )
    cur.para(
        "A requisition under section 94 is issued to obtain a document or thing necessary "
        "or desirable for the purposes of an investigation. Nothing in this notice "
        "determines the guilt or innocence of any person.",
        size=11,
    )
    cur.space(3 * LINE)
    cur.field("Place:", "____________________")
    cur.field("Date:", "____________________")
    cur.field("Officer:", "____________________")
    cur.space(2 * LINE)
    cur.para(
        "This notice was generated from the evidence packet referenced above. Identifiers "
        "are truncated in this rendering; the machine-readable packet holds the values "
        "from which the truncated forms were derived.",
        size=9,
    )
    return doc.render()


def _utc_iso(generated_at_us: int) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(generated_at_us / 1_000_000, tz=UTC).isoformat()
