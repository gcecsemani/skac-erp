#!/usr/bin/env bash
# Enable HTTPS for SKAC on the droplet (nginx + Let's Encrypt).
# FastAPI stays on 127.0.0.1:5174. Nginx terminates TLS.
#
# Domain (recommended, 90-day certs):
#   sudo DOMAIN=erp.yourclinic.com EMAIL=you@yourclinic.com bash setup-https.sh
#
# IP only (6-day certs; staff keep using the droplet IP):
#   sudo USE_IP=1 EMAIL=you@yourclinic.com bash setup-https.sh
#
# Prerequisites:
#   - this repo's deploy/nginx files are on the server (or copy them first)
#   - DigitalOcean firewall AND ufw allow inbound TCP 80 and 443
#   - DNS A record for DOMAIN points at this droplet (domain mode only)

set -euo pipefail

EMAIL="${EMAIL:-}"
USE_IP="${USE_IP:-0}"
DROPLET_IP="${DROPLET_IP:-64.227.168.129}"
DOMAIN="${DOMAIN:-}"
SITE_AVAILABLE="/etc/nginx/sites-available/skac"
SITE_ENABLED="/etc/nginx/sites-enabled/skac"
PROXY_INC="/etc/nginx/skac-proxy.inc"
WEBROOT="/var/www/certbot"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

if [[ -z "$EMAIL" ]]; then
  echo "Set EMAIL=you@yourclinic.com" >&2
  exit 1
fi

if [[ "$USE_IP" == "1" && -n "$DOMAIN" ]]; then
  echo "Use either USE_IP=1 or DOMAIN=..., not both." >&2
  exit 1
fi

if [[ "$USE_IP" != "1" && -z "$DOMAIN" ]]; then
  echo "Set DOMAIN=erp.yourclinic.com  (recommended)" >&2
  echo "or   USE_IP=1                  (Let's Encrypt IP cert, 6-day lifetime)" >&2
  exit 1
fi

if [[ "$USE_IP" == "1" ]]; then
  SERVER_NAME="$DROPLET_IP"
  CERT_NAME="$DROPLET_IP"
else
  SERVER_NAME="$DOMAIN"
  CERT_NAME="$DOMAIN"
fi

echo "==> Installing certbot (snap, needed for IP certs / current Let's Encrypt)"
if ! command -v snap >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y snapd
fi
snap install core 2>/dev/null || true
snap refresh core 2>/dev/null || true
snap install --classic certbot
ln -sfn /snap/bin/certbot /usr/bin/certbot

echo "==> Opening HTTP/HTTPS ports (ufw, if present)"
if command -v ufw >/dev/null 2>&1; then
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  ufw allow 5173/tcp || true
fi

echo "==> ACME webroot $WEBROOT"
mkdir -p "$WEBROOT"

echo "==> Installing nginx includes"
cp "$SCRIPT_DIR/skac-proxy.inc" "$PROXY_INC"

render_server_name() {
  local src="$1" dest="$2"
  sed \
    -e "s/server_name 64\\.227\\.168\\.129;/server_name ${SERVER_NAME};/g" \
    -e "s#/etc/letsencrypt/live/64\\.227\\.168\\.129/#/etc/letsencrypt/live/${CERT_NAME}/#g" \
    "$src" > "$dest"
}

echo "==> Enabling HTTP bootstrap (site stays on :5173 while the cert is issued)"
render_server_name "$SCRIPT_DIR/skac.http-bootstrap.conf" "$SITE_AVAILABLE"
mkdir -p /etc/nginx/sites-enabled
ln -sfn "$SITE_AVAILABLE" "$SITE_ENABLED"
# Avoid two default servers fighting if an old copy is also enabled.
if [[ -e /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
fi
echo "    Currently enabled sites (only 'skac' should listen on 80/5173/443):"
ls -l /etc/nginx/sites-enabled/ || true
if ! nginx -t; then
  echo "nginx -t failed. Another site file is probably still listening on 80/5173." >&2
  echo "Disable it, then re-run. Enabled sites:" >&2
  ls -l /etc/nginx/sites-enabled/ >&2
  exit 1
fi
systemctl reload nginx

echo "==> Requesting Let's Encrypt certificate for $SERVER_NAME"
if [[ "$USE_IP" == "1" ]]; then
  certbot certonly --non-interactive --agree-tos -m "$EMAIL" \
    --webroot -w "$WEBROOT" \
    --preferred-profile shortlived \
    --ip-address "$DROPLET_IP" \
    --deploy-hook "systemctl reload nginx"
else
  certbot certonly --non-interactive --agree-tos -m "$EMAIL" \
    --webroot -w "$WEBROOT" \
    -d "$DOMAIN" \
    --deploy-hook "systemctl reload nginx"
fi

echo "==> Switching nginx to HTTPS"
render_server_name "$SCRIPT_DIR/skac.conf" "$SITE_AVAILABLE"
if ! nginx -t; then
  echo "HTTPS nginx -t failed. Certificate files may be under a different live/ name:" >&2
  ls -l /etc/letsencrypt/live/ >&2
  exit 1
fi
systemctl reload nginx

echo
echo "HTTPS is live:  https://${SERVER_NAME}/"
echo "Old URL http://${DROPLET_IP}:5173  now redirects there."
echo
echo "Update backend CORS, then restart the API:"
echo "  sudo sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=https://${SERVER_NAME}|' /opt/skac-erp/backend/.env"
echo "  sudo systemctl restart skac-api"
echo
echo "If the frontend was built with an http:// API URL, rebuild with same-origin:"
echo "  cd /opt/skac-erp/frontend && VITE_API_BASE_URL=/api/v1 npm run build"
echo "  sudo rsync -a --delete dist/ /opt/skac-erp/dist/"
echo
echo "In DigitalOcean → Networking → Firewalls, allow inbound TCP 80 and 443."
echo "Renewal:  sudo certbot renew --dry-run"
if [[ "$USE_IP" == "1" ]]; then
  echo "IP certificates last ~6 days. Confirm snap.certbot.renew.timer is enabled:"
  echo "  systemctl list-timers | grep certbot"
fi
