@echo off
rem Double-click to stop the TwinGuard AI demo (UI + AI service + GPU worker).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_twinguard.ps1" -Stop
echo.
pause
