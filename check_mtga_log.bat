@echo off
cls
echo ========================================
echo    MTGA Log File Checker
echo ========================================
echo.

echo Searching for MTGA log files...
echo.

REM Check AppData\LocalLow\Wizards Of The Coast\MTGA for Player.log
if exist "%APPDATA%\..\LocalLow\Wizards Of The Coast\MTGA\Player.log" (
    echo ✅ Found: AppData\LocalLow\Wizards Of The Coast\MTGA\Player.log
    goto :found
)

REM Check LocalAppData\Wizards Of The Coast\MTGA for Player.log
if exist "%LOCALAPPDATA%\Wizards Of The Coast\MTGA\Player.log" (
    echo ✅ Found: LocalAppData\Wizards Of The Coast\MTGA\Player.log
    goto :found
)

REM Check AppData\LocalLow\WOTC\MTGA for output_log.txt (legacy)
if exist "%APPDATA%\..\LocalLow\WOTC\MTGA\output_log.txt" (
    echo ✅ Found: AppData\LocalLow\WOTC\MTGA\output_log.txt
    goto :found
)

REM Check LocalAppData\WOTC\MTGA for output_log.txt (legacy)
if exist "%LOCALAPPDATA%\WOTC\MTGA\output_log.txt" (
    echo ✅ Found: LocalAppData\WOTC\MTGA\output_log.txt
    goto :found
)

REM Check Documents
if exist "%USERPROFILE%\Documents\MTGA\Player.log" (
    echo ✅ Found: Documents\MTGA\Player.log
    goto :found
)

echo ❌ No MTGA log files found in common locations
echo.
echo The game event log is only created when you're actively playing a match.
echo Make sure you:
echo 1. Start a match in MTGA Arena
echo 2. Let it run for a few minutes
echo 3. Then run this finder again
echo.
goto :end

:found
echo.
echo ✅ MTGA log files found! You can now run the AI Coach.
echo.

:end
echo Press any key to continue...
pause >nul
