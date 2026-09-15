"""Build a `vendor/` tree for the synthetic world, out of the two files that already describe it.

`setu/enrich.py` reads MaxMind GeoLite2 CSVs and a Tor exit list and says nothing at all when they
are absent, which is correct and is also why nothing downstream of SETU has ever been exercised
with a populated `net_class`. This writes those files for the generated world so that path can be
run: ASN and country blocks per region, and an exit list for the Tor pool.

Everything here comes from `run_config.json`'s `network.ip_pools` / `tor_asn` / `vpn_asn` and
`world.ip_pools`, plus `regions.yaml`'s per-region country and ASN. No ground truth, no per-address
knowledge, no run directory: the pools are a property of the world's configuration, and which
address a particular entity drew from one is not consulted and would be a leak if it were. Pure
function of two committed files, so two invocations write identical bytes.

Rows are whole CIDRs, never single addresses. `mayajaal.entities._ip` gives each region a
contiguous slice of every pool and `region_of` is the documented inverse, so a slice is exactly
what a vendor row describes. The one exception is the Tor exit list, which is a list of addresses
by format; it enumerates the whole `tor_exit` pool rather than the 40 exits a particular run minted,
because the pool is *defined* as the Tor pool and enumerating it needs no run to have happened.

Not run by any gate, and its output is deliberately not committed. Writing into the repository's own
`vendor/` turns `make verify-s04` red: that gate asserts SETU's absent-vendor warnings and its null
enrichment columns, and it is asserting the deployment most operators will actually have.

    python scripts/make_vendor_lists.py --out "$TMPDIR/vendor"
"""

from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from chakravyuh.mayajaal.regions import Regions  # noqa: E402
from chakravyuh.mayajaal.regions import load as load_regions  # noqa: E402

CONFIG = REPO / "run_config.json"
VENDOR_ROOT = REPO / "vendor"

# File names transcribed from `setu/enrich.py`'s constants by hand rather than imported. A
# generator that imported the reader's names could only ever write files that reader looks for,
# which would make a rename silently agree with itself instead of failing one side.
ASN_BLOCKS = {4: "GeoLite2-ASN-Blocks-IPv4.csv", 6: "GeoLite2-ASN-Blocks-IPv6.csv"}
COUNTRY_BLOCKS = {4: "GeoLite2-Country-Blocks-IPv4.csv", 6: "GeoLite2-Country-Blocks-IPv6.csv"}
COUNTRY_LOCATIONS = "GeoLite2-Country-Locations-en.csv"
TOR_LIST = "exit-addresses.txt"

ASN_COLUMNS = ("network", "autonomous_system_number", "autonomous_system_organization")
COUNTRY_COLUMNS = (
    "network",
    "geoname_id",
    "registered_country_geoname_id",
    "represented_country_geoname_id",
    "is_anonymous_proxy",
    "is_satellite_provider",
)
LOCATION_COLUMNS = (
    "geoname_id",
    "locale_code",
    "continent_code",
    "continent_name",
    "country_iso_code",
    "country_name",
)

# Synthetic geoname ids, deliberately outside the range GeoNames itself uses. `enrich.py` only
# joins blocks to locations on this value, so it needs to be stable and unique and nothing else;
# reusing a real GeoNames id would assert a place this world does not describe.
GEONAME_BASE = 9_000_001

# Organisation strings are free text in MaxMind's data and `enrich._classify` reads them with
# substring rules, so each one below is chosen to land on the class the pool actually is. Getting
# one wrong is invisible here and shows up as a wrong `net_class` three stages later.
TOR_ORG = "Tor exit relay hosting (documentation)"
VPN_ORG = "VPN provider (documentation)"


@dataclass(frozen=True, slots=True)
class Pool:
    """One address pool and what a vendor lookup should say about it.

    `asn` and `org` null mean "whatever region owns this slice", which is the ordinary case: the
    world's own pools are partitioned by region and each region carries its own ASN. The Tor and
    VPN pools override both, because they are one operator's range rather than eight regions'.
    """

    cidr: str
    asn: int | None = None
    org: str | None = None
    anonymous: bool = False
    org_suffix: str = "documentation network"


def _pools(cfg: dict[str, Any]) -> tuple[Pool, ...]:
    """Every pool an address in this world can come from, in the order the files list them."""
    world = cfg["world"]["ip_pools"]
    network = cfg["network"]["ip_pools"]
    return (
        Pool(world["ipv4"]),
        # A carrier NAT is what `behind_cgnat` models, so the class it enriches to is `mobile`.
        Pool(world["cgnat"], org_suffix="mobile carrier (documentation)"),
        Pool(world["ipv6"]),
        Pool(network["observer"]),
        Pool(network["tor_exit"], asn=cfg["network"]["tor_asn"], org=TOR_ORG, anonymous=True),
        Pool(network["vpn"], asn=cfg["network"]["vpn_asn"], org=VPN_ORG, anonymous=True),
    )


def _address(value: int, version: int) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """An address of the pool's own version. `ip_address(int)` guesses v4 and would be wrong."""
    return ipaddress.IPv6Address(value) if version == 6 else ipaddress.IPv4Address(value)


def region_cidrs(cidr: str, n_regions: int) -> list[list[str]]:
    """Each region's contiguous slice of `cidr`, as the fewest CIDRs that cover it.

    The partition `mayajaal.entities._ip` writes: region `r` owns
    `[base + r*block, base + (r+1)*block)` for `block = size // n_regions`. The last region also
    owns the remainder, because `region_of` clamps its answer to `n_regions - 1` and any address
    past the final whole block therefore reads back as the last region.

    A slice is only one CIDR when the pool divides into aligned power-of-two blocks, which is true
    of the pools this world ships with and is not guaranteed, so every slice is summarised.
    """
    net = ipaddress.ip_network(cidr)
    base, size, version = int(net.network_address), net.num_addresses, net.version
    block = size // n_regions
    if block < 1:
        raise ValueError(f"pool {cidr} holds {size} addresses, too few for {n_regions} regions")
    slices: list[list[str]] = []
    for region in range(n_regions):
        low = base + region * block
        high = base + size - 1 if region == n_regions - 1 else low + block - 1
        slices.append(
            [
                str(one)
                for one in ipaddress.summarize_address_range(
                    _address(low, version), _address(high, version)
                )
            ]
        )
    return slices


def _geonames(regions: Regions) -> dict[str, int]:
    """One id per distinct country, assigned in sorted order so the file is reproducible."""
    return {code: GEONAME_BASE + i for i, code in enumerate(sorted(set(regions.countries)))}


def rows(
    cfg: dict[str, Any], regions: Regions
) -> tuple[dict[int, list[tuple[str, ...]]], dict[int, list[tuple[str, ...]]]]:
    """The ASN and country block rows for every pool, keyed by IP version."""
    geonames = _geonames(regions)
    n_regions = len(regions)
    asn_rows: dict[int, list[tuple[str, ...]]] = {4: [], 6: []}
    country_rows: dict[int, list[tuple[str, ...]]] = {4: [], 6: []}
    for pool in _pools(cfg):
        version = ipaddress.ip_network(pool.cidr).version
        for region, nets in enumerate(region_cidrs(pool.cidr, n_regions)):
            country = regions.countries[region]
            asn = pool.asn if pool.asn is not None else regions.asns[region]
            org = pool.org if pool.org is not None else f"AS{asn} {country} {pool.org_suffix}"
            geoname = str(geonames[country])
            for one in nets:
                asn_rows[version].append((one, str(asn), org))
                country_rows[version].append(
                    (one, geoname, geoname, "", "1" if pool.anonymous else "0", "0")
                )
    return asn_rows, country_rows


def _write_csv(path: Path, columns: tuple[str, ...], body: list[tuple[str, ...]]) -> int:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(body)
    return len(body)


# A Tor pool larger than this is a configuration mistake rather than a list worth writing, and
# enumerating one would hang instead of failing. The shipped pool is a /24.
MAX_TOR_ADDRESSES = 65536


def _tor_addresses(cidr: str) -> list[str]:
    """Every address in the Tor pool.

    The whole pool rather than the exits one run happened to mint: which 40 of these a run used is
    a property of that run's seed, and reading it would make this generator depend on a run having
    happened. The pool is the Tor pool by definition, so enumerating it says nothing more than
    `run_config.json` already does.

    Every address, not `hosts()`. MAYAJAAL draws Tor exits with `randrange` over a region's whole
    slice, so it can and does mint the network and broadcast addresses, and a list that skipped
    them would leave those exits classified as `vpn_suspect`.
    """
    net = ipaddress.ip_network(cidr)
    if net.num_addresses > MAX_TOR_ADDRESSES:
        raise ValueError(
            f"tor_exit pool {cidr} holds {net.num_addresses} addresses; an exit list is a list of "
            f"addresses, so a pool above {MAX_TOR_ADDRESSES} needs a different representation"
        )
    return [str(one) for one in net]


def build(out: Path, cfg: dict[str, Any], regions: Regions) -> dict[str, int]:
    """Write the tree. Returns rows written per file, for the caller to report."""
    out.mkdir(parents=True, exist_ok=True)
    asn_rows, country_rows = rows(cfg, regions)
    written: dict[str, int] = {}
    for version in (4, 6):
        written[ASN_BLOCKS[version]] = _write_csv(
            out / ASN_BLOCKS[version], ASN_COLUMNS, asn_rows[version]
        )
        written[COUNTRY_BLOCKS[version]] = _write_csv(
            out / COUNTRY_BLOCKS[version], COUNTRY_COLUMNS, country_rows[version]
        )
    written[COUNTRY_LOCATIONS] = _write_csv(
        out / COUNTRY_LOCATIONS,
        LOCATION_COLUMNS,
        [
            (str(geoname), "en", "", "", code, code)
            for code, geoname in sorted(_geonames(regions).items())
        ],
    )
    exits = _tor_addresses(cfg["network"]["ip_pools"]["tor_exit"])
    (out / TOR_LIST).write_text("".join(f"{one}\n" for one in exits), encoding="utf-8")
    written[TOR_LIST] = len(exits)
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a vendor/ tree for the synthetic world.")
    parser.add_argument(
        "--out", type=Path, required=True, help="directory to write the vendor files into"
    )
    parser.add_argument("--config", type=Path, default=CONFIG, help="run configuration to read")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    regions = load_regions(Path(args.config).resolve().parent / cfg["network"]["latency_matrix"])

    out = Path(args.out).resolve()
    if out == VENDOR_ROOT:
        sys.stderr.write(
            "make_vendor_lists: writing into the repository's own vendor/ will turn "
            "`make verify-s04` red, because that gate asserts SETU's absent-vendor warnings and "
            "its null enrichment columns. Remove the directory again before running it.\n"
        )

    written = build(out, cfg, regions)
    for name in sorted(written):
        sys.stderr.write(f"  {name}: {written[name]} rows\n")
    sys.stderr.write(
        f"make_vendor_lists: {len(written)} files under {out}, "
        f"{len(regions)} regions over {len(_pools(cfg))} pools\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
