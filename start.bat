@echo off
REM Voice Time Recording System - Web UI Launcher

echo.
echo ======================================
echo   Voice Time Recording System
echo ======================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then run: venv\Scripts\activate
    echo Then run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Auto-start Ollama if not running
echo Starting Ollama (if needed)...
call start_ollama.bat
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Could not start Ollama automatically
    echo Please install Ollama from: https://ollama.ai
    echo.
    pause
)

REM Check if database exists
if not exist "%USERPROFILE%\.voice_time\voice_time.db" (
    echo.
    echo Database not found. Initializing...
    python run.py --init
    echo.
    echo Database initialized!
    echo.
    pause
)

REM Start the application
echo.
echo Starting Voice Time web server...
echo.
echo Open your browser to: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python run.py

pause
