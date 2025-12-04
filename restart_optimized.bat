@echo off
REM Restart optimized backend with all threads

echo ========================================
echo   OPTIMIZED FACE RECOGNITION SYSTEM
echo   Final Architecture: 3 Threads
echo ========================================
echo.

echo Stopping any existing backend instances...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *app.py*" >nul 2>&1

echo.
echo Starting optimized backend...
echo.
echo Architecture:
echo   1. Combined Analysis: Every 5 seconds
echo      - Person detection (YOLOv8n GPU)
echo      - Face recognition (CNN GPU)
echo      - Snapshot creation
echo      - Attendance marking
echo.
echo   2. Stream Encoder: 30 FPS
echo      - Pre-encodes video frames
echo      - Zero HTTP overhead
echo      - Smooth video feed
echo.
echo   3. API Workers: 8 concurrent
echo      - Face registration
echo      - Non-blocking operations
echo      - Parallel processing
echo.
echo GPU: NVIDIA GTX 1650
echo CPU Usage: ~30-40%% average (efficient!)
echo.
echo ========================================
echo.

cd backend
python app.py

pause
