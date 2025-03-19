@echo off
REM Run the Telegram Shadow Mode with specified parameters

REM Set console colors for better readability
color 0A

echo ===================================================================
echo              AI Football Betting Advisor - Telegram Shadow Mode
echo ===================================================================
echo.

REM Check if Python is installed with correct version
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or later and try again
    echo.
    pause
    exit /b 1
)

REM Check for required directories
if not exist "logs" mkdir logs
if not exist "data\shadow" mkdir data\shadow
if not exist "utils" mkdir utils

REM Check for required files
if not exist ".env" (
    color 0E
    echo Warning: .env file not found. Configuration may be incomplete.
    echo You should run setup.py first to initialize the environment.
    echo.
    set /p CONTINUE=Continue anyway? (y/n): 
    if /i not "%CONTINUE%"=="y" exit /b 1
    color 0A
)

REM Check for the Telegram bot token in .env
findstr /C:"TELEGRAM_BOT_TOKEN=your_bot_token_here" .env >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    color 0E
    echo Warning: Telegram bot token not set in .env file.
    echo You need to update the TELEGRAM_BOT_TOKEN value in the .env file.
    echo.
    set /p CONTINUE=Continue anyway? (y/n): 
    if /i not "%CONTINUE%"=="y" exit /b 1
    color 0A
)

REM Parse command line arguments
set DURATION=14
set BANKROLL=100
set QUICK=

:parse_args
if "%~1"=="" goto run
if /i "%~1"=="--duration" (
    set DURATION=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-d" (
    set DURATION=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--bankroll" (
    set BANKROLL=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="-b" (
    set BANKROLL=%~2
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--quick" (
    set QUICK=--quick
    shift
    goto parse_args
)
if /i "%~1"=="-q" (
    set QUICK=--quick
    shift
    goto parse_args
)
if /i "%~1"=="--help" (
    echo Usage: run_telegram_shadow.bat [OPTIONS]
    echo.
    echo Options:
    echo   -d, --duration NUMBER  Simulation duration in days (default: 14)
    echo   -b, --bankroll NUMBER  Initial bankroll amount (default: 100)
    echo   -q, --quick            Enable quick mode (faster simulation)
    echo   --help                 Show this help message
    echo.
    exit /b 0
)

echo Unknown parameter: %~1
shift
goto parse_args

:run
echo Starting Telegram Shadow Mode with:
echo   🕒 Duration: %DURATION% days
echo   💰 Bankroll: $%BANKROLL%
if defined QUICK echo   ⚡ Quick mode: Enabled

echo.
echo Press Ctrl+C to stop the simulation at any time
echo.
echo This window will display the simulation progress...
echo.

REM Install any missing requirements
python -c "import telegram" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    pip install python-telegram-bot==13.7 python-dotenv
)

REM Run the simulation
python run_telegram_shadow.py --duration %DURATION% --bankroll %BANKROLL% %QUICK%

echo.
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo ❌ Shadow mode exited with errors. Check the logs for details.
    echo   See logs/telegram_shadow_mode.log for more information.
) else (
    color 0A
    echo ✅ Shadow mode completed successfully.
    echo   Results saved to data/shadow/ directory.
)

echo.
echo Press any key to exit...
pause > nul 