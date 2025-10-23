@echo off
echo ========================================
echo    MTGA AI Coach - Smart Launcher
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

REM Check for MTGA log file
set "LOG_PATH=%APPDATA%\..\LocalLow\WOTC\MTGA\output_log.txt"

if not exist "%LOG_PATH%" (
    echo ❌ MTGA log file not found!
    echo.
    echo To use the AI Coach:
    echo 1. Start MTGA Arena
    echo 2. Begin a match (any format)
    echo 3. Let it run for a few minutes
    echo 4. Then run this launcher again
    echo.
    echo Expected location: %LOG_PATH%
    echo.
    echo Would you like to:
    echo [1] Test AI Coach with sample data
    echo [2] Exit and start MTGA first
    echo.
    set /p choice="Enter your choice (1 or 2): "
    
    if "%choice%"=="1" (
        echo.
        echo Running AI Coach in test mode...
        python parser\main_with_heuristic.py test
        pause
        exit /b 0
    ) else (
        echo.
        echo Please start MTGA Arena first, then run this launcher again.
        pause
        exit /b 0
    )
)

echo ✅ Found MTGA log file!
echo Location: %LOG_PATH%
echo.

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
echo 1. The AI will analyze your MTGA game in real-time
echo 2. Watch for AI recommendations in this window
echo 3. Press Ctrl+C to stop the AI Coach
echo.

REM Start the AI Coach
python parser\main_with_heuristic.py

echo.
echo MTGA AI Coach stopped.
pause
