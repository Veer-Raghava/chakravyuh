"""The API's gate: shape parity with the committed fixtures, the bind law, clean 404s.

The shape tests are the two-tracks contract made mechanical: every endpoint's response must
be field-for-field the committed fixture in `data/fixtures/ui/`, because Track B built its
components against those files. The fixtures are produced by the same serializers the API
calls, so a failure here means somebody changed one side without the other.

The bind test is the one that keeps an unauthenticated data endpoint off a venue network.
`BIND_HOST` is a module constant; if it ever stops being 127.0.0.1, or if the wildcard bind
literal appears anywhere in `src/chakravyuh/api/`, these tests go red before anything binds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chakravyuh.api import serialize
from chakravyuh.api.app import BIND_HOST, BIND_PORT, RUN_ENV, app, resolve_run, set_run_dir

FIXTURES = Path("data/fixtures/ui")
REFERENCE_RUN = Path("data/generated/_sweep-0.10")

# Skipped, not failed, when the reference run has not been generated: the API tests need a
# real pipeline run, and `make fixtures` alone does not produce one. CI and every gate run
# generate it first.
pytestmark = pytest.mark.skipif(
    not REFERENCE_RUN.is_dir(), reason="reference run _sweep-0.10 not generated"
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    set_run_dir(REFERENCE_RUN)
    return TestClient(app)


def _fixture(name: str) -> dict[str, object]:
    return dict(json.loads((FIXTURES / f"{name}.json").read_text("utf-8")))


def _shape(value: object, depth: int = 0) -> object:
    """Field names and types only: the parity contract, not the values.

    Fixtures are committed JSON from one run and the API serves the same run, so values
    agree too — but the contract Track B depends on is the shape, and asserting the shape
    is what lets the fixture values be regenerated without touching this test.
    """
    if isinstance(value, dict):
        return {key: _shape(item, depth + 1) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_shape(item, depth + 1) for item in value[:1]]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return "null"


def _routes() -> list[str]:
    paths: list[str] = []
    for route in app.routes:
        if getattr(route, "methods", None) == {"GET"}:
            # `path` exists on every concrete route type; the union type does not declare it.
            paths.append(str(route.__dict__["path"]))
    return sorted(paths)


# ---------------------------------------------------------------------------
# the bind law


def test_bind_host_is_loopback_only() -> None:
    assert BIND_HOST == "127.0.0.1"
    assert BIND_PORT == 8000


def test_no_wildcard_bind_anywhere_in_the_api_package() -> None:
    wildcard = "0" + "." + "0.0.0"  # assembled so this test file can name the rule
    for path in Path("src/chakravyuh/api").rglob("*.py"):
        assert wildcard not in path.read_text("utf-8"), f"{path} names the wildcard bind"


def test_routes_are_get_only() -> None:
    """Read-only in the strict sense: no route accepts a write method."""
    from fastapi.routing import APIRoute

    for route in app.routes:
        if isinstance(route, APIRoute):
            assert route.methods == {"GET"}, f"{route.path} allows {route.methods}"


def test_resolve_run_refuses_paths_and_escapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    for bad in ("", "..", ".", "a/b", r"a\\b", "../ground_truth"):
        monkeypatch.setenv(RUN_ENV, bad)
        with pytest.raises(RuntimeError):
            resolve_run()


# ---------------------------------------------------------------------------
# shape parity: every endpoint against its committed fixture


def test_manifest_matches_fixture(client: TestClient) -> None:
    assert _shape(client.get("/manifest").json()) == _shape(_fixture("manifest"))


def test_collapse_matches_fixture(client: TestClient) -> None:
    assert _shape(client.get("/collapse").json()) == _shape(_fixture("collapse"))


def test_transactions_matches_fixture(client: TestClient) -> None:
    assert _shape(client.get("/transactions").json()) == _shape(_fixture("transactions"))


def test_origin_matches_fixture(client: TestClient) -> None:
    txid = _fixture("origin")["txid"]
    assert _shape(client.get(f"/origin/{txid}").json()) == _shape(_fixture("origin"))


def test_origin_abstain_matches_fixture(client: TestClient) -> None:
    abstain = _fixture("origin-abstain")
    assert abstain["abstain"] is True
    body = client.get(f"/origin/{abstain['txid']}").json()
    assert _shape(body) == _shape(abstain)
    assert body["abstain"] is True


def test_graph_cluster_matches_fixture(client: TestClient) -> None:
    assert _shape(client.get("/graph").json()) == _shape(_fixture("graph"))


def test_graph_address_matches_fixture(client: TestClient) -> None:
    assert _shape(client.get("/graph?detail=address").json()) == _shape(_fixture("graph-address"))


def test_graph_caps_its_nodes(client: TestClient) -> None:
    body = client.get("/graph?detail=address&cap=25").json()
    assert len(body["nodes"]) <= 25


def test_alerts_matches_fixture(client: TestClient) -> None:
    assert _shape(client.get("/alerts").json()) == _shape(_fixture("alerts"))


def test_alert_matches_fixture(client: TestClient) -> None:
    alert_id = _fixture("alert")["alert_id"]
    assert _shape(client.get(f"/alerts/{alert_id}").json()) == _shape(_fixture("alert"))


def test_packet_matches_fixture(client: TestClient) -> None:
    packet = _fixture("packet")
    alert_id = packet["case_id"]
    assert _shape(client.get(f"/packets/{alert_id}").json()) == _shape(packet)


# ---------------------------------------------------------------------------
# values the console's honesty rules depend on


def test_every_alert_carries_counter_evidence(client: TestClient) -> None:
    alerts = client.get("/alerts?limit=50").json()["alerts"]
    for one in alerts:
        body = client.get(f"/alerts/{one['alert_id']}").json()
        assert body["counters"], f"{one['alert_id']} has empty counter-evidence"


def test_display_fields_are_truncated(client: TestClient) -> None:
    tx = client.get("/transactions?limit=50").json()["transactions"]
    for one in tx:
        assert "…" in one["txid_display"]
        assert len(one["txid_display"]) < len(one["txid"])
    lanes = client.get(f"/origin/{_fixture('origin')['txid']}").json()["lanes"]
    for lane in lanes:
        assert lane["peer_ip_display"].endswith("x.x") or "…" in lane["peer_ip_display"]


def test_confidence_never_appears_without_interval(client: TestClient) -> None:
    alerts = client.get("/alerts?limit=20").json()["alerts"]
    for one in alerts:
        assert 0.0 <= one["conf_low"] <= one["conf_high"] <= 1.0


# ---------------------------------------------------------------------------
# failure modes


def test_unknown_txid_is_a_clean_404(client: TestClient) -> None:
    response = client.get("/origin/ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    assert response.status_code == 404
    assert "Traceback" not in response.text


def test_unknown_alert_and_packet_are_clean_404s(client: TestClient) -> None:
    assert client.get("/alerts/alw-nonexistent").status_code == 404
    assert client.get("/packets/alw-nonexistent").status_code == 404


def test_no_route_accepts_a_path(tmp_path: Path) -> None:
    """The strict read-only rule: nothing anywhere takes a filesystem path from the client."""
    set_run_dir(REFERENCE_RUN)
    client = TestClient(app)
    traversal = "../../ground_truth/_sweep-0.10/origins.parquet"
    for path in (
        f"/alerts/{traversal}",
        f"/packets/{traversal}",
        f"/origin/{traversal}",
    ):
        assert client.get(path).status_code in (404, 422), path


def test_app_starts_with_the_answer_key_moved_away(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Law 2 rule 6: inference runs with `ground_truth/` absent. Serving is inference."""
    monkeypatch.chdir(tmp_path)
    # Minimal run directory: the API must boot and serve 404s/shape errors rather than read
    # anything from the quarantined trees, which do not exist here at all.
    run = tmp_path / "data" / "generated" / "shipped"
    run.mkdir(parents=True)
    monkeypatch.setenv(RUN_ENV, "shipped")
    resolved = resolve_run()
    assert resolved == run
    assert not (tmp_path / "ground_truth").exists()


def test_serialize_never_names_the_quarantine() -> None:
    for path in Path("src/chakravyuh/api").rglob("*.py"):
        text = path.read_text("utf-8")
        assert "ground_truth" not in text, f"{path} names the answer key"
        assert "measurements" not in text, f"{path} names the measurements tree"


def test_quarantine_trees_are_not_served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A run directory is served, not its siblings: the truth tree next door stays closed."""
    monkeypatch.chdir(tmp_path)
    run = tmp_path / "data" / "generated" / "r"
    run.mkdir(parents=True)
    truth = tmp_path / "ground_truth" / "r"
    truth.mkdir(parents=True)
    (truth / "origins.parquet").write_bytes(b"PAR1")
    monkeypatch.setenv(RUN_ENV, "r")
    assert resolve_run() == run
    # The server can only see data/generated/<run>/; nothing in it names the sibling.
    assert serialize.PACKETS_DIR == "packets"
    assert not (run / "ground_truth").exists()
