@echo off
REM Push Voice Time to GitHub

title Pushing to GitHub

echo.
echo ==========================================
echo   Push to GitHub
echo ==========================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git is not installed!
    echo.
    echo Please install Git from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

REM Check if already initialized
if exist ".git" (
    echo Git repository already initialized
) else (
    echo Initializing Git repository...
    git init
    echo.
)

REM Add remote if not exists
git remote | findstr "origin" >nul 2>&1
if %errorlevel% neq 0 (
    echo Adding GitHub remote...
    git remote add origin https://github.com/jamescockburn47/voice-time.git
    echo.
) else (
    echo Remote 'origin' already exists
    echo.
)

REM Configure git to use main branch
git branch -M main

REM Show what will be committed
echo Files to be committed:
echo.
git status --short
echo.

REM Ask for confirmation
set /p confirm="Push these files to GitHub? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo.
    echo Cancelled.
    pause
    exit /b 0
)

REM Add all files
echo.
echo Adding files...
git add .

REM Commit
echo.
set /p message="Enter commit message (or press Enter for default): "
if "%message%"=="" (
    set message=Initial commit - Voice Time Recording System
)

echo.
echo Committing...
git commit -m "%message%"

REM Push to GitHub
echo.
echo Pushing to GitHub...
echo.
echo You may be prompted for your GitHub credentials...
echo.

git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo   SUCCESS!
    echo ==========================================
    echo.
    echo Your code has been pushed to:
    echo https://github.com/jamescockburn47/voice-time
    echo.
) else (
    echo.
    echo ==========================================
    echo   PUSH FAILED
    echo ==========================================
    echo.
    echo This might be because:
    echo   1. You need to authenticate with GitHub
    echo   2. You don't have permission to push
    echo   3. Network issue
    echo.
    echo Try running this manually:
    echo   git push -u origin main
    echo.
)

pause
