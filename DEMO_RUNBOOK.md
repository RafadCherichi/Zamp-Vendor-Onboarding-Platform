# Vendor Onboarding Platform — Operational Demo Runbook

This runbook guides the presenter through the live demo step-by-step, providing exact click paths, inputs, talking points, and recovery procedures.

---

## Pre-Flight Checklist (1 Minute Before Demo)

1. **Verify Backend Server is running:**  
   Open `http://127.0.0.1:8000/docs` in your browser. Verify the OpenAPI documentation loads.
2. **Verify Frontend Server is running:**  
   Open `http://localhost:5173` in your browser.
3. **Execute Clean Demo Reset:**  
   Open PowerShell in the workspace root:
   ```powershell
   $env:PYTHONPATH='backend'
   backend\.venv\Scripts\python.exe backend\app\db\seed_demo.py
   ```
   *Expected output: `[Seed Demo] Successfully seeded deterministic demo environment`.*

---

## Walkthrough Phase 1: Procurement Oversight & Invitation
**Duration:** ~45 seconds  
**Actor:** Procurement Officer (`procurement@apex.com` / `Password123!`)

### Actions:
1. Open browser to `http://localhost:5173/login`.
2. Enter email: `procurement@apex.com` and password: `Password123!`. Click **Sign In**.
3. You are redirected to the **Procurement Dashboard** (`/procurement`).
4. **Point out the top metrics cards:**
   - Active applications, awaiting review, open exceptions, and ready for approval.
5. **Show the Live Invitations table:**
   - Locate the pending invitation for `National Industrial Supplies LLP`.
   - Point out the expiration countdown (7 days valid) and token masking.
6. Click **Invite Vendor** button:
   - Enter Vendor Name: `Bharat Precision Tools Pvt Ltd`
   - Enter Email: `sales@bharattools.in`
   - Set validity: 7 days
   - Click **Send Invitation**.
   - Show the generated `/invite/<token>` link. Explain that in production, this raw token is dispatched strictly via transactional email and stored only as a SHA-256 hash in the database.
7. Click **Sign Out** in the navigation header.

---

## Walkthrough Phase 2: Live Vendor Registration & Dynamic Checklist
**Duration:** ~60 seconds  
**Actor:** Vendor (`National Industrial Supplies LLP`)

### Actions:
1. Navigate directly to the pre-seeded invitation link:
   `http://localhost:5173/invite/vYBYY1zO6gy6sp1L4RxsK9hpop9d-jV8CWDtgelP1UY`
2. **Show the Invitation Acceptance Screen:**
   - Point out that the buyer name ("Apex Enterprises Ltd.") is verified, vendor name is pre-filled, and vendor email is masked.
   - Enter Password: `Password123!`
   - Select Legal Constitution: **Private Limited Company (`PVT_LTD`)**.
   - Click **Accept & Begin Onboarding**.
3. **Show the Multi-Step Wizard:**
   - Point out the 5-step stepper: Identity, Tax/Registration, Contact, Banking, Declarations.
4. **Demonstrate Dynamic Document Checklist:**
   - Scroll down to the Document Checklist.
   - Point out that because `PVT_LTD` was selected, the checklist demands:
     - Entity PAN Card
     - Certificate of Incorporation & MOA/AOA
     - Cancelled Cheque / Bank Proof
     - Board Resolution for Authorized Signatory (mandatory for corporate entities)
   - Toggle to "Sole Proprietorship" on Step 1: observe that the Board Resolution immediately disappears, and the PAN requirement switches to "Proprietor's Individual PAN Card".
5. Click **Sign Out**.

---

## Walkthrough Phase 3: Reviewer Workspace & Clean Application Approval (Case 1)
**Duration:** ~60 seconds  
**Actor:** Reviewer / Approver (`reviewer@apex.com` / `Password123!`)

### Actions:
1. Login as `reviewer@apex.com` / `Password123!`.
2. You land on the **Reviewer Application Queue** (`/reviewer`).
3. Point out the filters: Status, Severity, Ready for Approval, Assigned Reviewer.
4. Click on **Case 1: `APP-2026-CLEAN-001`** (Tata Industrial Supplies Private Limited).
5. **Walk through the 7-Section Comprehensive Workspace:**
   - **Section 1: Overview:** Reference number, assigned reviewer, submitted timestamp.
   - **Section 2: Business Details:** Sensitive identifiers (PAN `AA***4K`, Bank Account `5020****5678`) are masked for data privacy.
   - **Section 3: Document Evidence:** Inspect the 4 verified documents. Show that extraction confidence is 98%+, bounding coordinates are recorded, and no values were hallucinated.
   - **Section 4: Validation Engine Findings:**
     - Expand **Layer A (Input Syntax):** Mod-36 GSTIN checksum passed, PAN 4th character `C` matches Private Limited.
     - Expand **Layer B (Cross-Field):** Embedded PAN in GSTIN matches declared PAN.
     - Expand **Layer C (External):** Simulated Income Tax, GSTN, and Penny-Drop verifications all show `VERIFIED`.
   - **Section 5: Policy Compliance Gate:**
     - Point out the green badge: **"Eligible for Approval"**.
     - All mandatory documents uploaded, zero unresolved exceptions, completed validation evaluation.
6. **Execute Approval:**
   - In the Reviewer Decision card, enter Decision Notes: *"All statutory documents verified. Verified against external sandbox registries. Approved for vendor master."*
   - Click **Approve Application**.
   - Observe instant transition to `APPROVED` with verified timestamp.
7. Click back to **Application Queue**.

---

## Walkthrough Phase 4: Exception Clarification & Vendor Correction (Case 2)
**Duration:** ~75 seconds  
**Actors:** Reviewer (`reviewer@apex.com`) followed by Vendor (`vendor.mismatch@sharmaworks.in`)

### Actions (Reviewer):
1. In the Reviewer Queue, click on **Case 2: `APP-2026-MISM-002`** (Sharma Engineering Works).
2. Point out that the **Approve Application** button is disabled with an amber alert:
   *"Approval Blocked: Unresolved HIGH Exception: EXC-B-MISM-002 (Bank Account Number Discrepancy)"*.
3. Click the **Exceptions** tab:
   - Show the discrepancy: Form account number differs from cancelled cheque extraction.
4. Click **Request Clarification**:
   - Instructions: *"Please update your registered bank account number to match the cheque."*
   - Click **Submit Request**.
   - Show that status transitions to `ACTION_REQUIRED`.
5. Click **Sign Out**.

### Actions (Vendor Correction):
1. Login as Vendor: `vendor.mismatch@sharmaworks.in` / `Password123!`.
2. Notice the prominent **Vendor Clarification Banner** at the top of the onboarding screen:
   - Reviewer instruction is displayed: *"Please update your registered bank account number to match the cheque."*
3. Click **Resolve Exception / Update Details**.
4. Change Bank Account Number from `9876543210123` to `502000998877`.
5. Enter vendor explanation: *"Corrected typographical error in registered account number."*
6. Click **Submit Correction**.
7. Observe success confirmation: Application transitions back to `UNDER_REVIEW`.
8. Click **Sign Out**.

### Actions (Reviewer Re-Evaluation & Final Sign-Off):
1. Log back in as `reviewer@apex.com` / `Password123!`.
2. Open `APP-2026-MISM-002`.
3. In the **Exceptions** tab:
   - Notice the vendor's submitted response: *"Corrected typographical error in registered account number."*
   - Notice the **Field Corrections** table showing previous value vs new value with timestamps.
4. Click **Resolve Exception**:
   - Notes: *"Account number corrected and verified against cheque MICR."*
   - Click **Confirm Resolution**.
5. The policy gate unlocks and turns green.
6. Click **Approve Application**, enter notes, and confirm approval.

---

## Walkthrough Phase 5: External Registry Timeout & Duplicate Candidate (Case 3)
**Duration:** ~45 seconds  
**Actor:** Reviewer (`reviewer@apex.com`)

### Actions:
1. In the Reviewer Queue, click on **Case 3: `APP-2026-WARN-003`** (Apex Logistics & Cargo LLP).
2. Open the **External Verifications** tab:
   - Show the simulated MCA registry status: **`UNAVAILABLE`** (504 Gateway Timeout).
   - Point out that the system explicitly distinguishes `UNAVAILABLE` from `FAILED`: it does **not** fail or reject the vendor, but marks the statutory check as pending.
3. Open the **Duplicate Detection** tab:
   - Point out the **Duplicate Candidate Signal**:
     - Matched against existing vendor: `Apex Logistics Express LLP` (88% name similarity).
     - Explanation: *"Similar legal name and identical state jurisdiction (Maharashtra)."*
4. Explain the human-in-the-loop philosophy:
   - *"The platform never auto-rejects or auto-merges duplicate candidates. A human reviewer must investigate."*
5. Click **Dismiss Duplicate Flag**:
   - Reason: *"Verified distinct LLPIN; different entity operating under common brand."*
   - Click **Confirm Dismissal**.
   - Show that the dismissal is recorded in the immutable audit trail.

---

## Walkthrough Phase 6: Admin Dashboard & 1-Click Demo Reset
**Duration:** ~15 seconds  
**Actor:** Admin (`admin@apex.com`)

1. Login as `admin@apex.com` / `Password123!`.
2. Navigate to `/admin`.
3. Point out system configuration, active tenants, and user management.
4. Click the purple button: **"Reset & Re-Seed Demo"**.
5. Show the instant success toast: all demo cases are reset back to their initial state, ready for the next evaluator.

---

## Troubleshooting & FAQ

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| Login fails with 401 | Database has not been seeded or has outdated state | Run `$env:PYTHONPATH='backend'; python backend/app/db/seed_demo.py` |
| Approval button disabled | Mandatory policy requirements not met | Check the "Blocking Reasons" list in Section 1 Overview. Resolve open exceptions or upload missing documents. |
| Port 8000 or 5173 occupied | Another dev process is running on the port | Kill the conflicting process or change port via `--port 8001` (backend) / `vite --port 5174` (frontend). |
