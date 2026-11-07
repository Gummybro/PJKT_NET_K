@echo off
cd /d "%~dp0..\.."
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File backend\collector\start-collector.ps1
pause
