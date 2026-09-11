@echo off
REM API pentru utilizatori (login, /me/*), folosit de aplicatia mobila, pe http://localhost:8001
cd /d "%~dp0..\backend"
..\.venv\Scripts\python.exe -m uvicorn user_api.main:app --host 0.0.0.0 --port 8001 %*
