# Start-DiagnosticTool.ps1
# This script launches the monitoring diagnostic tool directly from PowerShell

# Get the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run the diagnostic tool
Write-Host "Starting Betting Advisor Monitoring Diagnostics..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to exit at any time." -ForegroundColor Yellow

# Execute the main diagnostic script
& "$scriptPath\monitor_connection.ps1"

# Keep console open
Write-Host "`nDiagnostic tool completed. Press any key to exit..." -ForegroundColor Green
$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null 