@echo off
REM Porneste backend-ul (API + dashboard, port 8000) si aplicatia Flutter in Chrome
start "VPP backend :8000" cmd /k "%~dp0start_backend.bat"
echo Backend:  http://localhost:8000  (dashboard, /docs)
call "%~dp0start_mobile.bat" %*
