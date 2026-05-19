import threading
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)

_monitor_thread: Optional[threading.Thread] = None
_running = False

# Track last log entry time for frontend warning banner
last_log_received_at: Optional[datetime] = None


def resolve_web_log_path(config_path: Optional[str] = None) -> str:
    """Resolve WEB_SERVER_LOG_PATH relative to backend/ (same as tailer + inject-log)."""
    log_path = config_path or os.getenv('WEB_SERVER_LOG_PATH', '../vuln-web/logs/access.log')
    if log_path and not os.path.isabs(log_path):
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.normpath(os.path.join(backend_dir, log_path))
    return log_path


def _process_log_line(line: str, engine, responder, db, redis_client, app) -> Optional[int]:
    """Parse one line, run detection, create incident if needed. Returns incident id or None."""
    global last_log_received_at
    from app.core.log_parser import parse_log_line
    from app.models import Incident, SeverityLevel, IncidentStatus, DetectionRule

    entry = parse_log_line(line)
    if not entry:
        return None

    last_log_received_at = datetime.utcnow()

    threat = engine.analyze(entry)
    if not threat:
        return None

    skip_dedup = False
    if redis_client:
        try:
            ip = threat['ip']
            attack = threat['attack_type']
            if redis_client.exists(f"unblocked:{ip}"):
                waiver_key = f"unblock_waiver:{ip}:{attack}"
                if redis_client.set(waiver_key, '1', nx=True, ex=600):
                    skip_dedup = True
        except Exception:
            pass

    if not skip_dedup:
        dedup_window = datetime.utcnow() - timedelta(minutes=5)
        recent = Incident.query.filter(
            Incident.source_ip == threat['ip'],
            Incident.attack_type == threat['attack_type'],
            Incident.created_at >= dedup_window,
        ).first()
        if recent:
            logger.debug(f"Dedup skip: {threat['attack_type']} from {threat['ip']} (seen within 5m)")
            return None

    sev_map = {
        'low': SeverityLevel.LOW,
        'medium': SeverityLevel.MEDIUM,
        'high': SeverityLevel.HIGH,
        'critical': SeverityLevel.CRITICAL,
    }
    severity_enum = sev_map.get(threat['severity'], SeverityLevel.MEDIUM)

    rule = DetectionRule.query.filter_by(
        attack_type=threat['attack_type'], is_active=True,
    ).first()
    rule_id = rule.id if rule else None
    if rule:
        rule.match_count += 1

    incident = Incident(
        source_ip=threat['ip'],
        attack_type=threat['attack_type'],
        severity=severity_enum,
        status=IncidentStatus.NEW,
        raw_payload=threat.get('raw_payload', ''),
        request_path=threat.get('request_path', ''),
        request_method=threat.get('request_method', ''),
        user_agent=threat.get('user_agent', ''),
        response_code=threat.get('response_code'),
        rule_id=rule_id,
    )
    db.session.add(incident)
    db.session.commit()

    logger.info(f"[THREAT] {threat['attack_type']} from {threat['ip']} | Severity: {threat['severity']}")

    responder.respond(threat, incident.id)

    try:
        from app.services.ai_service import generate_explanation_task
        generate_explanation_task.delay(incident.id)
    except Exception as e:
        logger.warning(f"AI task error: {e}")

    from app.services.threat_intel_service import _do_reputation_check
    from app.services.notification_service import _get_setting
    if _get_setting('ABUSEIPDB_API_KEY'):
        try:
            def _rep_thread(app_ref, inc_id, ip):
                try:
                    with app_ref.app_context():
                        _do_reputation_check(inc_id, ip)
                except Exception as e:
                    logger.error(f"AbuseIPDB thread error: {e}")
            threading.Thread(
                target=_rep_thread,
                args=(app, incident.id, threat['ip']),
                daemon=True,
            ).start()
        except Exception as e:
            logger.warning(f"IP reputation check skipped: {e}")

    return incident.id


def ingest_log_lines(lines: List[str], app, db, redis_client=None) -> List[int]:
    """Process lines through the detection pipeline (used by inject-log and tailer)."""
    from app.core.detection_engine import DetectionEngine, register_detection_engine
    from app.core.response_manager import ResponseManager

    engine = DetectionEngine(redis_client=redis_client)
    register_detection_engine(engine)
    responder = ResponseManager(db=db, redis_client=redis_client, app=app)

    created = []
    with app.app_context():
        for line in lines:
            if not line or not line.strip():
                continue
            try:
                inc_id = _process_log_line(line, engine, responder, db, redis_client, app)
                if inc_id:
                    created.append(inc_id)
            except Exception as e:
                logger.error(f"ingest_log_lines error: {e}", exc_info=True)
    return created


def start_monitor(app, db, redis_client=None):
    """Start the log monitor in a background thread."""
    global _monitor_thread, _running, last_log_received_at

    if _running:
        logger.info("Log monitor already running.")
        return

    _running = True
    last_log_received_at = datetime.utcnow()

    def _run():
        from app.core.log_parser import LogTailer, SimulatedLogFeeder
        from app.core.detection_engine import DetectionEngine, register_detection_engine
        from app.core.response_manager import ResponseManager

        log_path = resolve_web_log_path(app.config.get('WEB_SERVER_LOG_PATH', ''))
        logger.info(f"Log monitor path: {log_path}")

        use_simulated = os.getenv('USE_SIMULATED_LOGS', 'true').lower() == 'true'
        demo_mode = os.getenv('DEMO_MODE', 'true').lower() == 'true'

        if use_simulated:
            if demo_mode:
                logger.info("USE_SIMULATED_LOGS=true, DEMO_MODE=true: simulated feeder (single pass).")
                feeder = SimulatedLogFeeder(repeat=False, delay=float(os.getenv('SIMULATED_LOG_DELAY', '5')))
            else:
                logger.info("USE_SIMULATED_LOGS=true: simulated feeder (repeating).")
                feeder = SimulatedLogFeeder(repeat=True, delay=float(os.getenv('SIMULATED_LOG_DELAY', '5')))
        else:
            if not os.path.exists(log_path):
                logger.warning(f"Log file not found yet: {log_path} — tailer will wait for it.")
            logger.info(f"Tailing real log: {log_path}")
            feeder = LogTailer(log_path)

        engine = DetectionEngine(redis_client=redis_client)
        register_detection_engine(engine)
        responder = ResponseManager(db=db, redis_client=redis_client, app=app)

        with app.app_context():
            for line in feeder.tail():
                if not _running:
                    break
                try:
                    _process_log_line(line, engine, responder, db, redis_client, app)
                except Exception as e:
                    logger.error(f"Monitor error: {e}", exc_info=True)

    _monitor_thread = threading.Thread(target=_run, daemon=True, name='LogMonitor')
    _monitor_thread.start()
    logger.info("Log monitor started.")


def stop_monitor():
    global _running
    _running = False
    logger.info("Log monitor stopping.")
