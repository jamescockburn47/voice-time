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

REM Check Ollama
echo.
echo [4/4] Checking Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Ollama is not installed!
    echo.
    echo Please install Ollama from: https://ollama.ai
    echo.
    echo After installing Ollama:
    echo   1. Open a terminal
    echo   2. Run: ollama serve
    echo   3. Run: ollama pull qwen2.5:7b-instruct
    echo.
) else (
    ollama --version
    echo.
    echo Checking if model is installed...
    ollama list | findstr "qwen2.5:7b-instruct" >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo Model not found. Downloading qwen2.5:7b-instruct...
        echo This may take a few minutes (~4GB download)...
        ollama pull qwen2.5:7b-instruct
    ) else (
        echo Model already installed!
    )
)

echo.
echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Make sure Ollama is running: ollama serve
echo   2. Double-click: init_database.bat
echo   3. Double-click: start.bat
echo.

pause
