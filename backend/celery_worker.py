"""
CELERY WORKER — SIDANG: patokan file ini untuk pertanyaan Celery.

Yang BENAR-BENAR JALAN di runtime:
  cleanup_expired_blocks  →  setiap 1 jam (beat_schedule baris bawah)

Yang TERDAFTAR tapi TIDAK dipanggil .delay() saat runtime:
  generate_explanation_task  → explain = sync HTTP di incidents.py
  notify_critical_incident   → email = thread di response_manager._notify_async()
  check_ip_reputation        → AbuseIPDB = thread di log_monitor.py

Broker: Redis (CELERY_BROKER_URL di docker-compose.yml — db /1, terpisah dari app Redis /0)
Jalankan: docker-compose service celery_worker (worker + beat dalam 1 container)
"""
import os
from app import create_app, celery

app = create_app(os.getenv('FLASK_ENV', 'production'))
app.app_context().push()  # worker butuh Flask context untuk SQLAlchemy query

# Import tasks hanya REGISTER ke Celery — bukan bukti semua task dipakai runtime
from app.services.ai_service import generate_explanation_task          # unused runtime
from app.services.notification_service import notify_critical_incident  # unused runtime
from app.services.threat_intel_service import check_ip_reputation       # unused runtime


@celery.task
def cleanup_expired_blocks():
    """Housekeeping hourly — BUKAN bagian pipeline deteksi log.

    Langkah 1: hapus BlockedIP temporary yang expire_time sudah lewat (PostgreSQL)
    Langkah 2: sync blocked_ips.json supaya vuln-web tidak block IP expired
    Langkah 3: bersihkan rate_limited.json + delete Redis ratelimit:{ip} yang expired
    """
    from app.models import BlockedIP
    from app import db
    from datetime import datetime
    try:
        now = datetime.utcnow()

        # ─── Langkah 1: expired temporary blocks di PostgreSQL ───
        expired = BlockedIP.query.filter(
            BlockedIP.block_type == 'temporary',
            BlockedIP.expire_time < now
        ).all()
        count = len(expired)
        for block in expired:
            db.session.delete(block)
        db.session.commit()

        # ─── Langkah 2: sync JSON block list ke vuln-web ───
        if count > 0:
            from app.core.response_manager import _write_blocked_ips_json
            _write_blocked_ips_json()
            import logging
            logging.getLogger(__name__).info(f"Cleaned up {count} expired IP blocks.")

        # ─── Langkah 3: expired rate limits (JSON + Redis ratelimit:{ip}) ───
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
                ttl = get_rate_limit_redis_ttl(redis_client, ip)  # Redis ratelimit:{ip}
                expires_at = rate_data.get('limits', {}).get(ip, {}).get('expires_at')

                is_expired = False
                if redis_client:
                    if ttl <= 0:  # Redis TTL habis = rate limit expired
                        is_expired = True
                else:
                    if expires_at and now > expires_at:  # fallback tanpa Redis
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


# Beat schedule — satu-satunya task terjadwal di project ini
from celery.schedules import crontab
celery.conf.beat_schedule = {
    'cleanup-expired-blocks-hourly': {
        'task': 'celery_worker.cleanup_expired_blocks',
        'schedule': 3600.0,  # every 3600 seconds = 1 jam
    },
}
