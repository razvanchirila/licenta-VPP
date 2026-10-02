# licenta-VPP

Simulator pentru o centrală electrică virtuală (VPP) într-o comunitate de 10 case cu panouri fotovoltaice și baterii. Proiect de licență, pornit de la aplicația făcută pentru concursul E.ON.

## Structura

```
backend/     simulare + API (Python, FastAPI)
admin/       panoul operatorului (React, TypeScript, Vite)
mobile/      aplicația pentru utilizatori (Flutter)
web/         imaginea Docker care servește aplicația și panoul (nginx)
scripts/     scripturi de pornire pentru Windows
```

Nucleul de simulare e în `backend/vpp_core` și poate fi rulat separat, fără bază de date.

## Pornire rapidă

Proiectul rulează în Docker, așa că pe calculator trebuie instalat doar Docker Desktop, o singură dată:

```
winget install -e --id Docker.DockerDesktop
```

sau de pe https://www.docker.com/products/docker-desktop/. După instalare calculatorul trebuie repornit, iar Docker Desktop deschis o dată, ca să accepți termenii.

Apoi dublu-click pe `start.bat`. Scriptul pornește Docker Desktop dacă nu rulează, construiește și pornește containerele, așteaptă să răspundă backend-ul și aplicația, apoi le deschide în browser. Prima pornire durează câteva minute (imaginea Flutter e mare); următoarele durează câteva secunde.

| Ce | Adresă | Cont |
|---|---|---|
| Aplicația (Flutter) | http://localhost:13000 | `user1` / `123` (până la `user10`) |
| Panoul operatorului | http://localhost:13000/admin | `admin` / `123` |
| Documentație API | http://localhost:18000/docs | |

| Container | Ce rulează | Port |
|---|---|---|
| `db` | PostgreSQL 16, datele într-un volum Docker | 15432 |
| `api` | backend-ul (simulare + API); la pornire creează conturile demo dacă lipsesc | 18000 |
| `web` | nginx cu aplicația Flutter la `/` și panoul operatorului la `/admin/`; cererile `/api/` (inclusiv WebSocket) merg la `api` | 13000 |

Imaginea `web` se construiește din `web/Dockerfile` în trei etape: Flutter compilează aplicația din `mobile/`, Node compilează panoul din `admin/`, iar nginx primește ambele rezultate. Cele două foldere ajung în build ca contexte separate (`additional_contexts` în `docker-compose.yml`).

`start.bat` afișează și adresa pentru telefon, de forma `http://192.168.x.x:13000`. Telefonul trebuie să fie în aceeași rețea Wi-Fi cu calculatorul; aplicația merge la fel ca pe calculator, pentru că și API-ul trece prin același nginx.

În fereastra lui `start.bat` apare apoi jurnalul backend-ului. Ctrl+C oprește containerele, iar datele rămân pentru pornirea următoare. `start.bat --reset` șterge baza de date înainte de pornire, ca simularea să înceapă de la zero, cu conturile demo create din nou.

Porturile 18000 și 13000 sunt alese ca să nu se ciocnească cu alte programe de dezvoltare. Dacă totuși unul e ocupat sau rezervat de Windows, `start.bat` alege singur următorul port liber și afișează adresa corectă. Porturile se pot fixa și de mână, într-un fișier `.env` lângă `start.bat`: `API_PORT=...` și `WEB_PORT=...`.

Setările (cheia JWT, controllerul, anul prețurilor) au valori implicite în `docker-compose.yml` și se pot schimba prin variabile de mediu cu același nume ca în `backend/.env.example`.

## Instalare manuală / dezvoltare

Pentru teste, pentru scripturile de evaluare și pentru a rula backend-ul direct din cod e nevoie de Python 3.11:

```
scripts\install.bat
```

Scriptul creează mediul Python (`.venv`) și instalează pachetele. Baza de date este întotdeauna PostgreSQL din containerul `db`, și când backend-ul rulează în afara Docker-ului:

```
scripts\start_backend.bat
scripts\start_mobile.bat --dart-define=WEATHER_API_KEY=<cheie>
```

`start_backend.bat` pornește întâi containerul `db` (`docker compose up -d db`), creează `backend\.env` din `.env.example` dacă lipsește și pornește backend-ul pe `localhost:8000`, cu aceleași adrese și conturi ca mai sus. Containerul `api` se poate opri înainte (`docker compose stop api web`), ca simularea să nu ruleze de două ori pe aceeași bază de date. `start_mobile.bat` rulează aplicația Flutter din cod, în Chrome, și are nevoie de Flutter instalat. `scripts\seed_users.bat` creează conturile demo: `admin` și `user1`..`user10` (câte unul pentru fiecare casă), toate cu parola `123`.

### Panoul operatorului

Panoul din `admin/` e o aplicație React 19 cu TypeScript, construită cu Vite. Pentru lucru pe el e nevoie de Node.js 20 sau mai nou:

```
cd admin
npm install
npm run dev
```

Serverul de dezvoltare pornește pe http://localhost:5173/admin/ și trimite cererile `/api` (și WebSocket-ul) la backend-ul din Docker, pe portul 18000. Pentru backend-ul pornit cu `scripts\start_backend.bat` se setează înainte `API_TARGET=http://localhost:8000`. Alte comenzi: `npm run lint`, `npm run typecheck`, `npm test` (Vitest), `npm run build` (rezultatul în `admin/dist`).

Structura: `src/api` (clientul HTTP cu token-ul de sesiune, hook-ul pentru WebSocket cu reconectare), `src/types` (tipurile răspunsurilor API), `src/hooks` (autentificare, starea live a simulării), `src/pages` (Prezentare generală, Case, Simulare, Login), `src/components`, `src/lib` (formatare și calcule pentru grafice). Datele de pe server sunt citite cu TanStack Query, graficele sunt făcute cu Recharts, iar harta comunității e un SVG desenat direct.

## Teste

```
scripts\run_tests.bat
scripts\run_experiments.bat
```

`run_tests.bat` pornește containerul `db` dacă Docker rulează. Testele API folosesc o bază separată, `vpp_test`, creată automat la prima rulare; baza aplicației (`vpp`) nu este atinsă. Fără Docker rulează doar testele nucleului de simulare, iar cele cu baza de date apar ca sărite (`skipped`).

Al doilea script compară strategiile de control pe o săptămână de vară și una de iarnă.

## Evaluare

`scripts\run_evaluation.bat` rulează toate strategiile (reguli, baterie locală, MPC, optim LP) pe patru anotimpuri și mai multe seed-uri și scrie tabelele și graficele în `results/`. Cu `--real` folosește producția PV reală din 2023 și prețurile PZU din 2023, 2025 sau 2026 (`--price-year`), iar consumul fiecărei case vine din `backend/data/dispozitive.csv`. Sursele sunt descrise în `backend/data/README.md`. `scripts\run_results.bat` regenerează toate rezultatele cu o singură comandă.
