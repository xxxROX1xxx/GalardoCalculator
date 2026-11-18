@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"

if exist "%PY%" goto deps

where uv >nul 2>nul
if not errorlevel 1 (
    echo [1/4] Creating virtual environment with uv...
    uv venv .venv --python 3.13
    if errorlevel 1 exit /b 1
    goto deps
)

where py >nul 2>nul
if not errorlevel 1 (
    echo [1/4] Creating virtual environment with Python launcher...
    py -3 -m venv .venv
    if errorlevel 1 exit /b 1
    goto deps
)

echo [ERROR] Python not found. Install Python 3.10+ or uv from https://docs.astral.sh/uv/
pause
exit /b 1

:deps
echo [2/4] Installing dependencies...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [3/4] Generating application icon...
"%PY%" tools\make_icon.py
if errorlevel 1 exit /b 1

echo [4/4] Building Galardo.exe...
"%PY%" -m PyInstaller ^
    --noconfirm --clean --windowed --onefile ^
    --name Galardo ^
    --icon "%~dp0assets\galardo.ico" ^
    --add-data "%~dp0assets\fonts;assets\fonts" ^
    --add-data "%~dp0assets\galardo.png;assets" ^
    --distpath dist ^
    --workpath build\work ^
    --specpath build ^
    main.py
if errorlevel 1 exit /b 1

echo.
echo Done! The program is here: dist\Galardo.exe
pause
