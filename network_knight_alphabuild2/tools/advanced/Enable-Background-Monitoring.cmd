@echo off
cd /d "%~dp0..\.."
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File background\install.ps1
pause
