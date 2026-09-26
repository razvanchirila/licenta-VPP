@echo off
REM Backend (API, simulare, dashboard) pe http://localhost:8000
REM   start_backend.bat --dev   reincarcare automata la modificari
cd /d "%~dp0..\backend"
..\.venv\Scripts\python.exe main.py %*
