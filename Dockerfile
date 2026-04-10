FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8443 \
    HOST=0.0.0.0 \
    TLS_ENABLED=true \
    TLS_CERT_FILE=/app/tls/fullchain.pem \
    TLS_KEY_FILE=/app/tls/privkey.pem

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8443

CMD ["/app/docker-entrypoint.sh"]
