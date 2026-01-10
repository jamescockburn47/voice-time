@echo off
REM Quick Ollama Status Check

title Checking Ollama

echo.
echo ==========================================
echo   Checking Ollama Status
echo ==========================================
echo.

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo Status: ✓ Ollama is RUNNING
    echo.
    
    REM Check model
    echo Checking for model...
    ollama list | findstr "qwen2.5:1.5b-instruct"
    
    if %errorlevel% equ 0 (
        echo.
        echo ✓ Model installed and ready!
    ) else (
        echo.
        echo ✗ Model not found!
        echo.
        echo Downloading now...
        ollama pull qwen2.5:1.5b-instruct
    )
    
    echo.
    echo Testing model...
    curl -s http://localhost:11434/api/generate -d "{\"model\":\"qwen2.5:1.5b-instruct\",\"prompt\":\"Say hello\",\"stream\":false}"
    echo.
    echo.
    
    if %errorlevel% equ 0 (
        echo ✓ Ollama is working correctly!
    ) else (
        echo ✗ Ollama test failed
    )
    
) else (
    echo Status: ✗ Ollama is NOT RUNNING
    echo.
    echo Starting Ollama now...
    start "Ollama Server" /MIN ollama serve
    echo.
    echo Waiting for Ollama to start...
    timeout /t 3 /nobreak >nul
    echo.
    echo Try running the app again now.
)

echo.
echo ==========================================
pause
