@echo off
echo ========================================
echo    MTGA AI Coach - Test Mode
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "parser\main_with_heuristic.py" (
    echo ERROR: Please run this from the mtga-coach directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo Running AI Coach in test mode...
echo This will test the AI system with sample data.
echo.

REM Run the test
python parser\main_with_heuristic.py test

echo.
echo Test completed.
pause
