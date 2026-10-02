@echo off
REM Creeaza conturile demo admin + user1..user10, parola 123 (sau cea data ca argument: seed_users.bat parola)
cd /d "%~dp0.."
docker compose up -d --wait db || (echo Nu pot porni baza de date. Docker Desktop e pornit? & pause & exit /b 1)
.venv\Scripts\python.exe backend\scripts\seed.py demo %*
