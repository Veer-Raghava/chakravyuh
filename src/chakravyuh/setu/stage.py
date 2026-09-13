"""SETU as a stage: read `sealed/`, write `normalised/`, account for every row.

The path guards are KAVACH's, restated rather than imported. No stage imports another stage's
internals, and the rule pays for itself here: `--in` is allowlisted to `data/`, so a SETU
invocation cannot be pointed at the answer key even by an operator who wants to, because the
answer key is a sibling tree and not under `data/`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.setu import normalise, schema
from chakravyuh.setu.enrich import Enricher

INPUT_ROOT: Final[str] = "data"
OUTPUT_ROOT: Final[str] = "data/generated"
ROWS_FILE: Final[str] = "rows.parquet"
OUT_DIR: Final[str] = "normalised"


class InputPathError(ValueError):
    """A path SETU will not read from, or will not write to."""


def _relative_to_cwd(path: Path, root: str) -> Path:
    """`path` resolved, refused unless it sits inside `<cwd>/<root>`."""
    base = (Path.cwd() / root).resolve()
    resolved = path.resolve()
    if resolved != base and base not in resolved.parents:
        raise InputPathError(
            f"{path} resolves outside {base}. SETU only reads and writes inside that directory, "
            f"which is how a stage input can never reach a sibling tree it has no business in."
        )
    return resolved


def resolve_in(target: Path) -> Path:
    """The `sealed/` directory to normalise."""
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    if not (resolved / ROWS_FILE).is_file():
        raise InputPathError(
            f"{target} holds no {ROWS_FILE}. SETU reads a sealed/ directory written by KAVACH: "
            f"run `python -m chakravyuh.kavach --in <capture> --out <run>` first."
        )
    return resolved


def resolve_out(target: Path) -> Path:
    """The run directory to write `normalised/` into."""
    resolved = _relative_to_cwd(target, OUTPUT_ROOT)
    if resolved == (Path.cwd() / OUTPUT_ROOT).resolve():
        raise InputPathError(
            f"--out must name a run directory inside {OUTPUT_ROOT}/, not {OUTPUT_ROOT}/ itself"
        )
    return resolved


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _write_parquet(frame: pl.DataFrame, path: Path) -> str:
    """Write, then hash what was written. Compression is pinned so two runs agree byte for byte."""
    frame.write_parquet(path, compression="zstd", compression_level=3, statistics=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _upstream_meta(sealed: Path) -> tuple[str | None, str | None]:
    """The staleness link: `sealed/_meta.json` as a repo-relative path and a hash.

    Recorded so `scripts/check_stage.py` can fail when the upstream moves after this ran. Null
    for a sealed directory with no `_meta.json`, which only happens in a hand-built fixture.
    """
    candidate = sealed / "_meta.json"
    if not candidate.is_file():
        return None, None
    return _repo_relative(candidate), hashlib.sha256(candidate.read_bytes()).hexdigest()


def normalise_run(sealed: Path, out: Path, vendor: Path | None = None) -> Path:
    """Normalise `sealed/` into `<out>/normalised/`. Returns the path to `_meta.json`.

    `sealed` and `out` are already resolved and guarded by the caller. `vendor` overrides the
    enrichment root, which is what lets a test exercise the populated path without a download.
    """
    started_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    rows = pl.read_parquet(sealed / ROWS_FILE)

    enricher = Enricher(vendor)
    base = normalise.base_announcements(rows)
    facts = normalise.peer_facts(sorted(base["peer_ip"].unique().to_list()), enricher)
    peer_table = normalise.peers(base, facts)
    announcement_table = normalise.announcements(base, peer_table)
    transaction_table = normalise.transactions(rows)
    address_table = normalise.addresses(transaction_table, normalise.declared_script_types(rows))

    tables = {
        "announcements.parquet": announcement_table,
        "transactions.parquet": transaction_table,
        "addresses.parquet": address_table,
        "peers.parquet": peer_table,
    }
    out_dir = out / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {name: _write_parquet(frame, out_dir / name) for name, frame in tables.items()}

    warnings = list(enricher.warnings)
    if not enricher.available:
        # The demo-killing case the brief names, made visible rather than silent: every geo,
        # ASN and net_class column in this run is null because no vendored list was found.
        warnings.append("enrichment_unavailable_geo_asn_net_class_are_null")

    upstream_path, upstream_hash = _upstream_meta(sealed)
    if upstream_hash is None:
        warnings.append("upstream_meta_absent_no_staleness_link")

    finished_at_us = int(datetime.now(tz=UTC).timestamp() * 1_000_000)
    meta = {
        "stage": schema.STAGE,
        "run_id": out.name,
        "started_at_us": started_at_us,
        "finished_at_us": finished_at_us,
        "code_version": buildinfo.code_version(),
        "seed": 0,
        "params": {
            "input": _repo_relative(sealed),
            "upstream_meta": {"path": upstream_path, "sha256": upstream_hash},
            "vendor_root": _repo_relative(vendor) if vendor is not None else "vendor",
            "enrichment": {
                "geolite2_country": enricher.has_geo,
                "geolite2_asn": enricher.has_asn,
                "tor_exit_list": enricher.has_tor,
            },
            "change_index_rule": "sole_non_round_output_not_paying_an_input_address",
            "change_index_round_sats": normalise.ROUND_SATS,
        },
        "inputs": [
            {
                "path": _repo_relative(sealed / ROWS_FILE),
                "sha256": hashlib.sha256((sealed / ROWS_FILE).read_bytes()).hexdigest(),
                "rows": rows.height,
            }
        ],
        "outputs": [
            {"path": f"{OUT_DIR}/{name}", "sha256": hashes[name], "rows": tables[name].height}
            for name in sorted(tables)
        ],
        # SETU reshapes and never rejects: a row that survived the seal is an announcement, and
        # there is no second opinion to have about it here. `dropped` is structurally zero, so
        # `counts.in == counts.out` is the whole of contract section 10 for this stage.
        "counts": {
            "in": rows.height,
            "out": announcement_table.height,
            "dropped": 0,
            "drop_reasons": {},
        },
        "warnings": warnings,
        "optional_deps": {
            "geolite2": enricher.has_geo or enricher.has_asn,
            "kuzu": False,
            "gpu": False,
        },
    }
    meta_path = out_dir / "_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if rows.height != announcement_table.height:
        raise AssertionError(
            f"read {rows.height} sealed rows and wrote {announcement_table.height} "
            "announcements. The grain split must preserve the announcement count exactly."
        )
    return meta_path
