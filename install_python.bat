@echo off
REM Auto-install Python (no manual steps needed!)

title Installing Python

echo.
echo ==========================================
echo   AUTO-INSTALLING PYTHON
echo ==========================================
echo.
echo Python is required to run Voice Time.
echo Installing it automatically...
echo.

REM Method 1: Try winget (Windows Package Manager)
echo [Method 1] Trying Windows Package Manager (winget)...
winget --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Found winget! Installing Python 3.11...
    echo.
    echo This may take 2-3 minutes...
    echo.
    winget install --id=Python.Python.3.11 -e --silent --accept-package-agreements --accept-source-agreements
    
    if %errorlevel% equ 0 (
        echo.
        echo ==========================================
        echo   Python installed successfully!
        echo ==========================================
        echo.
        echo Refreshing environment...
        timeout /t 3 /nobreak >nul
        
        REM Refresh PATH
        call :RefreshPath
        
        REM Verify installation
        python --version >nul 2>&1
        if %errorlevel% equ 0 (
            echo.
            echo Python is now ready!
            echo.
            timeout /t 2 /nobreak >nul
            exit /b 0
        ) else (
            echo.
            echo Installation complete!
            echo.
            echo IMPORTANT: Please close this window and run the app again.
            echo (Python PATH needs terminal restart)
            echo.
            pause
            exit /b 0
        )
    )
)

REM Method 2: Direct download
echo.
echo [Method 2] Downloading Python installer...
echo.

set "TEMP_DIR=%TEMP%\python_install"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo Downloading Python 3.11 from python.org...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP_DIR%\python-installer.exe'}"

if %errorlevel% equ 0 (
    echo Download complete!
    echo.
    echo Installing Python...
    echo (Installing to user directory, adding to PATH)
    echo.
    
    REM Run installer with silent flags
    REM /quiet = silent, InstallAllUsers=0 = user install, PrependPath=1 = add to PATH
    start /wait "" "%TEMP_DIR%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    
    echo.
    echo Installation complete!
    echo.
    
    REM Clean up
    rmdir /s /q "%TEMP_DIR%" 2>nul
    
    echo.
    echo ==========================================
    echo   Python installed successfully!
    echo ==========================================
    echo.
    echo IMPORTANT: Please close this window and run the app again.
    echo (Python PATH needs terminal restart)
    echo.
    pause
    exit /b 0
) else (
    echo.
    echo ==========================================
    echo   AUTO-INSTALL FAILED
    echo ==========================================
    echo.
    echo Please install manually:
    echo   1. Visit: https://www.python.org/downloads/
    echo   2. Download Python 3.11 or higher
    echo   3. During install, check "Add Python to PATH"
    echo   4. Come back and run this app again
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

exit /b 1

:RefreshPath
REM Refresh environment variables
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%b"
set "PATH=%SYS_PATH%;%USER_PATH%"
exit /b 0
