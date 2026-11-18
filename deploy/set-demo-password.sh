#!/usr/bin/env bash
# Schimba parola conturilor demo (admin, user1..user10) intr-un mediu. Parola se citeste fara ecou, ajunge doar
# in .env (chmod 600), iar api-ul este recreat ca seed.py sa o aplice.
#   ssh -t -i ~/.ssh/vpp_azure vpp@<server> /opt/vpp/set-demo-password.sh [prod|staging]
set -euo pipefail

env=${1:-prod}
case "$env" in
    prod) cd /opt/vpp ;;
    staging) cd /opt/vpp-staging ;;
    *) echo "folosire: $0 [prod|staging]" >&2; exit 2 ;;
esac

read -rsp "Parola noua pentru conturile demo ($env): " p
echo
read -rsp "Inca o data: " q
echo
[ "$p" = "$q" ] || { echo "Parolele difera, nu am schimbat nimic." >&2; exit 1; }
[[ $p != *"'"* ]] || { echo "Parola nu poate contine apostrof." >&2; exit 1; }
bytes=$(LC_ALL=C; echo ${#p})
[ "$bytes" -ge 8 ] && [ "$bytes" -le 72 ] || { echo "Parola trebuie sa aiba intre 8 si 72 de octeti." >&2; exit 1; }

umask 077
{
    grep -v '^DEMO_PASSWORD=' .env || true
    printf "DEMO_PASSWORD='%s'\n" "$p"
} > .env.new
mv .env.new .env
unset p q

docker compose up -d --wait --wait-timeout 300 api

docker compose exec -T api grep -q "environ.*DEMO_PASSWORD" scripts/seed.py \
    || echo "Imaginea api care ruleaza acum nu citeste DEMO_PASSWORD; parola se aplica la urmatorul deploy."

status=$(docker compose exec -T api python -c '
import json, urllib.error, urllib.request
req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login", headers={"Content-Type": "application/json"},
                             data=json.dumps({"username": "admin", "password": "123"}).encode())
try:
    urllib.request.urlopen(req, timeout=5)
    print(200)
except urllib.error.HTTPError as e:
    print(e.code)
')
if [ "$status" = 200 ]; then
    echo "admin se autentifica acum cu parola 123."
else
    echo "Gata: parola 123 nu mai este acceptata pentru admin ($env)."
fi
