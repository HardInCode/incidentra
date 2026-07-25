# Railway deployment image — combines the backend API (+ Celery worker/beat + log
# monitor) and vuln-web (intentionally vulnerable demo app) into ONE container so they
# can share a local filesystem for blocked_ips.json / rate_limited.json / access.log.
# Railway does not support a volume shared across multiple services, unlike the local
# docker-compose.yml setup, which keeps them as separate containers.
#
# This file is Railway-only and additive: it does not replace or change
# backend/Dockerfile or vuln-web/Dockerfile, which remain untouched for local Docker
# Compose use.
#
# Build context MUST be the repository root, e.g.:
#   docker build -f railway/core/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

# backend/requirements.txt is a superset of vuln-web/requirements.txt (both pin the same
# flask==3.0.3 / python-dotenv==1.0.1) — one install covers both apps.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Backend source lives at /app (identical layout to backend/Dockerfile).
COPY backend/ ./
RUN chmod +x docker_entrypoint.sh

# vuln-web source lives at /app/vulnweb. Its app.py is renamed to wsgi_entry.py to avoid
# a Python module-name collision with backend's own `app` package — both would otherwise
# be importable as top-level module `app` in the same interpreter (see railway/core/wsgi.py).
COPY vuln-web/ ./vulnweb/
RUN mv ./vulnweb/app.py ./vulnweb/wsgi_entry.py \
    && mkdir -p ./vulnweb/logs ./vulnweb/safe_files ./vulnweb/lab_secrets \
    # The command-injection lab hint ("cat lab_secrets/capstone_flag.txt") is a path
    # relative to the *serving* process's CWD, which is /app here (not /app/vulnweb) —
    # duplicate the folder at /app so that hint keeps working unmodified.
    && cp -r ./vulnweb/lab_secrets ./lab_secrets

# Combined WSGI app + Railway-specific startup orchestration (migrate/seed/init/workers).
COPY railway/core/wsgi.py ./wsgi.py
COPY railway/core/entrypoint.sh ./railway_entrypoint.sh
RUN chmod +x ./railway_entrypoint.sh

ENV FLASK_APP=run.py \
    PYTHONUNBUFFERED=1 \
    # --- Shared state between backend (writer+reader) and vuln-web (writer+reader) ---
    # Same absolute paths on both sides so one container filesystem replaces the local
    # docker-compose `vuln_logs` shared volume.
    WATCHED_LOG_DIR=/app/shared \
    WEB_SERVER_LOG_PATH=/app/shared/access.log \
    BLOCKED_IPS_JSON_PATH=/app/shared/blocked_ips.json \
    RATE_LIMITED_JSON_PATH=/app/shared/rate_limited.json \
    VULN_LOG_FILE=/app/shared/access.log \
    BLOCKED_IPS_JSON=/app/shared/blocked_ips.json \
    RATE_LIMITED_JSON=/app/shared/rate_limited.json \
    # --- vuln-web's own self-contained state (not shared with backend) ---
    VULN_DB_PATH=/app/vulnweb/vuln.db \
    VULN_SAFE_FILES_DIR=/app/vulnweb/safe_files \
    VULN_UNSAFE_CMD=1 \
    VULN_UNSAFE_UPLOAD=1

EXPOSE 8080

CMD ["./railway_entrypoint.sh"]
