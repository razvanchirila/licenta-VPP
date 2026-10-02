@echo off
REM Toate testele. Cele cu baza de date (API) au nevoie de containerul db: daca Docker merge, il pornesc;
REM altfel ruleaza doar testele nucleului de simulare, iar cele cu baza de date apar ca sarite (skipped).
setlocal
cd /d "%~dp0.."
docker info >nul 2>&1 || goto no_docker
echo Pornesc baza de date ...
docker compose up -d --wait db || echo Containerul db nu a pornit: testele cu baza de date vor fi sarite.
goto tests

:no_docker
echo Docker nu ruleaza: testele cu baza de date vor fi sarite.

:tests
cd backend
..\.venv\Scripts\python.exe -m pytest %*
