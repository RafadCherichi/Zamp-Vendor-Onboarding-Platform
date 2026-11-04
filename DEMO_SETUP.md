# Vendor Onboarding Platform — Demo Setup & Environment Guide

This document details all technical prerequisites, local environment configuration, pre-seeded accounts, canonical demo test cases, and reset instructions for running the Vendor Onboarding Platform demo.

---

## 1. Environment Prerequisites

Ensure the following runtimes and tools are installed:

- **Python:** 3.12+ (tested on Python 3.12.6)
- **Node.js:** 20+ (tested on Node v24.16.0 with npm 10.9.2)
- **Operating System:** Windows 10/11, macOS, or Ubuntu 22.04 LTS
- **Database:** SQLite (default for development and demo; zero-configuration local file)
- **Optical Character Recognition (OCR):** Tesseract OCR (optional local binary; falls back gracefully to synthetic text and regex parsing if binary is not on system path)

---

## 2. Quickstart Startup Guide

### Step 1: Backend API Server
In a terminal window:

```powershell
cd backend
# Activate virtual environment
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell
# source .venv/bin/activate    # On Linux/macOS

# Set python path and run FastAPI server on port 8000
$env:PYTHONPATH='backend'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API server will run at: `http://127.0.0.1:8000`  
Interactive OpenAPI Swagger docs: `http://127.0.0.1:8000/docs`

---

### Step 2: Frontend Web Application
In a second terminal window:

```powershell
cd frontend
# Install dependencies (if not already done)
npm install

# Start Vite development server on port 5173
npm run dev
```

The frontend will be accessible at: `http://localhost:5173`

---

## 3. Seed & Reset the Deterministic Demo Environment

The demo environment includes a dedicated seed script that creates clean, repeatable scenarios. You can reset and re-seed the environment in two ways:

### Option A: From the Web UI (1-Click)
1. Log into the application as an Administrator (`admin@apex.com` / `Password123!`).
2. Navigate to the **Admin Dashboard** (`/admin`).
3. Click the purple button: **"Reset & Re-Seed Demo"**.
4. The database is wiped and restored with all 3 canonical demo scenarios in under 1 second.

### Option B: From the Command Line
Run the seed script directly from the backend root:

```powershell
$env:PYTHONPATH='backend'
backend\.venv\Scripts\python.exe backend\app\db\seed_demo.py
```

### Option C: Via REST API
Send an authenticated or administrative HTTP POST request:

```bash
POST http://127.0.0.1:8000/api/v1/demo/reset
Content-Type: application/json
```

---

## 4. Pre-Seeded User Accounts & Roles

All pre-seeded accounts share the uniform default password: **`Password123!`**

| Role | Email | Password | Organisation | Description & Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin@apex.com` | `Password123!` | Apex Enterprises Ltd. | System administrator. Can reset demo, inspect queues, configure policies, and review applications. |
| **Procurement Officer** | `procurement@apex.com` | `Password123!` | Apex Enterprises Ltd. | Buyer procurement officer. Creates vendor invitations, tracks submission rates, inspects exceptions. |
| **Reviewer / Approver** | `reviewer@apex.com` | `Password123!` | Apex Enterprises Ltd. | Compliance reviewer. Inspects 7-section workspace, requests clarifications, resolves exceptions, approves/rejects. |
| **Procurement (Tenant B)** | `procurement@zenith.com` | `Password123!` | Zenith Dynamics Ltd. | Multi-tenant isolation test user. Cannot access Apex Enterprises vendors or applications. |
| **Vendor (Case 1)** | `vendor.clean@tatasupply.in` | `Password123!` | Apex Enterprises Ltd. | Vendor with clean, passing application ready for instant approval (`APP-2026-CLEAN-001`). |
| **Vendor (Case 2)** | `vendor.mismatch@sharmaworks.in` | `Password123!` | Apex Enterprises Ltd. | Vendor with bank account mismatch exception (`APP-2026-MISM-002`). |
| **Vendor (Case 3)** | `vendor.issue@apexlogistics.in` | `Password123!` | Apex Enterprises Ltd. | Vendor with external verification issue and duplicate candidate signal (`APP-2026-WARN-003`). |

---

## 5. Three Canonical Demo Cases

### Case 1: Clean Application Ready for Approval (Happy Path)
- **Reference Number:** `APP-2026-CLEAN-001`
- **Legal Name:** Tata Industrial Supplies Private Limited
- **Constitution:** Private Limited Company (`PVT_LTD`)
- **Status:** `UNDER_REVIEW`
- **Assigned Reviewer:** `reviewer@apex.com`
- **Validation Health:** 6 passed checks, 0 warnings, 0 failures across Layers A–D.
- **Active Exceptions:** 0 open exceptions.
- **Statutory Policy Gate:** **PASS (Eligible for immediate Approval)**.
- **Demonstration Value:** Proves straight-through processing for high-quality corporate suppliers.

---

### Case 2: Mismatch Exception Requiring Clarification & Correction
- **Reference Number:** `APP-2026-MISM-002`
- **Legal Name:** Sharma Engineering Works
- **Constitution:** Sole Proprietorship (`PROPRIETORSHIP`)
- **Status:** `ACTION_REQUIRED` (Vendor Clarification Requested)
- **Active Exception:** `EXC-B-MISM-002`
  - **Category:** `BANK_DETAIL_MISMATCH`
  - **Severity:** `HIGH`
  - **Description:** Form registered bank account differs from cancelled cheque MICR extraction.
  - **Reviewer Instructions:** *"Please update your registered bank account number to match the cheque."*
- **Statutory Policy Gate:** **BLOCKED (Unresolved High Exception)**.
- **Demonstration Value:** Proves reviewer clarification workflow, vendor inline field correction, selective revalidation, and historical field correction audit trail.

---

### Case 3: External Verification Issue & Duplicate Signal
- **Reference Number:** `APP-2026-WARN-003`
- **Legal Name:** Apex Logistics & Cargo LLP
- **Constitution:** Limited Liability Partnership (`LLP`)
- **Status:** `UNDER_REVIEW`
- **Verification Issue:** External MCA Corporate Registry gateway simulated timeout (`UNAVAILABLE`). Distinct from `FAILED`.
- **Duplicate Candidate Signal:** Flagged against an existing registered supplier with 88% token similarity (`Apex Logistics Express LLP`).
- **Statutory Policy Gate:** **BLOCKED (Requires manual review of duplicate flag and registry retry)**.
- **Demonstration Value:** Proves that external registry outages do not corrupt data or auto-fail vendors, and duplicate flags require explicit human dismissal rather than risky auto-merges.

---

### Active Live Invitation Link (Self-Serve Demo)
For demonstrating live end-to-end invitation acceptance:
- **Invited Vendor:** National Industrial Supplies LLP
- **Invited Email:** `invite.national@suppliernet.in`
- **Direct Demo Link:** `http://localhost:5173/invite/vYBYY1zO6gy6sp1L4RxsK9hpop9d-jV8CWDtgelP1UY`
