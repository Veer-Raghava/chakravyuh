"""Identifier truncation at write time, for every human-readable string VAANI emits.

Contract section 8's `statement` columns are prose a non-specialist reads, so no complete
identifier may sit in one: addresses keep first six and last four, txids first eight and
last four, IPv4 two octets, IPv6 two hextets. SHA-256 values are the deliberate exception
and never pass through here.

The structured columns of `alerts.parquet` (`origin_txid`, `origin_peer_ip`) are contract
fields, not rendered prose: section 9's packet quotes them, and the console's shared
formatter truncates defensively on display. This module exists for the prose.
"""

from __future__ import annotations

from typing import Final

ELLIPSIS: Final[str] = "…"


def redact_address(address: str) -> str:
    """First six and last four characters, whatever the length survives as."""
    if len(address) <= 10:
        return address
    return address[:6] + ELLIPSIS + address[-4:]


def redact_txid(txid: str) -> str:
    """First eight and last four hex characters of a transaction id."""
    if len(txid) <= 12:
        return txid
    return txid[:8] + ELLIPSIS + txid[-4:]


def redact_ip(ip: str) -> str:
    """Two octets of an IPv4, two hextets of an IPv6, per the truncation law."""
    if "." in ip:
        octets = ip.split(".")
        if len(octets) == 4:
            return f"{octets[0]}.{octets[1]}.x.x"
        return octets[0] + ".x.x"
    hextets = ip.split(":")
    return f"{hextets[0]}:{hextets[1]}:x:x" if len(hextets) >= 4 else hextets[0] + ":x"
