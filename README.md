# Vendor Onboarding Platform (India Edition)

> **Invitation-first • AI-assisted • Human-controlled**  
> *"Collect the right information once, check it consistently, explain what is wrong, make corrections easy, and give reviewers traceable evidence for decisions."*

This repository implements the India-focused Vendor Onboarding Platform based on the **Final Consolidated Product Specification (Version 1.0)**.

## PS-2 evaluator quick start

- **Live demo:** [zamp-vendor-onboarding-5i4e.onrender.com](https://zamp-vendor-onboarding-5i4e.onrender.com/). The free service may take about a minute to wake and its local demo data can reset after a restart.
- **Narrated video (under five minutes):** [Watch or download the submission demo](grade_evidence/zamp-submission-demo.mp4) and [read its captions](grade_evidence/zamp-submission-demo.srt). It shows a live clean submission, procurement assignment, human approval, vendor notice, a fresh GSTIN/PAN conflict submission, correction and saved run history.
- **Health check:** [open `/api/health`](https://zamp-vendor-onboarding-5i4e.onrender.com/api/health). A healthy response reports the database and upload storage status.
- **Try the workflow:** sign in as a seeded procurement or reviewer user, inspect the clean case, then open the bank-conflict case and its vendor correction. Use **Processing Runs** to inspect persisted validation output. The clean vendor portal can be used to inspect the result and next step.
- **Demo roles:** `procurement@apex.com` and `reviewer@apex.com`; password `Password123!`.
- **What is simulated:** PAN/GST/MCA/Udyam/bank registry responses are synthetic. Human reviewers remain responsible for the final approval or rejection.
- **Recording setup:** The video uses the same built frontend and backend in a disposable local database. The GST conflict draft has no validation run before the recorded submission; its sole failed check is the embedded PAN mismatch. The registry timeout is a separate prepared example.
- **Grading and evidence:** [PS-2 rubric](PROTOTYPE_GRADING_RUBRIC.md), [current grade](PROTOTYPE_GRADE.md), [decision note](CASE_STUDY_DECISION_NOTE.md), [scenario workbook](testdata/vendor_scenario_dataset.xlsx), and [scenario results](testdata/scenario_results.json).

The Render service follows the `main` branch. Confirm the latest deployment before using the public link for evaluation; the free tier uses temporary local storage and SQLite.

---

## 1. Architecture & Security Overview

- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4 (Role-aware application shell, unified single-page layout with role-specific workspaces).
- **Backend**: Python 3.12 + FastAPI (Asynchronous REST API, Pydantic v2 schemas, strict type safety, CORS security, JWT session tokens).
- **Identity & RBAC**: Backend-enforced role-based access control with 4 roles:
  1. **Administrator**
  2. **Procurement Officer**
  3. **Reviewer / Approver**
  4. **Vendor**
- **Organisation-Level Data Isolation**: All invitation, application, and member queries are scoped to the authenticated user's `organisation_id`. Cross-tenant queries are blocked with HTTP 404/403.
- **Invitation-First Security**: Vendor onboarding starts exclusively via buyer invitation. Only a SHA-256 hash of the cryptographically random token (`secrets.token_urlsafe(32)`) is stored in the database. Raw tokens are never logged or persisted.
- **Database**: PostgreSQL (production/staging) with SQLAlchemy 2.0 and Alembic migrations; zero-dependency SQLite fallback (`vendor_onboarding.db`) for immediate local evaluation.
- **Object Storage**: Private, isolated object storage adapter interface (`StorageAdapter`) with local and Supabase Storage / S3 implementations.

---

## 2. Seeded Demo Accounts (Development & Evaluation)

All seeded accounts use password: **`Password123!`** (stored as bcrypt hash).

| Organisation | Role | Name | Email | Password | Test Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Apex Enterprises Ltd.** | **Administrator** | Aditya Sharma | `admin@apex.com` | `Password123!` | Organisation settings & policy oversight |
| **Apex Enterprises Ltd.** | **Procurement Officer** | Pooja Verma | `procurement@apex.com` | `Password123!` | Create, list & revoke vendor invitations |
| **Apex Enterprises Ltd.** | **Reviewer / Approver** | Rajesh Iyer | `reviewer@apex.com` | `Password123!` | Application review queue & audit authority |
| **Apex Enterprises Ltd.** | **Vendor** | Vikram Malhotra | `vendor@apexcomponents.com` | `Password123!` | Scoped vendor portal access |
| **Zenith Global Corp** | **Procurement (Tenant B)** | Zoya Akhtar | `procurement@zenith.com` | `Password123!` | **Cross-tenant isolation test** (cannot see or revoke Apex invitations) |

> **Interactive Quick-Login**: On the frontend login page, click any of the pre-filled role buttons to instantly authenticate as that user.

---

## 3. Role-Permission Matrix

| Action / Resource | Vendor | Procurement Officer | Reviewer / Approver | Administrator |
| :--- | :---: | :---: | :---: | :---: |
| **Sign in / View Profile** | ✅ | ✅ | ✅ | ✅ |
| **Issue Vendor Invitation** | ❌ (403) | ✅ (Own Org) | ❌ (403) | ✅ (Own Org) |
| **List Invitations** | ❌ (403) | ✅ (Own Org) | ✅ (Own Org) | ✅ (Own Org) |
| **Revoke Invitation** | ❌ (403) | ✅ (Own Org) | ❌ (403) | ✅ (Own Org) |
| **Validate Public Invitation Token** | ✅ (Public) | ✅ (Public) | ✅ (Public) | ✅ (Public) |
| **Access Another Organisation's Data**| ❌ (404/403) | ❌ (404/403) | ❌ (404/403) | ❌ (404/403) |
| **Manage Organisation Settings** | ❌ (403) | ❌ (403) | ❌ (403) | ✅ (Own Org) |

---

## 4. Setup and Execution Instructions

### Backend Setup

1. **Activate virtual environment**:
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run database migrations**:
   ```powershell
   alembic upgrade head
   ```

4. **Seed demo organisations and accounts**:
   ```powershell
   $env:PYTHONPATH='backend'
   python app/db/seed.py
   ```

5. **Start FastAPI backend server**:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health Diagnostic Endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Frontend Setup

1. **Navigate to the frontend directory and install dependencies**:
   ```powershell
   cd frontend
   npm.cmd install
   ```

2. **Start the development server**:
   ```powershell
   npm.cmd run dev
   ```
   - Application URL: [http://localhost:5173](http://localhost:5173)

---

## 5. Verification & Testing

### Running All Backend Tests (Auth, RBAC, Scoping, Vendor Onboarding, OCR & Document Extraction)
From the project root:
```powershell
$env:PYTHONPATH='backend'
backend\.venv\Scripts\pytest.exe backend/tests -v
```
*Current checked-in development suite: 118 passing tests, with one dependency deprecation warning. The case-study scenario runner and browser verification are separate; see the current grade and progress ledger.*

### Running Frontend Type-Check & Production Build
From the `frontend` directory:
```powershell
npm.cmd run build
```

---

## 6. Increment 2 & 3 Features: Vendor Onboarding, OCR & Document Understanding

### 1. Vendor Onboarding Wizard & Dynamic Checklist
- **6-Step Progress Stepper**: Business Identity, Tax & Compliance (with PAN 4th character validation against constitution), Authorised Contact, Banking Details (IFSC validation), Business Classification, and Dynamic Document Checklist.
- **Conditional Document Checklist**: Evaluates mandatory vs optional documents based on legal constitution (Proprietorship, Partnership, LLP, Company), GST status, Udyam MSME status, and commercial activity categories.
- **Draft Persistence & Locking**: Auto-save on section transition; submitted applications are locked against edits.

### 2. Document Processing Pipeline, OCR & AI Extraction (Increment 3)
- **Dual-Path Text & OCR Engine**:
  - Digital PDFs: Extracts selectable text and page layout via `pypdf` for pristine accuracy.
  - Scanned Documents & Images (JPEG, PNG): Neural visual OCR via `rapidocr-onnxruntime` running locally offline with zero external C++ dependencies.
- **Statutory Document Classifier**:
  - Automatically identifies document type (`PAN_PROOF`, `GST_CERTIFICATE`, `BANK_PROOF`, `UDYAM_CERTIFICATE`, `CONSTITUTION_PROOF`, `SIGNATORY_PROOF`, `INDUSTRY_LICENCE`).
  - Evaluates matching confidence and detects mismatches (e.g. uploading a GST certificate to a PAN card slot flags `is_type_match == False` and transitions status to `NEEDS_REVIEW`).
- **Structured Field Extraction**:
  - Dedicated extractors per statutory document extracting compliance fields with field-level confidence (0.0 to 1.0), normalization, page numbers, and evidence text context.
- **Pluggable AI & Fallback Architecture**:
  - Provider interface (`BaseExtractionProvider`) with `LocalDeterministicProvider` (offline, instant, deterministic regex & layout heuristics) and `GeminiExtractionProvider` (activated if `GEMINI_API_KEY` is present; protected with delimiter safeguards against prompt injection; transparent local fallback).
- **Security & Privacy Safeguards**:
  - All files stored in private object storage (`./storage_uploads`).
  - Sensitive identifiers (PAN and Bank Account Number) are masked in API summaries (`AA*****8L`, `****1234`) with a client-side unmask toggle in the inspection drawer.
  - Never logs or exposes raw file contents or secret keys.
- **UI Inspection Modal**:
  - Side-by-side view with visual document streaming on the left and extracted compliance metadata, classification evidence, review flags, and reprocess actions on the right.

### 3. Seeded Synthetic Demo Documents (`./demo_documents/`)
1. `synthetic_pan_card.pdf` & `synthetic_pan_card.png` (PAN `AAPFU0938L`, Vikram Malhotra)
2. `synthetic_gst_certificate.pdf` (Form GST REG-06, GSTIN `27AAPFU0938L1ZV`)
3. `synthetic_cancelled_cheque.png` (HDFC Bank, IFSC `HDFC0000123`, A/c `9876543210123`)
4. `synthetic_udyam_certificate.pdf` (Udyam `UDYAM-MH-02-0012345`, Micro Manufacturing)
5. `synthetic_coi_certificate.pdf` (MCA COI, CIN `U72200KA2020PTC123456`, Zenith Cloud Systems)
6. `synthetic_unreadable_noise.png` (Noisy pixel blur verifying `NEEDS_REVIEW` / `is_unreadable: true`)

---

## 7. Current case-study scope and verification

The prototype currently covers the PS-2 path from invitation and vendor submission through document processing, saved validation results, vendor correction, reviewer decision, and procurement run history. Processing Runs opens the exact saved findings and links back to the current case. Approval remains human controlled; external registry responses are labelled as simulated.

- **Regression suite:** 118 backend tests pass in the isolated development test database; one dependency deprecation warning remains.
- **Scenario set:** 14 synthetic vendor case IDs across company, proprietor, partnership and LLP rules; 15 result records because the bank mismatch case includes multiple correction attempts. Current expected-result assertions pass in [`testdata/scenario_results.json`](testdata/scenario_results.json).
- **Browser checks:** fresh submission/refresh/reviewer decision and 390px responsive vendor views are recorded in [`testdata/fresh_browser_results.json`](testdata/fresh_browser_results.json) and [`testdata/ui_results.json`](testdata/ui_results.json).
- **Limits:** the public Render free tier uses temporary local SQLite and file storage; records can reset after restart. Synthetic cases do not establish real-world accuracy. Keyboard-only usability and first-time-user comprehension still need a human review.

For score details and evidence, see [`PROTOTYPE_GRADE.md`](PROTOTYPE_GRADE.md) and [`PROTOTYPE_GRADING_RUBRIC.md`](PROTOTYPE_GRADING_RUBRIC.md). The narrated demo still needs a timed rehearsal before claiming submission readiness.
