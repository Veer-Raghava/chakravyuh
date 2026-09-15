"""The plain-English gloss of a model feature name, read from `docs/FEATURES.md`.

Never show a raw column name in an alert: the gloss table is the map from what the model
saw to what an analyst reads. The table is parsed from the same markdown the S07 gate
validates `top_features` against, so the two cannot drift apart, and a name missing from
the table raises rather than rendering a bare identifier into prose.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

FEATURES_PATH: Final[str] = "docs/FEATURES.md"
_ROW: Final[re.Pattern[str]] = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(.+?)\s*\|\s*$")

# The checkout this module was imported from: the table is a repo document, not run data, so
# a stage run from any working directory still reads the same glosses.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]


def default_path() -> Path:
    """Where the gloss table lives: the working directory's copy if present, else the repo's."""
    for base in (Path.cwd(), _REPO_ROOT):
        candidate = base / FEATURES_PATH
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"no gloss table at {FEATURES_PATH} in the working directory or the checkout; "
        f"VAANI cannot name features in prose without it."
    )


def load_glosses(path: Path) -> dict[str, str]:
    """Feature name to its plain-English phrase, from the markdown table's second column."""
    glosses: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := _ROW.match(line):
            glosses[match.group(1)] = match.group(2)
    if not glosses:
        raise ValueError(f"{path} holds no feature glosses; VAANI cannot name features in prose")
    return glosses


def gloss(glosses: dict[str, str], name: str) -> str:
    """The phrase for one feature name. Raises rather than rendering a raw column name."""
    try:
        return glosses[name]
    except KeyError as exc:
        raise ValueError(
            f"feature {name!r} is not glossed in {FEATURES_PATH}; showing a raw column name "
            f"in an alert is forbidden. Add the gloss first."
        ) from exc
