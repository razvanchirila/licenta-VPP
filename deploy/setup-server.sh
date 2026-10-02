#!/usr/bin/env bash
# Pregateste serverul Ubuntu 24.04 pentru stivele din docker-compose.prod.yml si docker-compose.staging.yml.
# Se poate rula de mai multe ori.
#   ssh vpp@<server> 'sudo bash -s' < deploy/setup-server.sh
set -euo pipefail

APP_USER=${APP_USER:-vpp}
APP_DIR=/opt/vpp
STAGING_DIR=/opt/vpp-staging

[ "$(id -u)" -eq 0 ] || { echo "Ruleaza cu sudo." >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive

if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
fi
swapon --show=NAME --noheadings | grep -qx /swapfile || swapon /swapfile
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo 'vm.swappiness=10' > /etc/sysctl.d/90-vpp.conf
sysctl -q -p /etc/sysctl.d/90-vpp.conf

timedatectl set-timezone Europe/Bucharest

apt-get update -q
apt-get install -y -q ca-certificates curl gnupg unattended-upgrades fail2ban python3-systemd

install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
fi
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
apt-get update -q
apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

DAEMON_JSON='{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}'
if [ "$(cat /etc/docker/daemon.json 2>/dev/null)" != "$DAEMON_JSON" ]; then
    echo "$DAEMON_JSON" > /etc/docker/daemon.json
    systemctl restart docker
fi
systemctl enable --now docker containerd
usermod -aG docker "$APP_USER"

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
systemctl enable --now unattended-upgrades

cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
backend = systemd
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable fail2ban
systemctl restart fail2ban

cat > /etc/ssh/sshd_config.d/10-vpp.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
sshd -t
systemctl reload ssh

mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/90-vpp.conf <<'EOF'
[Journal]
SystemMaxUse=200M
MaxRetentionSec=1month
EOF
systemctl restart systemd-journald

# servicii inutile pe o masina virtuala Azure; elibereaza ~50 MB de RAM
for unit in ModemManager.service udisks2.service multipathd.service multipathd.socket; do
    systemctl disable --now "$unit" 2>/dev/null || true
done

install -d -o "$APP_USER" -g "$APP_USER" -m 0750 "$APP_DIR" "$APP_DIR/backups" "$STAGING_DIR"

new_env() {
    local example=$1 env=$2
    [ -f "$example" ] && [ ! -f "$env" ] || return 0
    (
        umask 077
        sed -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" \
            -e "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(openssl rand -hex 32)|" \
            "$example" > "$env"
    )
    chown "$APP_USER:$APP_USER" "$env"
    echo "Creat $env cu secrete noi."
}
new_env "$APP_DIR/.env.example" "$APP_DIR/.env"
new_env "$STAGING_DIR/.env.staging.example" "$STAGING_DIR/.env"

docker network inspect vpp-edge >/dev/null 2>&1 || docker network create vpp-edge >/dev/null

if [ -f "$APP_DIR/backup.sh" ]; then
    chmod 0755 "$APP_DIR/backup.sh" "$APP_DIR/deploy.sh" "$APP_DIR/set-demo-password.sh"
    echo "30 3 * * * $APP_USER $APP_DIR/backup.sh >> $APP_DIR/backups/backup.log 2>&1" > /etc/cron.d/vpp-backup
    chmod 0644 /etc/cron.d/vpp-backup
fi

echo "Gata: $(docker --version), $(docker compose version), swap $(swapon --show=SIZE --noheadings | head -1)"
