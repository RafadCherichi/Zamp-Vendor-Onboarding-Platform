"""Film real browser interactions, including every role's sign-in screen."""

from browser_support import launch_browser

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
    scenes = json.loads((ROOT / "testdata/live_demo_script.json").read_text(encoding="utf-8"))
    for index, scene in enumerate(scenes):
        scene["audio"] = str(OUTPUT / "narration" / f"live-scene-{index}.wav")
        with wave.open(scene["audio"]) as sound:
            scene["duration"] = sound.getnframes() / sound.getframerate()
    timeline = []
    try:
        with sync_playwright() as pw:
            from playwright.sync_api import expect
            browser = launch_browser(pw, headless=True)
            context = browser.new_context(viewport={"width":1280,"height":720}, record_video_dir=str(OUTPUT), record_video_size={"width":1280,"height":720})
            context.add_init_script("""
                document.addEventListener('DOMContentLoaded', () => {
                  if (document.getElementById('demo-pointer')) return;
                  const pointer = document.createElement('div');
                  pointer.id = 'demo-pointer';
                  pointer.style.cssText = 'position:fixed;left:0;top:0;width:17px;height:17px;background:#f4bd49;border:2px solid #163d2a;border-radius:50%;box-shadow:0 0 0 4px #f4bd4960,0 2px 8px #0005;z-index:2147483647;pointer-events:none;transform:translate(-30px,-30px);transition:transform 100ms linear';
                  document.body.appendChild(pointer);
                  document.addEventListener('mousemove', e => {
                    pointer.style.transform = 'translate(' + (e.clientX - 8) + 'px,' + (e.clientY - 8) + 'px)';
                  });
                });
            """)
            page = context.new_page()
            page.set_default_timeout(20000)
            base = f"http://127.0.0.1:{port}/"
            page.goto(base)
            page.get_by_role('heading',name='Sign in').wait_for()
            clock_start = time.monotonic()
            def point(target):
                target.scroll_into_view_if_needed()
                box = target.bounding_box()
                assert box, f'Cannot point to {target}'
                page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=12)
            def show_click(target):
                point(target)
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(250)
                target.click()
            def login(email):
                sign_out = page.get_by_title('Sign out of your session')
                if sign_out.count():
                    show_click(sign_out)
                elif not page.get_by_role('heading',name='Sign in').count():
                    page.goto(base)
                page.get_by_role('heading',name='Sign in').wait_for()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(1700)
                if email.endswith('@apex.com') or email == 'vendor@apexcomponents.com':
                    show_click(page.locator('button').filter(has_text=email))
                else:
                    mail = page.locator('input[type=email]')
                    show_click(mail)
                    mail.press_sequentially(email, delay=18 if os.getenv('ZAMP_FAST_RECORD') else 32)
                    page.locator('input[type=password]').fill('Password123!')
                    show_click(page.locator('button[type=submit]'))
                page.get_by_title('Sign out of your session').wait_for()
                page.goto(base)
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
            def start_supplier():
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(2500)
                login('vendor@apexcomponents.com')
            scene(0, start_supplier)
            def clean_submission():
                show_click(page.get_by_role('button',name=re.compile('Fill with demo data: Apex Components')))
                page.get_by_role('status').filter(has_text='ready to review').wait_for(timeout=60000)
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4500)
                show_click(page.get_by_role('button',name=re.compile('Step 6')))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(5000)
                show_click(page.get_by_role('button',name=re.compile('Step 7')))
                for checkbox in page.locator('input[type=checkbox]').all():
                    checkbox.check()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4000)
                show_click(page.get_by_role('button',name='Submit Application for Review'))
                page.get_by_text('Thank You! Application Submitted Successfully').wait_for()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4300)
                page.get_by_role('heading',name='Application status').scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4000)
                page.get_by_role('heading',name='Thank You! Application Submitted Successfully').scroll_into_view_if_needed()
            scene(1, clean_submission)
            def assign_case():
                login('procurement@apex.com')
                card = page.locator('.case-card').filter(has_text='APP-2026-PROP-001')
                card.scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(5500)
                card.get_by_role('combobox').select_option(label='Rajesh Iyer')
                expect(card.get_by_role('combobox')).to_have_value(re.compile('.+'))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4400)
                page.get_by_role('heading',name='Keep each handoff moving').scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4400)
                card.scroll_into_view_if_needed()
            scene(2, assign_case)
            def approve_case():
                login('reviewer@apex.com')
                show_click(page.locator('.case-card').filter(has_text='APP-2026-PROP-001').get_by_role('button',name='Open case'))
                show_click(page.get_by_role('button',name=re.compile('C\\. Documents')))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(5500)
                show_click(page.get_by_role('button',name=re.compile('D\\. 4-Layer Validation')))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(5500)
                show_click(page.get_by_role('button',name=re.compile('A\\. Overview')))
                show_click(page.get_by_role('button',name='Approve Vendor',exact=True))
                page.get_by_placeholder('Optional approval notes or internal reference...').fill('Evidence reviewed. Onboarding approved for the demonstrated supplier.')
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(3600)
                show_click(page.get_by_role('button',name='Confirm Approval'))
                page.get_by_text('Formal Approval Recorded').wait_for()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4000)
                show_click(page.get_by_role('button',name=re.compile('G\\. Activity Trail')))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(3600)
                show_click(page.get_by_role('button',name=re.compile('A\\. Overview')))
            scene(3, approve_case)
            def vendor_receipt():
                login('vendor@apexcomponents.com')
                page.get_by_role('heading',name='Onboarding Application Approved!').wait_for()
                show_click(page.get_by_role('button',name='Notifications',exact=True))
                show_click(page.get_by_role('button',name=re.compile('Open: Application Approved')))
                page.get_by_text('Your onboarding application is complete. You have no further tasks in this application.').wait_for()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4200)
                page.get_by_role('heading',name='Application status').scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4000)
                page.get_by_role('heading',name='Onboarding Application Approved!').scroll_into_view_if_needed()
            scene(4, vendor_receipt)
            def edge_sign_in():
                login('vendor.gst@meridian-demo.in')
                show_click(page.get_by_role('button',name=re.compile('Step 2')))
                point(page.locator('input[placeholder="e.g. AAPFU0938L"]'))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(3000)
                point(page.locator('input[placeholder="e.g. 27AAPFU0938L1ZV"]'))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(2600)
            scene(5, edge_sign_in)
            def submit_gst_conflict():
                point(page.locator('input[placeholder="e.g. AAPFU0938L"]'))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(7800)
                point(page.locator('input[placeholder="e.g. 27AAPFU0938L1ZV"]'))
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(7800)
                show_click(page.get_by_role('button',name=re.compile('Step 7')))
                show_click(page.get_by_role('button',name='Submit Application for Review'))
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
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4200)
                page.get_by_role('heading',name=re.compile('GSTIN Embedded PAN')).scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4500)
                page.get_by_text('What to do').first.scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(3500)
                page.get_by_role('heading',name='Application status').scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4700)
                page.get_by_role('heading',name=re.compile('GSTIN Embedded PAN')).scroll_into_view_if_needed()
            scene(6, submit_gst_conflict)
            def edge_review():
                login('procurement@meridian-demo.in')
                card = page.locator('.case-card').filter(has_text='APP-2026-VIDEO-GST')
                card.get_by_role('combobox').select_option(label='Aarav Nair')
                expect(card).to_contain_text('high priority')
                login('reviewer@meridian-demo.in')
                show_click(page.locator('.case-card').filter(has_text='APP-2026-VIDEO-GST').get_by_role('button',name='Open case'))
                expect(page.get_by_role('button',name='Approve Vendor',exact=True)).to_be_disabled()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(1200)
                show_click(page.get_by_role('button',name=re.compile('E\\. Exceptions')))
                page.get_by_role('heading',name=re.compile('GSTIN Embedded PAN')).scroll_into_view_if_needed()
            scene(7, edge_review)
            def correct_gst():
                login('vendor.gst@meridian-demo.in')
                correction = page.get_by_label('Correct Gstin')
                correction.scroll_into_view_if_needed()
                show_click(correction)
                correction.press_sequentially('29AAACZ1234K1Z5',delay=25)
                page.get_by_placeholder('Tell the reviewer what you changed').fill('I corrected the GST number to match this company PAN.')
                show_click(page.get_by_role('button',name='Send response'))
                page.get_by_role('heading',name=re.compile('Responses Submitted')).wait_for()
                login('reviewer@meridian-demo.in')
                card = page.locator('.case-card').filter(has_text='APP-2026-VIDEO-GST')
                expect(card).to_contain_text('Vendor replied')
                show_click(card.get_by_role('button',name='Open case'))
                page.get_by_role('heading',name='Vendor responses to review').wait_for()
                page.get_by_role('heading',name='Vendor responses to review').scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4400)
                page.get_by_role('heading',name=re.compile('Statutory Compliance')).scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(3600)
                page.get_by_role('heading',name='Vendor responses to review').scroll_into_view_if_needed()
            scene(8, correct_gst)
            def inspect_history():
                login('procurement@meridian-demo.in')
                show_click(page.get_by_role('button',name='Verification history'))
                row = page.get_by_role('row').filter(has_text='APP-2026-VIDEO-GST').filter(has_text='Needs review').first
                show_click(row.get_by_role('button',name='Inspect run'))
                finding = page.locator('article').filter(has_text='GSTIN Embedded PAN')
                expect(finding).to_contain_text('FAILED')
                finding.scroll_into_view_if_needed()
                if not os.getenv('ZAMP_FAST_RECORD'): page.wait_for_timeout(4800)
                show_click(page.get_by_role('button',name='Close',exact=True))
                login('reviewer@apex.com')
                show_click(page.locator('.case-card').filter(has_text='APP-2026-WARN-003').get_by_role('button',name='Open case'))
            scene(9, inspect_history)
            video = page.video
            page.close()
            context.close()
            source = Path(video.path())
            browser.close()
        trim = timeline[0]['start']
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        destination = OUTPUT / 'zamp-live-demo-narrated.mp4'
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
        result = {'duration_seconds':round(duration,1),'within_five_minutes':True,'visible_role_sign_ins':True,'live_browser_recording':True,'fresh_ui_submission':True,'procurement_assignment':True,'happy_decision_recorded':True,'vendor_notice_opened':True,'draft_validation_runs_before_recording':0,'edge_failed_checks':['B_GSTIN_EMBEDDED_PAN_MATCH'],'edge_response_saved':True,'reviewer_reply_visible':True,'narration':'Optional neural guide; script in testdata/live_demo_script.json','recording':'grade_evidence/zamp-live-demo-narrated.mp4','scenes':timeline}
        (ROOT/'testdata/live_demo_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
    finally:
        server.should_exit = True
        thread.join(2)
        engine.dispose()
        os.chdir(ROOT)
