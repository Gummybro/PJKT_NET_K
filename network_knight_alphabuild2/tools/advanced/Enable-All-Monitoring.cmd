@echo off
cd /d "%~dp0..\.."
if not exist ".venv\Scripts\python.exe" (
 py -3 tools\manage_monitoring.py all on
) else (
 ".venv\Scripts\python.exe" tools\manage_monitoring.py all on
)
pause
