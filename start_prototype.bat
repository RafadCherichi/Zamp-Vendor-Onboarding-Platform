@echo off
setlocal enabledelayedexpansion

title India-Focused Vendor Onboarding Platform - Launcher
echo =====================================================================
echo    India-Focused Vendor Onboarding Platform - Local Launcher
echo =====================================================================
echo.

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

:: 1. Locate Python
set PYTHON_EXE=
if exist "%ROOT_DIR%backend\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%backend\.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found! Please install Python 3.11 or 3.12.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Using Python: %PYTHON_EXE%

:: 2. Check Python Dependencies
if not exist "%ROOT_DIR%backend\.venv" (
    echo [INFO] First-time setup: Creating Python virtual environment...
    python -m venv "%ROOT_DIR%backend\.venv"
    echo [INFO] Installing backend dependencies (this may take a couple minutes)...
    "%ROOT_DIR%backend\.venv\Scripts\pip" install -r "%ROOT_DIR%backend\requirements.txt"
    set "PYTHON_EXE=%ROOT_DIR%backend\.venv\Scripts\python.exe"
)

:: 3. Check / Seed Database if needed
if not exist "%ROOT_DIR%backend\app.db" (
    echo [INFO] Database not found. Seeding pristine demo environment...
    set "PYTHONPATH=backend"
    set "OPENBLAS_NUM_THREADS=1"
    set "OMP_NUM_THREADS=1"
    "%PYTHON_EXE%" -m app.db.seed_demo
)

:: 4. Locate Node.js & npm
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / npm not found! Please install Node.js 18+ to run the Vite frontend.
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

:: 5. Check frontend dependencies
if not exist "%ROOT_DIR%frontend\node_modules" (
    echo [INFO] First-time setup: Installing frontend dependencies...
    cd /d "%ROOT_DIR%frontend"
    call npm install
    cd /d "%ROOT_DIR%"
)

echo.
echo =====================================================================
echo    Starting Backend (FastAPI on http://127.0.0.1:8000)
echo    Starting Frontend (Vite React on http://127.0.0.1:5173)
echo =====================================================================
echo.

:: Launch Backend in separate persistent console
start "Backend - FastAPI (Port 8000)" cmd /k "title Backend Server && cd /d ""%ROOT_DIR%"" && set PYTHONPATH=backend&& set OPENBLAS_NUM_THREADS=1&& set OMP_NUM_THREADS=1&& ""%PYTHON_EXE%"" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:: Launch Frontend in separate persistent console
start "Frontend - Vite React (Port 5173)" cmd /k "title Frontend Server && cd /d ""%ROOT_DIR%frontend"" && set NODE_OPTIONS=--max-old-space-size=2048&& npm run dev -- --host 127.0.0.1 --port 5173"

echo Waiting 4 seconds for servers to initialize...
timeout /t 4 /nobreak >nul

echo Opening prototype in default browser...
start http://127.0.0.1:5173/

echo.
echo =====================================================================
echo Prototype is now running!
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000 (API Docs: http://127.0.0.1:8000/docs)
echo.
echo To stop the servers, simply close the two opened terminal windows.
echo =====================================================================
echo.
pause
