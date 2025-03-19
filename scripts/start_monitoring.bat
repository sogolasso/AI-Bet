@echo off
title Betting Advisor Monitoring Proxy
color 0B
echo Betting Advisor Monitoring Proxy
echo =======================================
echo.
echo This script will start a web-based proxy to access Grafana and Prometheus.
echo.
echo Requirements:
echo  - Python 3.6 or higher
echo  - kubectl configured and accessible
echo.
echo The web interface will open automatically in your browser.
echo.
echo Press any key to continue...
pause > nul

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo ERROR: Python is not installed or not in PATH
  echo Please install Python 3.6 or higher and try again
  echo.
  echo Press any key to exit...
  pause > nul
  exit /b 1
)

REM Run the monitoring proxy
python "%~dp0monitoring_proxy.py"

echo.
echo Press any key to exit...
pause > nul 