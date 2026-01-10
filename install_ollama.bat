@echo off
REM Auto-install Ollama (no manual steps needed!)

title Installing Ollama

echo.
echo ==========================================
echo   AUTO-INSTALLING OLLAMA
echo ==========================================
echo.
echo Ollama is the AI engine that powers Voice Time.
echo Installing it automatically...
echo.

REM Method 1: Try winget (Windows Package Manager)
echo [Method 1] Trying Windows Package Manager (winget)...
winget --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Found winget! Installing Ollama...
    echo.
    winget install --id=Ollama.Ollama -e --silent --accept-package-agreements --accept-source-agreements
    
    if %errorlevel% equ 0 (
        echo.
        echo ==========================================
        echo   Ollama installed successfully!
        echo ==========================================
        echo.
        echo Refreshing environment...
        timeout /t 2 /nobreak >nul
        
        REM Refresh PATH
        call :RefreshPath
        
        REM Verify installation
        ollama --version >nul 2>&1
        if %errorlevel% equ 0 (
            echo Ollama is now ready!
            exit /b 0
        )
    )
)

REM Method 2: Download and install manually
echo.
echo [Method 2] Downloading Ollama installer...
echo.

REM Create temp directory
set "TEMP_DIR=%TEMP%\ollama_install"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM Download installer using PowerShell
echo Downloading from ollama.ai...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://ollama.ai/download/OllamaSetup.exe' -OutFile '%TEMP_DIR%\OllamaSetup.exe'}"

if %errorlevel% equ 0 (
    echo Download complete!
    echo.
    echo Installing Ollama...
    echo.
    
    REM Run installer silently
    start /wait "" "%TEMP_DIR%\OllamaSetup.exe" /SILENT /SUPPRESSMSGBOXES
    
    echo.
    echo Installation complete!
    echo.
    
    REM Clean up
    rmdir /s /q "%TEMP_DIR%" 2>nul
    
    REM Refresh PATH
    call :RefreshPath
    
    REM Verify installation
    timeout /t 2 /nobreak >nul
    ollama --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo.
        echo ==========================================
        echo   Ollama installed successfully!
        echo ==========================================
        echo.
        exit /b 0
    ) else (
        echo.
        echo Installation complete, but please restart your terminal.
        echo Then run this script again.
        echo.
        exit /b 0
    )
) else (
    echo.
    echo ==========================================
    echo   AUTO-INSTALL FAILED
    echo ==========================================
    echo.
    echo Please install manually:
    echo   1. Visit: https://ollama.ai
    echo   2. Click "Download for Windows"
    echo   3. Run the installer
    echo   4. Come back and run this app again
    echo.
    pause
    start https://ollama.ai
    exit /b 1
)

exit /b 1

:RefreshPath
REM Refresh environment variables
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
set "PATH=%SYS_PATH%;%USER_PATH%"
exit /b 0
