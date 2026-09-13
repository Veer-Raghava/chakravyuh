"""Geo, ASN and network class for a peer IP, from files in `vendor/` and nothing else.

Two things shape this module.

There is no MaxMind reader in the pinned dependencies and this sandbox cannot resolve a new
one, so the `.mmdb` binary format is not read. What is read is MaxMind's **CSV** distribution,
which carries the same data and needs only the standard library. An `.mmdb` with no CSV beside
it is recorded as a warning and enriches nothing, because a half-built binary parser would be a
worse answer than an honest null.

The lookup is per **distinct IP**, not per announcement. A capture of a million announcements
holds a few thousand peers, so a sorted list and `bisect` beat any dataframe interval join here
by enough that the join is not worth writing. `ipaddress` gives arbitrary-precision integers,
which is what makes one code path serve both IPv4 and IPv6.
"""

from __future__ import annotations

import csv
import ipaddress
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Final

VENDOR_ROOT: Final[str] = "vendor"

_COUNTRY_BLOCKS: Final[tuple[str, ...]] = (
    "GeoLite2-Country-Blocks-IPv4.csv",
    "GeoLite2-Country-Blocks-IPv6.csv",
)
_COUNTRY_LOCATIONS: Final[str] = "GeoLite2-Country-Locations-en.csv"
_ASN_BLOCKS: Final[tuple[str, ...]] = (
    "GeoLite2-ASN-Blocks-IPv4.csv",
    "GeoLite2-ASN-Blocks-IPv6.csv",
)
_TOR_LIST: Final[tuple[str, ...]] = ("exit-addresses.txt", "tor-exit-addresses.txt")

# Matched against a lowercased AS organisation. Order of the checks in `_classify` matters more
# than the contents: a VPN provider usually rents from a hosting AS, so the more specific claim
# is tested first. These are heuristics over a free-text field and they are wrong sometimes,
# which is why `net_class` is a hint downstream and never an assertion about a person.
_MOBILE: Final[tuple[str, ...]] = ("mobile", "cellular", "wireless", "gsm", "lte")
_VPN: Final[tuple[str, ...]] = (
    "vpn",
    "proxy",
    "privacy",
    "anonym",
    "tunnel",
    "mullvad",
    "private internet",
)
_HOSTING: Final[tuple[str, ...]] = (
    "hosting",
    "cloud",
    "data center",
    "datacenter",
    "data centre",
    "server",
    "vps",
    "dedicated",
    "colocation",
    "amazon",
    "google",
    "microsoft",
    "digitalocean",
    "ovh",
    "hetzner",
    "linode",
    "vultr",
    "alibaba",
    "oracle",
)


@dataclass(frozen=True, slots=True)
class PeerFacts:
    """What `vendor/` can say about one IP. Every field is null when it cannot say."""

    geo_country: str | None = None
    asn: int | None = None
    as_org: str | None = None
    net_class: str | None = None


@dataclass(frozen=True, slots=True)
class _Ranges:
    """Non-overlapping address ranges, sorted by their low end, split by IP version."""

    los: dict[int, list[int]]
    his: dict[int, list[int]]
    values: dict[int, list[tuple[object, object]]]

    def find(self, version: int, key: int) -> tuple[object, object] | None:
        los = self.los.get(version)
        if not los:
            return None
        index = bisect_right(los, key) - 1
        if index < 0 or key > self.his[version][index]:
            return None
        return self.values[version][index]


def _empty_ranges() -> _Ranges:
    return _Ranges(los={}, his={}, values={})


def _build_ranges(rows: list[tuple[str, tuple[object, object]]]) -> _Ranges:
    """Turn `(cidr, value)` pairs into version-split sorted range tables.

    Rows whose network does not parse are skipped rather than raised on: a vendored file is
    third-party data and one bad line in it must not take the pipeline down.
    """
    staged: dict[int, list[tuple[int, int, tuple[object, object]]]] = {}
    for cidr, value in rows:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        staged.setdefault(network.version, []).append(
            (int(network.network_address), int(network.broadcast_address), value)
        )
    los: dict[int, list[int]] = {}
    his: dict[int, list[int]] = {}
    values: dict[int, list[tuple[object, object]]] = {}
    for version, entries in staged.items():
        entries.sort(key=lambda entry: entry[0])
        los[version] = [entry[0] for entry in entries]
        his[version] = [entry[1] for entry in entries]
        values[version] = [entry[2] for entry in entries]
    return _Ranges(los=los, his=his, values=values)


def _find_files(root: Path, names: tuple[str, ...] | str) -> list[Path]:
    """Every file under `vendor/` with one of these names, in a stable order.

    A recursive search rather than a fixed path, because MaxMind's zip unpacks into a
    date-stamped directory and pinning the date would break on the next download.
    """
    wanted = (names,) if isinstance(names, str) else names
    found: list[Path] = []
    for name in wanted:
        found.extend(sorted(root.rglob(name)))
    return found


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_countries(root: Path, warnings: list[str]) -> _Ranges:
    locations = _find_files(root, _COUNTRY_LOCATIONS)
    blocks = _find_files(root, _COUNTRY_BLOCKS)
    if not blocks or not locations:
        return _empty_ranges()
    iso_by_geoname: dict[str, str] = {}
    for path in locations:
        for row in _read_csv(path):
            code = (row.get("country_iso_code") or "").strip()
            if code:
                iso_by_geoname[row["geoname_id"]] = code
    rows: list[tuple[str, tuple[object, object]]] = []
    for path in blocks:
        for row in _read_csv(path):
            geoname = row.get("geoname_id") or row.get("registered_country_geoname_id") or ""
            anonymous = (row.get("is_anonymous_proxy") or "0").strip() == "1"
            rows.append((row["network"], (iso_by_geoname.get(geoname), anonymous)))
    if not rows:
        warnings.append("geolite2_country_csv_empty")
    return _build_ranges(rows)


def _load_asns(root: Path, warnings: list[str]) -> _Ranges:
    blocks = _find_files(root, _ASN_BLOCKS)
    if not blocks:
        return _empty_ranges()
    rows: list[tuple[str, tuple[object, object]]] = []
    for path in blocks:
        for row in _read_csv(path):
            number = (row.get("autonomous_system_number") or "").strip()
            org = (row.get("autonomous_system_organization") or "").strip() or None
            rows.append((row["network"], (int(number) if number.isdigit() else None, org)))
    if not rows:
        warnings.append("geolite2_asn_csv_empty")
    return _build_ranges(rows)


def _load_tor(root: Path) -> frozenset[str]:
    """Every IP in a vendored Tor exit list, in normalised form.

    Accepts both the plain one-address-per-line list and Tor's own `ExitAddress <ip> <time>`
    format, by taking any whitespace token on a non-comment line that parses as an address.
    Normalising through `ip_address` is what makes `2001:db8::1` match `2001:0db8::0001`.
    """
    found: set[str] = set()
    for path in _find_files(root, _TOR_LIST):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#"):
                continue
            for token in line.split():
                try:
                    found.add(str(ipaddress.ip_address(token)))
                except ValueError:
                    continue
    return frozenset(found)


def _matches(org: str, needles: tuple[str, ...]) -> bool:
    return any(needle in org for needle in needles)


class Enricher:
    """Vendor lookups for one run. Construct once, call `lookup` per distinct IP.

    `available` is false when `vendor/` offered nothing usable. In that state every field of
    every result is null and the stage still completes, which is contract section 4's
    "null if unavailable" rather than a degraded guess.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.warnings: list[str] = []
        self._countries: _Ranges = _empty_ranges()
        self._asns: _Ranges = _empty_ranges()
        self._tor: frozenset[str] = frozenset()
        base = Path(root) if root is not None else Path.cwd() / VENDOR_ROOT
        if not base.is_dir():
            self.warnings.append("vendor_absent")
        else:
            self._countries = _load_countries(base, self.warnings)
            self._asns = _load_asns(base, self.warnings)
            self._tor = _load_tor(base)
            self._warn_absent(base)
        self.has_geo = bool(self._countries.los)
        self.has_asn = bool(self._asns.los)
        self.has_tor = bool(self._tor)
        self.available = self.has_geo or self.has_asn or self.has_tor

    def _warn_absent(self, base: Path) -> None:
        if not _find_files(base, _COUNTRY_BLOCKS) and not _find_files(base, _ASN_BLOCKS):
            self.warnings.append("geolite2_csv_absent")
            if _find_files(base, "*.mmdb"):
                # Recorded loudly: the operator has the data and would otherwise assume it was
                # in use. Reading it needs a MaxMind library this project cannot install.
                self.warnings.append("geolite2_mmdb_present_but_unreadable_csv_required")
        if not self._tor:
            self.warnings.append("tor_exit_list_absent")

    def lookup(self, ip: str) -> PeerFacts:
        """Country, ASN, organisation and network class for one address."""
        if not self.available:
            return PeerFacts()
        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            return PeerFacts()
        key, version = int(parsed), parsed.version

        country: str | None = None
        anonymous = False
        found = self._countries.find(version, key)
        if found is not None:
            country, anonymous = found  # type: ignore[assignment]

        asn: int | None = None
        as_org: str | None = None
        found = self._asns.find(version, key)
        if found is not None:
            asn, as_org = found  # type: ignore[assignment]

        return PeerFacts(
            geo_country=country,
            asn=asn,
            as_org=as_org,
            net_class=self._classify(str(parsed), as_org, anonymous),
        )

    def _classify(self, ip: str, as_org: str | None, anonymous: bool) -> str | None:
        """Contract section 4's vocabulary, or null when nothing could classify at all.

        Null and `unknown` are different answers. Null means no list was available to ask.
        `unknown` means the lists were there and none of them recognised this address, which
        is a fact about the address rather than about the deployment.
        """
        if self.has_tor and ip in self._tor:
            return "tor_exit"
        if not self.has_asn:
            return "unknown" if self.has_geo or self.has_tor else None
        if anonymous:
            return "vpn_suspect"
        if as_org is None:
            return "unknown"
        org = as_org.lower()
        if _matches(org, _VPN):
            return "vpn_suspect"
        if _matches(org, _MOBILE):
            return "mobile"
        if _matches(org, _HOSTING):
            return "hosting"
        return "residential"
