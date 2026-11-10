# Zamp Vendor Onboarding Platform

An India-focused vendor onboarding prototype for the PS-2 case study. Zamp helps suppliers submit business details and evidence, helps buyer teams compare the two, and keeps clarification and final decisions traceable. Automated checks support the review; a human reviewer makes the final decision.

## Evaluator quick start

- **Live demo:** [Open the Zamp prototype](https://zamp-vendor-onboarding-5i4e.onrender.com/). The free service may take about a minute to wake; its demo data can reset after a restart.
- **Walkthrough video:** [Watch the narrated walkthrough with captions](submission/demo/zamp-vendor-onboarding-walkthrough-with-voice-and-captions.mp4). Editable captions are in [SRT format](submission/demo/zamp-rafad-voice-recording-timed.srt).
- **Demo guide:** [How the walkthrough works](submission/demo/README.md).
- **Health check:** [API health](https://zamp-vendor-onboarding-5i4e.onrender.com/api/health).
- **Demo accounts:** `admin@apex.com`, `procurement@apex.com`, `reviewer@apex.com`, and `vendor@apexcomponents.com`; password `Password123!`. The login screen also offers demo-profile shortcuts.
- **Try:** inspect a clean case, a vendor clarification/correction, and a case with a cross-field identity conflict or uncertain evidence. Processing Runs retains each check result for staff review.
- **Data disclosure:** vendor documents and external PAN/GST/MCA/Udyam/bank responses are synthetic simulations. They do not represent official registry verification.

## Product and case-study evidence

- [Candidate guide and extracted text](docs/case-study/)
- [Product specification, rubric, score and traceability](docs/product/)
- [Decision note](docs/case-study/decision-note.md)
- [Completion and iteration reports](docs/reports/)
- [Demo runbook and setup](docs/demo/)
- [Hosting and local setup](docs/operations/)
- [Acceptance and UX screenshots](docs/evidence/)
- [Synthetic vendor scenarios and results](testdata/)

The latest internal grade is an evidence-based diagnostic, not an official evaluator score. It records its uncertainty and limits in [the grade report](docs/product/prototype-grade.md).

## Run locally

### Prerequisites

- Python 3.11 or 3.12
- Node.js 18+ and npm

### Quick launch on Windows

Run `scripts/local/start_prototype.ps1` (PowerShell) or `scripts/local/start_prototype.bat` (Command Prompt). The first launch installs dependencies and prepares the local demo database. It opens the frontend at `http://127.0.0.1:5173`; the API runs at `http://127.0.0.1:8000`.

For manual setup, see [Local setup](docs/operations/local-setup.md). Deployment settings are in [`render.yaml`](render.yaml), and hosting notes are in [Hosting](docs/operations/hosting.md).

## Project map

```text
backend/                 FastAPI service, domain logic, migrations and backend tests
frontend/                React application
scripts/local/           Windows local launchers
scripts/validation/      Browser acceptance and UX inspection scripts
testdata/                Synthetic vendor cases, scenario runner and results
demo_documents/           Synthetic evidence used by seeded demo cases
docs/case-study/         Case study source and product decision
 docs/demo/              Walkthrough script, runbook and fixtures guide
 docs/product/            Specification, rubric, grade and design review
 docs/reports/            Completion and iteration reports
 docs/operations/         Local setup and hosting guidance
 docs/evidence/           Acceptance and UX screenshot sets
submission/demo/          Final narrated video, editable subtitles and script
```

All example people, organizations, identifiers and documents are synthetic. Do not use them as real compliance evidence.
