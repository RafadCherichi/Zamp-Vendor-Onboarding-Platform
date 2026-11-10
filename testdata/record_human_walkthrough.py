"""Capture the case-study walkthrough as silent, subtitled live browser footage.

The browser and database are disposable. This never changes the hosted demo.
"""

from browser_support import launch_browser

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "grade_evidence" / "human_walkthrough" / "final"
OUTPUT.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")

SCENES = [
    {
        "title": "Introduction and demo profiles",
        "target": 32,
        "words": "Hi, I'm Rafad Abdul Rasheed. A buyer may need to review many suppliers, but each application arrives with different details and documents. The challenge is to make the process clear for suppliers, useful for reviewers, and safe for the buyer. I'll show one application from start to decision, then a tax identity mismatch. These are fictional demo profiles. Zoya works for another buyer company and can only see that company's cases.",
    },
    {
        "title": "Choose the supplier demo profile",
        "target": 4,
        "words": "I'll choose Vikram's supplier profile for Apex Components.",
    },
    {
        "title": "Supplier business identity",
        "target": 13,
        "words": "This sample profile belongs to Vikram's own company, Apex Components. He can enter its legal identity and address here.",
    },
    {
        "title": "Supplier tax registration",
        "target": 12,
        "words": "Here Vikram enters tax and business registrations. Zamp checks their format and later compares related values with the documents he provides.",
    },
    {
        "title": "Supplier authorised contact",
        "target": 7,
        "words": "This section gives the buyer a named contact and records who can act for the supplier.",
    },
    {
        "title": "Supplier banking details",
        "target": 8,
        "words": "The banking details will later be compared with the uploaded bank proof before payment setup. Sensitive values are masked in staff views.",
    },
    {
        "title": "Supplier business classification",
        "target": 7,
        "words": "Business activity helps the buyer understand what this supplier provides and which documents apply to the case.",
    },
    {
        "title": "Supplier document checklist",
        "target": 10,
        "words": "The checklist adapts to the supplier's business type. Each document can be previewed, and Zamp shows what it read before the supplier submits.",
    },
    {
        "title": "OCR review and applicant correction",
        "target": 18,
        "words": "This prepared example starts with one OCR misread. Vikram compares the PAN card preview with Zamp's reading, corrects it himself, and explains the change. The original reading and his correction stay on record. Checks rerun, but a person still makes the decision.",
    },
    {
        "title": "Supplier reviews and declares",
        "target": 7,
        "words": "Vikram reviews the completed details and makes the required declarations himself before submitting.",
    },
    {
        "title": "Live submission and check result",
        "target": 13,
        "words": "On submission, the document checks run and the supplier gets a reference and status. These checks prepare the review; they do not approve the supplier.",
    },
    {
        "title": "Procurement assigns the reviewer",
        "target": 13,
        "words": "Pooja assigns the case to Rajesh, giving the review a clear owner and recorded handoff.",
    },
    {
        "title": "Reviewer examines the evidence",
        "target": 12,
        "words": "Rajesh signs in to his assigned queue. He opens the submitted documents and validation findings. Zamp brings the evidence together for a human review.",
    },
    {
        "title": "Reviewer records the decision",
        "target": 9,
        "words": "After confirming nothing blocks approval, Rajesh records the decision. The reviewer makes the final call.",
    },
    {
        "title": "Supplier receives the decision",
        "target": 12,
        "words": "Vikram sees the approval notice and can open the decision. He knows onboarding is complete and no task remains in this application.",
    },
    {
        "title": "Live GSTIN and PAN conflict",
        "target": 22,
        "words": "Now a second supplier submits a separate case. A GSTIN carries the business PAN inside it: characters three through twelve are that ten-character PAN. Zamp compares it with the form. They don't match, so approval pauses and the supplier is asked to check the right entity's details. These records are synthetic.",
    },
    {
        "title": "Supplier corrects the GSTIN",
        "target": 22,
        "words": "The supplier checks the GST certificate, enters the number that matches the declared PAN, and explains the change. Zamp keeps the original request and response together.",
    },
    {
        "title": "Reviewer sees the supplier's reply",
        "target": 11,
        "words": "The reply does not approve the case. A person still needs to review the updated evidence.",
    },
    {
        "title": "Conflict run remains traceable",
        "target": 8,
        "words": "The run history preserves the GST mismatch and the reason approval was held.",
    },
    {
        "title": "Registry timeout means unknown",
        "target": 9,
        "words": "A different case has a registry timeout. That result is unknown, not a supplier failure. The team can retry; the supplier does not need to resubmit.",
    },
    {
        "title": "Thank you and close on the sign-in page",
        "target": 31,
        "words": "Zamp brings supplier details, documents and review into one traceable process. It helps teams catch mismatches early, gives suppliers a clear next step, and keeps the final decision with a person. The records and registry results in this demo are synthetic. In a pilot, we'd measure decision time and make sure valid suppliers are not held unnecessarily. Thank you for your time, and for watching our walkthrough.",
    },
]


def stamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02},{milliseconds:03}"


def caption_chunks(value: str) -> list[str]:
    words = value.split()
    chunks = []
    while words:
        count = min(8, len(words))
        if len(words) > 8 and len(words) - count < 4:
            count = len(words) - 4
        for index in range(max(4, count - 2), count + 1):
            if words[index - 1].endswith((".", ";", ":", "?", "!")):
                count = index
                break
        chunks.append(" ".join(words[:count]))
        words = words[count:]
    return chunks


with tempfile.TemporaryDirectory(prefix="zamp-human-recording-", ignore_cleanup_errors=True) as temporary:
    sandbox = Path(temporary)
    os.chdir(sandbox)
    os.environ.update(
        DATABASE_URL=f"sqlite:///{(sandbox / 'recording.db').as_posix()}",
        STORAGE_LOCAL_DIR=str(sandbox / "uploads"),
        GEMINI_API_KEY="",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
    )
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app
    from app.database import Base, engine
    from app.db.seed_demo import reset_and_seed_demo
    from app.database import SessionLocal
    from app.models.application import Application
    from app.models.validation import (
        ValidationRun, ValidationFinding, ExternalVerificationRecord, DuplicateSignal,
    )
    from app.models.exception import OnboardingException
    from app.models.notification import Notification
    from app.models.audit import AuditEvent
    from app.services.validation.checksums import calculate_gstin_check_digit
    from app.models.extraction import DocumentExtractionResult, ExtractedField
    from playwright.sync_api import sync_playwright, expect
    import uvicorn

    Base.metadata.create_all(engine)
    reset_and_seed_demo()
    with SessionLocal() as db:
        assert db.get(Application, "app-apex-base-01").status == "IN_PROGRESS"
        assert db.query(ValidationRun).filter_by(application_id="app-apex-base-01").count() == 0
        # Reuse the seeded second vendor in this disposable database as a fresh
        # draft so its conflicting GSTIN is submitted and checked during filming.
        conflict = db.get(Application, "app-mism-002")
        assert conflict is not None
        old_exception_ids = [row.id for row in db.query(OnboardingException.id).filter_by(application_id=conflict.id).all()]
        db.query(Notification).filter(Notification.entity_id.in_([conflict.id, *old_exception_ids])).delete(synchronize_session=False)
        db.query(OnboardingException).filter_by(application_id=conflict.id).delete(synchronize_session=False)
        db.query(ValidationFinding).filter_by(application_id=conflict.id).delete(synchronize_session=False)
        db.query(ValidationRun).filter_by(application_id=conflict.id).delete(synchronize_session=False)
        db.query(ExternalVerificationRecord).filter_by(application_id=conflict.id).delete(synchronize_session=False)
        db.query(DuplicateSignal).filter_by(application_id=conflict.id).delete(synchronize_session=False)
        db.query(AuditEvent).filter_by(application_id=conflict.id).delete(synchronize_session=False)
        conflict.status = "IN_PROGRESS"
        conflict.assigned_reviewer_id = "usr-apex-rev-01"
        conflict.assigned_at = datetime.now(timezone.utc)
        conflict.reviewed_by_user_id = None
        conflict.reviewed_at = None
        conflict.clarification_requested_at = None
        conflict.declaration_accurate_info = False
        conflict.declaration_authorised_rep = False
        conflict.declaration_verification_consent = False
        conflict.is_udyam_registered = False
        conflict.udyam_number = None
        conflict.bank_account_number = "60200012345678"
        bad_gstin_prefix = "27AAPFU0939L1Z"
        conflict.gstin = bad_gstin_prefix + calculate_gstin_check_digit(bad_gstin_prefix)
        db.commit()

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)

    timeline = []
    try:
        with sync_playwright() as playwright:
            browser = launch_browser(playwright, headless=True)
            raw_video_dir = sandbox / "browser_raw"
            raw_video_dir.mkdir(parents=True, exist_ok=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 810},
                record_video_dir=str(raw_video_dir),
                record_video_size={"width": 1440, "height": 810},
                device_scale_factor=1,
                reduced_motion="reduce",
            )
            context.add_init_script("""
                document.addEventListener('DOMContentLoaded', () => {
                  if (document.getElementById('demo-pointer')) return;
                  const pointer = document.createElement('div');
                  pointer.id = 'demo-pointer';
                  pointer.style.cssText = 'position:fixed;left:0;top:0;width:16px;height:16px;background:#e7bb65;border:2px solid #19382b;border-radius:50%;box-shadow:0 0 0 4px #e7bb6570,0 2px 8px #0005;z-index:2147483647;pointer-events:none;transform:translate(-30px,-30px);transition:transform 100ms linear';
                  document.body.appendChild(pointer);
                  document.addEventListener('mousemove', e => {
                    pointer.style.transform = 'translate(' + (e.clientX - 8) + 'px,' + (e.clientY - 8) + 'px)';
                  });
                });
            """)
            page = context.new_page()
            page.set_default_timeout(25000)
            base = f"http://127.0.0.1:{port}/"
            video_start = time.monotonic()
            page.goto(base)
            page.get_by_role("heading", name="Sign in").wait_for()
            first_start = [None]

            def show(target, pause=0.5):
                target.evaluate("element => element.scrollIntoView({behavior: 'smooth', block: 'center'})")
                page.wait_for_timeout(400)
                box = target.bounding_box()
                assert box, f"No screen position: {target}"
                page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=15)
                page.wait_for_timeout(pause * 1000)

            def click(target, pause=0.4):
                show(target, pause)
                target.click()

            def login(email):
                signout = page.get_by_title("Sign out of your session")
                if signout.count():
                    click(signout, 0.2)
                page.get_by_role("heading", name="Sign in").wait_for()
                page.wait_for_timeout(900)
                profile = page.locator("button").filter(has_text=email).first
                show(profile, 1.6)
                profile.click()
                page.get_by_title("Sign out of your session").wait_for()
                page.goto(base)
                page.get_by_title("Sign out of your session").wait_for()
                page.wait_for_timeout(700)

            def scene(index, action):
                start = time.monotonic()
                if index == 0:
                    first_start[0] = start
                print(f"Scene {index + 1}/{len(SCENES)}: {SCENES[index]['title']}", flush=True)
                try:
                    action()
                except Exception:
                    print(page.locator("body").inner_text()[-6000:], flush=True)
                    raise
                elapsed = time.monotonic() - start
                rest = max(0, SCENES[index]["target"] - elapsed)
                if rest:
                    page.wait_for_timeout(rest * 1000)
                end = time.monotonic()
                timeline.append({"title": SCENES[index]["title"], "start": start, "end": end, "actual_actions": round(elapsed, 2)})
                print(f"  {end-start:.1f}s (actions {elapsed:.1f}s)", flush=True)

            def intro():
                page.wait_for_timeout(2200)
                show(page.get_by_role("heading", name="Sign in"), 1.5)
                show(page.get_by_text("Zoya Akhtar", exact=True), 1.2)
                show(page.get_by_text("Vikram Malhotra", exact=True), 1.2)
                page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
                page.wait_for_timeout(1200)
            scene(0, intro)

            def supplier_login():
                login("vendor@apexcomponents.com")
                show(page.get_by_role("heading", name="Step 1: About Your Business"), 0.4)
            scene(1, supplier_login)

            def supplier_identity():
                click(page.get_by_role("button", name=re.compile("Fill with demo data: Apex Components")), 0.3)
                page.get_by_role("status").filter(has_text="ready to review").wait_for(timeout=60000)
                show(page.get_by_role("heading", name="Step 1: About Your Business"), 1.5)
                show(page.get_by_text("Sole Proprietorship", exact=True).first, 1.0)
            scene(2, supplier_identity)

            def supplier_step(step, heading):
                click(page.get_by_role("button", name=re.compile(f"Step {step}")), 0.3)
                show(page.get_by_role("heading", name=heading), 1.4)
                page.mouse.wheel(0, 210)
                page.wait_for_timeout(850)

            scene(3, lambda: supplier_step(2, "Step 2: Tax Details"))
            scene(4, lambda: supplier_step(3, "Step 3: Contact Details"))
            scene(5, lambda: supplier_step(4, "Step 4: Bank Account Details"))
            scene(6, lambda: supplier_step(5, "Step 5: What Does Your Business Do?"))
            def supplier_ocr_review():
                with SessionLocal() as correction_db:
                    docs = correction_db.query(DocumentExtractionResult).filter_by(application_id="app-apex-base-01").all()
                    pan_fields = correction_db.query(ExtractedField).filter(
                        ExtractedField.extraction_result_id.in_([d.id for d in docs]),
                        ExtractedField.field_name == "pan_number",
                    ).all()
                    assert pan_fields, "The prepared PAN OCR example has no extracted PAN field."
                    for field in pan_fields:
                        field.extracted_value = "ABCPV1234G"
                        field.normalized_value = "ABCPV1234G"
                        field.evidence_text = "PAN: ABCPV1234G"
                    correction_db.commit()
                inspect = page.get_by_role("button", name="Inspect OCR").first
                click(inspect, 0.4)
                page.get_by_text("Original Document Preview", exact=True).wait_for()
                show(page.get_by_text("Original Document Preview", exact=True), 1.2)
                value = page.get_by_label("Value from your document").last
                value.fill("ABCPV1234F")
                page.get_by_label("Why did you change it?").last.fill("I checked the PAN card preview and corrected one misread character.")
                show(page.get_by_role("button", name="Save correction & rerun checks").last, 0.8)
                click(page.get_by_role("button", name="Save correction & rerun checks").last, 0.3)
                page.get_by_role("status").filter(has_text="Correction saved").wait_for(timeout=30000)
                show(page.get_by_role("status").filter(has_text="Correction saved"), 1.0)
                click(page.get_by_role("button", name="Done"), 0.3)
            scene(7, lambda: supplier_step(6, "Step 6: Documents You Need to Provide"))
            scene(8, supplier_ocr_review)

            def supplier_review():
                click(page.get_by_role("button", name=re.compile("Step 7")), 0.3)
                show(page.get_by_role("heading", name="Step 7: Review and Submit"), 1.0)
                for checkbox in page.locator("input[type=checkbox]").all():
                    show(checkbox, 0.3)
                    checkbox.check()
                show(page.get_by_role("button", name="Submit Application for Review"), 0.7)
            scene(9, supplier_review)

            def submit_clean():
                click(page.get_by_role("button", name="Submit Application for Review"), 0.2)
                page.get_by_role("heading", name="Thank You! Application Submitted Successfully").wait_for(timeout=60000)
                show(page.get_by_role("heading", name="Application status"), 3.0)
                show(page.get_by_text("2. Automated checks", exact=False).first, 2.0)
                show(page.get_by_role("heading", name="Thank You! Application Submitted Successfully"), 2.0)
                show(page.get_by_text("APP-2026-PROP-001", exact=True).first, 1.0)
                with SessionLocal() as proof:
                    assert proof.get(Application, "app-apex-base-01").status in ("SUBMITTED", "UNDER_REVIEW")
                    assert proof.query(ValidationRun).filter_by(application_id="app-apex-base-01").count() >= 1
            scene(10, submit_clean)

            def assign_clean():
                login("procurement@apex.com")
                card = page.locator(".case-card").filter(has_text="APP-2026-PROP-001")
                show(card, 0.6)
                owner = card.get_by_role("combobox")
                show(owner, 0.3)
                owner.select_option(label="Rajesh Iyer")
                expect(owner).to_have_value(re.compile(".+"))
                show(card, 1.5)
            scene(11, assign_clean)

            def reviewer_evidence():
                login("reviewer@apex.com")
                card = page.locator(".case-card").filter(has_text="APP-2026-PROP-001")
                click(card.get_by_role("button", name="Open case"), 0.2)
                show(page.get_by_role("heading", name=re.compile("Statutory Compliance")), 0.9)
                click(page.get_by_role("button", name=re.compile(r"C\. Documents")), 0.2)
                show(page.get_by_role("button", name=re.compile(r"C\. Documents")), 2.5)
                click(page.get_by_role("button", name=re.compile(r"D\. 4-Layer Validation")), 0.2)
                show(page.get_by_role("button", name=re.compile(r"D\. 4-Layer Validation")), 2.5)

            def reviewer_decision():
                click(page.get_by_role("button", name=re.compile(r"A\. Overview")), 0.2)
                approve = page.get_by_role("button", name="Approve Vendor", exact=True)
                expect(approve).to_be_enabled()
                click(approve, 0.3)
                page.get_by_placeholder("Optional approval notes or internal reference...").fill("Reviewed the submitted evidence and completed checks.")
                click(page.get_by_role("button", name="Confirm Approval"), 0.4)
                page.get_by_text("Formal Approval Recorded").wait_for(timeout=25000)
                page.wait_for_timeout(800)
            scene(12, reviewer_evidence)
            scene(13, reviewer_decision)

            def supplier_decision():
                login("vendor@apexcomponents.com")
                approved = page.get_by_role("heading", name="Onboarding Application Approved!")
                approved.wait_for()
                show(approved, 0.9)
                click(page.get_by_role("button", name="Notifications", exact=True), 0.2)
                click(page.get_by_role("button", name=re.compile("Open: Application Approved")), 0.2)
                show(page.get_by_text("Your onboarding application is complete. You have no further tasks in this application."), 1.0)
            scene(14, supplier_decision)

            def submit_gst_conflict():
                login("vendor.mismatch@sharmaworks.in")
                click(page.get_by_role("button", name=re.compile("Step 7")), 0.2)
                show(page.get_by_role("heading", name="Step 7: Review and Submit"), 1.0)
                for checkbox in page.locator("input[type=checkbox]").all():
                    if not checkbox.is_checked():
                        checkbox.check()
                show(page.get_by_role("button", name="Submit Application for Review"), 0.8)
                click(page.get_by_role("button", name="Submit Application for Review"), 0.4)
                page.get_by_text("APPLICATION STATUS: ACTION NEEDED", exact=False).wait_for(timeout=60000)
                show(page.get_by_text("GSTIN Embedded PAN Differs from Declared Business PAN", exact=False).first, 2.0)
                with SessionLocal() as proof:
                    conflict = proof.get(Application, "app-mism-002")
                    assert conflict.status in ("ACTION_REQUIRED", "SUBMITTED", "UNDER_REVIEW")
                    assert proof.query(ValidationRun).filter_by(application_id=conflict.id).count() >= 1
            scene(15, submit_gst_conflict)

            def gst_correction():
                login("vendor.mismatch@sharmaworks.in")
                show(page.get_by_text("What to do").first, 3.0)
                correction = page.get_by_label("Correct GSTIN")
                click(correction, 1.2)
                correction.fill("27AAPFU0938L1ZV")
                note = page.get_by_placeholder("Tell the reviewer what you changed")
                click(note, 0.2)
                note.fill("I checked the GST certificate and corrected the GSTIN to match the PAN on this application.")
                click(page.get_by_role("button", name="Send response"), 0.3)
                page.get_by_role("heading", name=re.compile("Responses Submitted")).wait_for(timeout=60000)
                show(page.get_by_role("heading", name=re.compile("Responses Submitted")), 1.5)
                page.wait_for_timeout(1000)
            scene(16, gst_correction)

            def reviewer_reply():
                login("reviewer@apex.com")
                card = page.locator(".case-card").filter(has_text="APP-2026-MISM-002")
                expect(card).to_contain_text("Vendor replied")
                click(card.get_by_role("button", name="Open case"), 0.2)
                reply = page.get_by_role("heading", name="Vendor responses to review")
                reply.wait_for()
                show(reply, 2.0)
                show(page.get_by_text("I checked the GST certificate and corrected the GSTIN to match the PAN on this application."), 2.0)
                show(page.get_by_role("button", name="Review evidence and record resolution"), 1.5)
            scene(17, reviewer_reply)

            def open_conflict_history():
                login("procurement@apex.com")
                click(page.get_by_role("button", name="Verification history"), 0.2)
                rows = page.get_by_role("row").filter(has_text="APP-2026-MISM-002")
                expect(rows.first).to_be_visible()
                show(rows.first, 0.7)
                click(rows.last.get_by_role("button", name="Inspect run"), 0.2)
                show(page.get_by_role("heading", name="What the checks found"), 1.0)
                show(page.locator("article").filter(has_text=re.compile("GSTIN Embedded PAN|embedded PAN")).first, 1.1)

            def open_timeout_history():
                close = page.get_by_role("button", name="Close")
                if close.count():
                    click(close.last, 0.2)
                warning_rows = page.get_by_role("row").filter(has_text="APP-2026-WARN-003")
                expect(warning_rows.first).to_be_visible()
                click(warning_rows.first.get_by_role("button", name="Inspect run").first, 0.2)
                show(page.get_by_role("heading", name="What the checks found"), 0.7)
                show(page.get_by_text("sample verification service could not respond", exact=False).first, 1.2)
            scene(18, open_conflict_history)
            scene(19, open_timeout_history)

            def close_on_sign_in_page():
                modal_close = page.get_by_role("button", name="Close")
                if modal_close.count():
                    click(modal_close.last, 0.3)
                signout = page.get_by_title("Sign out of your session")
                click(signout, 0.3)
                page.get_by_role("heading", name="Sign in").wait_for()
                show(page.get_by_role("heading", name="Sign in"), 1.2)
                show(page.get_by_text("Vikram Malhotra", exact=True), 0.8)
                show(page.get_by_text("Zoya Akhtar", exact=True), 0.8)
                page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
                page.wait_for_timeout(600)
            scene(20, close_on_sign_in_page)
            video = page.video
            page.close()
            context.close()
            raw = Path(video.path())
            browser.close()

        def relative(item):
            return item - first_start[0]

        duration = relative(timeline[-1]["end"])
        assert duration < 300, f"Recording exceeded five minutes: {duration:.1f}s"
        captions = []
        guide = ["# Zamp walkthrough — Rafad's voiceover", "", "Read naturally. The subtitles in the silent video follow these exact words. Fine-tune their timing after recording your voice.", ""]
        for scene_data, item in zip(SCENES, timeline):
            start = relative(item["start"])
            end = relative(item["end"])
            guide.extend([f"## {int(start)//60:02}:{int(start)%60:02} — {scene_data['title']}", "", scene_data["words"], ""])
            groups = caption_chunks(scene_data["words"])
            total = sum(len(group.split()) for group in groups)
            previous = 0
            for group in groups:
                now = previous + len(group.split())
                cue_start = start + (end - start) * previous / total
                cue_end = start + (end - start) * now / total
                captions.append(f"{len(captions)+1}\n{stamp(cue_start)} --> {stamp(cue_end)}\n{group}\n")
                previous = now
        subtitle_path = OUTPUT / "zamp-rafad-walkthrough.srt"
        subtitle_path.write_text("\n".join(captions), encoding="utf-8")
        (OUTPUT / "zamp-rafad-voiceover.md").write_text("\n".join(guide), encoding="utf-8")
        result = {
            "duration_seconds": round(duration, 2),
            "source": "real browser UI in isolated seeded database",
            "format": "silent MP4 with selectable English subtitles plus separate editable SRT",
            "fresh_clean_submission": True,
            "supplier_approval_notice": True,
            "vendor_ocr_correction_saved": True,
            "gstin_pan_conflict_submitted_live": True,
            "gstin_correction_response_submitted": True,
            "reviewer_reply_visible": True,
            "registry_timeout_contrast_visible": True,
            "scenes": [{"title": x["title"], "start": round(relative(x["start"]), 2), "end": round(relative(x["end"]), 2), "action_seconds": x["actual_actions"]} for x in timeline],
        }
        (OUTPUT / "recording-results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        destination = OUTPUT / "zamp-vendor-onboarding-walkthrough.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-ss", str(first_start[0]-video_start), "-i", str(raw),
             "-i", str(subtitle_path), "-t", str(duration), "-map", "0:v:0", "-map", "1:s:0", "-an",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
             "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-metadata:s:s:0",
             "title=English captions (editable SRT)", "-disposition:s:0", "default", "-movflags", "+faststart",
             str(destination)],
            cwd=ROOT, check=True,
        )
        print(json.dumps({"video": str(destination), "subtitles": str(subtitle_path), "duration": duration}, indent=2), flush=True)
    finally:
        server.should_exit = True
        thread.join(3)
        engine.dispose()
        os.chdir(ROOT)
