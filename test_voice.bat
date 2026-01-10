@echo off
REM Test Voice Activation Components

title Testing Voice Components

echo.
echo ==========================================
echo   Voice Activation Diagnostics
echo ==========================================
echo.

call venv\Scripts\activate.bat

echo [1/5] Checking pynput (hotkey support)...
pip show pynput >nul 2>&1
if %errorlevel% neq 0 (
    echo MISSING: pynput not installed
    echo Installing now...
    pip install pynput
) else (
    echo INSTALLED: pynput
)
echo.

echo [2/5] Checking faster-whisper (speech recognition)...
pip show faster-whisper >nul 2>&1
if %errorlevel% neq 0 (
    echo MISSING: faster-whisper not installed  
    echo Installing now...
    pip install faster-whisper
) else (
    echo INSTALLED: faster-whisper
)
echo.

echo [3/5] Checking sounddevice (audio capture)...
pip show sounddevice >nul 2>&1
if %errorlevel% neq 0 (
    echo MISSING: sounddevice not installed
    echo Installing now...
    pip install sounddevice
) else (
    echo INSTALLED: sounddevice
)
echo.

echo [4/5] Testing microphone access...
python -c "import sounddevice as sd; print('Microphones found:'); print(sd.query_devices()); print('\nDefault input device:', sd.query_devices(kind='input'))"
echo.

echo [5/5] Testing hotkey listener...
echo.
echo This will test the Ctrl+Space hotkey.
echo Press Ctrl+Space now, then press Ctrl+C to stop.
echo.
pause

python -c "from voice_time.voice.hotkey import HotkeyListener, HotkeyConfig; import time; print('Testing hotkey...'); print('Press Ctrl+Space to test'); listener = HotkeyListener(lambda: print('🎤 Recording started!'), lambda audio: print('⏹️ Recording stopped!'), HotkeyConfig()); listener.start(); time.sleep(30)"

echo.
echo ==========================================
echo   Diagnostic Complete!
echo ==========================================
echo.

pause
