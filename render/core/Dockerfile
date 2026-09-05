# Render deployment image — combines the backend API (+ Celery worker/beat + log
# monitor) and vuln-web (intentionally vulnerable demo app) into ONE container so they
# can share a local filesystem for blocked_ips.json / rate_limited.json / access.log.
#
# Build context MUST be the repository root:
#   docker build -f render/core/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

# backend/requirements.txt is a superset of vuln-web/requirements.txt — one install
# covers both apps.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Backend source lives at /app (identical layout to backend/Dockerfile).
COPY backend/ ./
RUN chmod +x docker_entrypoint.sh

# vuln-web source lives at /app/vulnweb. Its app.py is renamed to wsgi_entry.py to
# avoid a Python module-name collision with backend's own `app` package.
COPY vuln-web/ ./vulnweb/
RUN mv ./vulnweb/app.py ./vulnweb/wsgi_entry.py \
    && mkdir -p ./vulnweb/logs ./vulnweb/safe_files ./vulnweb/lab_secrets \
    && cp -r ./vulnweb/lab_secrets ./lab_secrets

# Combined WSGI app + startup orchestration.
COPY render/core/wsgi.py ./wsgi.py
COPY render/core/entrypoint.sh ./render_entrypoint.sh
RUN chmod +x ./render_entrypoint.sh

ENV FLASK_APP=run.py \
    PYTHONUNBUFFERED=1 \
    # Shared state between backend and vuln-web (same container filesystem)
    WATCHED_LOG_DIR=/app/shared \
    WEB_SERVER_LOG_PATH=/app/shared/access.log \
    BLOCKED_IPS_JSON_PATH=/app/shared/blocked_ips.json \
    RATE_LIMITED_JSON_PATH=/app/shared/rate_limited.json \
    VULN_LOG_FILE=/app/shared/access.log \
    BLOCKED_IPS_JSON=/app/shared/blocked_ips.json \
    RATE_LIMITED_JSON=/app/shared/rate_limited.json \
    # vuln-web standalone state
    VULN_DB_PATH=/app/vulnweb/vuln.db \
    VULN_SAFE_FILES_DIR=/app/vulnweb/safe_files \
    VULN_UNSAFE_CMD=1 \
    VULN_UNSAFE_UPLOAD=1 \
    USE_SIMULATED_LOGS=false \
    DEMO_MODE=false

EXPOSE 8080

CMD ["./render_entrypoint.sh"]
