"""Record one short, silent browser rehearsal of a decision and an edge case."""

import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "grade_evidence"
OUTPUT.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory(prefix="zamp-recording-", ignore_cleanup_errors=True) as tmp:
    sandbox = Path(tmp)
    os.chdir(sandbox)
    os.environ.update(DATABASE_URL=f"sqlite:///{(sandbox / 'recording.db').as_posix()}", STORAGE_LOCAL_DIR=str(sandbox / "uploads"), GEMINI_API_KEY="", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app
    from app.database import Base, engine
    from app.db.seed_demo import reset_and_seed_demo
    from fastapi.staticfiles import StaticFiles
    from playwright.sync_api import sync_playwright
    import uvicorn

    Base.metadata.create_all(engine)
    reset_and_seed_demo()
    app.mount("/assets", StaticFiles(directory=str(ROOT / "frontend/dist/assets")), name="assets")
    app.mount("/web", StaticFiles(directory=str(ROOT / "frontend/dist"), html=True), name="web")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    started = time.monotonic()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=str(Path(os.environ["LOCALAPPDATA"]) / "ms-playwright/chromium-1234/chrome-win64/chrome.exe"), headless=True, args=["--disable-gpu", "--no-sandbox"])
            context = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(OUTPUT), record_video_size={"width": 1280, "height": 720})
            page = context.new_page()
            page.set_default_timeout(15000)
            page.goto(f"http://127.0.0.1:{port}/web/")
            page.locator("input[type=email]").fill("reviewer@apex.com")
            page.locator("input[type=password]").fill("Password123!")
            page.locator("button[type=submit]").click()
            page.get_by_text("APP-2026-CLEAN-001").wait_for()
            page.wait_for_timeout(1800)
            page.locator("tr").filter(has_text="APP-2026-CLEAN-001").get_by_role("button", name="Inspect").click()
            page.get_by_text("Approve Vendor", exact=True).wait_for()
            page.wait_for_timeout(2200)
            page.get_by_text("Approve Vendor", exact=True).click()
            page.get_by_text("Approve Vendor Application").wait_for()
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Confirm Approval").click()
            page.get_by_text("Formal Approval Recorded").wait_for()
            page.wait_for_timeout(2200)
            page.get_by_title("Sign out of your session").click()
            page.locator("input[type=email]").fill("vendor.mismatch@sharmaworks.in")
            page.locator("input[type=password]").fill("Password123!")
            page.locator("button[type=submit]").click()
            page.get_by_text("1 item needs your attention").wait_for()
            page.wait_for_timeout(2200)
            page.get_by_label("Correct Bank Account Number").fill("50200012345678")
            page.get_by_role("button", name="Send response").click()
            page.wait_for_timeout(2200)
            edge_text = page.locator("body").inner_text()
            video = page.video
            page.close()
            context.close()
            browser.close()
            duration = time.monotonic() - started
            assert video is not None
            source = Path(video.path())
            destination = OUTPUT / "iteration2-demo-rehearsal.webm"
            source.replace(destination)
            result = {"duration_seconds": round(duration, 1), "within_five_minutes": duration <= 300, "happy_decision_recorded": True, "edge_response_clicked": True, "edge_screen_excerpt": edge_text[:240], "recording": str(destination)}
            (ROOT / "testdata/demo_rehearsal_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result), flush=True)
    finally:
        server.should_exit = True
        thread.join(2)
        engine.dispose()
        os.chdir(ROOT)
