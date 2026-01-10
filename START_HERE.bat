@echo off
REM Voice Time - Easy Launcher

title Voice Time Recording System

:menu
cls
echo.
echo ==========================================
echo   Voice Time Recording System
echo ==========================================
echo.
echo What would you like to do?
echo.
echo   1. First Time Setup
echo   2. Start Web UI (Type mode)
echo   3. Start VOICE Mode (Hotkey activation)
echo   4. Start CLI Mode
echo   5. Initialize/Reset Database
echo   6. Check Ollama Status
echo   7. Exit
echo.
echo ==========================================
echo.

set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto webui
if "%choice%"=="3" goto voice
if "%choice%"=="4" goto cli
if "%choice%"=="5" goto initdb
if "%choice%"=="6" goto checkollama
if "%choice%"=="7" goto end

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

:setup
cls
echo.
echo Running first time setup...
echo.
call setup.bat
pause
goto menu

:webui
cls
echo.
echo Starting Web UI...
echo.

REM Auto-start Ollama if not running
call start_ollama.bat

REM Start the app
call start.bat
goto menu

:voice
cls
echo.
echo Starting VOICE Mode...
echo.

REM Auto-start Ollama if not running
call start_ollama.bat

REM Start voice mode
call start_voice.bat
goto menu

:cli
cls
echo.
echo Starting CLI Mode...
echo.

REM Auto-start Ollama if not running
call start_ollama.bat

REM Start CLI
call start_cli.bat
goto menu

:initdb
cls
echo.
echo Initializing Database...
echo.
call init_database.bat
goto menu

:checkollama
cls
echo.
echo ==========================================
echo   Checking Ollama Status
echo ==========================================
echo.

REM Check if Ollama is installed
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Status: NOT INSTALLED
    echo.
    echo Please install Ollama from: https://ollama.ai
    echo.
    pause
    goto menu
)

echo Ollama Version:
ollama --version
echo.

REM Check if Ollama server is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Server Status: NOT RUNNING
    echo.
    echo To start Ollama server:
    echo   1. Open a new terminal
    echo   2. Run: ollama serve
    echo.
) else (
    echo Server Status: RUNNING
    echo.
    
    REM Check if model is installed
    ollama list | findstr "qwen2.5:7b-instruct" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Model Status: NOT INSTALLED
        echo.
        echo To install the model, run:
        echo   ollama pull qwen2.5:7b-instruct
        echo.
    ) else (
        echo Model Status: INSTALLED
        echo.
        echo All systems ready!
    )
)

pause
goto menu

:end
cls
echo.
echo Goodbye!
echo.
timeout /t 1 >nul
exit
