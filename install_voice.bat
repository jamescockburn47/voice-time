@echo off
REM Install voice dependencies (pynput for hotkey support)

echo.
echo ==========================================
echo   Installing Voice Mode Dependencies
echo ==========================================
echo.

REM Activate virtual environment
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Installing pynput for hotkey support...
pip install pynput

echo.
echo ==========================================
echo   Installation Complete!
echo ==========================================
echo.
echo You can now use voice mode!
echo.
echo Double-click: 🎤 VOICE MODE.bat
echo.

pause
