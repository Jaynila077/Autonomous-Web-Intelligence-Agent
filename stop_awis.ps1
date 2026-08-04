<#
.SYNOPSIS
    Stops all AWIS stack windows started by start_awis.ps1, by matching window title.

.USAGE
    .\stop_awis.ps1
#>

$titles = @("AWIS - FastAPI", "AWIS - arq Worker", "AWIS - Streamlit")

$closed = 0
foreach ($proc in Get-Process powershell -ErrorAction SilentlyContinue) {
    if ($titles -contains $proc.MainWindowTitle) {
        Write-Host "Closing: $($proc.MainWindowTitle)" -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force
        $closed++
    }
}

if ($closed -eq 0) {
    Write-Host "No matching AWIS windows found running." -ForegroundColor Gray
} else {
    Write-Host "Closed $closed AWIS process window(s)." -ForegroundColor Green
}
