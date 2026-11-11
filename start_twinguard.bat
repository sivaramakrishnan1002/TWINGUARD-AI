@echo off
rem Double-click to start the whole TwinGuard AI demo (AI service + GPU + live forecasts + UI + browser).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_twinguard.ps1" %*
echo.
pause
