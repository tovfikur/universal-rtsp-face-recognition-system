@echo off
echo ============================================================
echo Restarting Face Recognition Backend
echo ============================================================
echo.

echo [1] Stopping old backend process...
taskkill /F /FI "WINDOWTITLE eq backend*" /T 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "MEMUSAGE gt 1000000" 2>nul
timeout /t 2 >nul

echo [2] Starting backend with new settings...
echo    - Confidence: 0.35 (lowered from 0.65)
echo    - Min person area: 1500 (lowered from 3000)
echo.

cd /d "%~dp0"
start "backend" .venv\Scripts\python.exe backend\app.py

echo [3] Waiting for backend to initialize...
timeout /t 5 >nul

echo [4] Testing backend health...
curl -s http://localhost:5000/api/health | python -m json.tool | findstr /C:"status" /C:"faces"

echo.
echo ============================================================
echo Backend restarted successfully!
echo ============================================================
echo.
echo Web interface: http://localhost:5000
echo.
echo Press any key to exit...
pause >nul
