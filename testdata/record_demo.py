from browser_support import launch_browser
"""Record a narrated browser rehearsal using a disposable seeded database."""

import json
import re
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

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
    # Prepare a complete draft in a separate buyer workspace. No validation
    # result or issue exists until the on-camera Submit action.
    from app.database import SessionLocal
    from app.db.seed_demo import seed_document
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.member import OrganisationMember
    from app.models.vendor import Vendor
    from app.models.application import Application
    from app.models.validation import ValidationRun
    from app.models.exception import OnboardingException
    from app.core.security import hash_password
    from app.services.checklist import sync_application_documents
    from app.utils.synthetic_docs import generate_all_demo_documents
    with SessionLocal() as db:
        clean = db.get(Application, 'app-clean-001')
        buyer = Organization(name='Meridian Buyer Group', slug='meridian-video-demo')
        db.add(buyer)
        db.flush()
        password_hash = hash_password('Password123!')
        for email, name, role in [
            ('procurement@meridian-demo.in', 'Meera Singh', 'procurement_officer'),
            ('reviewer@meridian-demo.in', 'Aarav Nair', 'reviewer'),
            ('vendor.gst@meridian-demo.in', 'Ratan Verma', 'vendor'),
        ]:
            user = User(email=email, full_name=name, hashed_password=password_hash, is_active=True)
            db.add(user)
            db.flush()
            db.add(OrganisationMember(user_id=user.id, organisation_id=buyer.id, role=role, is_active=True))
            if role == 'vendor': vendor_user = user
            if role == 'reviewer': edge_reviewer = user
        vendor = Vendor(organisation_id=buyer.id, created_by_user_id=vendor_user.id,
                        legal_name=clean.legal_name, trade_name=clean.trade_name,
                        constitution=clean.constitution, pan=clean.pan)
        db.add(vendor)
        db.flush()
        copied = {column.name: getattr(clean, column.name) for column in Application.__table__.columns
                  if column.name not in {'id', 'reference_number', 'organisation_id', 'vendor_id',
                  'created_by_user_id', 'status', 'submitted_at', 'assigned_reviewer_id',
                  'assigned_at', 'reviewed_by_user_id', 'reviewed_at', 'decision_notes',
                  'rejection_reason', 'clarification_requested_at', 'created_at', 'updated_at'}}
        copied.update(reference_number='APP-2026-VIDEO-GST', organisation_id=buyer.id,
                      vendor_id=vendor.id, created_by_user_id=vendor_user.id,
                      status='IN_PROGRESS', gstin='29BBBCA5678B1ZM',
                      contact_email=vendor_user.email)
        edge = Application(**copied)
        db.add(edge)
        db.flush()
        sync_application_documents(db, edge)
        docs = generate_all_demo_documents('./demo_documents')
        for slot, key in [('PAN_PROOF','pan_tata_pdf'),('GST_CERTIFICATE','gst_tata_pdf'),
                          ('BANK_PROOF','bank_tata_pdf'),('CONSTITUTION_PROOF','coi_tata_pdf'),
                          ('SIGNATORY_PROOF','board_res_tata_pdf')]:
            seed_document(db, edge, slot, docs[key], 'application/pdf', Path(docs[key]).name, vendor_user.id)
        db.commit()
        assert db.query(ValidationRun).filter_by(application_id=edge.id).count() == 0
        assert db.query(OnboardingException).filter_by(application_id=edge.id).count() == 0
        print('Prepared GST conflict draft without validation or exceptions', flush=True)
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
    import wave, subprocess
    import imageio_ffmpeg
    scenes = json.loads((ROOT / "testdata/demo_script.json").read_text(encoding="utf-8"))
    for index, scene in enumerate(scenes):
        scene["audio"] = str(OUTPUT / "narration" / f"scene-{index}.wav")
        with wave.open(scene["audio"]) as sound:
            scene["duration"] = sound.getnframes() / sound.getframerate()
    timeline = []
    try:
        with sync_playwright() as pw:
            from playwright.sync_api import expect
            browser = launch_browser(pw, headless=True)
            context = browser.new_context(viewport={"width":1280,"height":720}, record_video_dir=str(OUTPUT), record_video_size={"width":1280,"height":720}, reduced_motion="reduce")
            page = context.new_page()
            clock_start = time.monotonic()
            page.set_default_timeout(20000)
            base = f"http://127.0.0.1:{port}/"
            def login(email):
                # Authentication happens on a separate page whose recording is
                # discarded; credentials never appear in the final screen film.
                context.clear_cookies()
                auth = context.new_page()
                auth.goto(base)
                auth.evaluate('localStorage.clear()')
                auth.reload()
                auth.locator('input[type=email]').fill(email)
                auth.locator('input[type=password]').fill('Password123!')
                auth.locator('button[type=submit]').click()
                auth.get_by_title('Sign out of your session').wait_for()
                token = auth.evaluate("localStorage.getItem('token') || localStorage.getItem('vop_auth_token')")
                auth.close()
                page.goto(base)
                page.evaluate("([t]) => { localStorage.clear(); localStorage.setItem('token', t); localStorage.setItem('vop_auth_token', t); }", [token])
                page.reload()
                page.get_by_title('Sign out of your session').wait_for()
            def scene(index, action):
                print(f"Scene {index + 1}: {scenes[index]['title']}", flush=True)
                start = time.monotonic()
                timeline.append({"title":scenes[index]["title"],"start":start-clock_start,"duration":scenes[index]["duration"]})
                try:
                    action()
                except Exception:
                    print('Scene page text:', page.locator('body').inner_text()[-5000:], flush=True)
                    raise
                remaining = (0 if os.getenv('ZAMP_FAST_RECORD') else max(scenes[index]['duration'] + 0.5, scenes[index]['seconds'])) - (time.monotonic()-start)
                if remaining > 0:
                    page.wait_for_timeout(remaining*1000)
            login('vendor@apexcomponents.com')
            scene(0, lambda: page.get_by_role('button',name=re.compile('Fill with demo data: Apex Components')).wait_for())
            def clean_submission():
                page.get_by_role('button',name=re.compile('Fill with demo data: Apex Components')).click()
                page.get_by_role('status').filter(has_text='ready to review').wait_for(timeout=60000)
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4500)
                page.get_by_role('button',name=re.compile('Step 7')).click()
                for checkbox in page.locator('input[type=checkbox]').all():
                    checkbox.check()
                page.get_by_role('button',name='Submit Application for Review').click()
                page.get_by_text('Thank You! Application Submitted Successfully').wait_for()
            scene(1, clean_submission)
            def assign_case():
                login('procurement@apex.com')
                card = page.locator('.case-card').filter(has_text='APP-2026-PROP-001')
                card.get_by_role('combobox').select_option(label='Rajesh Iyer')
                expect(card.get_by_role('combobox')).to_have_value(re.compile('.+'))
                card.scroll_into_view_if_needed()
            scene(2, assign_case)
            def approve_case():
                login('reviewer@apex.com')
                page.locator('.case-card').filter(has_text='APP-2026-PROP-001').get_by_role('button',name='Open case').click()
                page.get_by_role('button',name=re.compile('C\\. Documents')).click()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(5000)
                page.get_by_role('button',name=re.compile('D\\. 4-Layer Validation')).click()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(5000)
                page.get_by_role('button',name=re.compile('A\\. Overview')).click()
                page.get_by_role('button',name='Approve Vendor',exact=True).click()
                page.get_by_placeholder('Optional approval notes or internal reference...').fill('Evidence reviewed. Onboarding approved for the demonstrated supplier.')
                page.get_by_role('button',name='Confirm Approval').click()
                page.get_by_text('Formal Approval Recorded').wait_for()
            scene(3, approve_case)
            def vendor_receipt():
                login('vendor@apexcomponents.com')
                page.get_by_role('heading',name='Onboarding Application Approved!').wait_for()
                page.get_by_role('button',name='Notifications',exact=True).click()
                page.get_by_role('button',name=re.compile('Open: Application Approved')).click()
                page.get_by_text('Your onboarding application is complete. You have no further tasks in this application.').wait_for()
            scene(4, vendor_receipt)
            def submit_gst_conflict():
                login('vendor.gst@meridian-demo.in')
                page.get_by_role('button',name=re.compile('Step 7')).click()
                page.get_by_text('29BBBCA5678B1ZM').scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(7000)
                page.get_by_role('button',name='Submit Application for Review').click()
                page.get_by_role('heading',name='Action Required on Your Application').wait_for()
                for _ in range(60):
                    with SessionLocal() as proof:
                        runs = proof.query(ValidationRun).filter_by(application_id=edge.id).all()
                        failed_checks = sorted({
                            f.check_id for run in runs for f in run.findings if f.status == 'FAILED'
                        })
                        conflict_found = any(
                            f.check_id == 'B_GSTIN_EMBEDDED_PAN_MATCH' and f.status == 'FAILED'
                            for run in runs for f in run.findings
                        )
                    if conflict_found:
                        break
                    time.sleep(0.5)
                assert conflict_found, f'GST conflict finding missing; run count={len(runs)}'
                assert failed_checks == ['B_GSTIN_EMBEDDED_PAN_MATCH'], failed_checks
                print(f'GST conflict generated live; {len(runs)} saved run(s); failed checks: {failed_checks}', flush=True)
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(6000)
                login('procurement@meridian-demo.in')
                card = page.locator('.case-card').filter(has_text='APP-2026-VIDEO-GST')
                card.get_by_role('combobox').select_option(label='Aarav Nair')
                expect(card).to_contain_text('high priority')
                login('reviewer@meridian-demo.in')
                page.locator('.case-card').filter(has_text='APP-2026-VIDEO-GST').get_by_role('button',name='Open case').click()
                expect(page.get_by_role('button',name='Approve Vendor',exact=True)).to_be_disabled()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(3500)
                page.get_by_role('button',name=re.compile('E\\. Exceptions')).click()
                page.get_by_role('heading',name=re.compile('GSTIN Embedded PAN')).scroll_into_view_if_needed()
            scene(5, submit_gst_conflict)
            def correct_gst():
                login('vendor.gst@meridian-demo.in')
                page.get_by_label('Correct Gstin').fill('29AAACZ1234K1Z5')
                page.get_by_placeholder('Tell the reviewer what you changed').fill('I corrected the GST number to match this company PAN.')
                page.get_by_role('button',name='Send response').click()
                page.get_by_role('heading',name=re.compile('Responses Submitted')).wait_for()
                login('reviewer@meridian-demo.in')
                card = page.locator('.case-card').filter(has_text='APP-2026-VIDEO-GST')
                expect(card).to_contain_text('Vendor replied')
                card.get_by_role('button',name='Open case').click()
                page.get_by_role('heading',name='Vendor responses to review').wait_for()
                page.get_by_role('heading',name='Vendor responses to review').scroll_into_view_if_needed()
            scene(6, correct_gst)
            def inspect_history():
                login('procurement@meridian-demo.in')
                page.get_by_role('button',name='Verification history').click()
                row = page.get_by_role('row').filter(has_text='APP-2026-VIDEO-GST').filter(has_text='Needs review').first
                row.get_by_role('button',name='Inspect run').click()
                finding = page.locator('article').filter(has_text='GSTIN Embedded PAN')
                expect(finding).to_contain_text('FAILED')
                finding.scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(9000)
                login('reviewer@apex.com')
                page.locator('.case-card').filter(has_text='APP-2026-WARN-003').get_by_role('button',name='Open case').click()
            scene(7, inspect_history)
            video = page.video
            page.close()
            context.close()
            source = Path(video.path())
            browser.close()
        trim = timeline[0]['start']
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        destination = OUTPUT / 'zamp-submission-demo.mp4'
        command = [ffmpeg,'-y','-ss',str(trim),'-i',str(source)]
        for item in scenes:
            command += ['-i',item['audio']]
        filters = []
        for index, item in enumerate(timeline):
            delay = round((item['start']-trim)*1000)
            filters.append(f'[{index+1}:a]adelay={delay}:all=1[a{index}]')
        filters.append(''.join(f'[a{i}]' for i in range(len(scenes)))+f'amix=inputs={len(scenes)}:duration=longest:normalize=0[audio]')
        command += ['-filter_complex',';'.join(filters),'-map','0:v','-map','[audio]','-c:v','libx264','-preset','fast','-crf','22','-c:a','aac','-b:a','128k','-movflags','+faststart','-shortest',str(destination)]
        subprocess.run(command,check=True,capture_output=True)
        duration = timeline[-1]['start']-trim+scenes[-1]['duration']
        assert duration <= 300, duration
        result = {'duration_seconds':round(duration,1),'within_five_minutes':True,'fresh_ui_submission':True,'procurement_assignment':True,'happy_decision_recorded':True,'vendor_notice_opened':True,'draft_validation_runs_before_recording':0,'edge_failed_checks':['B_GSTIN_EMBEDDED_PAN_MATCH'],'edge_response_saved':True,'reviewer_reply_visible':True,'narration':'Synthetic voice; script in testdata/demo_script.json','recording':'grade_evidence/zamp-submission-demo.mp4','captions':'grade_evidence/zamp-submission-demo.srt','scenes':timeline}
        (ROOT/'testdata/demo_rehearsal_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
    finally:
        server.should_exit = True
        thread.join(2)
        engine.dispose()
        os.chdir(ROOT)
