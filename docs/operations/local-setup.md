# How to Run the Vendor Onboarding Platform (Any PC)

This guide explains how to run the prototype on your current computer or any other PC (Windows, macOS, or Linux).

---

## 1. Quick Start on Windows (1-Click)

Simply double-click the included batch script in the root directory:

```text
scripts/local/start_prototype.bat
```

*(Or right-click `scripts/local/start_prototype.ps1` and select **Run with PowerShell**)*

### What the script does automatically:
1. Detects your Python and Node.js installations.
2. Creates the Python virtual environment and installs dependencies if running for the first time.
3. Initializes and seeds the SQLite demo database with the 3 benchmark demonstration cases if not already present.
4. Launches the **FastAPI Backend** on port `8000` in its own window.
5. Launches the **Vite React Frontend** on port `5173` in its own window.
6. Automatically opens your default web browser to [http://127.0.0.1:5173/](http://127.0.0.1:5173/).

---

## 2. Moving & Running on Another PC

If you zip or copy this folder to another PC or laptop, here are the simple requirements and steps:

### Prerequisites (Install Once):
1. **Python 3.11 or 3.12**: [Download Python](https://www.python.org/downloads/)  
   *(⚠️ Check the box **"Add Python to PATH"** during installation!)*
2. **Node.js (v18 or v20 LTS)**: [Download Node.js](https://nodejs.org/)

### First-Time Run:
1. Copy the project folder to the target machine.
2. Double-click `scripts/local/start_prototype.bat`.
3. The script will automatically detect that dependencies are missing, install them, seed the database, and launch the platform.

---

## 3. Manual Terminal Startup (Any Platform)

If you prefer running commands manually in separate terminal tabs:

### Terminal 1 — Backend (FastAPI on Port 8000)
**Windows (PowerShell):**
```powershell
# In project root:
$env:PYTHONPATH = "backend"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**macOS / Linux (Bash/Zsh):**
```bash
# In project root:
export PYTHONPATH=backend
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

*Backend Health Check:* [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)  
*Interactive Swagger API Docs:* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Terminal 2 — Frontend (Vite on Port 5173)
**Windows (PowerShell):**
```powershell
cd frontend
$env:NODE_OPTIONS = "--max-old-space-size=2048"
npm run dev -- --host 127.0.0.1 --port 5173
```

**macOS / Linux (Bash/Zsh):**
```bash
cd frontend
export NODE_OPTIONS="--max-old-space-size=2048"
npm run dev -- --host 127.0.0.1 --port 5173
```

*Frontend Application:* [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 4. Resetting or Re-Seeding the Demo Data

If you test approvals, rejections, or edits and want to return to the pristine benchmark demonstration cases:

### Method A: From the Browser UI (Easiest)
1. Log in as **Administrator** (`admin@apex.com` / `Password123!`).
2. Click the **"Reset & Re-Seed Demo"** button in the top navigation bar or dashboard.
3. Within 5 seconds, the demo database is restored to the pristine baseline.

### Method B: From the Terminal
```powershell
$env:PYTHONPATH = "backend"
backend\.venv\Scripts\python.exe -m app.db.seed_demo
```

---

## 5. Demo Accounts Reference

| Role | Name | Email | Password | Primary Demo Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Reviewer / Approver** | Rajesh Iyer | `reviewer@apex.com` | `Password123!` | Case 1 (Clean approval), Case 2 (Raise exception), Case 3 (Timeout check) |
| **Procurement Officer** | Priya Sharma | `procurement@apex.com` | `Password123!` | Dashboard metrics, sending new vendor invitations |
| **Vendor Contact** | Ramesh Sharma | `vendor.mismatch@sharmaworks.in` | `Password123!` | Case 2 (Respond to bank mismatch clarification request) |
| **Administrator** | Aditya Sharma | `admin@apex.com` | `Password123!` | 1-Click Demo Reset, audit governance |

*(The login screen also features 1-click quick login buttons for all 4 roles!)*
