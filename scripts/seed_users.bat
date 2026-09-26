@echo off
REM Creeaza conturile demo admin + user1..user10, parola 123 (sau cea data ca argument: seed_users.bat parola)
cd /d "%~dp0.."
.venv\Scripts\python.exe backend\scripts\seed.py demo %*
