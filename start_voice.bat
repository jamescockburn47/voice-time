@echo off
REM Voice Time - Voice Mode with Hotkey Activation

title Voice Time - Voice Mode

echo.
echo ==========================================
echo   Voice Time - VOICE MODE
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Auto-start Ollama if not running
echo Starting Ollama (if needed)...
call start_ollama.bat

REM Check if database exists
if not exist "%USERPROFILE%\.voice_time\voice_time.db" (
    echo.
    echo Database not found. Initializing...
    python run.py --init
    echo.
)

REM Start voice mode
echo.
echo ==========================================
echo   VOICE MODE READY
echo ==========================================
echo.
echo Press and hold Ctrl+Space to record
echo Or press Ctrl+Shift+T to toggle
echo.
echo NO typing needed - just use hotkey!
echo.
echo Press Ctrl+C to exit
echo.

python run_voice.py

pause
