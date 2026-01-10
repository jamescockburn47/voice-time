@echo off
REM Voice Time - First Time Setup

echo.
echo ==========================================
echo   Voice Time Recording System - Setup
echo ==========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.11 or higher from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version

REM Create virtual environment
if exist "venv" (
    echo.
    echo Virtual environment already exists. Skipping creation.
) else (
    echo.
    echo [2/4] Creating virtual environment...
    python -m venv venv
)

REM Activate and install dependencies
echo.
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

REM Check/Install Ollama and model
echo.
echo [4/4] Setting up Ollama and AI model...
call start_ollama.bat
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Ollama setup failed
    pause
    exit /b 1
)
echo Ollama is ready!

echo.
echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Everything is ready!
echo.
echo Next step:
echo   Double-click: ⭐ START HERE.bat
echo.
echo No other manual steps needed!
echo.

pause
