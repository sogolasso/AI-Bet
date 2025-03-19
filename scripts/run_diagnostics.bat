@echo off
title Betting Advisor Monitoring Diagnostics
color 0B
echo Betting Advisor Monitoring Diagnostics
echo =======================================
echo.
echo This will run the PowerShell monitoring script to diagnose and fix connection issues.
echo.
echo If you encounter any PowerShell execution policy errors, you may need to run:
echo Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
echo.
echo Press any key to continue...
pause > nul

REM Run PowerShell script with bypass execution policy to ensure it works on all systems
PowerShell -Command "& {Start-Process PowerShell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0monitor_connection.ps1\"' -Verb RunAs -Wait}"

echo.
echo Script completed. Press any key to exit...
pause > nul 