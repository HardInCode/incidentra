# Railway deployment image — vuln-web as its OWN standalone service with its OWN
# public domain, decoupled from the "core" backend service (no shared filesystem/
# volume at all). Additive only:
#   - Does NOT replace vuln-web/Dockerfile, which stays exactly as-is for local Docker
#     Compose (shared-volume topology).
#   - Is an ALTERNATIVE to railway/core/Dockerfile's DispatcherMiddleware /lab mount
#     (that "merged, single-domain" topology still works unchanged if you prefer it —
#     see railway/README.md, "Two ways to deploy vuln-web").
#
# State that would normally live on the shared volume (access.log, blocked_ips.json,
# rate_limited.json) is instead pushed/pulled over HTTP to the core service's
# /api/internal/* endpoints — see vuln-web/config.py's LOG_INGEST_URL /
# BLOCKLIST_API_URL / INTERNAL_API_TOKEN.
#
# Build context MUST be the repository root, e.g.:
#   docker build -f railway/vulnweb/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

COPY vuln-web/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn==22.0.0

COPY vuln-web/ ./
RUN mkdir -p logs safe_files lab_secrets

COPY railway/vulnweb/entrypoint.sh ./railway_entrypoint.sh
RUN chmod +x ./railway_entrypoint.sh

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["./railway_entrypoint.sh"]
