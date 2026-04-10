#!/bin/sh
set -eu

PORT="${PORT:-8443}"
TLS_ENABLED="${TLS_ENABLED:-true}"
TLS_CERT_FILE="${TLS_CERT_FILE:-/app/tls/fullchain.pem}"
TLS_KEY_FILE="${TLS_KEY_FILE:-/app/tls/privkey.pem}"

if [ "$TLS_ENABLED" = "true" ]; then
  if [ ! -f "$TLS_CERT_FILE" ]; then
    echo "Certificato TLS non trovato: $TLS_CERT_FILE" >&2
    exit 1
  fi

  if [ ! -f "$TLS_KEY_FILE" ]; then
    echo "Chiave TLS non trovata: $TLS_KEY_FILE" >&2
    exit 1
  fi

  exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --certfile "$TLS_CERT_FILE" \
    --keyfile "$TLS_KEY_FILE" \
    app:app
fi

exec gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  app:app
