@echo off
echo ========================================
echo    MTGA Log File Checker
echo ========================================
echo.

REM Check for MTGA log file
set "LOG_PATH=%APPDATA%\..\LocalLow\WOTC\MTGA\output_log.txt"

if exist "%LOG_PATH%" (
    echo ✅ Found MTGA log file!
    echo Location: %LOG_PATH%
    echo.
    echo You can now run the AI Coach:
    echo   - run_ai_coach.bat
    echo.
) else (
    echo ❌ MTGA log file not found
    echo.
    echo To fix this:
    echo 1. Start MTGA Arena
    echo 2. Begin a match (any format)
    echo 3. Let it run for a few minutes
    echo 4. Then run this checker again
    echo.
    echo Expected location: %LOG_PATH%
    echo.
)

echo Press any key to continue...
pause >nul
