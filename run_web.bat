@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ===============================================================================
echo     Spec2RTL ^& Procedural 3D Chip Workbench: 1-Click Web Server Launcher
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [1/2] Checking Python 3 environment...
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found on PATH! Please install Python 3.8+ or configure PATH.
    pause
    exit /b 1
)

echo [2/2] Launching Ponytail Web Server on default port 8080...
echo Server console will remain active. Press Ctrl+C to stop.
echo.

python web\server.py --port 8080 %*
