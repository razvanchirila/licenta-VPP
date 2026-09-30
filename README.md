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

## Pornire rapidă

Dublu-click pe `start.bat`. La prima rulare instalează ce lipsește (mediul Python, pachetele și, dacă vrei, Flutter), compilează aplicația web, creează conturile demo și pornește totul. Apoi se deschid în browser:

| Ce | Adresă | Cont |
|---|---|---|
| Dashboard operator | http://127.0.0.1:8000 | `admin` / `123` |
| Aplicația Flutter | http://127.0.0.1:3000 | `user1` / `123` (până la `user10`) |
| Documentație API | http://127.0.0.1:8000/docs | |

Se oprește cu Ctrl+C în fereastra deschisă. La fiecare pornire baza de date e creată din nou; `start.bat --keep-db` o păstrează, iar `start.bat --no-mobile` pornește doar backend-ul și dashboard-ul.

## Instalare manuală

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

`scripts\run_evaluation.bat` rulează toate strategiile (reguli, baterie locală, MPC, optim LP) pe patru anotimpuri și mai multe seed-uri și scrie tabelele și graficele în `results/`. Cu `--real` folosește producția PV reală din 2023 și prețurile PZU din 2023, 2025 sau 2026 (`--price-year`), iar consumul fiecărei case vine din `backend/data/dispozitive.csv`. Sursele sunt descrise în `backend/data/README.md`. `scripts\run_results.bat` regenerează toate rezultatele cu o singură comandă.
