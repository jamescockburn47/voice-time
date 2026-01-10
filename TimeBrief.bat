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

:: Check Python first - this is the only real prerequisite
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERROR: Python not found!
    echo.
    echo   Please install Python 3.10+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo   IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    pause
    exit /b 1
)

:: Create/activate venv and install dependencies
if not exist "venv\Scripts\activate.bat" (
    echo [1/5] Creating Python environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo Installing dependencies (this may take a few minutes)...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

:: Check and auto-install Ollama
echo [2/5] Checking AI engine...
where ollama >nul 2>&1
if errorlevel 1 (
    echo Ollama not found - attempting automatic install...
    
    :: Try winget first (built into Windows 10/11)
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo Installing Ollama via winget...
        winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements -h
        if not errorlevel 1 (
            echo Ollama installed successfully!
            :: Refresh PATH to find ollama
            set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"
        ) else (
            echo.
            echo   Automatic install failed. Please install manually:
            echo   https://ollama.com/download
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo.
        echo   Please install Ollama manually from:
        echo   https://ollama.com/download
        echo.
        echo   Then run this script again.
        echo.
        pause
        exit /b 1
    )
)

:: Ensure Ollama is running
echo [3/5] Starting Ollama service...
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if errorlevel 1 (
    start "" /B ollama serve
    timeout /t 3 /nobreak >nul
)

:: Pull the default model if not present
echo [4/5] Checking AI model...
ollama list 2>nul | find "qwen2.5:1.5b" >nul
if errorlevel 1 (
    echo Downloading AI model (first run only, ~1GB)...
    echo This may take a few minutes depending on your internet speed.
    ollama pull qwen2.5:1.5b-instruct
)
echo AI ready

:: Initialize database
if not exist "%USERPROFILE%\.voice_time\voice_time.db" (
    echo [5/5] Initializing database...
    python run.py --init
) else (
    echo [5/5] Database OK
)

:: Start Flask in background and capture PID
echo.
echo Starting backend...

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
    echo Opening in browser...
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
    if not errorlevel 1 (
        echo Backend stopped [PID: %FLASK_PID%]
    ) else (
        echo Backend may have already stopped
    )
) else (
    :: Fallback: try to find and kill only run.py processes
    for /f "tokens=2" %%p in ('wmic process where "commandline like '%%run.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
        taskkill /F /PID %%p >nul 2>&1
    )
    echo Backend stopped
)

echo Done.
