@echo off
REM Batch file to run PowerShell script as Administrator

echo ========================================================================
echo   Windows Firewall Configuration for Face Recognition Backend
echo ========================================================================
echo.
echo This will add a firewall rule to allow port 5000 for network access.
echo.
echo Requesting Administrator privileges...
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with Administrator privileges...
    echo.
    powershell -ExecutionPolicy Bypass -File "%~dp0add_firewall_rule.ps1"
) else (
    echo Not running as Administrator. Requesting elevation...
    echo.
    powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0add_firewall_rule.ps1\"' -Verb RunAs"
)

pause
