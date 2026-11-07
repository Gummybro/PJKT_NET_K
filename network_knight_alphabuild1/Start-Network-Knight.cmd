@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run Setup-Windows.cmd first.
 pause
 exit /b 1
)
echo Open http://127.0.0.1:8787 in your browser. Ctrl+C stops the server.
".venv\Scripts\python.exe" run.py
pause
