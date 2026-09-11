@echo off
REM Compara strategiile de control pe o saptamana de vara si una de iarna
cd /d "%~dp0..\backend"
..\.venv\Scripts\python.exe -m vpp_core.experiments
