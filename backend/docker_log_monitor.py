"""Standalone log monitor process for Docker (gunicorn does not run run.py)."""
import os
import time

from app import create_app, db
from app.core.detection_engine import get_redis_client
from app.core.log_monitor import start_monitor

app = create_app(os.getenv('FLASK_ENV', 'production'))
with app.app_context():
    redis_client = get_redis_client()
    start_monitor(app, db, redis_client)
    print('Log monitor started.', flush=True)

while True:
    time.sleep(3600)
