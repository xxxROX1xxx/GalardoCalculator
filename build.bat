@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] uv not found. Install it from https://docs.astral.sh/uv/ or use any Python 3.10+ with pip.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment with Python 3.13...
    uv venv .venv --python 3.13
    if errorlevel 1 exit /b 1
)

echo [2/4] Installing dependencies...
uv pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [3/4] Generating application icon...
".venv\Scripts\python.exe" tools\make_icon.py
if errorlevel 1 exit /b 1

echo [4/4] Building Galardo.exe...
".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm --clean --windowed --onefile ^
    --name Galardo ^
    --icon "%~dp0assets\galardo.ico" ^
    --add-data "%~dp0assets\galardo_bg.jpg;assets" ^
    --add-data "%~dp0assets\galardo.png;assets" ^
    --distpath dist ^
    --workpath build\work ^
    --specpath build ^
    main.py
if errorlevel 1 exit /b 1

echo.
echo Done! The program is here: dist\Galardo.exe
pause
