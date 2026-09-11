# licenta-VPP

Simulator pentru o centrală electrică virtuală (VPP) într-o comunitate de 10 case cu panouri fotovoltaice și baterii. Proiect de licență, pornit de la aplicația făcută pentru concursul E.ON.

## Structura

```
backend/     simulare + API (Python, FastAPI)
dashboard/   panou web pentru operator
mobile/      aplicația pentru utilizatori (Flutter)
scripts/     scripturi de pornire pentru Windows
```

Nucleul de simulare e în `backend/vpp_core` și poate fi rulat separat, fără bază de date.

## Instalare

Ai nevoie de Python 3.11, MySQL și Flutter.

```
scripts\install.bat
copy backend\.env.example backend\.env
```

În `backend\.env` completezi parola de MySQL și `JWT_SECRET_KEY`.

## Rulare

```
scripts\start_all.bat
scripts\start_mobile.bat --dart-define=WEATHER_API_KEY=<cheie>
```

Backend-ul pornește pe `localhost:8000` (dashboard-ul e pe aceeași adresă), iar API-ul pentru aplicația mobilă pe `localhost:8001`.

## Teste

```
scripts\run_tests.bat
scripts\run_experiments.bat
```

Al doilea script compară strategiile de control pe o săptămână de vară și una de iarnă.
