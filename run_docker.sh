#!/bin/sh
set -eu

IMAGE_NAME="pulizia-dati-sinergia:1.3.7"
CONTAINER_NAME="pulizia-dati-sinergia"
LETSENCRYPT_ROOT="/etc/letsencrypt"
LETSENCRYPT_SITE="rtapp.isti.cnr.it"
TLS_CERT_FILE="/etc/letsencrypt/live/${LETSENCRYPT_SITE}/fullchain.pem"
TLS_KEY_FILE="/etc/letsencrypt/live/${LETSENCRYPT_SITE}/privkey.pem"
CACHE_DIR="$(pwd)/cache"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
mkdir -p "$CACHE_DIR"
docker build -t "$IMAGE_NAME" .
exec docker run --rm \
  -p 9382:8443 \
  -v "${LETSENCRYPT_ROOT}:${LETSENCRYPT_ROOT}:ro" \
  -v "${CACHE_DIR}:/app/cache" \
  -e TLS_CERT_FILE="$TLS_CERT_FILE" \
  -e TLS_KEY_FILE="$TLS_KEY_FILE" \
  -e GEOCODER_CACHE_DIR="/app/cache" \
  --name "$CONTAINER_NAME" \
  "$IMAGE_NAME"
