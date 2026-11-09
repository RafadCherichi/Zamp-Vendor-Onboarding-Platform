# Synthetic vendor dataset

Open [vendor_scenario_dataset.xlsx](vendor_scenario_dataset.xlsx). The **Cases** tab contains 14 labelled, synthetic vendor cases, prewritten expected checks and decisions, observed results, and evidence references. The **Overview** tab explains the comparison. Excel recalculates the PASS/REVIEW/NOT RUN formulas when opened.

To reproduce with the project's backend virtual environment from the repository root:

```powershell
& .\backend\.venv\Scripts\python.exe testdata/run_scenarios.py
& .\backend\.venv\Scripts\python.exe testdata/build_vendor_dataset.py
```

The runner creates a disposable SQLite database and upload directory. It exercises authenticated application requests, including fresh upload, validation, correction and review. It does not alter the project's operational database. The workbook builder requires `openpyxl`; install it in the virtual environment if absent. For the full backend suite run `testdata/run_regression.py`; for the built frontend's sampled screens run `testdata/verify_ui.py`. `testdata/verify_fresh_browser.py` takes a new vendor through the form and checks the saved result against the staff queue.

The [live demo](../grade_evidence/zamp-live-demo-narrated.mp4) is an actual browser recording in a disposable database. It visibly signs in as each role, submits a clean case, records a human approval, submits a previously unchecked GSTIN/PAN conflict, and shows the correction and saved finding. English subtitles are burned into the picture. The [voiceover-ready copy](../grade_evidence/zamp-live-demo-voiceover-ready.mp4) has the same subtitles and no narration.

To remake the video, install `requirements-tools.txt`, then run `generate_live_narration.py`, `record_live_demo.py`, `finish_live_demo.py`, and `build_voiceover_guide.py` in that order. The voice generator uses an online neural service; the recording uses the project's built frontend and backend in an isolated browser. It does not use the user's Chrome session or change the hosted demo data.

V06–V08 are form validation and checklist coverage, not end-to-end approvals. V13 verifies that a declared MSME cannot submit without Udyam proof. Registry checks are simulated. Names, identifiers and bank details are synthetic. A PASS means the written scenario expectation matched the observed output; it does not mean the prototype has been validated with real vendors or official registries.
