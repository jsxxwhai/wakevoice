# One-click launcher for OpenVoice Desktop (Windows PowerShell).
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[OpenVoice] Python not found. Install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OpenVoice] Preparing environment (first run may take a few minutes)..." -ForegroundColor Cyan
python scripts\bootstrap.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[OpenVoice] Setup failed. See messages above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OpenVoice] Starting assistant (Ctrl+C to stop)..." -ForegroundColor Cyan
python main.py --wake

Read-Host "Press Enter to exit"
