"""Browser regression for real run selection, case handoffs and offline UI behavior."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path("research/bitcoin/results/drishti-redesign")
out.mkdir(parents=True, exist_ok=True)
errors, external, checks = [], [], []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000}, reduced_motion="reduce", accept_downloads=True
    )
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))

    def route(r):
        if r.request.url.startswith("http://127.0.0.1:4183"):
            r.continue_()
        else:
            external.append(r.request.url)
            r.abort()

    page.route("**/*", route)
    page.goto("http://127.0.0.1:4183/#app", wait_until="networkidle", timeout=60000)

    def stage(name):
        page.get_by_role("navigation", name="The thread — case workflow").get_by_role(
            "button", name=re.compile("^" + name)
        ).click()
        page.wait_for_timeout(250)

    def select_run(label, all_runs=False):
        page.locator('button[aria-haspopup="dialog"]').click()
        dialog = page.get_by_role("dialog", name="Choose an investigation run")
        if all_runs:
            dialog.get_by_role("button", name="All coverage runs").click()
        dialog.get_by_role("button", name=re.compile("^" + re.escape(label))).click()
        page.wait_for_function(
            "!document.querySelector('button[aria-haspopup=dialog]').textContent.includes('Loading')"
        )
        page.wait_for_timeout(200)

    assert "127.0.0.1" not in page.locator("body").inner_text()
    page.locator('button[aria-haspopup="dialog"]').click()
    dialog = page.get_by_role("dialog", name="Choose an investigation run")
    assert dialog.get_by_role("button", name=re.compile("^Agency")).count() == 1
    assert dialog.get_by_role("button", name=re.compile("^Stealth")).count() == 1
    assert dialog.get_by_role("button", name=re.compile("^Blind spots")).count() == 1
    assert "s11-test" not in dialog.inner_text()
    dialog.get_by_role("button", name="All coverage runs").click()
    assert dialog.locator("button[aria-pressed]").count() == 10  # two tabs + eight runs
    page.keyboard.press("Escape")
    checks.append("Three curated demos; eight operational runs; historical test runs hidden")
    page.screenshot(path=str(out / "globe.png"))
    page.get_by_role("button", name=re.compile("^Candidate trail")).click()
    selected = page.get_by_role("complementary", name="Investigation context").inner_text()
    stage("Map")
    assert "outside this bounded" not in page.locator("body").inner_text()
    assert (
        selected.split("TX ")[-1].split("\n")[0]
        in page.get_by_role("complementary", name="Investigation context").inner_text()
    )
    page.get_by_role("img", name=re.compile("Input addresses")).wait_for()
    page.screenshot(path=str(out / "atlas.png"), full_page=True)
    page.get_by_role("button", name="Inspect this transaction’s origin →").click()
    page.get_by_text("Relative likelihood", exact=False).wait_for()
    page.screenshot(path=str(out / "origin.png"), full_page=True)
    checks.append("Globe transaction follows into complete atlas trace and matching origin")
    page.get_by_role("complementary", name="Investigation context").get_by_role(
        "button", name="Clear selection"
    ).click()
    stage("Map")
    page.get_by_role("button", name="Spatial graph ↗").click()
    page.locator("canvas").wait_for()
    page.wait_for_timeout(2000)
    box = page.locator("canvas").bounding_box()
    assert box
    coordinates = json.loads(
        subprocess.check_output(
            [
                "node",
                "research/bitcoin/project_drishti_nodes.cjs",
                str(box["width"] / box["height"]),
            ]
        )
    )
    traced = False
    for point in coordinates[:25]:
        x, y = box["x"] + point["x"] * box["width"], box["y"] + point["y"] * box["height"]
        page.mouse.move(x, y)
        page.wait_for_timeout(150)
        tags = page.get_by_text("click to trace", exact=True)
        if tags.count():
            assert tags.first.evaluate("el => getComputedStyle(el).pointerEvents") == "none"
            page.mouse.click(x, y)
            page.wait_for_timeout(350)
            if page.get_by_role("heading", name="Trace", exact=True).count():
                traced = True
                break
    assert traced, "Hovered transaction must open Trace despite the passive HTML label"
    page.screenshot(path=str(out / "spatial-trace.png"))
    checks.append("Actual canvas money click opens 3D Trace; hover label cannot intercept click")
    page.get_by_role("button", name="Close properties").click()
    page.get_by_role("complementary", name="Investigation context").get_by_role(
        "button", name="Clear selection"
    ).click()
    for name in ["Intake", "Untangle", "Leads", "Proof", "World"]:
        stage(name)
        assert page.locator("main").inner_text()
        page.screenshot(path=str(out / (name.lower() + ".png")), full_page=True)
    stage("Proof")
    page.get_by_text("SHA-256 of the exact JSON download").click()
    fingerprint = page.locator("code").first.inner_text()
    if page.get_by_role("button", name="Review the packet", exact=True).count():
        page.get_by_role("button", name="Review the packet", exact=True).click()
    with page.expect_download() as download:
        page.get_by_role("button", name="Export packet (JSON)").click()
    download.value.save_as(out / "packet.json")
    assert hashlib.sha256((out / "packet.json").read_bytes()).hexdigest() == fingerprint
    select = page.get_by_label("Available signed packets")
    options = select.locator("option").all_text_contents()
    assert len(options) == 5
    for case in options:
        select.select_option(case)
        page.get_by_role("heading", name=case, exact=True).wait_for()
    checks.append("Proof switches real packets; displayed SHA-256 matches exact downloaded bytes")
    stage("Leads")
    page.locator("ul button").first.click()
    assert "Case " in page.get_by_role("complementary", name="Investigation context").inner_text()
    checks.append("Lead selection updates the shared case context")
    select_run("Stealth")
    assert page.get_by_role("complementary", name="Properties").count() == 0
    assert page.get_by_role("heading", name="This evidence is not in this run.").count() == 1
    stage("Proof")
    assert page.get_by_role("heading", name="This evidence is not in this run.").count() == 1
    stage("Map")
    page.get_by_role("heading", name=re.compile("See the flow")).wait_for()
    stage("World")
    assert "_sweep-0.10" in page.locator("body").inner_text()
    checks.append(
        "Stealth changes actual map/world artifacts and does not borrow Agency leads or proof"
    )
    for label in [
        "Blind spots",
        "Coverage 0.05",
        "Coverage 0.25",
        "Coverage 0.50",
        "Coverage 0.60",
        "Coverage 0.70",
    ]:
        select_run(label, all_runs=True)
        stage("Map")
        page.get_by_role("heading", name=re.compile("See the flow")).wait_for()
        stage("Origin")
        page.get_by_role("heading", name="Origin", exact=True).wait_for()
        stage("Globe")
        assert page.get_by_role("complementary", name="Geographic observation index").count() == 1
    checks.append("Every operational coverage run loads its own atlas, origin and globe")
    select_run("Agency")
    stage("World")
    snapshots = page.get_by_role("group", name="Research queue snapshots")
    snapshots.get_by_role("button", name=re.compile("^Window 7")).click()
    assert "Fixed synthetic research snapshot · window 7" in page.locator("body").inner_text()
    snapshots.get_by_role("button", name=re.compile("^Window 9")).click()
    assert "Fixed synthetic research snapshot · window 9" in page.locator("body").inner_text()
    checks.append(
        "Executed research snapshots 7/8/9 switch queues independently of capture metrics"
    )
    context.set_offline(True)
    stage("Map")
    page.get_by_label("Find a TXID").fill("no-match-for-this-tx")
    assert "No matching transaction" in page.locator("body").inner_text()
    page.get_by_label("Find a TXID").fill("")
    stage("Globe")
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(out / "globe-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    stage("Map")
    page.screenshot(path=str(out / "atlas-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    stage("World")
    page.screenshot(path=str(out / "world-mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    checks.append("Offline interactions, reduced motion and mobile viewport remain usable")
    assert not errors, errors
    assert not external, external
    (out / "report.json").write_text(
        json.dumps(
            {"checks": checks, "page_errors": errors, "external_requests": external}, indent=2
        )
        + "\n"
    )
    browser.close()
sys.stdout.write(json.dumps(checks, indent=2) + "\n")
