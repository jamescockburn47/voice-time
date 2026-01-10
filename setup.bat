@echo off
REM Voice Time - First Time Setup

echo.
echo ==========================================
echo   Voice Time Recording System - Setup
echo ==========================================
echo.

REM Check/Install Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed yet.
    echo Installing automatically...
    echo.
    
    call install_python.bat
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Could not install Python automatically
        pause
        exit /b 1
    )
    
    echo.
    echo Python installed! Continuing...
    echo.
)

echo [1/5] Checking Python version...
python --version

REM Create virtual environment
if exist "venv" (
    echo.
    echo Virtual environment already exists. Skipping creation.
) else (
    echo.
    echo [2/5] Creating virtual environment...
    python -m venv venv
)

REM Activate and install dependencies
echo.
echo [3/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

REM Check/Install Ollama and model
echo.
echo [4/5] Installing voice dependencies...
pip install pynput
echo.
echo [5/5] Setting up Ollama and AI model...
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
