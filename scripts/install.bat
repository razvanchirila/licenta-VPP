@echo off
REM Creeaza mediul Python (.venv) si instaleaza dependintele backend-ului
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
    echo Creez .venv ...
    py -3.11 -m venv .venv || python -m venv .venv
)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
