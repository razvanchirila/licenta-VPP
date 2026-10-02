# licenta-VPP

[![CI](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml/badge.svg)](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml)

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

## Cum lucrăm

Ramurile:

- `feature/<ceva>`: orice modificare începe pe o ramură nouă din `develop`;
- `develop`: ce s-a terminat și urmează să ajungă în producție; la fiecare push se publică pe serverul de staging;
- `main`: ce rulează în producție; se schimbă doar prin pull request din `develop`.

Pe `main` și `develop` nu se face push direct: se deschide un pull request (`feature/*` → `develop`, apoi `develop` → `main`), se așteaptă ca verificarea `ci-ok` să fie verde și abia apoi se face merge. Pull request-ul spre `main` rulează în plus build-ul imaginilor Docker, deci este ultima verificare înainte de producție.

Ce rulează și când (duratele sunt aproximative, cu cache-ul cald):

| Eveniment | Job-uri rapide (backend, flutter, admin) | Imagini Docker | Publicare imagini | Deploy |
|---|---|---|---|---|
| push pe `feature/*` | doar zona schimbată, 2-6 min | nu | nu | nu |
| pull request spre `develop` | doar zona schimbată | nu | nu | nu |
| push pe `develop` (merge) | doar zona schimbată | da, ~10 min | `develop` + sha | staging |
| pull request spre `main` | doar zona schimbată | da | nu | nu |
| push pe `main` (merge) | doar zona schimbată | da | `latest` + sha | producție |
| săptămânal (luni dimineața) și manual | toate | da | nu | nu |

Zonele sunt `backend/` (backend), `mobile/` (flutter) și `admin/` (admin); `web/`, `deploy/` și fișierele Docker contează doar pentru build-ul Docker. O modificare doar în fișiere `.md` nu pornește nimic greu: rulează doar job-ul care verifică ce s-a schimbat și `ci-ok`, în câteva secunde. Job-urile sărite apar ca reușite, așa că nu blochează pull request-ul.

Pentru un commit care nu are nevoie de CI deloc (de exemplu o corectură în README pe o ramură de lucru), mesajul commit-ului poate conține `[skip ci]`, iar GitHub nu mai pornește nicio rulare pentru acel push. Nu se folosește pe ultimul commit dintr-un pull request: fără rulare nu apare nici `ci-ok`, iar pull request-ul rămâne blocat.

Adresele:

- producție: https://vpp-licenta.switzerlandnorth.cloudapp.azure.com (`/admin`, `/docs`)
- staging: https://staging.51.107.88.91.nip.io (`/admin`, `/docs`), conturile demo cu parola `123`

## Integrare continuă

GitHub Actions rulează `.github/workflows/ci.yml`. Primul job, `changes`, află ce zone s-au schimbat (cu `dorny/paths-filter`: la push față de commit-ul dinaintea push-ului, la pull request față de ramura țintă). Urmează job-urile rapide, fiecare doar dacă zona lui s-a schimbat: backend-ul (ruff și pytest pe un PostgreSQL 16 pornit ca serviciu), aplicația Flutter (analyze, verificarea formatării, teste, build web) și panoul operatorului (lint, typecheck, teste, build). Job-ul `docker` construiește imaginile `api` și `web`, doar în cazurile din tabelul de mai sus. Ultimul job, `ci-ok`, pică dacă oricare dintre celelalte a picat sau a fost anulat; el este singura verificare cerută la pull request-uri.

Rulările mai vechi pe aceeași ramură de lucru sau pe același pull request sunt oprite când apare un push nou. Pe `main` și `develop` o rulare începută nu se oprește, ca să nu se întrerupă un deploy.

## Producție

Aplicația rulează public la https://vpp-licenta.switzerlandnorth.cloudapp.azure.com, cu panoul operatorului la `/admin` și documentația API la `/docs`. Conturile demo (`admin` și `user1`..`user10`) sunt create și aici, dar cu o parolă separată, cunoscută doar de autor, luată din `DEMO_PASSWORD` din `/opt/vpp/.env`. Fără această variabilă parola rămâne `123`, ca local și pe staging. La fiecare pornire a containerului `api`, conturile demo existente primesc din nou parola din `DEMO_PASSWORD`, deci o parolă schimbată din panou pentru aceste conturi se pierde la restart; celelalte conturi nu sunt atinse. Comanda care schimbă parola este în `deploy/README.md`.

Serverul este o mașină virtuală Azure din regiunea Switzerland North (Ubuntu 24.04, Standard_B2ats_v2: 2 vCPU, 1 GB RAM, plus 2 GB swap), cu IP public static. Adresa este eticheta DNS gratuită pe care Azure o oferă pentru IP-urile publice.

```
internet :80, :443
   |
 caddy   HTTPS (Let's Encrypt), HTTP -> HTTPS
   |-- vpp-licenta.switzerlandnorth.cloudapp.azure.com     stiva vpp, /opt/vpp
   |     |-- /docs, /openapi.json, /redoc, /health --> api:8000
   |     '-- restul: /, /admin, /api/* (și WebSocket) --> web:80 (nginx) -- /api/* --> api:8000 --> db:5432
   '-- staging.51.107.88.91.nip.io                         stiva vpp-staging, /opt/vpp-staging
         '-- aceeași împărțire, spre api, web și db proprii, prin rețeaua Docker vpp-edge
```

Fișierele sunt în `deploy/` și stau pe server în `/opt/vpp`. Doar containerul `caddy` are porturi deschise spre exterior; `db`, `api` și `web` se văd numai în rețeaua Docker a stivei. Caddy obține și reînnoiește singur certificatul. Fiecare container are o limită de memorie (db 256 MB, api 384 MB, web și caddy câte 64 MB) și repornește singur după o eroare sau după un restart al serverului. Cu producția singură, după 10 minute de simulare, cele patru containere foloseau împreună aproximativ 170 MB (api 75, db 53, caddy 34, web 4), iar sistemul întreg aproape 590 MB din 892. Cu staging pornit alături, cele șapte containere folosesc în jur de 250 MB (fiecare api 75, caddy 43, db 36 și 17, web sub 5), la sistem rămân disponibili 235-255 MB, iar în swap stau aproape 175 MB de pagini rar folosite, fără schimburi active între RAM și swap. Simularea pornește cu controllerul `reguli`. MPC se poate alege din panou: pe această mașină adaugă cam 0,1 s la fiecare pas (2,15 s pe pas față de 2,08 s, la un pas configurat de 2 s), cu api la aproximativ 105 MB.

`deploy/setup-server.sh` pregătește serverul: fișier swap, Docker din depozitul oficial, actualizări automate de securitate (`unattended-upgrades`), fail2ban pentru SSH, SSH doar cu cheie și fără root, jurnale limitate (journald 200 MB, la containere 3 fișiere de câte 10 MB), fus orar București. Pașii pentru o instalare de la zero sunt în `deploy/README.md`.

### Staging

Pe aceeași mașină rulează o a doua stivă, `vpp-staging`, din `deploy/docker-compose.staging.yml`, în `/opt/vpp-staging`. Are bază de date proprie (alt volum), alt `.env`, cu altă parolă PostgreSQL și altă cheie JWT, deci un token de pe staging nu este valid în producție. Primește imaginile cu eticheta `develop` la fiecare push pe ramura `develop`, înainte ca modificările să ajungă în `main`. Conturile demo au parola `123`.

Porturile 80 și 443 pot fi deschise de un singur container, așa că staging nu are Caddy propriu: același Caddy din producție servește ambele adrese. Containerele `web` și `api` din staging intră și în rețeaua Docker comună `vpp-edge`, cu aliasurile `staging-web` și `staging-api`; în rețeaua producției, `web` și `api` au aliasurile `prod-web` și `prod-api`. Caddyfile-ul folosește doar aceste nume, pentru că `web` și `api` există în ambele stive.

Adresa de staging este un nume `nip.io`: serviciul răspunde la orice nume de forma `<ceva>.<ip>.nip.io` cu IP-ul din nume, deci nu trebuie cumpărat un domeniu, iar Caddy obține pentru el un certificat Let's Encrypt ca pentru orice alt domeniu. Am încercat întâi `sslip.io`, care face același lucru, dar DNS-ul unor furnizori de internet din România îl redirecționează spre altă adresă.

Ca ambele stive să încapă în 1 GB de RAM, staging are limite mai mici (db 128 MB cu `shared_buffers` 16 MB, api 256 MB, web 32 MB), verificările de sănătate la 30 s în loc de 15 s și pasul simulării la 5 s în loc de 2 s. Răspunsurile staging au antetul `X-Robots-Tag: noindex`, ca adresa să nu apară în motoarele de căutare.

### Firewall

Porturile sunt filtrate de grupul de securitate al rețelei din Azure (`vpp-serverNSG`), care lasă să treacă doar 22, 80 și 443. Pe server nu este pornit `ufw`: Docker scrie direct reguli iptables pentru porturile publicate, iar acestea trec pe lângă regulile ufw, așa că ufw ar da impresia unei protecții pe care nu o oferă. Filtrul din Azure acționează înainte ca pachetele să ajungă la mașină și este un singur loc de configurat.

### Secrete

Parola bazei de date și cheia de semnare JWT sunt generate pe server cu `openssl rand`, separat pentru fiecare mediu, în `/opt/vpp/.env` și `/opt/vpp-staging/.env` (citibile doar de utilizatorul `vpp`). Tot acolo stă parola conturilor demo din producție. Nu există în git și nici pe alt calculator. O cheie JWT nouă deconectează toți utilizatorii. Parola PostgreSQL se fixează la prima pornire a volumului; dacă se schimbă în `.env`, trebuie schimbată și în baza de date (`ALTER USER vpp PASSWORD ...`).

### Deploy automat

După ce testele trec la un push pe `develop` sau pe `main`, job-ul `publish` construiește imaginile `api` și `web` și le publică în GitHub Container Registry (`ghcr.io/razvanchirila/licenta-vpp-api` și `-web`), cu eticheta `develop` sau `latest` și cu sha-ul commit-ului. Job-ul `deploy` se conectează apoi prin SSH la server cu o cheie dedicată, care pe server poate rula doar `/opt/vpp/deploy.sh`, și cere `deploy staging <sha>` pentru `develop` sau `deploy prod <sha>` pentru `main`; `deploy.sh` acceptă doar aceste două medii. Token-ul temporar al job-ului ajunge prin stdin la `docker login`, într-un director de configurare temporar care se șterge imediat după pull, iar stiva mediului respectiv repornește cu `TAG=<sha>`. Pe server nu rămâne niciun token. La final job-ul verifică din afară `/health` și `/api/auth/me` pe adresa mediului; dacă verificarea eșuează, doar acel mediu revine la imaginile care rulau înainte. Două deploy-uri nu rulează niciodată în același timp pe server, iar în GitHub rulările apar la Environments, ca `staging` și `production`.

Deploy-ul pornește doar după ce în repository sunt setate secretele:

| Secret | Valoare |
|---|---|
| `DEPLOY_HOST` | `vpp-licenta.switzerlandnorth.cloudapp.azure.com` |
| `DEPLOY_USER` | `vpp` |
| `DEPLOY_SSH_KEY` | cheia privată de deploy (ed25519, fără parolă) |
| `DEPLOY_KNOWN_HOSTS` | linia cu cheia publică a serverului, ca să nu fie acceptat alt server |
| `WEATHER_API_KEY` | opțional, cheia pentru vreme compilată în aplicație (ajunge publică în JavaScript) |

Fără ele, job-ul doar publică imaginile și afișează o notă. Modificările din `deploy/` (compose, Caddyfile, scripturi) nu se copiază automat; se trimit cu `scp` în `/opt/vpp` sau `/opt/vpp-staging` și se aplică cu `docker compose up -d` în directorul respectiv.

### Administrare

```
ssh -i ~/.ssh/vpp_azure vpp@vpp-licenta.switzerlandnorth.cloudapp.azure.com
cd /opt/vpp
docker compose ps
docker compose logs -f --tail 100 api
docker stats
./deploy.sh status
cd /opt/vpp-staging && docker compose ps
```

`docker compose` găsește singur fișierul stivei prin `COMPOSE_FILE` din `.env`-ul fiecărui director, iar `./deploy.sh status` arată ambele medii. În fiecare noapte la 3:30, `backup.sh` salvează baza de date cu `pg_dump` în `/opt/vpp/backups` (comprimată, ultimele 7 zile; jurnalul în `backups/backup.log`). Restaurarea este descrisă în `deploy/README.md`. Copiile stau pe același disc cu baza de date, deci nu protejează la pierderea mașinii virtuale; pentru asta se copiază din când în când pe alt calculator cu `scp`.

## Evaluare

`scripts\run_evaluation.bat` rulează toate strategiile (reguli, baterie locală, MPC, optim LP) pe patru anotimpuri și mai multe seed-uri și scrie tabelele și graficele în `results/`. Cu `--real` folosește producția PV reală din 2023 și prețurile PZU din 2023, 2025 sau 2026 (`--price-year`), iar consumul fiecărei case vine din `backend/data/dispozitive.csv`. Sursele sunt descrise în `backend/data/README.md`. `scripts\run_results.bat` regenerează toate rezultatele cu o singură comandă.
