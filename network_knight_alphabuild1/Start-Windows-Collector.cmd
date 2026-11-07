@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0backend\collector\start-collector.ps1"
pause
