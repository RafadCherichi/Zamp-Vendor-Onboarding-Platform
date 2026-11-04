# Vendor Onboarding Platform (India Edition)

> **Invitation-first • AI-assisted • Human-controlled**  
> *"Collect the right information once, check it consistently, explain what is wrong, make corrections easy, and give reviewers traceable evidence for decisions."*

This repository implements the India-focused Vendor Onboarding Platform based on the **Final Consolidated Product Specification (Version 1.0)**.

---

## 1. Architecture Overview

- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS v4 (Mobile-first vendor portal, desktop-first reviewer workspace).
- **Backend**: Python 3.12 + FastAPI (Asynchronous REST API, Pydantic v2 schemas, strict type safety, CORS security).
- **Database**: PostgreSQL (production/staging) with SQLAlchemy 2.0 and Alembic migrations; zero-dependency SQLite fallback for local test/demo environments.
- **Object Storage**: Private, isolated object storage adapter interface (`StorageAdapter`) with implementations for local filesystem (short-lived signed preview tokens) and Supabase Storage / S3.
- **Document Security**: Untrusted file handling pipeline with MIME sniffing, size constraints, allowlist checks (`.pdf`, `.jpg`, `.jpeg`, `.png`), and isolated preview tokens.

---

## 2. Project Directory Structure

```text
.
├── Final_Consolidated_Product_Specification_Vendor_Onboarding_Platform.docx
├── README.md
├── .gitignore
├── .env.example
├── backend/
│   ├── .env.example
│   ├── .env
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 4998f7c76ca4_create_organisations_table.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application root & CORS
│   │   ├── config.py               # Pydantic BaseSettings & env configuration
│   │   ├── database.py             # SQLAlchemy session & connectivity checks
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # Master API router (/api)
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       └── health.py       # GET /api/health diagnostic endpoint
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Declarative base & TimestampMixin
│   │   │   └── organization.py     # Buyer organisation workspace model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── health.py           # Health response Pydantic models
│   │   └── storage/
│   │       ├── __init__.py
│   │       ├── base.py             # StorageAdapter abstract base class
│   │       └── local.py            # Private local object storage implementation
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # Pytest client fixtures
│       └── test_health.py          # API & database connectivity tests
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts              # Vite config with Tailwind & /api proxy
    ├── index.html
    ├── .env.example
    ├── .env
    └── src/
        ├── App.tsx                 # Main application shell & diagnostic view
        ├── main.tsx
        ├── index.css               # Tailwind CSS v4 directives
        ├── api/
        │   └── client.ts           # Typed API fetch client
        ├── components/
        │   ├── Header.tsx          # Navigation header & live connection pill
        │   ├── HealthCard.tsx      # Real-time backend, DB & storage diagnostic
        │   └── FoundationRoadmap.tsx # Delivery sequence (Increments 0 to 7)
        └── types/
            └── api.ts              # Frontend API interfaces
```

---

## 3. Prerequisites

- **Python**: 3.11 or 3.12 (`python --version`)
- **Node.js**: v18.0.0 or higher (`node -v`, `npm.cmd -v`)
- **PostgreSQL** *(Optional for local demo)*: PostgreSQL 15+ or Supabase project URL. If PostgreSQL is not installed locally, the backend seamlessly defaults to local SQLite (`vendor_onboarding.db`) for immediate zero-dependency evaluation.

---

## 4. Setup and Installation

### Backend Setup

1. **Navigate to the backend directory and activate the virtual environment**:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(On Linux/macOS: `source .venv/bin/activate`)*

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *To use PostgreSQL, set:*
   ```env
   DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/vendor_onboarding
   ```
   *For zero-dependency local development:*
   ```env
   DATABASE_URL=sqlite:///./vendor_onboarding.db
   ```

4. **Run Database Migrations**:
   ```powershell
   alembic upgrade head
   ```

5. **Start the Backend Server**:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc Documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - Health Endpoint: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```powershell
   cd frontend
   ```

2. **Install dependencies**:
   ```powershell
   npm install
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```powershell
   cp .env.example .env
   ```

4. **Start the Frontend Development Server**:
   ```powershell
   npm run dev
   ```
   - Frontend Application: [http://localhost:5173](http://localhost:5173)

---

## 5. Verification & Testing

### Running Backend Unit & Health Tests
From the project root:
```powershell
$env:PYTHONPATH='backend'
backend\.venv\Scripts\pytest.exe backend/tests -v
```

### Running Frontend Type Checks and Production Build
From the `frontend` directory:
```powershell
npm run build
```

---

## 6. Build Sequence & Increments

As outlined in Section 16 of the Consolidated Product Specification:

| Increment | Title | Scope | Status |
| :--- | :--- | :--- | :--- |
| **0** | **Foundation** | Workspace inspection, FastAPI, React + Vite, Alembic, Storage Adapter, Health verification | **Complete** |
| **1** | **App Shell & Identity** | Multi-role RBAC, organisation scoping, expiring secure invitations | *Next* |
| **2** | **Vendor Onboarding** | 6-section dynamic form, activity/constitution conditional checklist, save/resume | *Upcoming* |
| **3** | **Document Processing** | Private storage versions, background worker, OCR & vision extraction adapter | *Upcoming* |
| **4** | **Validation & Verification**| Deterministic rules, PAN-GST matching, duplicate detection, simulated verification | *Upcoming* |
| **5** | **Exception Lifecycle** | Vendor-explainable corrections, versioned replacements, selective revalidation | *Upcoming* |
| **6** | **Internal Workspace** | Reviewer dashboard, evidence side-by-side inspection, human decision recording | *Upcoming* |
| **7** | **Hardening & Demo Data** | Append-only audit timeline, quarantine guards, acceptance test suite, synthetic demo data | *Upcoming* |
