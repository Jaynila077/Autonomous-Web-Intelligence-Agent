# =====================================================================
# AWIS Autonomous Web Intelligence Agent - Startup Script (PowerShell)
# =====================================================================
# Launches the 5 MCP tool servers FIRST and waits for them to actually
# respond before starting FastAPI/arq, since src/tools/registry.py
# connects to all 5 servers at import time (when MOCK_AGENT=false),
# and FastAPI/arq will crash or hang on startup if these servers are
# not already listening.
#
# Mock mode (MOCK_AGENT=true) does not need the MCP servers at all.
# This script always starts them anyway for simplicity.
# =====================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

# Define your Conda environment name here:
$CondaEnv = "AWIA"

# MCP server ports, must match src/tools/registry.py and src/mcp_servers/run_all.py
$McpPorts = @(8001, 8002, 8003, 8004, 8005)
$McpStartupTimeoutSeconds = 30

# --- Helper function to launch a new PowerShell window with Conda activated ---
function Start-AwisService {
    param (
        [string]$Title,
        [string]$Command
    )
    $wrappedCommand = "`$Host.UI.RawUI.WindowTitle = '$Title'; conda activate $CondaEnv; Set-Location -Path '$ProjectRoot'; $Command"
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $wrappedCommand
}

# --- 1. Load .env file check ---
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "Found .env file at project root." -ForegroundColor Green
} else {
    Write-Warning "No .env file found at root. Ensure environment variables are configured."
}

# --- 2. Launch MCP Tool Servers (must be up before FastAPI/arq if MOCK_AGENT=false) ---
Write-Host ""
Write-Host "[1/4] Starting AWIS MCP Tool Servers (5 microservices)..." -ForegroundColor Cyan
Start-AwisService -Title "AWIS - MCP Servers" -Command "python -m src.mcp_servers.run_all"

# --- 3. Wait for all 5 MCP servers to actually accept connections ---
Write-Host "Waiting for MCP servers to come online (up to $McpStartupTimeoutSeconds seconds)..." -ForegroundColor Yellow
$deadline = (Get-Date).AddSeconds($McpStartupTimeoutSeconds)
$allUp = $false

while ((Get-Date) -lt $deadline) {
    $upCount = 0
    foreach ($port in $McpPorts) {
        $test = Test-NetConnection -ComputerName "localhost" -Port $port -WarningAction SilentlyContinue
        if ($test.TcpTestSucceeded) { $upCount++ }
    }
    if ($upCount -eq $McpPorts.Count) {
        $allUp = $true
        break
    }
    Start-Sleep -Seconds 1
}

if ($allUp) {
    Write-Host "All 5 MCP servers are up." -ForegroundColor Green
} else {
    Write-Warning "Not all MCP servers came online within $McpStartupTimeoutSeconds seconds."
    Write-Warning "FastAPI or arq may fail to start if MOCK_AGENT is set to false."
    Write-Warning "Check the MCP Servers window for errors."
    Write-Warning "If you are running with MOCK_AGENT=true, this warning is safe to ignore."
}

# --- 4. Launch FastAPI Server ---
Write-Host ""
Write-Host "[2/4] Starting FastAPI Server (Port 8000) in $CondaEnv environment..." -ForegroundColor Cyan
Start-AwisService -Title "AWIS - FastAPI Server" -Command "uvicorn src.api.main:app --reload --port 8000"

# --- 5. Launch ARQ Background Worker ---
Write-Host "[3/4] Starting ARQ Task Worker in $CondaEnv environment..." -ForegroundColor Cyan
Start-AwisService -Title "AWIS - ARQ Worker" -Command "python -m arq src.api.arq_worker.WorkerSettings"

# --- 6. Launch Frontend / Streamlit UI ---
Write-Host "[4/4] Starting Frontend UI..." -ForegroundColor Cyan
Start-AwisService -Title "AWIS - Frontend UI" -Command "streamlit run src/ui/app.py"

Write-Host ""
Write-Host "All services launched in separate windows with Conda environment $CondaEnv active." -ForegroundColor Green
Write-Host "Run stop_awis.ps1 when you want to terminate the running services." -ForegroundColor Yellow
