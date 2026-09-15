"""PRAMAAN as a stage: read the run, write `packets/<case_id>/`, append the Merkle log.

The path guards are VAANI's, restated rather than imported: `--in` and `--out` resolve
under `data/generated/` only, so no invocation can point the stage at a sibling tree.

The signing key lives in `keys/` at the repository root, which `.gitignore` already
excludes. `--generate-keys` creates the pair when absent; the seed never crosses a log
line, an exception message, or the packet — only the signature ever proves it was used.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import polars as pl

from chakravyuh import buildinfo
from chakravyuh.pramaan import documents, merkle
from chakravyuh.pramaan import packet as packet_mod
from chakravyuh.pramaan.ed25519 import generate_seed, public_key, sign
from chakravyuh.vaani.stage import InputPathError as InputPathError  # re-exported guard
from chakravyuh.vaani.stage import _relative_to_cwd  # the shared guard shape

INPUT_ROOT: Final[str] = "data/generated"
PACKETS_DIR: Final[str] = "packets"
ALERTS_DIR: Final[str] = "alerts"
KEYS_DIR: Final[str] = "keys"
SEED_FILE: Final[str] = "ed25519.seed"
PUB_FILE: Final[str] = "ed25519.pub"
LOG_NAME: Final[str] = "merkle.log"

STAGES: Final[tuple[str, ...]] = (
    "sealed",
    "normalised",
    "graph",
    "signals",
    "scores",
    "alerts",
)


def resolve_in(target: Path) -> Path:
    """The run directory holding the upstream stages' outputs and `_meta.json` files."""
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    missing = [name for name in STAGES if not (resolved / name / "_meta.json").is_file()]
    if missing:
        raise InputPathError(
            f"{target} is missing {', '.join(missing)} under it. PRAMAAN reads a run "
            f"written through KAVACH, SETU, JAAL, SHASTRA, BUDDHI and VAANI: run those "
            f"stages first."
        )
    return resolved


def resolve_out(target: Path) -> Path:
    """The run directory to write `packets/` into."""
    resolved = _relative_to_cwd(target, INPUT_ROOT)
    if resolved == (Path.cwd() / INPUT_ROOT).resolve():
        raise InputPathError(
            f"--out must name a run directory inside {INPUT_ROOT}/, not {INPUT_ROOT}/ itself"
        )
    return resolved


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


class KeyMaterial:
    """The signing seed and the public key, loaded once. The seed never leaves this object
    except to `sign`; it is never formatted into a string."""

    def __init__(self, seed: bytes) -> None:
        self._seed = seed
        self.public = public_key(seed)

    def sign(self, message: bytes) -> bytes:
        return sign(self._seed, message)


def load_or_create_keys(repo_root: Path) -> KeyMaterial:
    """Load `keys/<seed file>`, or generate the pair on first use. Gitignored, local."""
    keys_dir = repo_root / KEYS_DIR
    seed_path = keys_dir / SEED_FILE
    if seed_path.is_file():
        seed = seed_path.read_bytes()
        if len(seed) != 32:
            raise InputPathError(f"{seed_path} does not hold a 32-byte key seed")
    else:
        seed = generate_seed()
        keys_dir.mkdir(parents=True, exist_ok=True)
        seed_path.write_bytes(seed)
    pub_path = keys_dir / PUB_FILE
    if not pub_path.is_file():
        keys_dir.mkdir(parents=True, exist_ok=True)
        pub_path.write_bytes(public_key(seed))
    return KeyMaterial(seed)


def build_run(
    run_dir: Path,
    out: Path,
    case: str | None,
    keys: KeyMaterial,
    repo_root: Path,
) -> list[Path]:
    """Generate packets for one case, or for every alert when `case` is None.

    Returns the case directories written. The Merkle log at `packets/merkle.log` is
    appended once per packet, and the new head goes to stdout, which the contract
    reserves for exactly this.
    """
    packets_dir = out / PACKETS_DIR
    packets_dir.mkdir(parents=True, exist_ok=True)
    log_path = packets_dir / LOG_NAME

    if case is not None:
        packet_mod.resolve_case(case, run_dir / "alerts")
        cases = [case]
    else:
        alerts = pl.read_parquet(run_dir / "alerts" / "alerts.parquet", columns=["alert_id"])
        cases = sorted(alerts["alert_id"].to_list())

    seed = _seed(run_dir)
    written: list[Path] = []
    for alert_id in cases:
        replay_command = (
            f"uv run python -m chakravyuh.pramaan --in {_repo_relative(run_dir)} "
            f"--out {_repo_relative(out)} --case {alert_id} --verify-replay"
        )
        packet = packet_mod.build(run_dir, alert_id, seed=seed, replay_command=replay_command)
        canonical = packet_mod.packet_bytes(packet)
        if not packet_mod.verify_replay_field(packet):
            raise InputPathError(
                "the replay digest does not recompute; refusing to write a claim that "
                "cannot be verified"
            )

        case_dir = packets_dir / alert_id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "packet.json").write_bytes(canonical)
        (case_dir / "packet.pdf").write_bytes(documents.packet_pdf(packet))
        (case_dir / "notice.pdf").write_bytes(documents.notice_pdf(packet))
        signature = keys.sign(canonical)
        (case_dir / "packet.sig").write_bytes(signature)
        # Section 9 puts a merkle.log in the case directory too; the authoritative chain
        # is the shared one, so this copy is written fresh each generation, byte-identical
        # to the shared log's prefix for this leaf's position.
        _write_case_log_copy(log_path, case_dir / LOG_NAME)

        head = merkle.append(log_path, canonical)
        sys.stdout.write(f"pramaan: packet {alert_id} signed, merkle head {head}\n")
        written.append(case_dir)

    _write_meta(out, packets_dir, log_path, len(cases), seed)
    return written


def _write_case_log_copy(log_path: Path, target: Path) -> None:
    """The case-local snapshot of the log, as section 9's directory listing describes."""
    if log_path.is_file():
        target.write_bytes(log_path.read_bytes())
    else:
        target.write_bytes(b"")


def verify_signature(case_dir: Path, keys_dir: Path) -> bool:
    """Verify one case's `packet.sig` over its `packet.json` with the public key on disk."""
    from chakravyuh.pramaan.ed25519 import verify

    packet_bytes = (case_dir / "packet.json").read_bytes()
    signature = (case_dir / "packet.sig").read_bytes()
    pub = (keys_dir / PUB_FILE).read_bytes()
    return verify(pub, packet_bytes, signature)


def verify_replay(run_dir: Path, out: Path, case: str, repo_root: Path) -> bool:
    """Rebuild the packet from the run and compare, byte for byte.

    Two checks, both of which must hold for the packet to be evidence rather than a
    screenshot: the rebuilt `packet.json` is byte-identical to the stored one, and the
    recorded replay digest recomputes over the canonical bytes with the field blanked.
    """
    case_dir = out / PACKETS_DIR / case
    if not (case_dir / "packet.json").is_file():
        raise InputPathError(f"{case_dir} holds no packet.json to replay")
    stored = (case_dir / "packet.json").read_bytes()
    seed = _seed(run_dir)
    replay_command = (
        f"uv run python -m chakravyuh.pramaan --in {_repo_relative(run_dir)} "
        f"--out {_repo_relative(out)} --case {case} --verify-replay"
    )
    rebuilt = packet_mod.build(run_dir, case, seed=seed, replay_command=replay_command)
    if packet_mod.packet_bytes(rebuilt) != stored:
        return False
    return packet_mod.verify_replay_field(json.loads(stored.decode("utf-8")))


def _seed(run_dir: Path) -> int:
    """The run's seed, from `config.effective.json`; 0 when the run records none."""
    path = run_dir / "config.effective.json"
    if not path.is_file():
        return 0
    return int(json.loads(path.read_text(encoding="utf-8")).get("seed", 0))


def _write_meta(out: Path, packets_dir: Path, log_path: Path, n_cases: int, seed: int) -> None:
    """`packets/_meta.json` per contract section 10.

    Counts grain: one alert in, one packet out. The Merkle log is not listed as an output
    because it is append-only history across generations, not this run's product; its
    head is recorded in params instead.
    """
    _leaves, prevs = merkle.read(log_path)
    head = merkle.root_of(_leaves)
    meta: dict[str, Any] = {
        "stage": "pramaan",
        "run_id": out.name,
        "started_at_us": int(datetime.now(tz=UTC).timestamp() * 1_000_000),
        "finished_at_us": int(datetime.now(tz=UTC).timestamp() * 1_000_000),
        "code_version": buildinfo.code_version(),
        "seed": seed,
        "params": {
            "input": _repo_relative(out),
            "cases": n_cases,
            "merkle_head": head,
            "merkle_leaves": len(_leaves),
            "identifier_policy": (
                "packet.json carries contract fields whole (section 9's machine artifact); "
                "every PDF renders identifiers truncated through vaani.redact"
            ),
            # check_stage.py reads this to verify the run's own staleness link.
            "upstream_meta": {
                "path": _repo_relative(out / ALERTS_DIR / "_meta.json"),
                "sha256": hashlib.sha256(
                    (out / ALERTS_DIR / "_meta.json").read_bytes()
                ).hexdigest(),
            },
        },
        "inputs": [
            {
                "path": _repo_relative(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rows": 0,
            }
            for path in sorted((out / ALERTS_DIR).iterdir())
            if path.is_file() and path.name != "_meta.json"
        ],
        "outputs": [
            {
                "path": f"{PACKETS_DIR}/{path.name}/packet.json",
                "sha256": hashlib.sha256((path / "packet.json").read_bytes()).hexdigest(),
                "rows": 1,
            }
            for path in sorted(packets_dir.iterdir())
            if (path / "packet.json").is_file()
        ],
        "counts": {"in": n_cases, "out": n_cases, "dropped": 0, "drop_reasons": {}},
        "warnings": [],
        "optional_deps": {"geolite2": False, "kuzu": False, "gpu": False},
    }
    (packets_dir / "_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def git_root() -> Path:
    """The repository root, for `keys/`. git's own answer, else the package's parents."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if done.returncode == 0:
            return Path(done.stdout.strip())
    except OSError:
        pass
    return Path(__file__).resolve().parents[3]
