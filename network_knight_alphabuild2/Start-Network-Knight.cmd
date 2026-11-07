@echo off
setlocal
cd /d "%~dp0"
title Network Knight - Setup and Monitoring
if exist ".venv\Scripts\python.exe" (
 ".venv\Scripts\python.exe" bootstrap.py %*
) else (
 where py >nul 2>&1
 if errorlevel 1 (
  echo Python is required. Install Python 3.11 or newer with the Windows py launcher.
  echo https://www.python.org/downloads/windows/
  pause
  exit /b 1
 )
 py -3 bootstrap.py %*
)
if errorlevel 1 (
 echo Network Knight did not start successfully. Read the error above.
 pause
 exit /b 1
)
endlocal
