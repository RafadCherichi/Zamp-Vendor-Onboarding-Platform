from browser_support import launch_browser
"""Take a new vendor through the actual browser form and reviewer decision."""

import json
import os
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

with tempfile.TemporaryDirectory(prefix="zamp-fresh-ui-", ignore_cleanup_errors=True) as tmp:
    sandbox = Path(tmp)
    os.chdir(sandbox)
    os.environ.update(DATABASE_URL=f"sqlite:///{(sandbox / 'fresh-ui.db').as_posix()}", STORAGE_LOCAL_DIR=str(sandbox / "uploads"), GEMINI_API_KEY="", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app
    from app.database import Base, engine, SessionLocal
    from app.db.seed_demo import reset_and_seed_demo
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.member import OrganisationMember
    from app.models.role import RoleEnum
    from app.core.security import hash_password
    from fastapi.testclient import TestClient
    from fastapi.staticfiles import StaticFiles
    from playwright.sync_api import sync_playwright
    import uvicorn

    Base.metadata.create_all(engine)
    reset_and_seed_demo()
    from app.services.extraction import pipeline
    original_read = pipeline.extract_document_text
    first_browser_upload = {"pending": True}

    def pause_first_upload(*args, **kwargs):
        if first_browser_upload["pending"]:
            first_browser_upload["pending"] = False
            time.sleep(2)
        return original_read(*args, **kwargs)

    pipeline.extract_document_text = pause_first_upload
    with SessionLocal() as db:
        org = Organization(name="Fresh browser buyer", slug="fresh-browser-buyer")
        db.add(org)
        db.flush()
        for email, role in (("po-browser@grade.in", RoleEnum.PROCUREMENT_OFFICER), ("review-browser@grade.in", RoleEnum.REVIEWER)):
            user = User(email=email, full_name=role.value, hashed_password=hash_password("Password123!"))
            db.add(user)
            db.flush()
            db.add(OrganisationMember(organisation_id=org.id, user_id=user.id, role=role.value))
        db.commit()
    client = TestClient(app)
    def login(email):
        response = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
        assert response.status_code == 200, response.text
        return response.json()["access_token"]
    po = login("po-browser@grade.in")
    invite = client.post("/api/invitations", headers={"Authorization": "Bearer " + po}, json={"vendor_name": "Tata Industrial Supplies Private Limited", "vendor_email": "fresh-browser@grade.in", "days_valid": 7})
    assert invite.status_code == 201, invite.text
    accepted = client.post("/api/invitations/token/" + invite.json()["demo_invitation_url"].split("/")[-1] + "/accept", json={"full_name": "Browser Vendor", "password": "Password123!"})
    assert accepted.status_code == 200, accepted.text
    application_id = accepted.json()["application_id"]
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
    try:
        with sync_playwright() as pw:
            browser = launch_browser(pw, headless=True, args=["--disable-gpu", "--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_default_timeout(15000)
            def wait_for_step(label):
                try:
                    page.get_by_text(label, exact=True).wait_for()
                except Exception:
                    page.screenshot(path=str(OUTPUT / "iteration3-wizard-step-failure.png"), full_page=True)
                    print(f"Wizard did not reach {label!r}. Visible page text:\n{page.locator('body').inner_text()}", flush=True)
                    raise
            page.goto(f"http://127.0.0.1:{port}/web/")
            page.locator("input[type=email]").fill("fresh-browser@grade.in")
            page.locator("input[type=password]").fill("Password123!")
            page.locator("button[type=submit]").click()
            wait_for_step("Step 1: About Your Business")
            page.get_by_placeholder("Official legal name as registered").fill("Tata Industrial Supplies Private Limited")
            page.locator('input[name="constitution"][value="PVT_LTD"]').check()
            page.get_by_placeholder("Full registered address as per tax / statutory records").fill("Plot 10, Industrial Hub, Electronic City Phase 1")
            page.get_by_placeholder("e.g. Mumbai, Bengaluru").fill("Bengaluru")
            page.get_by_placeholder("e.g. Maharashtra, Karnataka").fill("Karnataka")
            page.get_by_placeholder("6-digit postal code").fill("560100")
            page.get_by_text("Save & Continue").click()
            wait_for_step("Step 2: Tax Details")
            page.get_by_placeholder("e.g. AAPFU0938L").fill("AAACZ1234K")
            page.get_by_placeholder("e.g. U72200KA2020PTC123456").fill("U72200KA2020PTC123456")
            page.get_by_text("Save & Continue").click()
            wait_for_step("Step 3: Contact Details")
            page.get_by_placeholder("e.g. Vikram Malhotra").fill("Ratan Verma")
            page.get_by_placeholder("e.g. Proprietor, Director, Partner, Manager").fill("Director")
            page.get_by_placeholder("e.g. contact@company.in").fill("fresh-browser@grade.in")
            page.get_by_placeholder("e.g. 98200 12345").fill("9845012345")
            page.get_by_text("Save & Continue").click()
            wait_for_step("Step 4: Bank Account Details")
            page.get_by_placeholder("Name exactly as printed on cheque or bank statement").fill("Tata Industrial Supplies Private Limited")
            page.get_by_placeholder("e.g. State Bank of India, HDFC Bank, ICICI Bank").fill("ICICI Bank")
            page.get_by_placeholder("Enter account number").fill("50200012345678")
            page.get_by_placeholder("Re-type account number").fill("50200012345678")
            page.get_by_placeholder("e.g. HDFC0000123").fill("ICIC0000002")
            page.get_by_text("Save & Continue").click()
            wait_for_step("Step 5: What Does Your Business Do?")
            page.get_by_text("Goods Supplier / Trader").click()
            page.get_by_text("Save & Continue").click()
            wait_for_step("Step 6: Documents You Need to Provide")
            mapping = {"PAN_PROOF": "pan_tata.pdf", "CONSTITUTION_PROOF": "coi_tata.pdf", "BANK_PROOF": "bank_tata.pdf", "SIGNATORY_PROOF": "board_resolution_tata.pdf"}
            vendor_token = login("fresh-browser@grade.in")
            live_reading_seen = False
            for doc_type, filename in mapping.items():
                slots = client.get(f"/api/applications/{application_id}/checklist", headers={"Authorization": "Bearer " + vendor_token}).json()
                index = next(index for index, slot in enumerate(slots) if slot["document_type"] == doc_type)
                page.locator('input[type="file"]').nth(index).set_input_files(str(sandbox / "demo_documents" / filename))
                if not live_reading_seen:
                    page.get_by_text("Reading the document", exact=True).wait_for(timeout=12000)
                    page.screenshot(path=str(OUTPUT / "iteration3-live-document-stage.png"), full_page=True)
                    live_reading_seen = True
                page.get_by_text("Replace (v2)").first.wait_for(timeout=15000)
            page.screenshot(path=str(OUTPUT / "iteration2-fresh-documents.png"), full_page=True)
            page.get_by_text("Save & Continue").click()
            wait_for_step("Step 7: Review and Submit")
            page.locator('input[type="checkbox"]').last.check()
            for box in page.locator('input[type="checkbox"]').all():
                if not box.is_checked():
                    box.check()
            page.get_by_text("Submit Application for Review").click()
            page.get_by_text("Application Received").wait_for(timeout=20000)
            page.screenshot(path=str(OUTPUT / "iteration2-fresh-submitted.png"), full_page=True)
            page.reload()
            page.get_by_text("Application Received").wait_for()
            browser_status = page.locator("body").inner_text()
            reviewer = login("review-browser@grade.in")
            headers = {"Authorization": "Bearer " + reviewer}
            validation = client.get(f"/api/applications/{application_id}/validation", headers=headers).json()
            approval = client.post(f"/api/applications/{application_id}/approve", headers=headers, json={"notes": "Fresh browser submission reviewed"})
            assert approval.status_code == 200, approval.text
            page.reload()
            page.get_by_text("Onboarding Application Approved!").wait_for()
            page.screenshot(path=str(OUTPUT / "iteration2-fresh-approved.png"), full_page=True)
            vendor_current = client.get("/api/applications/current", headers={"Authorization": "Bearer " + vendor_token}).json()
            queue = client.get("/api/applications/queue", headers=headers).json()
            queue_item = next(item for item in queue["items"] if item["id"] == application_id)
            assert vendor_current["status"] == queue_item["status"] == "APPROVED"
            assert vendor_current["reference_number"] == queue_item["reference_number"]
            staff_page = browser.new_page(viewport={"width": 1440, "height": 900})
            staff_page.goto(f"http://127.0.0.1:{port}/web/")
            staff_page.locator("input[type=email]").fill("review-browser@grade.in")
            staff_page.locator("input[type=password]").fill("Password123!")
            staff_page.locator("button[type=submit]").click()
            staff_page.get_by_text(queue_item["reference_number"]).wait_for()
            staff_page.get_by_text(re.compile(r"Decision by reviewer", re.IGNORECASE)).wait_for()
            staff_page.screenshot(path=str(OUTPUT / "iteration2-fresh-reviewer-queue.png"), full_page=True)
            staff_page.get_by_role("button", name="Inspect").first.click()
            staff_page.get_by_text("Application Metadata").wait_for()
            staff_page.get_by_text("Decision recorded", exact=True).wait_for()
            assert "Pending Requirement(s)" not in staff_page.locator("body").inner_text()
            staff_page.screenshot(path=str(OUTPUT / "iteration3-reviewer-final-decision.png"), full_page=True)
            staff_page.get_by_role("button", name=re.compile("G. Activity Trail")).click()
            staff_page.get_by_text("Application Approved", exact=False).wait_for()
            staff_page.get_by_text("Fresh browser submission reviewed", exact=False).wait_for()
            staff_page.get_by_role("button", name="D. 4-Layer Validation").click()
            source_link = staff_page.get_by_role("button", name=re.compile("Open source:"))
            source_link.first.wait_for(timeout=10000)
            staff_page.screenshot(path=str(OUTPUT / "iteration3-reviewer-source-comparison.png"), full_page=True)
            source_link.first.click()
            staff_page.get_by_text(re.compile("PAN.*v1|v1.*PAN")).wait_for(timeout=10000)

            mismatch_page = browser.new_page(viewport={"width": 1440, "height": 900})
            mismatch_page.goto(f"http://127.0.0.1:{port}/web/")
            mismatch_page.locator("input[type=email]").wait_for(state="visible")
            mismatch_page.locator("input[type=email]").fill("reviewer@apex.com")
            mismatch_page.locator("input[type=password]").fill("Password123!")
            mismatch_page.locator("button[type=submit]").click()
            mismatch_row = mismatch_page.get_by_role("row", name=re.compile("APP-2026-MISM-002"))
            mismatch_row.get_by_role("button", name="Inspect").click()
            mismatch_page.get_by_text("Application Metadata").wait_for()
            approve_button = mismatch_page.get_by_role("button", name="Approve Vendor")
            assert approve_button.is_disabled(), "A case with unresolved blockers must not offer an enabled approval action."
            mismatch_page.get_by_role("button", name="D. 4-Layer Validation").click()
            mismatch_check = mismatch_page.get_by_text("Bank Account Number vs Bank Proof Document", exact=True)
            mismatch_check.wait_for(timeout=10000)
            mismatch_body = mismatch_page.locator("body").inner_text()
            assert "VENDOR ENTERED" in mismatch_body and "READ FROM DOCUMENT" in mismatch_body
            assert "FAILED" in mismatch_body
            mismatch_source = mismatch_page.get_by_role("button", name=re.compile("Open source: Bank Account Proof, version 1"))
            mismatch_source.first.wait_for(timeout=10000)
            mismatch_page.screenshot(path=str(OUTPUT / "iteration3-bank-conflict-review.png"), full_page=True)
            mismatch_source.first.click()
            mismatch_page.get_by_text("Bank Account Proof (v1)", exact=True).wait_for(timeout=10000)

            result = {"browser_submitted": "Application Received" in browser_status, "refresh_preserved_status": True, "reviewer_approval_http": approval.status_code, "finding_count": len(validation["findings"]), "vendor_approved_visible": True, "staff_queue_consistent": True, "live_reading_seen": live_reading_seen, "reviewer_source_comparison_visible": True, "bank_conflict_and_source_visible": True}
            (ROOT / "testdata/fresh_browser_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            browser.close()
            print(json.dumps(result), flush=True)
    finally:
        server.should_exit = True
        thread.join(2)
        client.close()
        engine.dispose()
        os.chdir(ROOT)
