@echo off
REM Start Ollama Server in Background

REM Check if Ollama is installed
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Ollama is not installed yet.
    echo Installing automatically...
    echo.
    
    call install_ollama.bat
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Could not install Ollama automatically
        exit /b 1
    )
    
    echo.
    echo Ollama installed! Continuing...
    echo.
)

REM Check if Ollama is already running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    goto check_model
)

REM Start Ollama in background (minimized window)
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
REM Check if model is already installed (silently)
ollama list 2>nul | findstr /C:"qwen2.5:1.5b-instruct" >nul 2>&1
if %errorlevel% equ 0 (
    REM Model exists, exit silently
    exit /b 0
)

REM Model not found - need to download
echo.
echo ==========================================
echo   FIRST TIME SETUP
echo ==========================================
echo.
echo Downloading AI model: qwen2.5:1.5b-instruct
echo Size: ~1GB (SMALL, FAST model)
echo Time: 2-3 minutes
echo.
echo This only happens ONCE!
echo.
echo ==========================================
echo.

ollama pull qwen2.5:1.5b-instruct

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo   Model downloaded successfully!
    echo   Future starts will be instant!
    echo ==========================================
    echo.
    timeout /t 2 /nobreak >nul
    exit /b 0
) else (
    echo.
    echo ERROR: Failed to download model
    exit /b 1
)

exit /b 0
