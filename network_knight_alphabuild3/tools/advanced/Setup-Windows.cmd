@echo off
cd /d "%~dp0..\.."
call Start-Network-Knight.cmd --setup-only
pause
