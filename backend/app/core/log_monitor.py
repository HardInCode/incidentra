"""
LOG MONITOR — orkestrator pipeline: access.log → incident → block.
Ctrl+F: start_monitor, _process_log_line, ingest_log_lines

Urutan baca file ini (sesuai alur runtime):
  ① start_monitor()        → background thread, loop baca log
  ② _process_log_line()    → 1 baris: parse → detect → incident → respond
  ③ ingest_log_lines()     → jalur alternatif (HTTP ingest / inject-log API)
  ④ Helper heartbeat/path  → Dashboard banner "No logs in 60s"

Alur lengkap:
  logging.py → access.log → LogTailer → line → _process_log_line
    → parse_log_line → analyze → Incident DB → respond
"""
import threading
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)

# ─── State monitor (level module = 1 copy per proses Python) ───
# Diubah lewat `global ...` di start_monitor / stop_monitor / touch_last_log_received.
# Bukan Redis — cuma flag & handle thread di memori proses ini.
_monitor_thread: Optional[threading.Thread] = None          # handle thread background LogTailer loop
_running = False                                            # True = loop tail masih jalan; False = stop_monitor() minta berhenti
last_log_received_at: Optional[datetime] = None             # timestamp log terakhir diproses (fallback kalau Redis kosong)
LOG_HEARTBEAT_REDIS_KEY = 'log_monitor:last_received_at'    # key Redis — share heartbeat antar worker/subprocess Docker


# ═══════════════════════════════════════════════════════════════════════════════
# ① start_monitor — ENTRY POINT (backend startup / docker_log_monitor.py)
#    Loop: LogTailer.tail() → yield line → _process_log_line(line)
# ═══════════════════════════════════════════════════════════════════════════════

def start_monitor(app, db, redis_client=None):
    """Start log monitor di background thread.

    Dipanggil dari: backend/run.py atau backend/docker_log_monitor.py saat startup.
    Parameter:
      app           ← Flask app (create_app di backend/app/__init__.py)
      db            ← SQLAlchemy db object (PostgreSQL incidents, rules, ...)
      redis_client  ← koneksi Redis (optional) — heartbeat + pass-through ke engine/responder
    """
    # `global` = ubah variable baris 26–28 (module-level), BUKAN buat variable lokal baru.
    # Tanpa baris ini, `_running = True` di bawah hanya lokal function dan stop_monitor tidak bisa stop loop.
    global _monitor_thread, _running, last_log_received_at

    if _running:  # cek flag baris 27 — hindari start monitor 2x
        logger.info("Log monitor already running.")
        return

    _running = True                        # set flag baris 27 → loop `for line in feeder.tail()` terus jalan
    touch_last_log_received(redis_client)  # update baris 28 + Redis — Dashboard tidak langsung banner stale

    def _run():                                                                            # inner function — body thread background (bukan request HTTP)
        from app.core.log_parser import LogTailer, SimulatedLogFeeder                      # ← log_parser.py ①
        from app.core.detection_engine import DetectionEngine, register_detection_engine   # ← detection_engine.py
        from app.core.response_manager import ResponseManager                              # ← response_manager.py

        log_path = resolve_web_log_path(app.config.get('WEB_SERVER_LOG_PATH', ''))         # ← helper bawah file + env Docker
        logger.info(f"Log monitor path: {log_path}")

        use_simulated = os.getenv('USE_SIMULATED_LOGS', 'true').lower() == 'true'          # ← .env Docker; false = tail access.log nyata
        demo_mode = os.getenv('DEMO_MODE', 'true').lower() == 'true'                       # ← .env

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
            feeder = LogTailer(log_path)                                        # ← log_parser.py — yield `line` dari access.log shared volume

        engine = DetectionEngine(redis_client=redis_client)                     # ← buat sekali per thread; punya method analyze()
        register_detection_engine(engine)                                       # ← simpan global ref (dipakai API lain)
        responder = ResponseManager(db=db, redis_client=redis_client, app=app)  # ← buat sekali; punya method respond()

        with app.app_context():         # ← wajib: SQLAlchemy query butuh Flask context di background thread
            for line in feeder.tail():  # ← `line` = string 1 baris log (dari file atau SimulatedLogFeeder)
                if not _running:  # baca flag baris 27 — stop_monitor() set False → keluar loop
                    break
                try:
                    _process_log_line(line, engine, responder, db, redis_client, app)
                except Exception as e:
                    logger.error(f"Monitor error: {e}", exc_info=True)

    _monitor_thread = threading.Thread(target=_run, daemon=True, name='LogMonitor')  # simpan ke baris 26
    _monitor_thread.start()  # jalankan _run() di thread terpisah (tidak block Flask/Gunicorn)
    logger.info("Log monitor started.")


def stop_monitor():
    global _running  # ubah flag baris 27 — loop di feeder.tail() lihat False lalu break
    _running = False
    logger.info("Log monitor stopping.")


# ═══════════════════════════════════════════════════════════════════════════════
# ② _process_log_line — PROSES 1 baris log
#    Input:  line (string dari LogTailer / ingest_log_lines)
#    Output: incident id (int) atau None (skip)
# ═══════════════════════════════════════════════════════════════════════════════

def _process_log_line(line: str, engine, responder, db, redis_client, app) -> Optional[int]:
    """Parse → detect → dedup → incident → respond.

    Parameter (semua dikirim dari start_monitor baris 78, atau ingest_log_lines baris 221):
      line          ← feeder.tail() — string 1 baris access.log
      engine        ← DetectionEngine() — hasil analyze() = threat
      responder     ← ResponseManager() — tulis blocklist
      db            ← SQLAlchemy — INSERT incident
      redis_client  ← Redis — heartbeat + waiver dedup
      app           ← Flask app — context thread AbuseIPDB
    """
    from app.core.log_parser import parse_log_line  # ← log_parser.py
    from app.models import Incident, SeverityLevel, IncidentStatus, DetectionRule  # ← backend/app/models — tabel PostgreSQL

    if not line or not line.strip(): # skip whitespace atau kosong
        return None

    touch_last_log_received(redis_client)  # ← helper bawah file; Dashboard baca via get_last_log_received_at

    entry = parse_log_line(line)  # ← log_parser.py ② — string → dict
    if not entry:
        return None

    threat = engine.analyze(entry)  # ← detection_engine.py analyze() — dict → threat dict atau None
    if not threat:
        return None

    skip_dedup = False  # ← variable lokal; True = lewati cek dedup 5 menit (setelah admin unblock)
    if redis_client:
        try:
            ip = threat['ip']                    # ← dari analyze() — sama dengan entry['ip']
            attack = threat['attack_type']       # ← dari analyze() — contoh 'SQL_INJECTION'
            if redis_client.exists(f"unblocked:{ip}"):  # ← key ditulis response_manager saat admin unblock
                waiver_key = f"unblock_waiver:{ip}:{attack}"
                if redis_client.set(waiver_key, '1', nx=True, ex=600):  # 1x waiver 10 menit
                    skip_dedup = True
        except Exception:
            pass

    if not skip_dedup:
        dedup_window = datetime.utcnow() - timedelta(minutes=5)  # ← variable lokal — batas waktu dedup
        recent = Incident.query.filter(  # ← query PostgreSQL tabel incidents (bukan Redis)
            Incident.source_ip == threat['ip'],
            Incident.attack_type == threat['attack_type'],
            Incident.created_at >= dedup_window,
        ).first()
        if recent:
            logger.debug(f"Dedup skip: {threat['attack_type']} from {threat['ip']} (seen within 5m)")
            return None  # sudah ada incident sama → skip

    # ── Step 4: simpan incident ke PostgreSQL → Dashboard/Incidents UI ──
    sev_map = {  # ← mapping string analyze() → enum SQLAlchemy di models
        'low': SeverityLevel.LOW,
        'medium': SeverityLevel.MEDIUM,
        'high': SeverityLevel.HIGH,
        'critical': SeverityLevel.CRITICAL,
    }
    severity_enum = sev_map.get(threat['severity'], SeverityLevel.MEDIUM)  # ← threat['severity'] dari analyze()

    rule = DetectionRule.query.filter_by(  # ← tabel detection_rules — rule DB aktif (Section 7)
        attack_type=threat['attack_type'], is_active=True,
    ).first()
    rule_id = rule.id if rule else None  # ← None kalau match baseline OWASP saja (tanpa rule DB)
    if rule:
        rule.match_count += 1  # statistik rule match di halaman Detection Rules

    incident = Incident(  # ← model SQLAlchemy — row baru tabel incidents
        source_ip=threat['ip'],              # ← dari analyze()
        attack_type=threat['attack_type'],   # ← dari analyze()
        severity=severity_enum,              # ← dari sev_map di atas
        status=IncidentStatus.NEW,             # ← enum model — incident baru
        raw_payload=threat.get('raw_payload', ''),       # ← dari analyze() — potongan payload match
        request_path=threat.get('request_path', ''),     # ← dari analyze() — biasanya entry['path']
        request_method=threat.get('request_method', ''), # ← dari analyze()
        user_agent=threat.get('user_agent', ''),         # ← dari analyze()
        response_code=threat.get('response_code'),       # ← dari analyze() — entry status_code
        rule_id=rule_id,                     # ← dari query DetectionRule di atas
    )
    db.session.add(incident)   # ← db = parameter start_monitor (SQLAlchemy)
    db.session.commit()        # ← INSERT ke PostgreSQL — setelah ini incident.id ada

    logger.info(f"[THREAT] {threat['attack_type']} from {threat['ip']} | Severity: {threat['severity']}")

    responder.respond(threat, incident.id)  # ← response_manager.py — block IP (Section 4)

    from app.services.threat_intel_service import _do_reputation_check   # ← opsional AbuseIPDB
    from app.services.notification_service import _get_setting           # ← baca setting dari DB
    if _get_setting('ABUSEIPDB_API_KEY'):  # ← skip kalau API key tidak diset
        try:
            def _rep_thread(app_ref, inc_id, ip):
                try:
                    with app_ref.app_context():
                        _do_reputation_check(inc_id, ip)
                except Exception as e:
                    logger.error(f"AbuseIPDB thread error: {e}")
            threading.Thread(  
                target=_rep_thread,                    # Function yang dijalankan thread
                args=(app, incident.id, threat['ip']), # Argument app dari start monitor, Argument — app dari start_monitor, incident.id baru dari commit 
                daemon=True,                           # True = thread akan berhenti bersama proses utama (Flask/Gunicorn)
            ).start()                                  # Jalankan thread (non-blocking) — caller tidak tunggu selesai, tidak blocking, tidak menunggu thread selesai
        except Exception as e:
            logger.warning(f"IP reputation check skipped: {e}")

    return incident.id  # return id kalau incident baru dibuat


# ═══════════════════════════════════════════════════════════════════════════════
# ③ ingest_log_lines — jalur alternatif (Railway LOG_INGEST_URL / inject-log API)
#    Input: list string lines → loop _process_log_line (pipeline sama tailer)
# ═══════════════════════════════════════════════════════════════════════════════

def ingest_log_lines(lines: List[str], app, db, redis_client=None) -> List[int]:
    """Process batch lines — same pipeline as LogTailer."""
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
                    created.append(inc_id)  # kumpulkan id incident yang baru dibuat
            except Exception as e:
                logger.error(f"ingest_log_lines error: {e}", exc_info=True)
    return created


# ═══════════════════════════════════════════════════════════════════════════════
# ④ Helper — path log + heartbeat untuk Dashboard GET /log-status
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_web_log_path(config_path: Optional[str] = None) -> str:
    """Resolve WEB_SERVER_LOG_PATH — Docker: /app/watched_logs/access.log."""
    log_path = config_path or os.getenv('WEB_SERVER_LOG_PATH', '../vuln-web/logs/access.log')
    if log_path and not os.path.isabs(log_path):
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.normpath(os.path.join(backend_dir, log_path))  # relative → absolute path
    return log_path


def touch_last_log_received(redis_client=None) -> datetime:
    """Catat waktu log terakhir diterima — dipanggil setiap _process_log_line."""
    global last_log_received_at  # ubah variable baris 28 — dibaca get_last_log_received_at() untuk Dashboard
    now = datetime.utcnow()
    last_log_received_at = now
    if redis_client:
        try:
            redis_client.set(LOG_HEARTBEAT_REDIS_KEY, now.isoformat() + 'Z', ex=86400)  # share ke worker lain
        except Exception as e:
            logger.debug(f"log heartbeat redis: {e}")
    return now


def get_last_log_received_at(redis_client=None) -> Optional[datetime]:
    """Baca heartbeat — dipakai dashboard.py log_status() → banner kuning stale > 60s."""
    if redis_client:
        try:
            raw = redis_client.get(LOG_HEARTBEAT_REDIS_KEY)
            if raw:
                s = raw.decode() if isinstance(raw, bytes) else str(raw)
                s = s.rstrip('Z')
                return datetime.fromisoformat(s)
        except Exception as e:
            logger.debug(f"log heartbeat read: {e}")
    return last_log_received_at


def get_log_file_last_activity() -> Optional[datetime]:
    """Fallback: mtime access.log kalau heartbeat Redis kosong."""
    try:
        path = resolve_web_log_path()
        if path and os.path.isfile(path):
            return datetime.utcfromtimestamp(os.path.getmtime(path))
    except Exception:
        pass
    return None
