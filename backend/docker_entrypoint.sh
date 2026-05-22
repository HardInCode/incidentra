#!/bin/sh
set -e

echo "=== Incidentra SOC Backend Starting ==="

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

echo "Preparing shared log volume..."
python -c "
import json, os
from datetime import datetime, timezone
log_dir = os.environ.get('WATCHED_LOG_DIR', '/app/watched_logs')
os.makedirs(log_dir, exist_ok=True)
open(os.path.join(log_dir, 'access.log'), 'a').close()
for name, default in [
    ('blocked_ips.json', {'blocked': [], 'updated_at': ''}),
    ('rate_limited.json', {'rate_limited': [], 'limits': {}, 'updated_at': ''}),
]:
    path = os.path.join(log_dir, name)
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default, f)
"

echo "Running DB init and seed..."
python -c "
from app import create_app, db
from app.utils.seeder import seed_all
app = create_app()
with app.app_context():
    db.create_all()
    seed_all()
print('DB init complete.')
"

echo "Starting log monitor..."
python docker_log_monitor.py &
MONITOR_PID=$!

echo "Starting gunicorn (log monitor PID=$MONITOR_PID)..."
exec gunicorn \
  --workers 2 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  "run:app"
