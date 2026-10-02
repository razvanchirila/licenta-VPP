@echo off
REM Backend (API si simulare) pe http://localhost:8000 din .venv, pentru lucru pe cod.
REM Baza de date e tot cea din containerul db. Containerul api nu trebuie sa ruleze (ocupa portul 8000).
REM   start_backend.bat --dev   reincarcare automata la modificari
cd /d "%~dp0.."
docker compose up -d --wait db || (echo Nu pot porni baza de date. Docker Desktop e pornit? & pause & exit /b 1)
if not exist backend\.env copy backend\.env.example backend\.env >nul
cd backend
..\.venv\Scripts\python.exe main.py %*
