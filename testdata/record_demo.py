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
            context = browser.new_context(viewport={"width":1280,"height":800}, record_video_dir=str(OUTPUT), record_video_size={"width":1280,"height":800}, reduced_motion="reduce")
            page = context.new_page()
            clock_start = time.monotonic()
            page.set_default_timeout(20000)
            base = f"http://127.0.0.1:{port}/"
            def login(email):
                page.goto(base)
                if page.get_by_title("Sign out of your session").count():
                    page.get_by_title("Sign out of your session").click()
                page.locator('input[type=email]').fill(email)
                page.locator('input[type=password]').fill('Password123!')
                page.locator('button[type=submit]').click()
                page.get_by_title('Sign out of your session').wait_for()
            def scene(index, action):
                print(f"Scene {index + 1}: {scenes[index]['title']}", flush=True)
                start = time.monotonic()
                timeline.append({"title":scenes[index]["title"],"start":start-clock_start,"duration":scenes[index]["duration"]})
                action()
                remaining = scenes[index]['duration'] + 1 - (time.monotonic()-start)
                if remaining > 0:
                    page.wait_for_timeout(remaining*1000)
            login('vendor@apexcomponents.com')
            def fill_vendor():
                page.get_by_role('button',name=re.compile('Fill with demo data: Apex Components')).click()
                page.get_by_role('status').filter(has_text='ready to review').wait_for(timeout=60000)
                page.get_by_role('button',name=re.compile('Step 7')).click()
            scene(0, fill_vendor)
            def submit_vendor():
                for checkbox in page.locator('input[type=checkbox]').all():
                    checkbox.check()
                page.get_by_role('button',name='Submit Application for Review').click()
                page.get_by_text('Thank You! Application Submitted Successfully').wait_for()
            scene(1, submit_vendor)
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
            def correct_bank():
                login('vendor.mismatch@sharmaworks.in')
                page.get_by_label('Correct Bank Account Number').fill('60200012345678')
                page.get_by_placeholder('Tell the reviewer what you changed').fill('Corrected the number to match my uploaded cheque.')
                page.get_by_role('button',name='Send response').click()
                page.get_by_role('heading',name=re.compile('Responses Submitted')).wait_for()
            scene(5, correct_bank)
            def inspect_reply():
                login('reviewer@apex.com')
                card = page.locator('.case-card').filter(has_text='APP-2026-MISM-002')
                expect(card).to_contain_text('Vendor replied')
                card.get_by_role('button',name='Open case').click()
                page.get_by_role('heading',name='Vendor responses to review').wait_for()
                page.get_by_role('heading',name='Vendor responses to review').scroll_into_view_if_needed()
            scene(6, inspect_reply)
            scene(7, lambda: None)
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
        result = {'duration_seconds':round(duration,1),'within_five_minutes':True,'fresh_ui_submission':True,'procurement_assignment':True,'happy_decision_recorded':True,'vendor_notice_opened':True,'edge_response_saved':True,'reviewer_reply_visible':True,'narration':'Windows system speech; script in demo_script.json','recording':str(destination),'scenes':timeline}
        (ROOT/'testdata/demo_rehearsal_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)
    finally:
        server.should_exit = True
        thread.join(2)
        engine.dispose()
        os.chdir(ROOT)
