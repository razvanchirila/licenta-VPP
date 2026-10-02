# deploy

Fișierele serverului (Ubuntu 24.04, Docker, Caddy pentru HTTPS). Producția stă în `/opt/vpp`, staging în `/opt/vpp-staging`.

Instalare pe un server nou:

```
ssh vpp@<server> 'sudo bash -s' < deploy/setup-server.sh
```

Publicarea se face din GitHub Actions: `develop` pe staging, `main` în producție. Secrete necesare: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`.

Parola conturilor demo în producție:

```
ssh -t vpp@<server> /opt/vpp/set-demo-password.sh prod
```

Restaurare din copia de noapte (`/opt/vpp/backups`):

```
cd /opt/vpp && docker compose stop api
gunzip -c backups/<fisier>.sql.gz | docker compose exec -T db psql -q -U vpp -d vpp
docker compose start api
```
