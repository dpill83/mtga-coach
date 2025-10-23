@echo off
echo ========================================
echo    MTGA AI Coach - Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python found: 
python --version

REM Check if we're in the right directory
if not exist "parser\main_with_heuristic.py" (
    echo ERROR: Please run this from the mtga-coach directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo.
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Downloading Scryfall card data...
python data\scryfall_downloader.py
if errorlevel 1 (
    echo ERROR: Failed to download Scryfall data
    pause
    exit /b 1
)

echo.
echo Running AI Coach tests...
python tests\test_heuristic.py
if errorlevel 1 (
    echo WARNING: Some tests failed, but continuing...
)

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo You can now run:
echo   - run_ai_coach.bat     (Start AI Coach with live MTGA)
echo   - test_ai_coach.bat    (Test AI Coach with sample data)
echo.
echo The AI Coach will:
echo   - Monitor your MTGA games in real-time
echo   - Provide intelligent play recommendations
echo   - Detect threats and suggest responses
echo   - Help you become a better Magic player!
echo.
pause
