#!/usr/bin/env python3
"""Serialise the hand-authored S00 capture fixture to CSV, JSONL and XML.

One row is one announcement of one transaction by one peer, exactly as
`docs/DATA-CONTRACTS.md` section 1 defines it. The transaction roster and the
announcement schedule below are hand-authored literals; this script only joins and
serialises them, which is what makes two guarantees structural rather than hoped for:
rows sharing a txid carry byte-identical chain columns (invariant 5), and the three
file formats describe the same capture.

There is no random number generator anywhere in this module. Every value is explicit,
so `--seed` is recorded in the XML header and the README but never consumed. Byte
identity across runs is guaranteed by construction rather than by a reproducible stream.

Every identifier is either drawn from a reserved range or made structurally invalid on
purpose, so none of them can belong to a real person or a real coin:

  peers, observers   RFC 5737 (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24)
  IPv6 peer          RFC 3849 (2001:db8::/32)
  ASNs               RFC 5398 documentation range 64496-64511
  bech32 addresses   contain "i", which is not in the bech32 charset
  base58 addresses   contain "0", which is not in the base58 alphabet
  txids              f1a7 + 4-digit index + 56 zeros; valid hex, obviously synthetic
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple, TypedDict
from xml.dom import minidom

BASE = datetime(2026, 3, 1, 9, 0, 0, tzinfo=UTC)
OBSERVERS = ("198.51.100.10", "198.51.100.11", "198.51.100.12", "198.51.100.13")
DST_PORT = 8333

COLUMNS = (
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
LIST_STR = ("input_addresses", "output_addresses", "script_types")
LIST_INT = ("input_amounts", "output_amounts")
NULLABLE = ("geo_country", "asn", "block_height")

# Real mainnet lengths, so a length-based script_type rule behaves as it would on real data.
_ADDR_SHAPES = {
    "p2pkh": ("1", 34, "2"),
    "p2sh": ("3", 34, "2"),
    "p2wpkh": ("bc1q", 42, "q"),
    "p2wsh": ("bc1q", 62, "q"),
    "p2tr": ("bc1p", 62, "q"),
}


def _addr(kind: str, tag: str) -> str:
    """Build a structurally invalid address of the right shape for `kind`.

    The literal "fixture0" in the body is what makes the result unusable: "i" is absent
    from the bech32 charset and "0" is absent from the base58 alphabet, so a bech32-style
    result can never decode and a base58-style result can never checksum. Padding uses a
    character that IS legal in the relevant alphabet so the invalid marker is the only
    reason the address fails.

    Padding sits between the marker and the tag so the tag lands at the end of the string.
    peek.py truncates addresses to first six and last four, and two fixture addresses that
    truncated to the same thing would make redacted output useless to read.
    """
    prefix, width, pad = _ADDR_SHAPES[kind]
    head = f"{prefix}fixture0"
    fill = width - len(head) - len(tag)
    if fill < 0:
        raise ValueError(f"tag {tag!r} too long for {kind}")
    return head + pad * fill + tag


def _script_type(addr: str) -> str:
    if addr.startswith("bc1p"):
        return "p2tr"
    if addr.startswith("bc1q"):
        return "p2wsh" if len(addr) > _ADDR_SHAPES["p2wpkh"][1] else "p2wpkh"
    if addr.startswith("3"):
        return "p2sh"
    return "p2pkh"


class Peer(NamedTuple):
    ip: str
    port: int
    asn: int | None
    country: str | None


# Twenty ordinary peers plus five that exist to carry one awkward case each.
PEERS: dict[str, Peer] = {
    "p01": Peer("203.0.113.11", 41221, 64496, "IN"),
    "p02": Peer("203.0.113.12", 41222, 64496, "IN"),
    "p03": Peer("203.0.113.21", 41231, 64497, "US"),
    "p04": Peer("203.0.113.22", 41232, 64497, "US"),
    "p05": Peer("203.0.113.31", 41241, 64498, "DE"),
    "p06": Peer("203.0.113.32", 41242, 64498, "DE"),
    "p07": Peer("203.0.113.41", 41251, 64499, "SG"),
    "p08": Peer("203.0.113.42", 41252, 64499, "SG"),
    "p09": Peer("203.0.113.51", 41261, 64500, "NL"),
    "p10": Peer("203.0.113.52", 41262, 64500, "NL"),
    "p11": Peer("203.0.113.61", 41271, 64501, "IN"),
    "p12": Peer("203.0.113.62", 41272, 64501, "IN"),
    "p13": Peer("203.0.113.71", 41281, 64502, "US"),
    "p14": Peer("203.0.113.72", 41282, 64502, "US"),
    "w01": Peer("192.0.2.11", 41301, 64503, "SG"),
    "w02": Peer("192.0.2.12", 41302, 64503, "SG"),
    "w03": Peer("192.0.2.13", 41303, 64503, "SG"),
    "w04": Peer("192.0.2.14", 41304, 64503, "SG"),
    "w05": Peer("192.0.2.15", 41305, 64503, "SG"),
    "w06": Peer("192.0.2.16", 41306, 64503, "SG"),
    # Case 8: a known Tor exit, so first-seen must not be trusted as an origin.
    "tor": Peer("203.0.113.66", 9001, 64500, "NL"),
    # Case 9: two distinct wallets behind one CGNAT address, split only by source port.
    "cga": Peer("203.0.113.90", 41000, 64501, "IN"),
    "cgb": Peer("203.0.113.90", 41001, 64501, "IN"),
    # Case 10: IPv6, which must not crash the /24 aggregation path.
    "v6": Peer("2001:db8:0:1::7", 41777, 64502, "DE"),
    # Case 11: an unresolvable ASN, which is a null and not a zero.
    "noasn": Peer("203.0.113.140", 41888, None, "SG"),
}

POOL_HOT = _addr("p2wpkh", "poolhot")
MINERS = (
    _addr("p2pkh", "miner01"),
    _addr("p2sh", "miner02"),
    _addr("p2wpkh", "miner03"),
    _addr("p2wsh", "miner04"),
    _addr("p2tr", "miner05"),
    _addr("p2wpkh", "miner06"),
)
PEEL_SRC = _addr("p2wpkh", "peelsrc")
PEEL_CHG = tuple(_addr("p2wpkh", f"peelchg{i}") for i in (1, 2, 3))
PEEL_OUT = tuple(_addr("p2pkh", f"peelout{i}") for i in (1, 2, 3))
CJ_IN = tuple(_addr("p2wpkh", f"cjin{i}") for i in (1, 2, 3, 4))
CJ_OUT = tuple(_addr("p2wpkh", f"cjout{i}") for i in (1, 2, 3, 4))
EXCH_DEP = _addr("p2sh", "exchdep1")
STR_DST = _addr("p2wpkh", "strdst")
FAN_OUT = tuple(_addr("p2wpkh", f"fanout{i:02d}") for i in range(1, 13))
CON_IN = tuple(_addr("p2pkh", f"conin{i}") for i in (1, 2, 3, 4))


class Tx(NamedTuple):
    """One transaction. `offset_us` is the first announcement, microseconds after BASE."""

    idx: int
    offset_us: int
    in_addrs: tuple[str, ...]
    in_amts: tuple[int, ...]
    out_addrs: tuple[str, ...]
    out_amts: tuple[int, ...]
    vsize: int
    block_height: int | None


TRANSACTIONS: tuple[Tx, ...] = (
    # 1: coinbase. Zero inputs, so KAVACH must accept empty input lists (invariant 3).
    Tx(1, 0, (), (), (POOL_HOT,), (312_500_000,), 200, 880_001),
    # 2, 3, 4: the same pool hot wallet paying out at 600 s intervals. Three beats is the
    # minimum a cadence detector can call regular, which is the point of the case.
    Tx(
        2,
        600_000_000,
        (POOL_HOT,),
        (312_500_000,),
        MINERS,
        (52_000_000, 51_000_000, 50_500_000, 50_000_000, 49_500_000, 59_480_000),
        420,
        880_002,
    ),
    Tx(
        3,
        1_200_000_000,
        (POOL_HOT,),
        (150_000_000,),
        MINERS,
        (26_000_000, 25_500_000, 25_000_000, 24_500_000, 24_000_000, 24_970_000),
        420,
        880_004,
    ),
    Tx(
        4,
        1_800_000_000,
        (POOL_HOT,),
        (150_000_000,),
        MINERS,
        (26_000_000, 25_500_000, 25_000_000, 24_500_000, 24_000_000, 24_970_000),
        420,
        880_006,
    ),
    # 5: announced by exactly one peer. No cascade to fit, so origin must abstain.
    Tx(
        5,
        120_000_000,
        (_addr("p2wpkh", "usera"),),
        (5_000_000,),
        (_addr("p2wpkh", "mercha"), _addr("p2wpkh", "changea")),
        (3_200_000, 1_795_000),
        141,
        880_003,
    ),
    # 6: seventeen peers. Wide enough that a naive first-seen rule looks confident.
    Tx(
        6,
        240_000_000,
        (_addr("p2wpkh", "userb"), _addr("p2wpkh", "userc")),
        (8_000_000, 4_000_000),
        (_addr("p2wpkh", "merchb"), _addr("p2wpkh", "changeb")),
        (9_500_000, 2_492_000),
        208,
        None,
    ),
    # 7: two peers announce in the same microsecond, so rank must not assume a total order.
    Tx(
        7,
        360_000_000,
        (_addr("p2wpkh", "userd"),),
        (2_500_000,),
        (_addr("p2pkh", "merchc"), _addr("p2wpkh", "changec")),
        (1_100_000, 1_396_000),
        141,
        880_005,
    ),
    # 8: first announcer is a Tor exit.
    Tx(
        8,
        420_000_000,
        (_addr("p2wpkh", "darka"),),
        (15_000_000,),
        (_addr("p2tr", "darkb"), _addr("p2wpkh", "darkchg")),
        (6_000_000, 8_988_000),
        141,
        None,
    ),
    # 9, 10: two wallets behind one CGNAT address, both depositing to one exchange address.
    Tx(
        9,
        480_000_000,
        (_addr("p2wpkh", "mulea"),),
        (1_800_000,),
        (EXCH_DEP, _addr("p2wpkh", "changed")),
        (1_500_000, 296_000),
        141,
        880_007,
    ),
    Tx(
        10,
        540_000_000,
        (_addr("p2wpkh", "muleb"),),
        (1_900_000,),
        (EXCH_DEP, _addr("p2wpkh", "changee")),
        (1_500_000, 396_000),
        141,
        880_007,
    ),
    # 11: four identical outputs, which defeats the common-input-ownership assumption.
    Tx(11, 660_000_000, CJ_IN, (260_000,) * 4, CJ_OUT, (250_000,) * 4, 380, None),
    # 12, 13, 14: a three-hop peel chain. Each hop spends the previous hop's change.
    Tx(
        12,
        720_000_000,
        (PEEL_SRC,),
        (50_000_000,),
        (PEEL_OUT[0], PEEL_CHG[0]),
        (40_000, 49_950_000),
        141,
        880_008,
    ),
    Tx(
        13,
        780_000_000,
        (PEEL_CHG[0],),
        (49_950_000,),
        (PEEL_OUT[1], PEEL_CHG[1]),
        (45_000, 49_895_000),
        141,
        880_009,
    ),
    Tx(
        14,
        840_000_000,
        (PEEL_CHG[1],),
        (49_895_000,),
        (PEEL_OUT[2], PEEL_CHG[2]),
        (38_000, 49_847_000),
        141,
        880_010,
    ),
    # 15: first announcer is IPv6, which must not crash /24 aggregation.
    Tx(
        15,
        900_000_000,
        (_addr("p2wpkh", "usere"),),
        (700_000,),
        (_addr("p2wpkh", "merchd"), _addr("p2wpkh", "changef")),
        (450_000, 246_000),
        141,
        880_011,
    ),
    # 16: one announcing peer has an unresolvable ASN, which is null and not zero.
    Tx(
        16,
        960_000_000,
        (_addr("p2wpkh", "userf"),),
        (3_300_000,),
        (_addr("p2sh", "merche"), _addr("p2wpkh", "changeg")),
        (2_000_000, 1_295_000),
        141,
        None,
    ),
    # 17: four inputs consolidated into one output.
    Tx(
        17,
        1_020_000_000,
        CON_IN,
        (400_000, 650_000, 720_000, 530_000),
        (_addr("p2wpkh", "condst"),),
        (2_275_000,),
        600,
        880_012,
    ),
    # 18: one input fanned out to twelve.
    Tx(
        18,
        1_080_000_000,
        (_addr("p2wpkh", "fansrc"),),
        (6_000_000,),
        FAN_OUT,
        (500_000,) * 11 + (485_000,),
        520,
        None,
    ),
    # 19, 20, 21: three near-equal transfers to one destination.
    Tx(
        19,
        1_140_000_000,
        (_addr("p2wpkh", "strsrc1"),),
        (1_000_000,),
        (STR_DST, _addr("p2wpkh", "strchg1")),
        (995_000, 2_000),
        141,
        880_013,
    ),
    Tx(
        20,
        1_260_000_000,
        (_addr("p2wpkh", "strsrc2"),),
        (1_000_000,),
        (STR_DST, _addr("p2wpkh", "strchg2")),
        (995_000, 2_000),
        141,
        880_013,
    ),
    Tx(
        21,
        1_320_000_000,
        (_addr("p2wpkh", "strsrc3"),),
        (1_000_000,),
        (STR_DST, _addr("p2wpkh", "strchg3")),
        (995_000, 2_000),
        141,
        880_014,
    ),
    Tx(
        22,
        1_380_000_000,
        (_addr("p2wpkh", "userg"), _addr("p2pkh", "userh")),
        (1_200_000, 900_000),
        (_addr("p2wpkh", "merchf"), _addr("p2wpkh", "changeh")),
        (1_750_000, 344_000),
        208,
        880_014,
    ),
    Tx(
        23,
        1_440_000_000,
        (_addr("p2wpkh", "useri"), _addr("p2wpkh", "userj"), _addr("p2sh", "userk")),
        (2_000_000, 1_500_000, 1_100_000),
        (_addr("p2sh", "exchdep2"), _addr("p2wpkh", "changei")),
        (4_000_000, 590_000),
        480,
        880_015,
    ),
    # 24: one in, one out, no change. A pass-through hop.
    Tx(
        24,
        1_500_000_000,
        (_addr("p2wpkh", "ptin"),),
        (7_400_000,),
        (_addr("p2wpkh", "ptout"),),
        (7_395_000,),
        110,
        880_016,
    ),
    Tx(
        25,
        1_560_000_000,
        (_addr("p2wpkh", "userl"), _addr("p2wpkh", "userm")),
        (2_600_000, 1_400_000),
        (_addr("p2wpkh", "merchg"), _addr("p2tr", "merchh"), _addr("p2wpkh", "changej")),
        (1_500_000, 1_200_000, 1_293_000),
        250,
        880_017,
    ),
    # 26: two input addresses against three input amounts. Violates invariant 3 on purpose.
    # This is the one row of the capture that KAVACH must quarantine rather than load.
    Tx(
        26,
        1_620_000_000,
        (_addr("p2wpkh", "bad1"), _addr("p2wpkh", "bad2")),
        (100_000, 100_000, 100_000),
        (_addr("p2wpkh", "badout"),),
        (290_000,),
        141,
        None,
    ),
)

# Announcement schedule: tx index -> ((peer key, microseconds after that tx's offset), ...).
# The first entry of each tuple is the first announcer at delta 0. Deltas are hand-picked to
# be uneven, because an arithmetic cascade would let a wrong origin estimator score well.
SCHEDULE: dict[int, tuple[tuple[str, int], ...]] = {
    1: (
        ("p01", 0),
        ("p02", 1_200),
        ("p05", 4_800),
        ("p03", 9_100),
        ("p09", 15_400),
        ("p07", 22_000),
        ("w01", 31_000),
        ("p11", 44_000),
        ("p13", 61_000),
    ),
    2: (
        ("p11", 0),
        ("p12", 900),
        ("p01", 3_400),
        ("p05", 8_800),
        ("p03", 14_200),
        ("p09", 21_000),
        ("w02", 33_000),
        ("p07", 52_000),
    ),
    3: (
        ("p11", 0),
        ("p12", 1_100),
        ("p02", 3_900),
        ("p06", 9_400),
        ("p04", 15_100),
        ("p10", 23_000),
        ("w03", 35_000),
        ("p08", 54_000),
    ),
    4: (
        ("p11", 0),
        ("p12", 800),
        ("p01", 3_100),
        ("p05", 8_200),
        ("p03", 13_900),
        ("p09", 20_500),
        ("w01", 31_500),
    ),
    5: (("p07", 0),),
    6: (
        ("p01", 0),
        ("p02", 700),
        ("p03", 1_500),
        ("p04", 2_600),
        ("p05", 3_900),
        ("p06", 5_200),
        ("p07", 6_800),
        ("p08", 8_300),
        ("p09", 10_100),
        ("p10", 12_400),
        ("p11", 14_900),
        ("p12", 17_700),
        ("p13", 20_800),
        ("p14", 24_200),
        ("w01", 28_000),
        ("w02", 32_100),
        ("w03", 36_500),
    ),
    # p05 and p09 share delta 4_400: the same-microsecond tie.
    7: (
        ("p03", 0),
        ("p04", 1_300),
        ("p05", 4_400),
        ("p09", 4_400),
        ("p11", 11_200),
        ("w04", 26_000),
    ),
    8: (
        ("tor", 0),
        ("p02", 2_100),
        ("p06", 5_600),
        ("p10", 11_800),
        ("p13", 19_400),
        ("w05", 30_000),
    ),
    9: (
        ("cga", 0),
        ("p01", 1_900),
        ("p05", 5_100),
        ("p09", 10_700),
        ("p12", 18_800),
        ("w06", 29_500),
    ),
    10: (
        ("cgb", 0),
        ("p02", 1_700),
        ("p06", 4_900),
        ("p10", 10_300),
        ("p14", 18_100),
        ("w01", 28_700),
    ),
    11: (
        ("p05", 0),
        ("p06", 800),
        ("p01", 2_200),
        ("p02", 3_600),
        ("p03", 5_900),
        ("p04", 7_400),
        ("p09", 9_800),
        ("p10", 12_100),
        ("p11", 15_600),
        ("p12", 18_900),
        ("p13", 23_400),
        ("w02", 31_200),
    ),
    12: (
        ("p09", 0),
        ("p10", 1_000),
        ("p01", 3_300),
        ("p03", 7_700),
        ("p05", 13_100),
        ("p11", 19_600),
        ("p13", 27_400),
        ("w03", 37_000),
        ("p07", 49_000),
    ),
    13: (
        ("p09", 0),
        ("p10", 1_200),
        ("p02", 3_500),
        ("p04", 8_100),
        ("p06", 13_800),
        ("p12", 20_400),
        ("p14", 28_600),
        ("w04", 38_200),
        ("p08", 50_500),
    ),
    14: (
        ("p09", 0),
        ("p10", 900),
        ("p01", 3_000),
        ("p03", 7_200),
        ("p05", 12_600),
        ("p11", 18_700),
        ("p13", 26_300),
        ("w05", 36_100),
    ),
    15: (
        ("v6", 0),
        ("p01", 2_400),
        ("p05", 6_300),
        ("p09", 12_900),
        ("p13", 21_500),
        ("w06", 31_900),
    ),
    16: (
        ("noasn", 0),
        ("p02", 2_200),
        ("p06", 5_800),
        ("p10", 12_200),
        ("p14", 20_100),
        ("w01", 29_900),
    ),
    17: (
        ("p13", 0),
        ("p14", 1_100),
        ("p01", 3_700),
        ("p03", 8_400),
        ("p05", 14_300),
        ("p09", 21_400),
        ("p11", 29_800),
        ("w02", 39_500),
        ("p07", 52_500),
    ),
    18: (
        ("p03", 0),
        ("p04", 1_000),
        ("p01", 3_200),
        ("p05", 7_900),
        ("p09", 13_400),
        ("p11", 20_000),
        ("p13", 28_100),
        ("w03", 37_800),
        ("p07", 51_000),
    ),
    19: (
        ("p11", 0),
        ("p12", 1_300),
        ("p01", 4_100),
        ("p05", 9_600),
        ("p09", 16_200),
        ("p13", 24_800),
        ("w04", 34_600),
    ),
    20: (
        ("p11", 0),
        ("p12", 1_400),
        ("p02", 4_300),
        ("p06", 9_900),
        ("p10", 16_700),
        ("p14", 25_400),
        ("w05", 35_300),
    ),
    21: (
        ("p11", 0),
        ("p12", 1_200),
        ("p01", 3_800),
        ("p05", 9_200),
        ("p09", 15_800),
        ("p13", 24_100),
        ("w06", 33_900),
    ),
    22: (
        ("p01", 0),
        ("p02", 1_000),
        ("p05", 3_400),
        ("p09", 8_600),
        ("p11", 14_700),
        ("p13", 22_300),
        ("w01", 32_400),
        ("p07", 48_000),
    ),
    23: (
        ("p05", 0),
        ("p06", 1_100),
        ("p01", 3_600),
        ("p03", 8_000),
        ("p09", 13_700),
        ("p11", 20_700),
        ("p13", 29_100),
        ("w02", 38_900),
        ("p07", 53_000),
    ),
    24: (
        ("p07", 0),
        ("p08", 600),
        ("p03", 2_900),
        ("p01", 7_100),
        ("p05", 12_000),
        ("p09", 18_300),
        ("p13", 25_900),
        ("w03", 35_800),
    ),
    25: (
        ("p02", 0),
        ("p01", 1_500),
        ("p06", 4_600),
        ("p10", 10_900),
        ("p12", 17_400),
        ("p14", 25_100),
        ("w04", 34_900),
        ("p08", 47_500),
    ),
    26: (("p01", 0),),
}

# Case name as section 11 of docs/DATA-CONTRACTS.md words it -> the transaction indices
# that carry it. Used by --cases to print a case-to-row_id map for data/fixtures/README.md.
CASES: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("coinbase, zero inputs", (1,)),
    ("regular payout cadence, 600 s", (2, 3, 4)),
    ("exactly one announcing peer", (5,)),
    ("more than fifteen announcing peers", (6,)),
    ("two peers, same microsecond", (7,)),
    ("first announcer is a Tor exit", (8,)),
    ("two wallets, one CGNAT address", (9, 10)),
    ("equal value outputs", (11,)),
    ("three-hop peel chain", (12, 13, 14)),
    ("IPv6 announcing peer", (15,)),
    ("null ASN", (16,)),
    ("malformed row, must be rejected", (26,)),
)


class Row(TypedDict):
    """One announcement of one transaction by one peer. Section 1, all eighteen columns."""

    timestamp: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    txid: str
    input_addresses: list[str]
    input_amounts: list[int]
    output_addresses: list[str]
    output_amounts: list[int]
    geo_country: str | None
    asn: int | None
    fee_sats: int
    vsize: int
    script_types: list[str]
    block_height: int | None
    msg_type: str
    observer_id: str


def txid_of(idx: int) -> str:
    """Synthetic txid for transaction `idx`: f1a7, four index digits, 56 zeros."""
    return f"f1a7{idx:04d}" + "0" * 56


def _stamp(us: int) -> str:
    """ISO 8601 with microseconds and an explicit +00:00, which section 1 requires."""
    return (BASE + timedelta(microseconds=us)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "+00:00"


def build_rows() -> list[Row]:
    """Join the roster to the schedule and return the capture in wire order.

    Chain columns are copied from one Tx literal into every row that shares its txid, so
    invariant 5 holds by construction rather than by discipline. Rows come out sorted by
    timestamp, interleaved across transactions the way a real capture is, so no stage can
    accidentally rely on rows arriving grouped by txid.
    """
    by_idx = {t.idx: t for t in TRANSACTIONS}
    rows: list[Row] = []
    for idx, sched in SCHEDULE.items():
        tx = by_idx[idx]
        fee = sum(tx.in_amts) - sum(tx.out_amts) if tx.in_amts else 0
        scripts = [_script_type(a) for a in tx.out_addrs]
        for i, (key, delta) in enumerate(sched):
            peer = PEERS[key]
            rows.append(
                Row(
                    timestamp=_stamp(tx.offset_us + delta),
                    src_ip=peer.ip,
                    dst_ip=OBSERVERS[i % 4],
                    src_port=peer.port,
                    dst_port=DST_PORT,
                    txid=txid_of(idx),
                    input_addresses=list(tx.in_addrs),
                    input_amounts=list(tx.in_amts),
                    output_addresses=list(tx.out_addrs),
                    output_amounts=list(tx.out_amts),
                    geo_country=peer.country,
                    asn=peer.asn,
                    fee_sats=fee,
                    vsize=tx.vsize,
                    script_types=list(scripts),
                    block_height=tx.block_height,
                    # Deliberately NOT correlated with arrival rank. If the originator were
                    # the only peer sending "tx", origin estimation would be a lookup and
                    # every accuracy number the project reports would be meaningless.
                    msg_type="tx" if i % 4 == 2 else "inv",
                    observer_id=f"obs-{i % 4 + 1}",
                )
            )
    rows.sort(key=lambda r: (r["timestamp"], r["txid"], r["src_ip"], r["src_port"]))
    return rows


def _ordered(row: Row) -> dict[str, object]:
    plain: dict[str, object] = dict(row)
    return {c: plain[c] for c in COLUMNS}


def write_csv(rows: list[Row], path: Path) -> None:
    """Lists become pipe-joined, nulls become the empty field. Section 1's CSV encoding."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            cells: list[str] = []
            for value in _ordered(row).values():
                if value is None:
                    cells.append("")
                elif isinstance(value, list):
                    cells.append("|".join(str(v) for v in value))
                else:
                    cells.append(str(value))
            writer.writerow(cells)


def write_jsonl(rows: list[Row], path: Path) -> None:
    """One JSON object per line. Lists stay lists, nulls stay null."""
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(_ordered(row), separators=(",", ":")) + "\n")


def write_xml(rows: list[Row], path: Path, seed: int) -> None:
    """List columns become repeated <item> children; nulls become an empty element.

    An empty list and a null therefore look identical in the XML. That is not a defect to
    paper over: which columns are lists is fixed by section 1, so a reader keyed on the
    column name recovers the distinction, and KAVACH must be tolerant of exactly this kind
    of format-specific ambiguity.
    """
    root = ET.Element("capture", seed=str(seed), rows=str(len(rows)))
    for row in rows:
        el = ET.SubElement(root, "row")
        for col, value in _ordered(row).items():
            child = ET.SubElement(el, col)
            if isinstance(value, list):
                for item in value:
                    ET.SubElement(child, "item").text = str(item)
            elif value is not None:
                child.text = str(value)
    pretty = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
    path.write_text(pretty, encoding="utf-8")


def cases_report(rows: list[Row]) -> str:
    """The twelve cases mapped to txids and row_id ranges. Identifiers truncated."""
    where: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        where.setdefault(row["txid"], []).append(i)
    lines = [f"{len(rows)} rows, {len(where)} txids", ""]
    for name, indices in CASES:
        for idx in indices:
            t = txid_of(idx)
            ids = where[t]
            lines.append(f"{name:34s}  {t[:8]}…{t[-4:]}  rows {min(ids)}-{max(ids)}  n={len(ids)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the S00 capture fixture.")
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="recorded in the XML header for provenance; never consumed, there is no RNG",
    )
    parser.add_argument("--out", type=Path, default=Path("data/fixtures/capture"))
    parser.add_argument(
        "--cases",
        action="store_true",
        help="print the case-to-row_id map and write nothing",
    )
    args = parser.parse_args(argv)

    rows = build_rows()
    if rows != build_rows():
        print("FAIL: build_rows() is not deterministic")
        return 1

    if args.cases:
        print(cases_report(rows))
        return 0

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out / "capture.csv")
    write_jsonl(rows, out / "capture.jsonl")
    write_xml(rows, out / "capture.xml", args.seed)
    print(f"fixtures: {len(rows)} rows to {out}/capture.{{csv,jsonl,xml}} (seed {args.seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
