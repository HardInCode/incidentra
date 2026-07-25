#!/bin/sh
set -e

echo "=== Incidentra SOC - Railway combined core service starting ==="

echo "Waiting for PostgreSQL..."
python -c "
import time, os, psycopg
db_url = os.getenv('DATABASE_URL', '').replace('postgresql+psycopg://', 'postgresql://')
for i in range(30):
    try:
        conn = psycopg.connect(db_url)
        conn.close()
        print('PostgreSQL ready.')
        break
    except Exception as e:
        print(f'Waiting ({i+1}/30)...')
        time.sleep(2)
else:
    print('ERROR: Could not connect to PostgreSQL after 30 attempts.')
    exit(1)
"

echo "Preparing shared state directory ($WATCHED_LOG_DIR)..."
python -c "
import json, os
shared_dir = os.environ.get('WATCHED_LOG_DIR', '/app/shared')
os.makedirs(shared_dir, exist_ok=True)
open(os.path.join(shared_dir, 'access.log'), 'a').close()
for name, default in [
    ('blocked_ips.json', {'blocked': [], 'updated_at': ''}),
    ('rate_limited.json', {'rate_limited': [], 'limits': {}, 'updated_at': ''}),
]:
    path = os.path.join(shared_dir, name)
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default, f)
"

echo "Running database migrations (flask db upgrade)..."
flask db upgrade

echo "Seeding database..."
python -c "
from app import create_app
from app.utils.seeder import seed_all
app = create_app()
with app.app_context():
    seed_all()
"
echo "Backend DB init complete."

if [ "${ENABLE_LAB:-true}" = "true" ]; then
  echo "Initializing vuln-web demo SQLite database..."
  python -c "
import sys
sys.path.insert(0, './vulnweb')
from db import init_db
init_db()
"
  echo "vuln-web DB init complete."
else
  echo "ENABLE_LAB=false - skipping vuln-web init (lab endpoints disabled)."
fi

echo "Starting log monitor..."
python docker_log_monitor.py &
MONITOR_PID=$!

echo "Starting Celery worker + beat..."
celery -A celery_worker.celery worker --loglevel=info --concurrency=2 &
celery -A celery_worker.celery beat --loglevel=info &

echo "Starting gunicorn (backend /api + vuln-web /lab, monitor PID=$MONITOR_PID)..."
exec gunicorn \
  --workers 2 \
  --bind 0.0.0.0:${PORT:-8080} \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  "wsgi:application"
