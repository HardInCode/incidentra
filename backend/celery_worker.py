import os
from app import create_app, celery

app = create_app(os.getenv('FLASK_ENV', 'production'))
app.app_context().push()

# Import tasks to register them
from app.services.ai_service import generate_explanation_task
from app.services.notification_service import notify_critical_incident
from app.services.threat_intel_service import check_ip_reputation


@celery.task
def cleanup_expired_blocks():
    """BUG 7 FIX: Remove expired temporary blocks every hour."""
    from app.models import BlockedIP
    from app import db
    from datetime import datetime
    try:
        now = datetime.utcnow()
        expired = BlockedIP.query.filter(
            BlockedIP.block_type == 'temporary',
            BlockedIP.expire_time < now
        ).all()
        count = len(expired)
        for block in expired:
            db.session.delete(block)
        db.session.commit()

        # Also update JSON file
        if count > 0:
            from app.core.response_manager import _write_blocked_ips_json
            _write_blocked_ips_json()
            import logging
            logging.getLogger(__name__).info(f"Cleaned up {count} expired IP blocks.")
        return count
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Cleanup error: {e}")
        db.session.rollback()
        return 0


# Schedule cleanup_expired_blocks to run every hour
from celery.schedules import crontab
celery.conf.beat_schedule = {
    'cleanup-expired-blocks-hourly': {
        'task': 'celery_worker.cleanup_expired_blocks',
        'schedule': 3600.0,  # every hour
    },
}
