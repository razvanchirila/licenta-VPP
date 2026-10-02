# Serverul: producție și staging

Fișierele de aici ajung pe server în `/opt/vpp` (producție) și `/opt/vpp-staging` (staging). Prezentarea generală este în README-ul principal, secțiunile „Cum lucrăm” și „Producție”.

| Fișier | Rol |
|---|---|
| `setup-server.sh` | pregătește un Ubuntu 24.04 gol (swap, Docker, actualizări de securitate, fail2ban, SSH doar cu cheie, limite de jurnal, fus orar, rețeaua `vpp-edge`); se poate rula de mai multe ori |
| `docker-compose.prod.yml` | stiva de producție: `db`, `api`, `web`, `caddy` (Caddy servește și adresa de staging) |
| `docker-compose.staging.yml` | stiva de staging: `db`, `api`, `web`, cu limite de memorie mai mici |
| `Caddyfile` | HTTPS automat pentru ambele adrese și împărțirea cererilor între `web` și `api` |
| `.env.example`, `.env.staging.example` | modelele pentru `/opt/vpp/.env` și `/opt/vpp-staging/.env`; secretele se generează pe server |
| `deploy.sh` | singura comandă permisă cheii de deploy din GitHub Actions (`deploy`, `rollback`, `status`) |
| `set-demo-password.sh` | schimbă parola conturilor demo într-un mediu, fără să o afișeze |
| `backup.sh` | copia de noapte a bazei de date de producție |

## Instalare de la zero

```
ssh vpp@<server> 'sudo bash -s' < deploy/setup-server.sh
scp deploy/docker-compose.prod.yml deploy/Caddyfile deploy/.env.example deploy/backup.sh deploy/deploy.sh deploy/set-demo-password.sh vpp@<server>:/opt/vpp/
scp deploy/docker-compose.staging.yml deploy/.env.staging.example vpp@<server>:/opt/vpp-staging/
ssh vpp@<server> 'sudo bash -s' < deploy/setup-server.sh
```

Prima rulare creează `/opt/vpp`, `/opt/vpp-staging` și rețeaua Docker `vpp-edge`. A doua găsește fișierele acolo, creează cele două fișiere `.env`, fiecare cu propria parolă a bazei de date și propria cheie JWT generate cu `openssl rand`, și instalează cron-ul pentru copii. Apoi:

```
ssh vpp@<server> 'cd /opt/vpp && docker compose pull && docker compose up -d --wait'
ssh vpp@<server> 'cd /opt/vpp-staging && docker compose pull && docker compose up -d --wait'
```

Fără imagini în ghcr.io (de exemplu la prima instalare), imaginile se construiesc local și se copiază direct:

```
docker compose -p vpp-deploy build api web
docker tag vpp-deploy-api ghcr.io/razvanchirila/licenta-vpp-api:latest
docker tag vpp-deploy-web ghcr.io/razvanchirila/licenta-vpp-web:latest
docker save ghcr.io/razvanchirila/licenta-vpp-api:latest ghcr.io/razvanchirila/licenta-vpp-web:latest | gzip | ssh vpp@<server> 'gunzip | docker load'
```

Numele de proiect `vpp-deploy` ține imaginile separat de cele ale stivei locale pornite cu `start.bat`. Pentru staging, aceleași imagini primesc pe server și eticheta `develop` (`docker tag ...-api:latest ...-api:develop`, la fel pentru `web`).

Ordinea contează la pornire: stiva de producție o primește prima, pentru că `caddy` are nevoie de `STAGING_DOMAIN` din `/opt/vpp/.env`; dacă staging nu rulează, adresa lui răspunde cu 502, iar producția nu este afectată.

## Cheia de deploy

În `~/.ssh/authorized_keys` pe server, cheia folosită de GitHub Actions are forma:

```
restrict,command="/opt/vpp/deploy.sh" ssh-ed25519 AAAA... github-actions-deploy@licenta-VPP
```

`restrict` oprește terminalul, port forwarding-ul și agentul, iar `command=` face ca orice conexiune cu această cheie să ruleze doar `deploy.sh`, oricare ar fi comanda cerută. Scriptul acceptă:

```
deploy prod|staging <sha> <utilizator-github>    token-ul ghcr.io vine pe stdin
rollback prod|staging
status [prod|staging]
```

Mediul trebuie să fie exact `prod` sau `staging`, sha-ul are 40 de caractere hexazecimale, iar orice altceva este refuzat. Înainte de deploy, imaginile care rulează primesc eticheta `rollback-prod` sau `rollback-staging`, așa că un rollback pe un mediu nu îl atinge pe celălalt. Cheia personală de administrare rămâne separată.

## Parola conturilor demo

Conturile `admin` și `user1`..`user10` iau parola din `DEMO_PASSWORD` din `.env`-ul mediului; fără ea, parola este `123`. La fiecare pornire a containerului `api`, `seed.py demo` pune din nou această parolă pe conturile demo existente, fără să atingă datele lor sau alte conturi.

Parola din producție se setează așa, de pe calculatorul propriu (o cere de două ori, fără să apară pe ecran, o scrie în `/opt/vpp/.env` cu drepturi 600 și repornește `api`):

```
ssh -t -i ~/.ssh/vpp_azure vpp@51.107.88.91 /opt/vpp/set-demo-password.sh prod
```

O parolă goală șterge `DEMO_PASSWORD`, deci revine la `123`. La final scriptul încearcă o autentificare locală cu `admin`/`123` și spune dacă mai merge. Parola nu poate conține apostrof și trebuie să aibă între 8 și 72 de octeți (limita bcrypt). Imaginile publicate înainte de această schimbare nu citesc `DEMO_PASSWORD`; în acest caz scriptul o spune, iar parola se aplică la primul deploy cu imaginea nouă.

## Setări în GitHub

Acestea se fac o singură dată, din contul proprietarului repository-ului:

1. Ramura `develop`, creată din `main`:

   ```
   git switch main
   git pull
   git switch -c develop
   git push -u origin develop
   ```

2. Settings → Rules → Rulesets → New ruleset → New branch ruleset:
   - Ruleset name: `main si develop`, Enforcement status: Active;
   - Target branches → Add target → Include by pattern: `main`, apoi încă o dată `develop`;
   - bifate: Restrict deletions, Block force pushes, Require a pull request before merging (Required approvals: 0, pentru că nu are cine altcineva să aprobe), Require status checks to pass;
   - la Require status checks to pass → Add checks: `ci-ok` (apare în listă după prima rulare a noului workflow; sursa GitHub Actions);
   - Bypass list rămâne goală.

   Pe un repository privat, regulile de protecție cer GitHub Pro, inclus în GitHub Student Developer Pack. Fără el, aceleași reguli se pot pune doar după ce repository-ul devine public.

3. Settings → Secrets and variables → Actions → Repository secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS` și, opțional, `WEATHER_API_KEY` (tabelul din README-ul principal). Fără ele imaginile se publică, dar deploy-ul este sărit.

4. Environments `staging` și `production` apar singure la primul deploy. Recomandat, după aceea: Settings → Environments → `production` → Deployment branches and tags → Selected branches and tags → `main`, iar la `staging` → `develop`. Astfel nicio altă ramură nu poate ajunge pe servere, chiar dacă workflow-ul ar fi schimbat greșit.

5. Pachetele din ghcr.io: dacă `licenta-vpp-api` și `licenta-vpp-web` sunt create de workflow, primesc singure acces de scriere din acest repository. Dacă au fost create altfel (de exemplu cu un `docker push` manual), pe pagina fiecărui pachet: Package settings → Manage Actions access → Add repository → `licenta-VPP`, rol Write.

## Restaurare din copie

```
cd /opt/vpp
docker compose stop api
gunzip -c backups/vpp-AAAA-LL-ZZ-HHMM.sql.gz | docker compose exec -T db psql -q -U vpp -d vpp
docker compose start api
```

Copia conține `DROP ... IF EXISTS` pentru fiecare tabel, deci înlocuiește datele curente. Pentru o verificare fără să atingi baza principală, se restaurează într-o bază separată (`createdb -U vpp vpp_test_restore`, apoi `psql -d vpp_test_restore`). Baza de staging nu are copii: se poate șterge oricând cu `docker compose down -v` în `/opt/vpp-staging`, iar la pornire se recreează cu conturile demo.

## Arhitectură și resurse

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

## Ce rulează în CI și când

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

GitHub Actions rulează `.github/workflows/ci.yml`. Primul job, `changes`, află ce zone s-au schimbat (cu `dorny/paths-filter`: la push față de commit-ul dinaintea push-ului, la pull request față de ramura țintă). Urmează job-urile rapide, fiecare doar dacă zona lui s-a schimbat: backend-ul (ruff și pytest pe un PostgreSQL 16 pornit ca serviciu), aplicația Flutter (analyze, verificarea formatării, teste, build web) și panoul operatorului (lint, typecheck, teste, build). Job-ul `docker` construiește imaginile `api` și `web`, doar în cazurile din tabelul de mai sus. Ultimul job, `ci-ok`, pică dacă oricare dintre celelalte a picat sau a fost anulat; el este singura verificare cerută la pull request-uri.

Rulările mai vechi pe aceeași ramură de lucru sau pe același pull request sunt oprite când apare un push nou. Pe `main` și `develop` o rulare începută nu se oprește, ca să nu se întrerupă un deploy.
