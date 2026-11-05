<#
.SYNOPSIS
    Starts the India-Focused Vendor Onboarding Platform on any Windows machine.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   India-Focused Vendor Onboarding Platform - Local Launcher" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Python
$PythonExe = $null
if (Test-Path "$ScriptDir\backend\.venv\Scripts\python.exe") {
    $PythonExe = "$ScriptDir\backend\.venv\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} else {
    Write-Host "[ERROR] Python not found! Please install Python 3.11 or 3.12." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Using Python: $PythonExe" -ForegroundColor Green

# 2. Check Virtual Environment
if (-not (Test-Path "$ScriptDir\backend\.venv")) {
    Write-Host "[INFO] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv "$ScriptDir\backend\.venv"
    Write-Host "[INFO] Installing backend dependencies..." -ForegroundColor Yellow
    & "$ScriptDir\backend\.venv\Scripts\pip" install -r "$ScriptDir\backend\requirements.txt"
    $PythonExe = "$ScriptDir\backend\.venv\Scripts\python.exe"
}

# 3. Check / Seed DB
if (-not (Test-Path "$ScriptDir\backend\app.db")) {
    Write-Host "[INFO] Seeding pristine demo environment..." -ForegroundColor Yellow
    $env:PYTHONPATH = "backend"
    $env:OPENBLAS_NUM_THREADS = "1"
    $env:OMP_NUM_THREADS = "1"
    & $PythonExe -m app.db.seed_demo
}

# 4. Check Node.js
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js / npm not found! Please install Node.js 18+ to run the Vite frontend." -ForegroundColor Red
    Write-Host "Download from: https://nodejs.org/"
    Read-Host "Press Enter to exit"
    exit 1
}

# 5. Check frontend dependencies
if (-not (Test-Path "$ScriptDir\frontend\node_modules")) {
    Write-Host "[INFO] Installing frontend packages..." -ForegroundColor Yellow
    Push-Location "$ScriptDir\frontend"
    npm.cmd install
    Pop-Location
}

Write-Host ""
Write-Host "Starting Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
Write-Host "Starting Frontend on http://127.0.0.1:5173..." -ForegroundColor Cyan

# Launch backend in separate PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='backend'; `$env:OPENBLAS_NUM_THREADS='1'; `$env:OMP_NUM_THREADS='1'; & '$PythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

# Launch frontend in separate PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ScriptDir\frontend'; `$env:NODE_OPTIONS='--max-old-space-size=2048'; npm.cmd run dev -- --host 127.0.0.1 --port 5173"

Start-Sleep -Seconds 4
Start-Process "http://127.0.0.1:5173/"

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "Prototype is now running!" -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Close the opened terminal windows to stop the servers." -ForegroundColor Gray
Write-Host "=====================================================================" -ForegroundColor Green
