@echo off
title TimeBrief - Production Build
color 0E

echo.
echo   ============================================================
echo            TimeBrief - Production Build
echo   ============================================================
echo.
echo   This creates a STANDALONE INSTALLER that includes everything.
echo   Users just download and run - no Python, no setup required!
echo.

:: Check prerequisites
echo [1/6] Checking prerequisites...

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

where cargo >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Rust/Cargo not found. Please install Rust from rustup.rs
    pause
    exit /b 1
)

:: Activate venv
echo [2/6] Setting up Python environment...
if not exist "venv\Scripts\activate.bat" (
    python -m venv venv
)
call venv\Scripts\activate.bat

:: Install PyInstaller if needed
pip show pyinstaller >nul 2>&1 || pip install pyinstaller -q

:: Build Python server as executable
echo [3/6] Building Python server executable...
cd src-tauri
if not exist "binaries" mkdir binaries

:: Create the PyInstaller spec for proper bundling
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name timebrief-server-x86_64-pc-windows-msvc ^
    --add-data "../voice_time;voice_time" ^
    --add-data "../config.yaml;." ^
    --hidden-import=flask ^
    --hidden-import=sqlalchemy ^
    --hidden-import=faster_whisper ^
    --hidden-import=sounddevice ^
    --hidden-import=numpy ^
    --distpath binaries ^
    ../run.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    cd ..
    pause
    exit /b 1
)

echo [4/6] Python server built successfully

:: Build Tauri app
echo [5/6] Building Tauri application...
cargo tauri build

if errorlevel 1 (
    echo [ERROR] Tauri build failed
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo [6/6] Build complete!
echo.
echo   ============================================================
echo   SUCCESS! Standalone installer created:
echo   ============================================================
echo.
echo   src-tauri\target\release\bundle\nsis\TimeBrief_0.1.0_x64-setup.exe
echo.
echo   This installer is FULLY SELF-CONTAINED:
echo   - Bundles the Python server (no Python install needed)
echo   - Auto-installs Ollama on first run
echo   - Auto-downloads AI models on first run
echo.
echo   Just share the .exe file - users double-click and go!
echo   ============================================================
echo.

pause
