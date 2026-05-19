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
    """Initialize database tables."""
    with app.app_context():
        db.create_all()
        print("Database tables created.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from app.utils.seeder import seed_all
        seed_all()

        # Add new columns to existing tables if missing (safe to run repeatedly)
        from sqlalchemy import text
        with db.engine.connect() as conn:
            for col, col_type in [
                ("country_code", "VARCHAR(5)"),
                ("abuse_confidence_score", "INTEGER"),
            ]:
                try:
                    conn.execute(text(
                        f"ALTER TABLE incidents ADD COLUMN IF NOT EXISTS {col} {col_type}"
                    ))
                    conn.commit()
                except Exception:
                    pass  # Column already exists

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
