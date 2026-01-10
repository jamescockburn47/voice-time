@echo off
REM Voice Time - Unified Launcher (THE ONLY FILE YOU NEED!)

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
    echo [1/5] First time setup...
    call setup.bat
    echo.
    echo Setup complete!
    echo.
)

REM Step 2: Check Ollama
echo [2/5] Checking Ollama and AI model...
call start_ollama.bat
if %errorlevel% neq 0 (
    echo ERROR: Ollama setup failed
    pause
    exit /b 1
)

REM Step 3: Check database
if not exist "%USERPROFILE%\.voice_time\voice_time.db" (
    echo [3/5] Creating database...
    call venv\Scripts\activate.bat
    python run.py --init
)

REM Step 4: Activate environment
echo [4/5] Activating environment...
call venv\Scripts\activate.bat

REM Step 5: Launch app
echo [5/5] Starting Voice Time...
echo.
echo ==========================================
echo   READY!
echo ==========================================
echo.
echo Unified Interface with:
echo   • VOICE: Click button or Ctrl+Space
echo   • TEXT: Type as backup
echo.
echo Opening browser → http://localhost:5000
echo.
echo Press Ctrl+C to stop
echo.

REM Auto-open browser
start "" timeout /t 2 /nobreak ^>nul ^& start http://localhost:5000

REM Start Flask
python run.py

pause
