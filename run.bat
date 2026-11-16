@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo The environment is missing. Run build.bat first.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" main.py
