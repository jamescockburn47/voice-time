@echo off
REM Test Ollama Installation and Model

echo.
echo ==========================================
echo   Testing Ollama Setup
echo ==========================================
echo.

REM Test 1: Check if Ollama is installed
echo [Test 1/4] Checking if Ollama is installed...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo FAIL: Ollama is not installed
    echo.
    echo Please install from: https://ollama.ai
    echo.
    goto end
)
echo PASS: Ollama is installed
ollama --version
echo.

REM Test 2: Check if Ollama server is running
echo [Test 2/4] Checking if Ollama server is running...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo FAIL: Ollama server is not running
    echo.
    echo Starting Ollama server...
    start "Ollama Server" /MIN ollama serve
    echo Waiting 5 seconds...
    timeout /t 5 /nobreak >nul
    
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel% neq 0 (
        echo FAIL: Could not start Ollama server
        goto end
    )
)
echo PASS: Ollama server is running
echo.

REM Test 3: Check if model is installed
echo [Test 3/4] Checking if model is installed...
ollama list | findstr "qwen2.5:7b-instruct" >nul 2>&1
if %errorlevel% neq 0 (
    echo FAIL: Model not found
    echo.
    echo Would you like to download it now? (Y/N)
    set /p download="Download model? (Y/N): "
    if /i "%download%"=="Y" (
        echo.
        echo Downloading model (this may take 5-10 minutes)...
        ollama pull qwen2.5:7b-instruct
        if %errorlevel% equ 0 (
            echo PASS: Model downloaded successfully
        ) else (
            echo FAIL: Model download failed
            goto end
        )
    ) else (
        goto end
    )
) else (
    echo PASS: Model is installed
)
echo.

REM Test 4: Test model
echo [Test 4/4] Testing model...
echo Testing with simple prompt...
curl -s http://localhost:11434/api/generate -d "{\"model\":\"qwen2.5:7b-instruct\",\"prompt\":\"Say hello\",\"stream\":false}" >nul 2>&1
if %errorlevel% equ 0 (
    echo PASS: Model is working!
) else (
    echo FAIL: Model test failed
)
echo.

echo ==========================================
echo   All Tests Complete!
echo ==========================================
echo.
echo Your Ollama setup is ready for Voice Time!
echo You can now run: START.bat
echo.

:end
pause
