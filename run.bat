@echo off
:: ====================================================================
:: AI Football Betting Advisor - One-Click Runner (Windows)
:: ====================================================================
:: This script provides easy commands to start, stop, and manage your
:: AI Football Betting Advisor system.
:: ====================================================================

setlocal enabledelayedexpansion

:: Set console colors
set GREEN=[92m
set YELLOW=[93m
set RED=[91m
set BLUE=[94m
set NC=[0m

:: Banner
echo %BLUE%
echo   █████╗ ██╗    ███████╗ ██████╗  ██████╗ ████████╗██████╗  █████╗ ██╗     ██╗     
echo  ██╔══██╗██║    ██╔════╝██╔═══██╗██╔═══██╗╚══██╔══╝██╔══██╗██╔══██╗██║     ██║     
echo  ███████║██║    █████╗  ██║   ██║██║   ██║   ██║   ██████╔╝███████║██║     ██║     
echo  ██╔══██║██║    ██╔══╝  ██║   ██║██║   ██║   ██║   ██╔══██╗██╔══██║██║     ██║     
echo  ██║  ██║██║    ██║     ╚██████╔╝╚██████╔╝   ██║   ██████╔╝██║  ██║███████╗███████╗
echo  ╚═╝  ╚═╝╚═╝    ╚═╝      ╚═════╝  ╚═════╝    ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝
echo %GREEN%       BETTING ADVISOR%NC%
echo %YELLOW%       Value-Based Football Betting Recommendations%NC%
echo.

:: Check if Docker is installed
docker --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%Error: Docker is not installed. Please install Docker Desktop for Windows first.%NC%
    exit /b 1
)

:: Check if docker-compose is installed
docker-compose --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%Error: docker-compose is not available. Please ensure Docker Desktop is properly installed.%NC%
    exit /b 1
)

:: Parse command line argument
if "%~1"=="" goto menu
if "%~1"=="start" goto start_system
if "%~1"=="stop" goto stop_system
if "%~1"=="restart" goto restart_system
if "%~1"=="status" goto check_status
if "%~1"=="logs" goto view_logs
if "%~1"=="shadow" goto run_shadow_mode
if "%~1"=="menu" goto menu
if "%~1"=="help" goto display_help
echo %RED%Unknown option: %~1%NC%
goto display_help

:start_system
    echo %BLUE%Starting AI Football Betting Advisor...%NC%
    docker-compose up -d
    echo %GREEN%System is now running!%NC%
    call :check_status
    goto end

:stop_system
    echo %YELLOW%Stopping AI Football Betting Advisor...%NC%
    docker-compose down
    echo %GREEN%System stopped.%NC%
    goto end

:restart_system
    echo %YELLOW%Restarting AI Football Betting Advisor...%NC%
    docker-compose restart
    echo %GREEN%System restarted!%NC%
    call :check_status
    goto end

:check_status
    echo %BLUE%Checking system status...%NC%
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr /i "football-betting redis"
    
    :: Check if advisor container is running
    docker ps -q -f name=football-betting-advisor > nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo %GREEN%✓ Advisor is running%NC%
        
        :: Get health status
        for /f "tokens=*" %%i in ('docker inspect --format="{{.State.Health.Status}}" football-betting-advisor 2^>nul') do set health=%%i
        echo %BLUE%Health status: !health!%NC%
        
        :: Show logs snippet
        echo %BLUE%Recent logs:%NC%
        docker logs --tail 5 football-betting-advisor
    ) else (
        echo %RED%✗ Advisor is not running%NC%
    )
    goto :eof

:view_logs
    echo %BLUE%Showing logs for AI Football Betting Advisor...%NC%
    echo %YELLOW%Press Ctrl+C to exit logs, then type 'Y' to exit%NC%
    docker logs -f football-betting-advisor
    goto end

:run_shadow_mode
    echo %BLUE%Running in shadow mode (no real bets)...%NC%
    echo %YELLOW%This will simulate betting without risking real money%NC%
    
    set days=14
    set bankroll=1000
    
    echo Days to simulate: %days%
    echo Virtual bankroll: %bankroll%
    
    docker exec football-betting-advisor python shadow_mode.py --days %days% --bankroll %bankroll%
    
    echo %GREEN%Shadow mode started. Check Telegram for updates or use 'view_logs' to monitor progress.%NC%
    goto end

:display_help
    echo %BLUE%AI Football Betting Advisor - Command Options:%NC%
    echo.
    echo %GREEN%run.bat%NC%               - Show interactive menu
    echo %GREEN%run.bat start%NC%         - Start the system
    echo %GREEN%run.bat stop%NC%          - Stop the system
    echo %GREEN%run.bat restart%NC%       - Restart the system
    echo %GREEN%run.bat status%NC%        - Check system status
    echo %GREEN%run.bat logs%NC%          - View system logs
    echo %GREEN%run.bat shadow%NC%        - Run in shadow mode (test without real money)
    echo %GREEN%run.bat menu%NC%          - Show interactive menu
    echo.
    goto end

:menu
    cls
    echo %BLUE%AI Football Betting Advisor - Management Menu%NC%
    echo.
    echo %GREEN%1)%NC% Start system
    echo %GREEN%2)%NC% Stop system
    echo %GREEN%3)%NC% Restart system
    echo %GREEN%4)%NC% Check system status
    echo %GREEN%5)%NC% View logs
    echo %GREEN%6)%NC% Run in shadow mode
    echo %GREEN%7)%NC% Generate performance report
    echo %GREEN%8)%NC% Re-train ML model
    echo %GREEN%9)%NC% Exit
    echo.
    
    set /p choice="Enter your choice: "
    
    if "%choice%"=="1" call :start_system
    if "%choice%"=="2" call :stop_system
    if "%choice%"=="3" call :restart_system
    if "%choice%"=="4" call :check_status
    if "%choice%"=="5" goto view_logs
    if "%choice%"=="6" call :run_shadow_mode
    if "%choice%"=="7" docker exec football-betting-advisor python main.py --report
    if "%choice%"=="8" docker exec football-betting-advisor python main.py --retrain
    if "%choice%"=="9" goto end
    
    echo.
    echo %YELLOW%Press any key to return to menu%NC%
    pause > nul
    goto menu

:end
    endlocal 