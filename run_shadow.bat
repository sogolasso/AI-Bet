@echo off
REM Shadow Mode Launcher for AI Football Betting Advisor
color 0A
echo.
echo ===================================================================
echo              AI Football Betting Advisor - Shadow Mode
echo ===================================================================
echo.
echo This will run the AI Football Betting Advisor in shadow mode.
echo Shadow mode simulates betting without risking real money.
echo.
echo Press Ctrl+C at any time to exit.
echo.
python run_shadow.py %*
echo.
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo Shadow mode exited with errors. See logs for details.
) else (
    echo Shadow mode completed successfully.
)
echo.
echo Press any key to exit...
pause > nul 