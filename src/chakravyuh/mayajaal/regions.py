"""Read `regions.yaml`: the region table and the region-to-region latency matrix.

Deliberately a strict parser for a small subset of YAML rather than PyYAML. PyYAML is not
installed and pypi is unreachable in the build sandbox, so a dependency here would make the
whole stage unbuildable. The subset is a section header at column zero and one two-space
indented `key: {inline flow mapping}` entry per line, which is valid YAML, so nothing stops
a real parser reading the same file later.

Latency is stored in microseconds, because every other time in this pipeline is integer
microseconds and converting at the boundary once is cheaper than converting at every use.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from . import weighted
from .weighted import WeightedIndex

_INDENT = "  "


def _scalar(text: str, where: str) -> int | float | str:
    """Ints stay ints. A float that happens to be whole is not silently narrowed."""
    body = text.strip()
    if not body:
        raise ValueError(f"regions.yaml: empty value at {where}")
    if body[0] in "\"'" and body[-1] == body[0]:
        return body[1:-1]
    try:
        return int(body)
    except ValueError:
        pass
    try:
        return float(body)
    except ValueError:
        return body


def _flow(text: str, where: str) -> dict[str, int | float | str]:
    body = text.strip()
    if not (body.startswith("{") and body.endswith("}")):
        raise ValueError(f"regions.yaml: {where} must be an inline `{{a: 1, b: 2}}` mapping")
    out: dict[str, int | float | str] = {}
    for part in body[1:-1].split(","):
        if not part.strip():
            continue
        key, sep, value = part.partition(":")
        if not sep:
            raise ValueError(f"regions.yaml: {where} has an entry with no colon: {part!r}")
        out[key.strip()] = _scalar(value, f"{where}.{key.strip()}")
    if not out:
        raise ValueError(f"regions.yaml: {where} is an empty mapping")
    return out


def parse(text: str) -> dict[str, dict[str, dict[str, int | float | str]]]:
    """Sections of two-space-indented entries. Comments must occupy a whole line.

    Trailing comments are rejected rather than stripped: a `#` inside a value is legal YAML
    and a stripper that did not know the difference would silently truncate one.
    """
    sections: dict[str, dict[str, dict[str, int | float | str]]] = {}
    current: str | None = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(_INDENT):
            name, sep, rest = line.partition(":")
            if not sep or rest.strip():
                raise ValueError(f"regions.yaml:{number}: expected a `section:` header")
            current = name.strip()
            sections[current] = {}
            continue
        if current is None:
            raise ValueError(f"regions.yaml:{number}: entry before any section header")
        key, sep, rest = line.strip().partition(":")
        if not sep:
            raise ValueError(f"regions.yaml:{number}: expected `key: value`")
        sections[current][key.strip()] = _flow(rest, f"{current}.{key.strip()}")
    return sections


@dataclass(frozen=True, slots=True)
class Regions:
    """The region table, indexed by position. Index, not name, is what the hot loops carry."""

    names: tuple[str, ...]
    shares: tuple[float, ...]
    countries: tuple[str, ...]
    asns: tuple[int, ...]
    jitter_us: tuple[int, ...]
    latency_us: tuple[tuple[int, ...], ...]

    def __len__(self) -> int:
        return len(self.names)

    def index(self, name: str) -> int:
        return self.names.index(name)

    def picker(self) -> WeightedIndex[int]:
        """A share-weighted index over region positions, for placing an entity."""
        return weighted.build(enumerate(self.shares))

    def link_us(self, source: int, target: int, rng: random.Random) -> int:
        """One-way delay for a single hop: base latency plus jitter from the sending region.

        Jitter is symmetric around zero and clamped so a link can never travel backwards in
        time. It is drawn per call rather than stored per link, because a real link's delay
        varies between packets and a fixed per-link offset would let a downstream model learn
        the topology from timing alone.
        """
        base = self.latency_us[source][target]
        spread = self.jitter_us[source]
        return max(1, base + int(rng.gauss(0.0, spread)))


def _number(node: dict[str, int | float | str], key: str, where: str) -> float:
    value = node.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"regions.yaml: {where}.{key} must be a number, got {value!r}")
    return float(value)


def load(path: Path) -> Regions:
    """Parse and validate. Every check here is a typo this file is easy to make."""
    sections = parse(path.read_text(encoding="utf-8"))
    for name in ("regions", "latency_ms"):
        if name not in sections:
            raise ValueError(f"regions.yaml: missing `{name}:` section")
    table = sections["regions"]
    matrix = sections["latency_ms"]
    names = tuple(table)
    if len(names) < 2:
        raise ValueError("regions.yaml: needs at least two regions to have a latency matrix")

    shares = tuple(_number(table[n], "share", f"regions.{n}") for n in names)
    total = sum(shares)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"regions.yaml: region shares must sum to 1.0, got {total}")

    countries: list[str] = []
    asns: list[int] = []
    jitter: list[int] = []
    for name in names:
        country = table[name].get("country")
        if not isinstance(country, str) or len(country) != 2 or not country.isupper():
            raise ValueError(f"regions.yaml: regions.{name}.country must be a 2-letter code")
        countries.append(country)
        asns.append(int(_number(table[name], "asn", f"regions.{name}")))
        jitter.append(round(_number(table[name], "jitter_ms", f"regions.{name}") * 1000))

    if set(matrix) != set(names):
        raise ValueError("regions.yaml: latency_ms must have exactly one row per region")
    rows: list[tuple[int, ...]] = []
    for source in names:
        row = matrix[source]
        if set(row) != set(names):
            raise ValueError(f"regions.yaml: latency_ms.{source} must name every region")
        values: list[int] = []
        for target in names:
            millis = _number(row, target, f"latency_ms.{source}")
            if millis <= 0.0:
                raise ValueError(f"regions.yaml: latency_ms.{source}.{target} must be positive")
            values.append(round(millis * 1000))
        rows.append(tuple(values))
    for i, source in enumerate(names):
        for j, target in enumerate(names):
            if rows[i][j] != rows[j][i]:
                raise ValueError(
                    f"regions.yaml: latency_ms is asymmetric at {source}/{target}: "
                    f"{rows[i][j]} != {rows[j][i]}"
                )
    return Regions(
        names=names,
        shares=shares,
        countries=tuple(countries),
        asns=tuple(asns),
        jitter_us=tuple(jitter),
        latency_us=tuple(rows),
    )
