@echo off
cd /d "%~dp0..\.."
".venv\Scripts\python.exe" -m backend.protection_monitor
pause
