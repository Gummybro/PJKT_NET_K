@echo off
cd /d "%~dp0"
echo Use this only if FastAPI was started manually. The normal launcher already starts protection monitoring.
".venv\Scripts\python.exe" -m backend.protection_monitor
pause
