"""Render the current built UI against a disposable seeded API."""

import os
import json
import re
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "grade_evidence"
OUTPUT.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory(prefix="zamp-ui-", ignore_cleanup_errors=True) as tmp:
    sandbox = Path(tmp)
    os.chdir(sandbox)
    os.environ.update(
        DATABASE_URL=f"sqlite:///{(sandbox / 'ui.db').as_posix()}",
        STORAGE_LOCAL_DIR=str(sandbox / "uploads"),
        GEMINI_API_KEY="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
    )
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app
    from app.database import Base, engine
    from app.db.seed_demo import reset_and_seed_demo
    from fastapi.testclient import TestClient
    from fastapi.staticfiles import StaticFiles
    from playwright.sync_api import sync_playwright
    import uvicorn

    Base.metadata.create_all(engine)
    reset_and_seed_demo()
    client = TestClient(app)
    reviewer_token = client.post("/api/auth/login", json={"email": "reviewer@apex.com", "password": "Password123!"}).json()["access_token"]
    reason = "The business evidence did not meet the buyer's requirements. Contact procurement if you think this decision needs review."
    rejected = client.post(
        "/api/applications/app-warn-003/reject",
        headers={"Authorization": "Bearer " + reviewer_token},
        json={"reason": reason},
    )
    assert rejected.status_code == 200, rejected.text
    metrics = client.get(
        "/api/applications/dashboard/metrics",
        headers={"Authorization": "Bearer " + reviewer_token},
    ).json()
    assert metrics["high_severity_exceptions_count"] == 2, metrics

    app.mount("/assets", StaticFiles(directory=str(ROOT / "frontend/dist/assets")), name="assets")
    app.mount("/web", StaticFiles(directory=str(ROOT / "frontend/dist"), html=True), name="web")
    sample_file = client.get("/demo-documents/pan_tata.pdf")
    assert sample_file.status_code == 200 and sample_file.content.startswith(b"%PDF"), sample_file.status_code
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)

    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=str(Path(os.environ["LOCALAPPDATA"]) / "ms-playwright/chromium-1234/chrome-win64/chrome.exe"),
                headless=True,
                args=["--disable-gpu", "--no-sandbox"],
            )
            cases = [
                ("login", None, 1440),
                ("vendor-rejected", "vendor.issue@apexlogistics.in", 390),
                ("vendor-action", "vendor.mismatch@sharmaworks.in", 390),
                ("vendor-autofill", "vendor@apexcomponents.com", 390),
                ("procurement-runs", "procurement@apex.com", 1440),
                ("reviewer", "reviewer@apex.com", 1440),
            ]
            for label, email, width in cases:
                page = browser.new_page(viewport={"width": width, "height": 900}, device_scale_factor=1)
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(f"http://127.0.0.1:{port}/web/")
                page.wait_for_load_state("networkidle")
                if email:
                    page.locator("input[type=email]").fill(email)
                    page.locator("input[type=password]").fill("Password123!")
                    page.locator("button[type=submit]").click()
                    page.get_by_title("Sign out of your session").wait_for()
                    page.wait_for_load_state("networkidle")
                    if label == "vendor-action":
                        page.locator("h3").filter(has_text=re.compile(r"items? needs? your attention")).wait_for()
                    elif label == "vendor-autofill":
                        page.get_by_role("button", name=re.compile(r"Fill with demo data: Established goods company")).wait_for()
                        page.get_by_role("button", name=re.compile(r"Fill with demo data: Proprietor with a bank mismatch")).wait_for()
                        page.get_by_role("button", name=re.compile(r"Fill with demo data: LLP service provider")).wait_for()
                        page.get_by_role("button", name=re.compile(r"Fill with demo data: Established goods company")).click()
                        page.get_by_role("status").filter(has_text="ready to review").wait_for(timeout=60000)
                        assert "fictional" in page.locator("body").inner_text().lower()
                        page.get_by_role("button", name=re.compile(r"Step 6 Documents")).click()
                        required = page.get_by_text("Required:", exact=True).locator("xpath=..").inner_text().split()[-1]
                        uploaded = page.get_by_text("Uploaded:", exact=True).locator("xpath=..").inner_text().split()[-1]
                        assert required == uploaded == "5", (required, uploaded)
                        page.get_by_role("button", name=re.compile(r"Step 7 Review")).click()
                        assert page.locator('input[type="checkbox"]').evaluate_all("els => els.length === 3 && els.every(el => !el.checked)")
                    elif label == "vendor-rejected":
                        page.get_by_text("Onboarding Application Declined").wait_for()
                    elif label == "reviewer":
                        page.get_by_text("Application decisions").wait_for()
                        page.get_by_text("APP-2026-CLEAN-001").wait_for()
                    elif label == "procurement-runs":
                        page.get_by_role("button", name="Processing Runs").click()
                        page.get_by_role("heading", name="Processing runs").wait_for()
                        clean_row = page.get_by_role("row").filter(has_text="APP-2026-CLEAN-001")
                        clean_row.get_by_role("button", name="Inspect run").first.click()
                        page.get_by_role("heading", name="What the checks found").wait_for()
                text = page.locator("body").inner_text()
                page.screenshot(path=str(OUTPUT / f"iteration2-{label}.png"), full_page=True)
                preview = text[:300].replace("\n", " | ").encode("ascii", "replace").decode("ascii")
                print(label, "width", width, "content", preview, flush=True)
                if label == "login":
                    assert "A clearer path from invitation to decision." in text
                elif label == "vendor-rejected":
                    assert reason in text
                    assert "items need your attention" not in text
                    assert "item needs your attention" not in text
                elif label == "vendor-action":
                    assert "item needs your attention" in text.lower() or "items need your attention" in text.lower()
                    assert "application status: action needed" in text.lower()
                elif label == "vendor-autofill":
                    assert "Review and Submit" in text
                    assert "DRAFT IN PROGRESS" in text
                elif label == "reviewer":
                    assert "Application decisions" in text and "Case queue" in text
                elif label == "procurement-runs":
                    assert "findings recorded" in text.lower()
                    assert "not applicable" in text.lower()
                    assert "Demo notice: external tax, bank, and registry results shown here use simulated records." in text
                if width == 390:
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.close()
            browser.close()
        assert not errors, errors
        (ROOT / "testdata/ui_results.json").write_text(json.dumps({
            "build": "current frontend/dist",
            "screens": [label for label, _, _ in cases],
            "rejection_reason_visible": True,
            "rejected_correction_banner_hidden": True,
            "mobile_no_horizontal_overflow": True,
            "reviewer_queue_visible": True,
            "run_history_detail_visible": True,
            "not_applicable_findings_explicit": True,
            "high_severity_open_count_excludes_rejected": metrics["high_severity_exceptions_count"] == 2,
        }, indent=2), encoding="utf-8")
    finally:
        server.should_exit = True
        thread.join(2)
        client.close()
        engine.dispose()
        os.chdir(ROOT)
