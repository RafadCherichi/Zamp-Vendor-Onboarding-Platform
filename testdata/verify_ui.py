from browser_support import launch_browser
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
    assert metrics["high_severity_exceptions_count"] == 1, metrics

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

    errors, checks = [], []
    try:
        with sync_playwright() as pw:
            from playwright.sync_api import expect
            browser = launch_browser(pw, headless=True)
            def open_role(email, width=1440):
                context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
                response = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
                assert response.status_code == 200
                token = response.json()["access_token"]
                context.add_init_script("localStorage.setItem('vop_auth_token', " + json.dumps(token) + ")")
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{port}/")
                page.get_by_title("Sign out of your session").wait_for()
                return context, page, token
            for width in [320, 767, 768, 1440]:
                context, page, _ = open_role("reviewer@apex.com", width)
                expect(page.locator('.case-card')).to_have_count(3)
                for card in page.locator('.case-card').all():
                    expect(card).to_be_visible()
                    expect(card.get_by_role('button', name='Open case')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                page.get_by_label('Application status', exact=True).focus()
                page.keyboard.press('Tab')
                expect(page.get_by_label('Issue severity', exact=True)).to_be_focused()
                page.screenshot(path=str(OUTPUT / f"release-reviewer-{width}.png"), full_page=True)
                checks.append(f"Reviewer cases visible and keyboard filters work at {width}px")
                context.close()
            context, page, _ = open_role('admin@apex.com')
            expect(page.locator('.case-card')).to_have_count(4)
            page.get_by_role('button', name=re.compile('Awaiting review')).click()
            expect(page.locator('.case-card')).to_have_count(1)
            page.screenshot(path=str(OUTPUT / 'release-admin.png'), full_page=True)
            checks.append('Admin case count and awaiting-review filter match')
            context.close()
            context, page, _ = open_role('procurement@apex.com')
            expect(page.locator('.case-card')).to_have_count(4)
            page.get_by_role('button', name=re.compile('Being completed')).click()
            expect(page.locator('.case-card')).to_have_count(1)
            expect(page.locator('.case-card')).to_contain_text('Apex Components & Fasteners')
            assert 'Approval blocked' not in page.locator('.case-card').inner_text()
            page.screenshot(path=str(OUTPUT / 'release-procurement.png'), full_page=True)
            checks.append('Procurement unfinished case filter and draft copy work')
            context.close()
            context, page, _ = open_role('reviewer@apex.com')
            page.locator('.case-card').filter(has_text='Tata Industrial').get_by_role('button', name='Open case').click()
            page.get_by_role('button', name=re.compile('C. Documents')).click()
            page.get_by_role('button', name='Inspect Document').first.click()
            expect(page.locator('iframe')).to_have_attribute('src', re.compile('^blob:'))
            page.screenshot(path=str(OUTPUT / 'release-private-preview.png'), full_page=True)
            checks.append('Authenticated exact-version document opens through a blob URL')
            context.close()
            context, page, _ = open_role('vendor.mismatch@sharmaworks.in', 320)
            page.get_by_role('button', name='Notifications', exact=True).click()
            page.get_by_role('button', name=re.compile('Open:')).first.click()
            page.wait_for_url(re.compile('request='))
            expect(page.locator('[id^="request-"]')).to_be_focused()
            page.reload()
            expect(page.locator('[id^="request-"]')).to_be_focused()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(OUTPUT / 'release-notification-request.png'), full_page=True)
            checks.append('Notification opens exact request, restores focus on reload, and fits 320px')
            context.close()
            context, page, token = open_role('vendor@apexcomponents.com', 320)
            page.get_by_role('button', name=re.compile('Fill with demo data: Apex Components')).click()
            page.get_by_role('status').filter(has_text='ready to review').wait_for(timeout=60000)
            current = client.get('/api/applications/current', headers={'Authorization': 'Bearer '+token}).json()
            assert current['pan'] == 'ABCPV1234F'
            assert all(d['status']=='UPLOADED' for d in current['documents'] if d['is_required'])
            page.screenshot(path=str(OUTPUT / 'release-autofill.png'), full_page=True)
            page.on('dialog', lambda dialog: dialog.accept())
            page.get_by_role('button', name='Start again', exact=True).click()
            expect(page.get_by_role('button', name='Start again', exact=True)).to_be_enabled()
            page.wait_for_load_state('networkidle')
            current = client.get('/api/applications/current', headers={'Authorization': 'Bearer '+token}).json()
            assert current['pan'] is None
            assert current['legal_name'] == 'Apex Components & Fasteners'
            assert not any(d['current_version'] for d in current['documents'])
            checks.append('Company-matched autofill uploads required proof; reset restores original draft')
            context.close()
            browser.close()
        assert not errors, errors
        (ROOT / 'testdata/ui_results.json').write_text(json.dumps({'build':'local candidate 2026-11-09','checks':checks,'page_errors':errors,'pass':True},indent=2),encoding='utf-8')
        print(json.dumps({'checks':len(checks),'pass':True}),flush=True)
    finally:
        server.should_exit = True
        thread.join(2)
        client.close()
        engine.dispose()
        os.chdir(ROOT)
