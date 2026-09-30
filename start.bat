@echo off
REM Porneste tot proiectul: instaleaza ce lipseste, creeaza conturile demo,
REM porneste backend-ul (API + dashboard) si aplicatia Flutter, apoi deschide browserul.
REM   start.bat              baza de date noua la fiecare pornire
REM   start.bat --keep-db    pastreaza baza de date existenta
REM   start.bat --no-mobile  fara aplicatia Flutter
setlocal
cd /d "%~dp0"
title VPP - pornire

set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto deps

echo [1/2] Caut Python 3.11 ...
set "BASE="
py -3.11 -c "import sys" >nul 2>&1 && set "BASE=py -3.11"
if not defined BASE py -3.12 -c "import sys" >nul 2>&1 && set "BASE=py -3.12"
if not defined BASE python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>&1 && set "BASE=python"
if not defined BASE (
    echo Python 3.11 nu este instalat. Il instalez cu winget ...
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "BASE="%LOCALAPPDATA%\Programs\Python\Python311\python.exe""
)
if not defined BASE (
    echo Nu am gasit Python 3.11. Instaleaza-l de pe https://www.python.org/downloads/ si ruleaza din nou.
    pause
    exit /b 1
)
echo Creez mediul Python in .venv ...
%BASE% -m venv .venv || (echo Nu am putut crea .venv & pause & exit /b 1)

:deps
fc /b backend\requirements.txt .venv\requirements.installed >nul 2>&1
if errorlevel 1 (
    echo [2/2] Instalez pachetele Python ...
    "%PY%" -m pip install --disable-pip-version-check -q --upgrade pip
    "%PY%" -m pip install --disable-pip-version-check -q -r backend\requirements.txt || (echo Instalarea a esuat & pause & exit /b 1)
    copy /y backend\requirements.txt .venv\requirements.installed >nul
)

"%PY%" scripts\launch.py %*
if errorlevel 1 pause
endlocal
