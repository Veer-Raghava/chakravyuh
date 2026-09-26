#!/usr/bin/env python3
"""Prove the demo serves from precomputed artifacts, offline, fast.

This is the cold-start gate S11 exists to protect. It does NOT regenerate anything:
regenerating data while a projector waits is the failure mode, not a feature. It boots
the read-only API against the committed demo run, confirms it answers on loopback within
the paint budget, optionally builds the console offline, and tears everything down.

Run it inside `unshare -rn` (a network namespace with only loopback) and it becomes the
airplane-mode test: if it passes with no route to the outside world, the demo is offline.

Exit zero only when every check passed. Any failure prints one decisive line and exits 1.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEMO_RUN = "s10-demo"
# The paint budget from the S11 brief. The API answering is the server-side half of
# "under three seconds to first paint"; the browser render is the console's own budget.
PAINT_BUDGET_S = 3.0


def _venv_python() -> str:
    candidate = REPO / ".venv" / "bin" / "python"
    return str(candidate) if candidate.exists() else sys.executable


def _get(url: str, timeout: float) -> tuple[int, bytes]:
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 loopback only
        return response.status, response.read()


def _wait_for_health(port: int, deadline: float) -> float:
    """Poll /health until it answers 200. Return seconds from call to first success."""
    start = time.monotonic()
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        try:
            status, _ = _get(url, timeout=1.0)
            if status == 200:
                return time.monotonic() - start
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.05)
    raise TimeoutError(f"API never answered on 127.0.0.1:{port} within the window")


def _check_api(port: int) -> None:
    run_dir = REPO / "data" / "generated" / DEMO_RUN
    if not run_dir.is_dir():
        _fail(
            f"demo artifact absent: {run_dir} does not exist. "
            "Build it once with `make demo-full`; the demo never regenerates it live."
        )

    env = dict(os.environ, CHAKRAVYUH_RUN=DEMO_RUN)
    # Launch via the venv interpreter directly, not `uv run`: uv may reach for the network
    # to resolve, and the whole point here is that nothing does.
    proc = subprocess.Popen(  # noqa: S603
        [
            _venv_python(),
            "-m",
            "uvicorn",
            "chakravyuh.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(REPO),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        # First paint budget starts once the process is up and we begin polling.
        paint = _wait_for_health(port, deadline=time.monotonic() + 30.0)
        if paint > PAINT_BUDGET_S:
            _fail(f"API answered in {paint:.2f}s, over the {PAINT_BUDGET_S:.0f}s paint budget")

        # A real data endpoint, not just liveness: the demo is worthless if /alerts 500s.
        status, body = _get(f"http://127.0.0.1:{port}/alerts?limit=1", timeout=2.0)
        if status != 200 or b"alert" not in body:
            _fail(f"/alerts did not serve the demo run (status {status})")
        print(f"demo-smoke: API served {DEMO_RUN} on loopback in {paint:.2f}s.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()


def _check_console_build() -> None:
    """Prove the console bundles with no network. Uses the already-installed node_modules;
    `npm ci` is Track B's gate, not this one, so a missing tree is a skip with instruction."""
    console = REPO / "apps" / "drishti"
    if not (console / "node_modules").is_dir():
        print(
            "demo-smoke: SKIP console build — apps/drishti/node_modules absent. "
            "Run `make verify-drishti` once to install, then this proves the offline build."
        )
        return
    result = subprocess.run(  # noqa: S603
        ["npm", "run", "build"],
        cwd=str(console),
        env=dict(os.environ, VITE_SOURCE="api"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0 or not (console / "dist").is_dir():
        _fail("console `npm run build` failed offline:\n" + (result.stderr or "").strip()[-400:])
    print("demo-smoke: console built offline (apps/drishti/dist).")


def _check_attached(port: int) -> None:
    """Poll an already-running API instead of spawning one. Used by `make demo` to gate on
    readiness of the server it just launched, without a second process fighting for the port."""
    paint = _wait_for_health(port, deadline=time.monotonic() + 30.0)
    status, body = _get(f"http://127.0.0.1:{port}/alerts?limit=1", timeout=2.0)
    if status != 200 or b"alert" not in body:
        _fail(f"attached API on :{port} did not serve /alerts (status {status})")
    print(f"demo-smoke: attached API on :{port} healthy in {paint:.2f}s.")


def _fail(message: str) -> None:
    print(f"FAIL demo-smoke: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--attach",
        action="store_true",
        help="poll an already-running API on --port instead of spawning one",
    )
    parser.add_argument(
        "--console", action="store_true", help="also prove the console builds offline"
    )
    args = parser.parse_args()

    if args.attach:
        _check_attached(args.port)
    else:
        _check_api(args.port)
    if args.console:
        _check_console_build()
    print("demo-smoke: OK.")


if __name__ == "__main__":
    main()
