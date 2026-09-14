"""Registers which tests belong to the quarantine gate, and proves the list still resolves.

The marker is applied here rather than as a decorator for one reason: `tests/test_contracts.py`
is stdlib-only on purpose, so that the guard the whole quarantine rests on can be run under a
bare interpreter with no pytest installed. Importing pytest there to hang a decorator on three
functions would trade that away.

Marking by name introduces its own failure: rename a test and it silently leaves the gate. So
every registered name must be collected whenever its file is collected, or the run is a usage
error. `make verify-quarantine` adds a count floor on top, which catches the case where the
marker itself is renamed or the registry is emptied.
"""

from __future__ import annotations

import pytest

QUARANTINE: dict[str, tuple[str, ...]] = {
    "test_contracts": (
        "test_no_src_module_reaches_for_ground_truth",
        "test_the_ground_truth_writer_never_reads",
        "test_no_ground_truth_column_name_appears_in_an_observable_fixture",
    ),
    "test_chain": ("test_no_observable_artifact_names_the_quarantine",),
    "test_network": ("test_no_capture_encoding_names_a_ground_truth_column",),
    "test_kavach": (
        "test_kavach_seals_with_the_answer_key_absent",
        "test_no_sealed_artifact_names_the_quarantine",
    ),
    "test_setu": (
        "test_setu_normalises_with_the_answer_key_absent",
        "test_no_normalised_artifact_names_the_quarantine",
    ),
    "test_jaal": (
        "test_jaal_builds_with_the_answer_key_absent",
        "test_no_graph_artifact_names_the_quarantine",
    ),
}


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """`tryfirst` so the marks exist before pytest's own `-m` filtering deselects on them."""
    seen: dict[str, set[str]] = {}
    for item in items:
        stem = item.path.stem
        if stem not in QUARANTINE:
            continue
        name = getattr(item, "originalname", None) or item.name
        seen.setdefault(stem, set()).add(name)
        if name in QUARANTINE[stem]:
            item.add_marker(pytest.mark.quarantine)

    for stem, names in QUARANTINE.items():
        if stem not in seen:
            continue
        missing = sorted(set(names) - seen[stem])
        if missing:
            raise pytest.UsageError(
                f"tests/conftest.py registers quarantine tests that no longer exist in "
                f"{stem}.py: {', '.join(missing)}. A renamed test drops out of "
                f"`make verify-quarantine` without failing anything, so fix the registry."
            )
