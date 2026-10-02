# licenta-VPP

[![CI](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml/badge.svg)](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml)

Simulator pentru o centrală electrică virtuală (VPP) într-o comunitate de 10 case cu panouri fotovoltaice și baterii. Proiect de licență, pornit de la aplicația făcută pentru concursul E.ON.

```
backend/     simulare, optimizare (LP, MPC) și API (Python, FastAPI, PostgreSQL)
admin/       panoul operatorului (React, TypeScript, Vite)
mobile/      aplicația pentru utilizatori (Flutter)
web/         nginx care servește aplicația și panoul
deploy/      serverul de producție și staging
scripts/     scripturi pentru Windows
```

## Pornire

Ai nevoie doar de Docker Desktop. Dublu-click pe `start.bat`: pornește containerele și deschide browserul. Prima pornire durează câteva minute.

| Ce | Adresă | Cont |
|---|---|---|
| Aplicația | http://localhost:13000 | `user1` / `123` (până la `user10`) |
| Panoul operatorului | http://localhost:13000/admin | `admin` / `123` |
| Documentație API | http://localhost:18000/docs | |

Ctrl+C oprește containerele; datele rămân. `start.bat --reset` pornește cu o bază de date nouă. Dacă un port e ocupat, scriptul alege altul și afișează adresa. Tot el afișează și adresa pentru telefon, din aceeași rețea Wi-Fi.

## Online

- producție: https://vpp-licenta.switzerlandnorth.cloudapp.azure.com
- staging: https://staging.51.107.88.91.nip.io

Detaliile despre server, publicarea automată și pipeline sunt în [deploy/README.md](deploy/README.md).

## Dezvoltare

`scripts\install.bat` instalează mediul Python, iar `scripts\run_tests.bat` rulează testele backend-ului (pornește singur baza de date de test). Panoul se dezvoltă cu `npm run dev` din `admin/`, iar aplicația cu `scripts\start_mobile.bat`. Toate scripturile sunt descrise în [scripts/README.md](scripts/README.md).

Modificările se fac pe ramuri `feature/...`, cu pull request spre `develop`, care se publică pe staging, apoi din `develop` spre `main`, care se publică în producție. La fiecare pull request rulează automat testele părții modificate.

## Evaluare

`scripts\run_evaluation.bat` compară strategiile de control (reguli, baterie individuală, MPC, optim teoretic) pe patru anotimpuri. Cu `--real` folosește producția PV și prețurile PZU reale, iar consumul caselor vine din `backend/data/dispozitive.csv`. Sursele datelor sunt în [backend/data/README.md](backend/data/README.md).
