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

        # Also clean up expired rate limits
        try:
            from app.core.response_manager import _read_rate_limited_data, _persist_rate_limited_data, get_rate_limit_redis_ttl
            from app.core.detection_engine import get_redis_client
            import time
            
            rate_data = _read_rate_limited_data()
            redis_client = get_redis_client()
            now = time.time()
            
            changed = False
            new_rate_limited = []
            new_limits = {}
            for ip in rate_data.get('rate_limited', []):
                ttl = get_rate_limit_redis_ttl(redis_client, ip)
                expires_at = rate_data.get('limits', {}).get(ip, {}).get('expires_at')
                
                is_expired = False
                if redis_client:
                    if ttl <= 0:
                        is_expired = True
                else:
                    if expires_at and now > expires_at:
                        is_expired = True
                
                if is_expired:
                    changed = True
                    if redis_client:
                        try:
                            redis_client.delete(f"ratelimit:{ip}")
                        except Exception:
                            pass
                else:
                    new_rate_limited.append(ip)
                    if ip in rate_data.get('limits', {}):
                        new_limits[ip] = rate_data['limits'][ip]
                        
            if changed:
                rate_data['rate_limited'] = new_rate_limited
                rate_data['limits'] = new_limits
                _persist_rate_limited_data(rate_data)
                import logging
                logging.getLogger(__name__).info("Cleaned up expired rate limited IPs in celery worker.")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Rate limit cleanup error: {e}")

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
