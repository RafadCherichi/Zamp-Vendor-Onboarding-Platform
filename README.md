# Vendor Onboarding Platform (India Edition)

> **Invitation-first • AI-assisted • Human-controlled**  
> *"Collect the right information once, check it consistently, explain what is wrong, make corrections easy, and give reviewers traceable evidence for decisions."*

This repository implements the India-focused Vendor Onboarding Platform based on the **Final Consolidated Product Specification (Version 1.0)**.

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

### Running All Backend Tests (Auth, RBAC, Scoping, Health)
From the project root:
```powershell
$env:PYTHONPATH='backend'
backend\.venv\Scripts\pytest.exe backend/tests -v
```
*Current test suite: 14 passing unit & integration tests.*

### Running Frontend Type-Check & Production Build
From the `frontend` directory:
```powershell
npm.cmd run build
```

---

## 6. Build Sequence & Progress

| Increment | Title | Scope | Status |
| :--- | :--- | :--- | :--- |
| **0** | **Foundation** | Workspace inspection, FastAPI, React + Vite, Alembic, Storage Adapter, Health verification | **Complete** |
| **1** | **App Shell & Identity** | Multi-role RBAC, organisation scoping, secure expiring invitation tokens, demo switcher | **Complete** |
| **2** | **Vendor Onboarding** | 6-section dynamic form, activity/constitution conditional checklist, save/resume | *Next* |
| **3** | **Document Processing** | Private storage versions, background worker, OCR & vision extraction adapter | *Upcoming* |
| **4** | **Validation & Verification**| Deterministic rules, PAN-GST matching, duplicate detection, simulated verification | *Upcoming* |
| **5** | **Exception Lifecycle** | Vendor-explainable corrections, versioned replacements, selective revalidation | *Upcoming* |
| **6** | **Internal Workspace** | Reviewer dashboard, evidence side-by-side inspection, human decision recording | *Upcoming* |
| **7** | **Hardening & Demo Data** | Append-only audit timeline, quarantine guards, acceptance test suite, synthetic demo data | *Upcoming* |
