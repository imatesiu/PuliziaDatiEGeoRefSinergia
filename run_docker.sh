#!/bin/sh
set -eu

IMAGE_NAME="pulizia-dati-sinergia:1.3.6"
CONTAINER_NAME="pulizia-dati-sinergia"
LETSENCRYPT_ROOT="/etc/letsencrypt"
LETSENCRYPT_SITE="rtapp.isti.cnr.it"
TLS_CERT_FILE="/etc/letsencrypt/live/${LETSENCRYPT_SITE}/fullchain.pem"
TLS_KEY_FILE="/etc/letsencrypt/live/${LETSENCRYPT_SITE}/privkey.pem"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker build -t "$IMAGE_NAME" .
exec docker run --rm \
  -p 9382:8443 \
  -v "${LETSENCRYPT_ROOT}:${LETSENCRYPT_ROOT}:ro" \
  -e TLS_CERT_FILE="$TLS_CERT_FILE" \
  -e TLS_KEY_FILE="$TLS_KEY_FILE" \
  --name "$CONTAINER_NAME" \
  "$IMAGE_NAME"
