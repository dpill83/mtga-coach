@echo off
echo ========================================
echo    MTGA AI Coach - Starting Up
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

REM Check if requirements are installed
echo Checking dependencies...
python -c "import watchdog, pydantic, orjson, websockets, requests, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check if Scryfall data exists
if not exist "data\cards.json" (
    echo Downloading Scryfall card data...
    python data\scryfall_downloader.py
    if errorlevel 1 (
        echo ERROR: Failed to download Scryfall data
        pause
        exit /b 1
    )
)

echo.
echo Starting MTGA AI Coach...
echo.
echo Instructions:
echo 1. Start a game in MTGA Arena
echo 2. The AI will analyze your game in real-time
echo 3. Watch for AI recommendations in this window
echo 4. Press Ctrl+C to stop the AI Coach
echo.

REM Start the AI Coach
python parser\main_with_heuristic.py

echo.
echo MTGA AI Coach stopped.
pause
