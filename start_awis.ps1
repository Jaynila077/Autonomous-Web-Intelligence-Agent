<#
.SYNOPSIS
    Launches the full AWIS stack (FastAPI + arq worker + Streamlit frontend)
    from a single command, each in its own PowerShell window.

.DESCRIPTION
    - No local Redis process is started: this assumes Upstash Redis (cloud) is
      used, so only 3 processes are needed, not 4.
    - Reads DATABASE_URL, UPSTASH_REDIS_URL, JWT_SECRET_KEY, MOCK_AGENT from
      a .env file in the project root (via dotenv, already a dependency),
      OR falls back to whatever is already set in your current shell session.
    - Each process gets its own titled window so you can see logs separately
      and Ctrl+C any one of them independently without killing the others.

.USAGE
    From the project root:
        .\start_awis.ps1

    To stop everything: close each window, or run .\stop_awis.ps1 (see below)
#>

$ErrorActionPreference = "Stop"

# --- Resolve project root (folder this script lives in) ---
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== AWIS Full Stack Launcher ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

# --- Sanity check: warn if required env vars aren't visible anywhere obvious ---
# (We don't hard-fail here because they might be defined inside a .env file
#  that each process loads itself via python-dotenv.)
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "Found .env file — each process will load it via python-dotenv." -ForegroundColor Green
} else {
    Write-Host "WARNING: No .env file found at project root." -ForegroundColor Yellow
    Write-Host "Make sure DATABASE_URL, UPSTASH_REDIS_URL, JWT_SECRET_KEY, and MOCK_AGENT" -ForegroundColor Yellow
    Write-Host "are set in this shell before continuing, or processes may fail to connect." -ForegroundColor Yellow
}

# --- Helper to launch a process in its own titled PowerShell window ---
function Start-NamedWindow {
    param(
        [string]$Title,
        [string]$Command
    )
    $wrappedCommand = "`$host.UI.RawUI.WindowTitle = '$Title'; Set-Location '$ProjectRoot'; $Command"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $wrappedCommand
}

# --- 1. FastAPI server ---
Write-Host "`nStarting FastAPI server..." -ForegroundColor Cyan
Start-NamedWindow -Title "AWIS - FastAPI" -Command "uvicorn src.api.main:app --reload --port 8000"
Start-Sleep -Seconds 2

# --- 2. arq worker ---
Write-Host "Starting arq worker..." -ForegroundColor Cyan
Start-NamedWindow -Title "AWIS - arq Worker" -Command "arq src.api.arq_worker.WorkerSettings"
Start-Sleep -Seconds 2

# --- 3. Streamlit frontend ---
Write-Host "Starting Streamlit frontend..." -ForegroundColor Cyan
Start-NamedWindow -Title "AWIS - Streamlit" -Command "streamlit run src/ui/app.py"

Write-Host "`n=== All processes launched in separate windows ===" -ForegroundColor Green
Write-Host "  - AWIS - FastAPI      -> http://localhost:8000"
Write-Host "  - AWIS - arq Worker   -> background job processing"
Write-Host "  - AWIS - Streamlit    -> http://localhost:8501 (usually opens automatically)"
Write-Host "`nClose each window individually to stop that process, or run .\stop_awis.ps1 to close all three." -ForegroundColor Cyan
