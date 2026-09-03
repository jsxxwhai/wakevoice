@echo off
setlocal
cd /d "%~dp0"

rem One-click launcher for WakeVoice (Windows).
rem Checks Python, installs dependencies, downloads the model, then runs.

where python >nul 2>nul
if errorlevel 1 (
    echo [WakeVoice] Python not found. Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [WakeVoice] Preparing environment (first run may take a few minutes)...
python scripts\bootstrap.py
if errorlevel 1 (
    echo [WakeVoice] Setup failed. See messages above.
    pause
    exit /b 1
)

echo [WakeVoice] Starting assistant (Ctrl+C to stop)...
python main.py --wake

pause
