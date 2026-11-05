# Register the weekly scheduled refresh (etl/scheduled_refresh.py) with
# Windows Task Scheduler, for the machine that hosts the database.
#
# Run once from the project root in PowerShell:
#     powershell -ExecutionPolicy Bypass -File etl\register_weekly_refresh.ps1
# Optional: -Day Monday -Time "06:00" -TaskName "Windsor Housing weekly refresh"
#
# Remove it again with:
#     Unregister-ScheduledTask -TaskName "Windsor Housing weekly refresh" -Confirm:$false
#
# The task runs only while the user is logged on (no password is stored).
# Docker Desktop must be running at that time for the database load steps.
# Each run writes logs\scheduled_refresh_<time>.log; failures are added to
# logs\refresh_alerts.log and sent to ALERT_WEBHOOK_URL if it is set in .env.
# On a Linux server use the cron line in etl/README.md instead.

param(
    [string]$Day = "Monday",
    [string]$Time = "06:00",
    [string]$TaskName = "Windsor Housing weekly refresh"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Script = Join-Path $ProjectRoot "etl\scheduled_refresh.py"

if (-not (Test-Path $Python)) { throw "Python virtual environment not found at $Python" }
if (-not (Test-Path $Script)) { throw "Scheduled refresh script not found at $Script" }

$action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`"" -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Downloads the latest StatCan data, runs the schema guard, then refreshes the Windsor housing warehouse." `
    -Force | Out-Null

Write-Host "Registered '$TaskName': every $Day at $Time."
Write-Host "Run it now with: Start-ScheduledTask -TaskName '$TaskName'"
