@echo off
REM Production Mode Launcher for AI Football Betting Advisor
color 0A
echo.
echo ===================================================================
echo              AI Football Betting Advisor - Production Mode
echo ===================================================================
echo.
echo This will run the AI Football Betting Advisor in production mode.
echo.
echo WARNING: Production mode will place REAL bets if configured to do so.
echo          Make sure you have set up your configuration correctly.
echo.
echo Are you sure you want to continue? (Y/N)
set /p CONFIRM=
if /i "%CONFIRM%" NEQ "Y" (
    echo Operation cancelled by user.
    pause
    exit /b 0
)

echo.
echo Starting production mode...
echo Press Ctrl+C at any time to exit.
echo.
python run_production.py %*
echo.
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo Production mode exited with errors. See logs for details.
) else (
    echo Production mode completed successfully.
)
echo.
echo Press any key to exit...
pause > nul 