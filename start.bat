@echo off
REM Porneste proiectul in Docker: baza de date (db), backend-ul (api) si aplicatia web (web), adica
REM aplicatia Flutter pentru utilizatori si panoul operatorului la /admin.
REM   start.bat           porneste; datele raman de la o pornire la alta
REM   start.bat --reset   sterge baza de date si porneste de la zero
REM Ctrl+C in fereastra opreste containerele.
setlocal
cd /d "%~dp0"
title VPP

set "RESET="
if exist .env for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
:args
if "%~1"=="" goto check_docker
if /i "%~1"=="--reset" (
    set "RESET=1"
    shift
    goto args
)
echo Argument necunoscut: %1
echo Folosire: start.bat [--reset]
goto fail

:check_docker
where docker >nul 2>&1 && goto check_daemon
if exist "%ProgramFiles%\Docker\Docker\resources\bin\docker.exe" (
    set "PATH=%ProgramFiles%\Docker\Docker\resources\bin;%PATH%"
    goto check_daemon
)
echo Docker nu este instalat. Se instaleaza o singura data, din PowerShell sau cmd:
echo     winget install -e --id Docker.DockerDesktop
echo sau de pe https://www.docker.com/products/docker-desktop/
echo Dupa instalare reporneste calculatorul, deschide o data Docker Desktop si ruleaza din nou start.bat.
goto fail

:check_daemon
docker info >nul 2>&1 && goto docker_ok
set "DOCKER_DESKTOP=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not exist "%DOCKER_DESKTOP%" (
    echo Docker nu raspunde si nu gasesc Docker Desktop. Porneste-l de mana si ruleaza din nou start.bat.
    goto fail
)
echo Pornesc Docker Desktop. Daca apare o fereastra cu termeni de acceptat, accepta-i acolo ...
start "" "%DOCKER_DESKTOP%"
set /a N=0
:wait_daemon
call :sleep 5
docker info >nul 2>&1 && goto docker_ok
set /a N+=1
if %N% lss 24 goto wait_daemon
echo Docker Desktop nu a pornit in 2 minute. Deschide-l, asteapta "Engine running" si ruleaza din nou start.bat.
goto fail

:docker_ok
REM Windows poate rezerva porturi pentru Hyper-V/WSL; se alege primul port care chiar se poate deschide
if defined RESET (
    echo Sterg containerele si baza de date ...
    docker compose down -v
) else (
    docker compose down >nul 2>&1
)
call :free_port API_PORT "%API_PORT% 18000 18100 28000 38000 45000"
call :free_port WEB_PORT "%WEB_PORT% 13000 13100 23000 33000 45100"
call :free_port POSTGRES_PORT "%POSTGRES_PORT% 15432 15532 25432 35432 45200"
if not defined API_PORT goto no_port
if not defined WEB_PORT goto no_port
if not defined POSTGRES_PORT goto no_port
echo Porturi folosite: backend %API_PORT%, aplicatie %WEB_PORT%, baza de date %POSTGRES_PORT%
echo.
echo Construiesc si pornesc containerele. Prima data dureaza cateva minute ...
docker compose up --build -d
docker compose ps --status running --services | findstr /x "api" >nul
if errorlevel 1 (
    echo.
    echo Pornirea a esuat. Daca mai sus scrie "ports are not available", portul %API_PORT% sau %WEB_PORT%
    echo e rezervat de Windows. Pune alte porturi intr-un fisier .env langa start.bat, de exemplu:
    echo     API_PORT=8600
    echo     WEB_PORT=3600
    echo Ultimele linii din jurnalul backend-ului:
    docker compose logs --tail 40 api
    goto fail
)

echo Astept backend-ul ...
call :wait_url http://localhost:%API_PORT%/health 60
if errorlevel 1 (
    echo Backend-ul nu raspunde dupa 3 minute. Ultimele linii din jurnal:
    docker compose logs --tail 40 api
    goto fail
)
echo Astept aplicatia web ...
call :wait_url http://localhost:%WEB_PORT%/admin/ 30
if errorlevel 1 (
    echo Aplicatia web nu raspunde. Ultimele linii din jurnal:
    docker compose logs --tail 40 web
    goto fail
)

call :lan_ip

echo.
echo ================================================================
echo  Gata. Proiectul ruleaza in Docker.
echo    Aplicatia            http://localhost:%WEB_PORT%          user1 / 123, pana la user10
echo    Panoul operatorului  http://localhost:%WEB_PORT%/admin    admin / 123
echo    Documentatie API     http://localhost:%API_PORT%/docs
if defined LAN_IP (
    echo    Pe telefon           http://%LAN_IP%:%WEB_PORT%   telefonul in aceeasi retea Wi-Fi
)
echo  Mai jos e jurnalul backend-ului. Ctrl+C opreste containerele;
echo  datele raman pentru data viitoare, start.bat --reset le sterge.
echo ================================================================
echo.
start "" http://localhost:%WEB_PORT%
start "" http://localhost:%WEB_PORT%/admin

REM "up" atasat opreste singur containerele la Ctrl+C; "stop" acopera cazul in care
REM la intrebarea "Terminate batch job" se raspunde N
set "COMPOSE_MENU=false"
docker compose up --attach api --no-build --no-recreate
docker compose stop
echo.
echo Containerele sunt oprite. Pornesti din nou cu start.bat.
if /i "%comspec% /c %~0 " equ "%cmdcmdline:"=%" pause
exit /b 0

:fail
echo.
pause
exit /b 1

:wait_url
set /a TRIES=%2
:wait_url_loop
curl.exe -s -f -o nul --max-time 2 %1 && exit /b 0
set /a TRIES-=1
if %TRIES% leq 0 exit /b 1
call :sleep 3
goto wait_url_loop

:sleep
ping -n %1 127.0.0.1 >nul
exit /b 0

:no_port
echo Nu am gasit niciun port liber pentru backend sau aplicatie. Pune porturi libere in .env, de exemplu API_PORT=45000 si WEB_PORT=45100.
goto fail

:free_port
set "%~1="
for /f %%p in ('powershell -NoProfile -Command "foreach ($p in ('%~2' -split ' ' -ne '')) { try { $l = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Any, [int]$p); $l.Start(); $l.Stop(); $p; break } catch {} }"') do set "%~1=%%p"
exit /b 0

REM adresa din reteaua locala: placa de retea care are gateway (Wi-Fi sau cablu), nu adaptoarele virtuale
:lan_ip
set "LAN_IP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$c = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1; if ($c) { @($c.IPv4Address)[0].IPAddress }"`) do set "LAN_IP=%%i"
exit /b 0
