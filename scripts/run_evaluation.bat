@echo off
REM Evaluarea completa: 4 anotimpuri x 5 seed-uri x 6 strategii, rezultate in results\
REM Optional: run_evaluation.bat --seeds 3 --days 7
cd /d "%~dp0..\backend"
..\.venv\Scripts\python.exe -m vpp_core.evaluation %*
