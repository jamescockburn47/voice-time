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

:: Initialize PID variable
set FLASK_PID=

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

:: Start Flask in background and capture PID
echo [4/4] Starting backend...

:: Use PowerShell to start process and get PID
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "Start-Process -FilePath 'python' -ArgumentList 'run.py' -WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id"') do set FLASK_PID=%%i

if defined FLASK_PID (
    echo Backend started [PID: %FLASK_PID%]
) else (
    echo Backend started
)

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

:: Cleanup - only kill OUR Flask process
echo.
echo Shutting down...

if defined FLASK_PID (
    :: Kill only the specific Flask process we started
    taskkill /F /PID %FLASK_PID% >nul 2>&1
    if errorlevel 0 (
        echo Backend stopped [PID: %FLASK_PID%]
    )
) else (
    :: Fallback: try to find and kill only run.py processes
    for /f "tokens=2" %%p in ('wmic process where "commandline like '%%run.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
)

echo Done.
