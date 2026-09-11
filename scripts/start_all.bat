@echo off
REM Porneste ambele servicii backend in ferestre separate
start "VPP backend :8000" cmd /k "%~dp0start_backend.bat"
timeout /t 3 /nobreak > nul
start "VPP user API :8001" cmd /k "%~dp0start_user_api.bat"
echo Backend:   http://localhost:8000  (dashboard + /docs)
echo User API:  http://localhost:8001/docs
