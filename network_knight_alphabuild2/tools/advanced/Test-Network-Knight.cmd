@echo off
cd /d "%~dp0..\.."
".venv\Scripts\python.exe" -m unittest discover -s backend/tests -v
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" tools/verify_http.py
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" tools/verify_services.py
pause
