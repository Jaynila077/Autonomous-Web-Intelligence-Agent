# =====================================================================
# AWIS Autonomous Web Intelligence Agent - Startup Script (PowerShell)
# =====================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

# Define your Conda environment name here:
$CondaEnv = "AWIA"

# --- Helper function to launch a new PowerShell window with Conda activated ---
function Start-AwisService {
    param (
        [string]$Title,
        [string]$Command
    )
    
    # 1. Sets window title
    # 2. Activates the Conda environment
    # 3. Navigates to project root
    # 4. Runs the target command
    $wrappedCommand = "`$Host.UI.RawUI.WindowTitle = '$Title'; conda activate $CondaEnv; Set-Location -Path '$ProjectRoot'; $Command"
    
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $wrappedCommand
}

# --- 1. Load .env file check ---
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "Found .env file at project root." -ForegroundColor Green
} else {
    Write-Warning "No .env file found at root! Ensure environment variables are configured."
}

# --- 2. Launch FastAPI Server ---
Write-Host "`n[1/3] Starting FastAPI Server (Port 8000) in '$CondaEnv' env..." -ForegroundColor Cyan
Start-AwisService -Title "AWIS - FastAPI Server" -Command "uvicorn src.api.main:app --reload --port 8000"

# --- 3. Launch ARQ Background Worker ---
Write-Host "[2/3] Starting ARQ Task Worker in '$CondaEnv' env..." -ForegroundColor Cyan
Start-AwisService -Title "AWIS - ARQ Worker" -Command "python -m arq src.api.arq_worker.WorkerSettings"

# --- 4. Launch Frontend / Streamlit UI (Optional) ---
Write-Host "[3/3] Starting Frontend UI..." -ForegroundColor Cyan
Start-AwisService -Title "AWIS - Frontend UI" -Command "streamlit run src/ui/app.py"

Write-Host "`nAll services launched in separate windows with Conda env '$CondaEnv' active!" -ForegroundColor Green
Write-Host "Run .\stop_awis.ps1 when you want to terminate the running services." -ForegroundColor Yellow