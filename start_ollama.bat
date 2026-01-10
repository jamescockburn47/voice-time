@echo off
REM Start Ollama Server in Background

REM Check if Ollama is installed
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Ollama is not installed!
    echo.
    echo Please install Ollama from: https://ollama.ai
    echo.
    exit /b 1
)

REM Check if Ollama is already running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama is already running
    goto check_model
)

REM Start Ollama in background (minimized window)
echo Starting Ollama server...
start "Ollama Server" /MIN ollama serve

REM Wait for it to start (with timeout)
set /a count=0
:check_loop
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 goto check_model

set /a count+=1
if %count% geq 30 (
    echo ERROR: Ollama failed to start after 30 seconds
    exit /b 1
)

timeout /t 1 /nobreak >nul
goto check_loop

:check_model
REM Check if model is installed
echo Checking if model is installed...
ollama list | findstr "qwen2.5:1.5b-instruct" >nul 2>&1
if %errorlevel% equ 0 (
    echo Model is already installed
    exit /b 0
)

REM Pull the model
echo.
echo Model not found. Downloading qwen2.5:1.5b-instruct...
echo This may take 2-3 minutes (~1GB download - SMALL MODEL)
echo.
ollama pull qwen2.5:1.5b-instruct

if %errorlevel% equ 0 (
    echo.
    echo Model downloaded successfully!
    exit /b 0
) else (
    echo.
    echo ERROR: Failed to download model
    exit /b 1
)

exit /b 0
