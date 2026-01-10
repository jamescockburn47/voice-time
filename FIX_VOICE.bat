@echo off
REM Fix Voice Activation Issues

title Fixing Voice Activation

echo.
echo ==========================================
echo   FIXING VOICE ACTIVATION
echo ==========================================
echo.

call venv\Scripts\activate.bat

echo Installing all voice dependencies...
echo.

pip install --upgrade pynput faster-whisper sounddevice numpy

echo.
echo ==========================================
echo   Installation Complete!
echo ==========================================
echo.
echo Voice dependencies installed:
echo   ✓ pynput (hotkey support)
echo   ✓ faster-whisper (speech recognition)
echo   ✓ sounddevice (audio capture)
echo   ✓ numpy (audio processing)
echo.
echo Now try running:
echo   ⭐ START HERE.bat
echo   Choose option 1 (VOICE MODE)
echo.

pause
