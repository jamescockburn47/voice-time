@echo off
title TimeBrief
color 0A

cls
echo.
echo   ==========================================
echo            TimeBrief
echo      Voice-First Legal Time Recording
echo   ==========================================
echo.

:: Set up paths
set PATH=%USERPROFILE%\.cargo\bin;%PATH%

:: Change to script directory
cd /d "%~dp0"

:: Activate venv
if not exist "venv\Scripts\activate.bat" (
    echo [1/4] Creating Python environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Python not found. Please install Python 3.10+
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt -q
) else (
    call venv\Scripts\activate.bat
)

:: Check Ollama
echo [2/4] Checking AI engine...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama not found - install from https://ollama.ai
) else (
    tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
    if errorlevel 1 (
        start "" /B ollama serve
        timeout /t 2 /nobreak >nul
    )
    echo Ollama OK
)

:: Initialize database
if not exist "%USERPROFILE%\.voice_time\voice_time.db" (
    echo [3/4] Initializing database...
    python run.py --init
)

:: Start Flask in background
echo [4/4] Starting backend...
start "" /B python run.py

:: Wait for server
echo Waiting for server...
timeout /t 5 /nobreak >nul

echo.
echo   ==========================================
echo   TimeBrief is ready!
echo   ==========================================
echo.

:: Check if cargo/tauri is available
where cargo >nul 2>&1
if errorlevel 1 (
    echo Rust not found - opening in browser instead...
    start http://localhost:5000
    echo.
    echo Press any key to stop the server...
    pause >nul
) else (
    echo Launching desktop app...
    cd src-tauri
    cargo tauri dev
)

:: Cleanup
echo.
echo Shutting down...
taskkill /F /IM python.exe >nul 2>&1
echo Done.
