"""The loopback read-only API. Binds 127.0.0.1, serves the eight adapter payloads.

There is deliberately no authentication: this is a single-user tool on an investigator's own
laptop. That choice is only safe because the bind address is a module constant, `BIND_HOST`,
and the test suite fails if it is anything but 127.0.0.1 — binding to the wildcard address
would put an unauthenticated endpoint on whatever network the laptop joined, which at a demo
venue is everyone else's.

No route mutates anything, no route accepts a filesystem path: the only parameter a route
takes that is not an int or a severity string is a case id or txid, resolved strictly inside
the run directory set at startup from `CHAKRAVYUH_RUN`. That value names a run id, never a
path, and resolves under `data/generated/` or the app refuses to start.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query

from chakravyuh.api import serialize

BIND_HOST = "127.0.0.1"
BIND_PORT = 8000
RUN_ENV = "CHAKRAVYUH_RUN"
GENERATED_ROOT = "data/generated"

app = FastAPI(title="chakravyuh", version="0.1.0", docs_url=None, redoc_url=None)


def resolve_run() -> Path:
    """The run directory this process serves, resolved once at startup.

    A run id, never a path: anything containing a separator or escaping `data/generated/`
    is refused, because a parameter that says where data lives is a parameter that can point
    somewhere quarantined.
    """
    run = os.environ.get(RUN_ENV, "")
    if not run or "/" in run or "\\" in run or run in (".", ".."):
        raise RuntimeError(
            f"{RUN_ENV} must name a run id under data/generated/, got {run!r}. "
            "Start with: CHAKRAVYUH_RUN=<run-id> make api"
        )
    root = (Path.cwd() / GENERATED_ROOT / run).resolve()
    if not root.is_dir():
        raise RuntimeError(f"{RUN_ENV}={run!r}: {root} does not exist")
    return root


_RUN_DIR: Path | None = None


def run_dir() -> Path:
    global _RUN_DIR
    if _RUN_DIR is None:
        _RUN_DIR = resolve_run()
    return _RUN_DIR


def set_run_dir(path: Path) -> None:
    """Tests inject the run directory directly; production resolves it from the environment."""
    global _RUN_DIR
    _RUN_DIR = path


@app.exception_handler(KeyError)
def _not_found(request: object, exc: KeyError) -> HTTPException:  # pragma: no cover
    return HTTPException(status_code=404, detail="not found")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "run": run_dir().name}


@app.get("/manifest")
def get_manifest() -> dict[str, Any]:
    try:
        return serialize.manifest(run_dir())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/collapse")
def get_collapse_stats() -> dict[str, Any]:
    return serialize.collapse(run_dir())


@app.get("/transactions")
def list_transactions(
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return serialize.transactions(run_dir(), limit, offset)


@app.get("/origin/{txid}")
def get_origin_estimate(txid: str) -> dict[str, Any]:
    try:
        return serialize.origin_estimate(run_dir(), txid)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown txid {txid[:8]}…") from None


@app.get("/graph")
def get_graph(
    detail: Literal["cluster", "address"] = "cluster",
    focus: str | None = None,
    cap: int = Query(default=serialize.DEFAULT_NODE_CAP, ge=1, le=20000),
) -> dict[str, Any]:
    return serialize.graph(run_dir(), detail, focus, cap)


@app.get("/alerts")
def list_alerts(
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    severity: str | None = None,
) -> dict[str, Any]:
    return serialize.alerts(run_dir(), limit, offset, severity)


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str) -> dict[str, Any]:
    try:
        return serialize.alert(run_dir(), alert_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown case") from None


@app.get("/packets/{alert_id}")
def get_packet(alert_id: str) -> dict[str, Any]:
    try:
        return serialize.packet(run_dir(), alert_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="no packet for this case") from None
