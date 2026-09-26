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

Ai nevoie de Python 3.11 și Flutter. Baza de date e SQLite (un fișier în `backend/`), nu trebuie instalat nimic.

```
scripts\install.bat
copy backend\.env.example backend\.env
```

Valorile din `.env.example` sunt suficiente pentru rulare locală. `scripts\seed_users.bat` creează conturile demo: `admin` și `user1`..`user10` (câte unul pentru fiecare casă), toate cu parola `123`.

## Rulare

```
scripts\start_backend.bat
scripts\start_mobile.bat --dart-define=WEATHER_API_KEY=<cheie>
```

Backend-ul pornește pe `localhost:8000`: dashboard-ul la `/` (`admin` / `123`), API-ul la `/api`, documentația la `/docs`. În aplicația Flutter intri cu `user1` / `123`. Casele sunt create automat la prima pornire, iar simularea avansează cu un pas de 15 minute la fiecare 2 secunde.

## Teste

```
scripts\run_tests.bat
scripts\run_experiments.bat
```

Al doilea script compară strategiile de control pe o săptămână de vară și una de iarnă.

## Evaluare

`scripts\run_evaluation.bat` rulează toate strategiile (reguli, baterie locală, MPC, optim LP) pe patru anotimpuri și mai multe seed-uri și scrie tabelele și graficele în `results/`. Cu `--real` folosește prețuri PZU, producție PV și profiluri de consum reale din 2023 (`backend/data/`, sursele sunt descrise acolo).
