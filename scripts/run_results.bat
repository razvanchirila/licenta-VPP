@echo off
REM Reface toate tabelele si graficele din results\ : sintetic, date reale cu preturi 2023 / 2025 / 2026,
REM sensibilitate, consum, comparatia pe ani. Dureaza cam o ora si foloseste toate nucleele.
REM Se ruleaza dupa ce se schimba backend\data\dispozitive.csv, gospodarii.csv sau modelul.
REM Optional numarul de procese in paralel: run_results.bat 12 (cu multe nuclee si memorie putina).
setlocal enabledelayedexpansion
cd /d "%~dp0..\backend"
set PY=..\.venv\Scripts\python.exe
set PROCESE=
if not "%~1"=="" set "PROCESE=--workers %~1"
set COMUN=--seeds 5 --days 7 --dt 0.25 %PROCESE%
set N=0
call :acum T0

set "PAS=experimente"
call :pas -m vpp_core.experiments || goto :esec
set "PAS=evaluare, sintetic"
call :pas -m vpp_core.evaluation %COMUN% || goto :esec
for %%a in (2023 2025 2026) do (
    set "PAS=evaluare, date reale %%a"
    call :pas -m vpp_core.evaluation --real --price-year %%a %COMUN% || goto :esec
)
set "PAS=pareto, sintetic"
call :pas -m vpp_core.pareto --seeds 3 --days 7 --dt 0.25 %PROCESE% || goto :esec
set "PAS=pareto, date reale 2025"
call :pas -m vpp_core.pareto --real --price-year 2025 --seeds 3 --days 7 --dt 0.25 %PROCESE% || goto :esec
set "PAS=factura pe casa, sintetic"
call :pas -m vpp_core.houses_report %COMUN% || goto :esec
for %%a in (2023 2025 2026) do (
    set "PAS=factura pe casa, date reale %%a"
    call :pas -m vpp_core.houses_report --real --price-year %%a %COMUN% || goto :esec
)
for %%s in (forecast deg p2p) do (
    set "PAS=sensibilitate %%s, sintetic"
    call :pas -m vpp_core.sensitivity --study %%s --seeds 3 --days 7 --dt 0.25 %PROCESE% || goto :esec
)
set "PAS=sensibilitate scale, sintetic, 2 zile"
call :pas -m vpp_core.sensitivity --study scale --seeds 3 --days 2 --dt 0.25 %PROCESE% || goto :esec
for %%s in (forecast deg p2p) do (
    set "PAS=sensibilitate %%s, date reale 2025"
    call :pas -m vpp_core.sensitivity --real --price-year 2025 --study %%s --seeds 3 --days 7 --dt 0.25 %PROCESE% || goto :esec
)
set "PAS=consum din dispozitive"
call :pas -m vpp_core.load_model || goto :esec
set "PAS=comparatie 2023 / 2025 / 2026"
call :pas -m vpp_core.compare_years || goto :esec

call :acum T1
set /a TOTAL=T1-T0
if !TOTAL! lss 0 set /a TOTAL+=86400
set /a MINUTE=TOTAL/60
echo.
echo Durate:
for /l %%i in (1,1,%N%) do echo   !DUR%%i! s   !NUME%%i!
echo Total: !TOTAL! s, adica !MINUTE! min
goto :sfarsit

:esec
echo.
echo EROARE la pasul "!PAS!"; rularea s-a oprit aici.
set ESEC=1

:sfarsit
if /i "%comspec% /c %~0 " equ "%cmdcmdline:"=%" pause
if defined ESEC exit /b 1
exit /b 0

:pas
set /a N+=1
echo.
echo === [!N!] !PAS! ===
call :acum S
%PY% %*
if errorlevel 1 exit /b 1
call :acum E
set /a D=E-S
if !D! lss 0 set /a D+=86400
set "NUME!N!=!PAS!"
set "DUR!N!=!D!"
exit /b 0

:acum
for /f "tokens=1-3 delims=:.," %%a in ("%TIME: =0%") do set /a %1=(1%%a-100)*3600+(1%%b-100)*60+(1%%c-100)
exit /b 0
