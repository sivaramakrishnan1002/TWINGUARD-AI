@echo off
rem TwinGuard AI service with live forecast mode and the persistent GPU worker (see start_live.ps1).
rem   start_live.bat              foreground (Ctrl+C stops)
rem   start_live.bat -Background  detached, survives closing this window
rem   start_live.bat -Stop        stop it
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_live.ps1" %*
