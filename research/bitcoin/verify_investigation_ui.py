import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path("research/bitcoin/results/investigation-ui")
root.mkdir(exist_ok=True)
errors = []
external = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--enable-unsafe-swiftshader"])
    context = browser.new_context(
        viewport={"width": 1440, "height": 1000}, reduced_motion="reduce", accept_downloads=True
    )
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))

    def route(r):
        if not r.request.url.startswith("http://127.0.0.1:4183"):
            external.append(r.request.url)
            r.abort()
        else:
            r.continue_()

    page.route("**/*", route)
    page.goto("http://127.0.0.1:4183/#app", wait_until="networkidle", timeout=60000)
    page.get_by_role("button", name=re.compile("^World")).first.click()
    heading = page.get_by_role("heading", name="Open an investigative lead")
    heading.wait_for(timeout=30000)
    nav = page.get_by_role("navigation", name="Ranked research leads")
    assert nav.get_by_role("button").count() == 20
    context.set_offline(True)
    nav.get_by_role("button").nth(1).click()
    assert nav.get_by_role("button").nth(1).get_attribute("aria-pressed") == "true"
    page.get_by_role("heading", name=re.compile("Lead #2")).wait_for()
    page.get_by_role(
        "img", name="Observed address, transaction and announcing-IP evidence"
    ).wait_for()
    page.get_by_text("View countervailing model contributions").click()
    page.get_by_text("Inspect exact amounts and observation times").click()
    with page.expect_download() as download:
        page.get_by_role("button", name="Export evidence queue · JSON").click()
    download.value.save_as(root / "downloaded-evidence.json")
    packet = json.loads((root / "downloaded-evidence.json").read_text())
    assert packet["lead_count"] == 20
    heading.scroll_into_view_if_needed()
    page.screenshot(path=str(root / "desktop.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    heading.scroll_into_view_if_needed()
    page.screenshot(path=str(root / "mobile.png"))
    nav.get_by_role("button").nth(0).click()
    assert nav.get_by_role("button").nth(0).get_attribute("aria-pressed") == "true"
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role(
        "img", name="Observed address, transaction and announcing-IP evidence"
    ).screenshot(path=str(root / "graph.png"))
    field = page.locator("input[type=file]")
    field.set_input_files(
        {
            "name": "invalid.json",
            "mimeType": "application/json",
            "buffer": b'{"schema_version":1,"leads":[]}',
        }
    )
    page.get_by_role("alert").wait_for()
    field.set_input_files(
        str(Path("research/bitcoin/results/investigation-demo-v2/window7/leads.json").resolve())
    )
    page.get_by_text("Local evidence queue · leads.json").wait_for()
    assert nav.get_by_role("button").count() == 20
    with page.expect_download() as imported_download:
        page.get_by_role("button", name="Export evidence queue · JSON").click()
    imported_download.value.save_as(root / "imported-roundtrip.json")
    assert json.loads((root / "imported-roundtrip.json").read_text()) == json.loads(
        Path("research/bitcoin/results/investigation-demo-v2/window7/leads.json").read_text()
    )
    browser.close()
report = {
    "lead_buttons": 20,
    "selection_works": True,
    "graph_renders": True,
    "details_open": True,
    "download_leads": 20,
    "offline_interactions": True,
    "local_import_roundtrip": True,
    "invalid_import_rejected": True,
    "external_requests": external,
    "page_errors": errors,
}
(root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
assert not errors, errors
assert not external, external
