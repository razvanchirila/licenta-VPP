#!/usr/bin/env bash
# Comanda fortata pentru cheia de deploy din GitHub Actions (authorized_keys: restrict,command="/opt/vpp/deploy.sh").
#   deploy <prod|staging> <sha> <utilizator-github>   token-ul ghcr.io vine pe stdin si nu se scrie pe disc
#   rollback <prod|staging>                           revine la imaginile care rulau inainte de ultimul deploy
#   status [prod|staging]
set -euo pipefail

read -r -a args <<< "${SSH_ORIGINAL_COMMAND:-$*}"
action=${args[0]:-}
env=${args[1]:-}
repo=ghcr.io/razvanchirila/licenta-vpp

usage() {
    echo "folosire: deploy <prod|staging> <sha> <utilizator> | rollback <prod|staging> | status [prod|staging]" >&2
    exit 2
}

dir_of() {
    case "$1" in
        prod) echo /opt/vpp ;;
        staging) echo /opt/vpp-staging ;;
        *) return 1 ;;
    esac
}

default_tag() {
    if [ "$1" = prod ]; then echo latest; else echo develop; fi
}

current_tag() {
    local t
    t=$(sed -n 's/^TAG=//p' "$(dir_of "$1")/.env" 2>/dev/null | tail -1)
    echo "${t:-$(default_tag "$1")}"
}

set_tag() {
    sed -i "s/^TAG=.*/TAG=$1/" .env
    grep -q '^TAG=' .env || echo "TAG=$1" >> .env
}

up() {
    docker network inspect vpp-edge >/dev/null 2>&1 || docker network create vpp-edge >/dev/null
    docker compose up -d --wait --wait-timeout 300
}

if [ "$action" = status ]; then
    for e in ${env:-prod staging}; do
        dir=$(dir_of "$e") || usage
        [ -f "$dir/.env" ] || { echo "$e: neinstalat"; continue; }
        echo "$e: TAG=$(current_tag "$e")"
        (cd "$dir" && docker compose ps --format '  {{.Service}} {{.Status}}')
    done
    exit 0
fi

dir=$(dir_of "$env") || usage
[ -f "$dir/.env" ] || { echo "$env nu e instalat in $dir" >&2; exit 2; }
cd "$dir"

# un singur deploy odata: curatenia imaginilor de la final nu trebuie sa stearga ce tocmai a descarcat celalalt mediu
exec 9>/opt/vpp/.deploy.lock
flock -w 900 9

case "$action" in
    deploy)
        tag=${args[2]:-}
        user=${args[3]:-}
        [[ $tag =~ ^[0-9a-f]{40}$ ]] || { echo "sha invalid: $tag" >&2; exit 2; }
        [[ $user =~ ^[A-Za-z0-9-]+(\[bot\])?$ ]] || { echo "utilizator invalid" >&2; exit 2; }

        token=$(cat)
        [ -n "$token" ] || { echo "lipseste token-ul pe stdin" >&2; exit 2; }

        for svc in api web; do
            id=$(docker compose ps -q "$svc")
            if [ -n "$id" ]; then
                docker tag "$(docker inspect --format '{{.Image}}' "$id")" "$repo-$svc:rollback-$env"
            fi
        done

        DOCKER_CONFIG=$(mktemp -d)
        export DOCKER_CONFIG
        trap 'rm -rf "$DOCKER_CONFIG"' EXIT
        printf '%s' "$token" | docker login ghcr.io -u "$user" --password-stdin >/dev/null
        unset token
        TAG=$tag docker compose pull --quiet api web
        docker logout ghcr.io >/dev/null

        set_tag "$tag"
        up

        keep="rollback-prod|rollback-staging|$(current_tag prod)|$(current_tag staging)"
        docker images --filter "reference=$repo-*" --format '{{.Repository}}:{{.Tag}}' \
            | grep -vE ":($keep)$" | xargs -r docker rmi >/dev/null 2>&1 || true
        docker image prune -f >/dev/null
        echo "deploy $env $tag ok"
        ;;
    rollback)
        docker image inspect "$repo-api:rollback-$env" "$repo-web:rollback-$env" >/dev/null
        set_tag "rollback-$env"
        up
        echo "rollback $env ok"
        ;;
    *)
        usage
        ;;
esac
