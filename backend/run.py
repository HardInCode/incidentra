import os
import logging

# Show log monitor startup messages in console
_log_mon = logging.getLogger('app.core.log_monitor')
_log_mon.setLevel(logging.INFO)
if not _log_mon.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    _log_mon.addHandler(_h)

from app import create_app, db

app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.cli.command('seed')
def seed():
    """Seed the database with default data."""
    from app.utils.seeder import seed_all
    with app.app_context():
        seed_all()


@app.cli.command('init-db')
def init_db():
    """Apply pending Alembic migrations (replaces the old db.create_all())."""
    from flask_migrate import upgrade
    with app.app_context():
        upgrade()
        print("Database migrated to head.")


if __name__ == '__main__':
    with app.app_context():
        from flask_migrate import upgrade
        upgrade()
        from app.utils.seeder import seed_all
        seed_all()

        # Start log monitor
        from app.core.log_monitor import start_monitor
        from app.core.detection_engine import get_redis_client
        redis_client = get_redis_client()
        start_monitor(app, db, redis_client)

    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_ENV', 'development') == 'development',
        use_reloader=False,  # Prevent double monitor start
    )
