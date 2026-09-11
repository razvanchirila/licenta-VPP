@echo off
REM Testele nucleului de simulare (vpp_core)
cd /d "%~dp0..\backend"
..\.venv\Scripts\python.exe -m pytest %*
