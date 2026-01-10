@echo off
REM Initialize Voice Time Database

echo.
echo ======================================
echo   Initialize Voice Time Database
echo ======================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Initialize database
echo Initializing database with sample data...
echo.

python run.py --init

echo.
echo Done!
echo.
pause
