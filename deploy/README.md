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
