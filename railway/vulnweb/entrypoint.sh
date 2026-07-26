#!/bin/sh
set -e

echo "=== Incidentra vuln-web - Railway standalone service starting ==="

if [ -z "$LOG_INGEST_URL" ] || [ -z "$BLOCKLIST_API_URL" ] || [ -z "$INTERNAL_API_TOKEN" ]; then
  echo "WARNING: LOG_INGEST_URL / BLOCKLIST_API_URL / INTERNAL_API_TOKEN not fully set."
  echo "This service will not push logs to, or enforce blocks from, the core service."
fi

echo "Initializing vuln-web demo SQLite database..."
python -c "from db import init_db; init_db()"
echo "vuln-web DB init complete."

echo "Starting gunicorn..."
exec gunicorn \
  --workers 2 \
  --bind 0.0.0.0:${PORT:-8080} \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  "app:app"
