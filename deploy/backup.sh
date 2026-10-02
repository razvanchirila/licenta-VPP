#!/usr/bin/env bash
# Copia de noapte a bazei de date (cron: /etc/cron.d/vpp-backup). Pastreaza ultimele 7 zile.
set -euo pipefail
cd /opt/vpp
umask 077

file="backups/vpp-$(date +%F-%H%M).sql.gz"
docker compose exec -T db pg_dump -U vpp -d vpp --clean --if-exists --no-owner | gzip > "$file.tmp"
mv "$file.tmp" "$file"
find backups -name 'vpp-*.sql.gz' -mtime +6 -delete
echo "$(date '+%F %T') $file $(du -h "$file" | cut -f1)"
