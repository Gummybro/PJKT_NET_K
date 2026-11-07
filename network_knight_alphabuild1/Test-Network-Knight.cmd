@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m unittest discover -s backend/tests -v
if errorlevel 1 goto failed
".venv\Scripts\python.exe" tools/verify_http.py
if errorlevel 1 goto failed
echo All Python tests passed.
pause
exit /b 0
:failed
echo Tests failed. Review the output above.
pause
exit /b 1
