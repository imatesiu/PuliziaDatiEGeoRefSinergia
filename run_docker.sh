#!/bin/sh
set -eu

IMAGE_NAME="pulizia-dati-sinergia:1.2.1"
CONTAINER_NAME="pulizia-dati-sinergia"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker build -t "$IMAGE_NAME" .
exec docker run --rm -p 9382:8443 --name "$CONTAINER_NAME" "$IMAGE_NAME"
