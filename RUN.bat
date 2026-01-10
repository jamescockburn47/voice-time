@echo off
REM Voice Time - One-Click Launcher (NO TERMINAL NEEDED!)

title Voice Time Recording System

echo.
echo ==========================================
echo   Voice Time Recording System
echo ==========================================
echo.
echo Starting everything automatically...
echo.

REM Step 1: Check if setup is needed
if not exist "venv\Scripts\activate.bat" (
    echo [1/5] First time setup detected...
    echo.
    call setup.bat
    echo.
    echo Setup complete!
    echo.
)

REM Step 2: Start Ollama and pull model
echo [2/5] Starting Ollama server and checking model...
call start_ollama.bat
if %errorlevel% equ 0 (
    echo Ollama is ready!
) else (
    echo.
    echo ERROR: Ollama setup failed
    echo.
    echo Please:
    echo   1. Install Ollama from https://ollama.ai
    echo   2. Run this script again
    echo.
    pause
    exit /b 1
)

REM Step 3: Check if database exists
if not exist "%USERPROFILE%\.voice_time\voice_time.db" (
    echo.
    echo [3/5] Creating database...
    call venv\Scripts\activate.bat
    python run.py --init
    echo Database created!
)

REM Step 4: Activate virtual environment
echo.
echo [4/5] Activating environment...
call venv\Scripts\activate.bat

REM Step 5: Start the application
echo.
echo [5/5] Starting Voice Time...
echo.
echo ==========================================
echo   READY!
echo ==========================================
echo.
echo The app will open in your browser automatically.
echo.
echo Web Interface: http://localhost:5000
echo.
echo Press Ctrl+C to stop
echo.

REM Auto-open browser after 2 seconds
start "" timeout /t 2 /nobreak ^>nul ^& start http://localhost:5000

REM Start Flask
python run.py
