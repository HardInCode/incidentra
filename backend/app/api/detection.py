"""
DETECTION API — 3 mode berbeda (jangan dicampur):
Ctrl+F: RULES_FLOW, INJECT_FLOW, SIMULATE_FLOW, test_payload, inject_log, simulate_attack

① POST /detection/test       — RULES_FLOW sandbox (DetectionRules.js handleTest)
   analyze() saja — TIDAK INSERT incident, TIDAK respond()

② POST /detection/inject-log  — INJECT_FLOW (admin inject baris ke access.log)
   tulis access.log → ingest_log_lines() → PIPELINE penuh (parse→analyze→INSERT→respond)

③ POST /detection/simulate    — SIMULATE_FLOW (Incidents.js handleSimulate)
   bypass log — INSERT incident manual + respond() langsung

Pasangan frontend:
  frontend/src/pages/DetectionRules.js  → /test
  frontend/src/pages/Incidents.js       → /simulate
  SimulateDialog / inject UI            → /inject-log
Pasangan core:
  backend/app/core/log_monitor.py       — PIPELINE, ingest_log_lines
  backend/app/core/detection_engine.py  — analyze()
  backend/app/core/response_manager.py  — respond()
"""
from flask import Blueprint, request, jsonify
from app.core.detection_engine import DetectionEngine, get_redis_client
from app.core.log_parser import parse_log_line

detection_bp = Blueprint('detection', __name__)
_engine = None  # singleton — rules DB di-cache di dalam DetectionEngine

from app.api.auth_middleware import verify_token, require_role


@detection_bp.before_request
def _check_auth():
    return verify_token()  # semua endpoint butuh JWT; admin-only di decorator route


def get_engine():
    """Lazy init engine — _maybe_reload_rules() baca rules_dirty dari Redis."""
    global _engine
    if _engine is None:
        _engine = DetectionEngine(redis_client=get_redis_client())
    return _engine


@detection_bp.route('/test', methods=['POST'])
@require_role('admin')
def test_payload():
    """
    RULES_FLOW sandbox — preview regex tanpa side effect.
    DetectionRules.js handleTest → api.testPayload → endpoint ini.
    """
    data = request.get_json()
    log_line = data.get('log_line', '')
    payload = data.get('payload', '')

    if log_line:
        entry = parse_log_line(log_line)  # tab Log — string access.log nginx penuh
        if not entry:
            return jsonify({'error': 'Could not parse log line'}), 400
    elif payload:
        # tab Payload — dict entry manual; query = string SQLi/XSS untuk di-regex
        entry = {
            'ip': data.get('ip', '1.2.3.4'),
            'method': data.get('method', 'GET'),
            'path': data.get('path', '/'),
            'query': payload,
            'user_agent': data.get('user_agent', 'test'),
            'status_code': 200,
            'raw': payload,
        }
    else:
        return jsonify({'error': 'Provide log_line or payload'}), 400

    engine = get_engine()  # merge: rule DB + DETECTION_PATTERNS baseline
    result = engine.analyze(entry)  # SEVERITY + attack_type di sini — tanpa DEDUP/respond

    if result:
        return jsonify({'detected': True, 'threat': result})
    return jsonify({'detected': False, 'message': 'No threat detected'})


@detection_bp.route('/inject-log', methods=['POST'])
@require_role('admin')
def inject_log():
    """
    INJECT_FLOW — demo pipeline natural lewat access.log.
    1) Tulis baris fake attack ke file log (sama path log_monitor tail)
    2) ingest_log_lines() → _process_log_line() per baris → PIPELINE penuh
    Bisa kena DEDUP kalau IP+attack_type sama dalam 5 menit.
    """
    import os
    from datetime import datetime
    from flask import current_app
    from app import db
    from app.core.log_monitor import resolve_web_log_path, ingest_log_lines

    data = request.get_json()
    attack_type = data.get('attack_type', 'SQL_INJECTION')
    ip = data.get('ip', '45.33.32.156')  # IP publik aman untuk demo

    ts = datetime.utcnow().strftime('%d/%b/%Y:%H:%M:%S +0000')
    # Template baris nginx — harus bisa di-parse parse_log_line() dan kena analyze()
    ATTACK_LOG_LINES = {
        'SQL_INJECTION': f"{ip} - - [{ts}] \"GET /search?q='+OR+1=1+UNION+SELECT+username,password+FROM+users-- HTTP/1.1\" 200 512 \"-\" \"sqlmap/1.7\"",
        'XSS': f"{ip} - - [{ts}] \"GET /search?q=<script>alert(document.cookie)</script> HTTP/1.1\" 200 1024 \"-\" \"Mozilla/5.0\"",
        'BRUTE_FORCE': '\n'.join([
            f"{ip} - - [{ts}] \"POST /login HTTP/1.1\" 401 64 \"-\" \"python-requests/2.28\""
            for _ in range(12)  # BruteForceTracker butuh ≥10 fail dalam window
        ]),
        'PATH_TRAVERSAL': f"{ip} - - [{ts}] \"GET /files?file=../../etc/passwd HTTP/1.1\" 200 256 \"-\" \"curl/7.68.0\"",
        'COMMAND_INJECTION': f"{ip} - - [{ts}] \"GET /cmd?cmd=;+cat+/etc/passwd HTTP/1.1\" 200 512 \"-\" \"Mozilla/5.0\"",
        'SCANNER': f"{ip} - - [{ts}] \"GET / HTTP/1.1\" 200 4096 \"-\" \"Nikto/2.1.6 (Evasions:None)\"",
        'LFI_RFI': f"{ip} - - [{ts}] \"GET /index.php?page=php://filter/convert.base64-encode/resource=config HTTP/1.1\" 200 2048 \"-\" \"curl/7.68.0\"",
        'FILE_UPLOAD': f'{ip} - - [{ts}] "POST /files HTTP/1.1" 302 0 "-" "Mozilla/5.0" POST_DATA:file=shell.php',
        'CSRF': f'{ip} - - [{ts}] "POST /forms HTTP/1.1" 403 128 "-" "Mozilla/5.0" POST_DATA:error=CSRF+token+missing',
    }

    log_block = ATTACK_LOG_LINES.get(attack_type, ATTACK_LOG_LINES['SCANNER'])
    log_lines = [ln for ln in log_block.split('\n') if ln.strip()]
    log_path = resolve_web_log_path()  # env WEB_LOG_PATH — shared dengan vuln-web

    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            for ln in log_lines:
                f.write(ln + '\n')
    except Exception as e:
        return jsonify({'error': f'Could not write to log file: {e}'}), 500

    app = current_app._get_current_object()
    # INJECT_FLOW step 2: jalankan PIPELINE sinkron (bukan nunggu log_monitor thread)
    created_ids = ingest_log_lines(log_lines, app, db, get_redis_client())

    if created_ids:
        msg = f'Log injected — {len(created_ids)} incident(s) created.'
    else:
        msg = (
            'Log written but no new incident (duplicate within 5 min, or not detected). '
            'Try a different IP or attack type.'
        )

    return jsonify({
        'message': msg,
        'log_lines': log_lines,
        'incident_ids': created_ids,
        'log_path': log_path,
    })


@detection_bp.route('/simulate', methods=['POST'])
@require_role('admin')
def simulate_attack():
    """
    SIMULATE_FLOW — bypass log file, langsung buat incident + respond().
    Incidents.js handleSimulate → api.simulateAttack → endpoint ini.
    Beda inject-log: tidak lewat parse_log_line / analyze() — severity hardcoded di severity_map.
    """
    from app import db
    from app.models import Incident, SeverityLevel, IncidentStatus
    from app.core.response_manager import ResponseManager
    from app.core.detection_engine import RESPONSE_ACTIONS
    from flask import current_app

    data = request.get_json()
    attack_type = data.get('attack_type', 'SQL_INJECTION')
    ip = data.get('ip', '45.33.32.156')

    ATTACK_PAYLOADS = {
        'SQL_INJECTION': "' OR 1=1 UNION SELECT username,password FROM users--",
        'XSS': '<script>alert(document.cookie)</script>',
        'BRUTE_FORCE': 'Multiple failed login attempts',
        'PATH_TRAVERSAL': '../../../etc/passwd',
        'COMMAND_INJECTION': '; cat /etc/passwd',
        'SCANNER': 'sqlmap/1.7 (https://sqlmap.org)',
        'FILE_UPLOAD': 'POST_DATA:file=webshell.php',
        'CSRF': 'POST /forms error=CSRF token missing',
    }

    payload = ATTACK_PAYLOADS.get(attack_type, data.get('payload', 'test'))
    # SIMULATE: severity preset per tipe — pipeline normal ambil dari analyze() / SEVERITY map
    severity_map = {
        'SQL_INJECTION': 'critical', 'XSS': 'high',
        'BRUTE_FORCE': 'high', 'PATH_TRAVERSAL': 'high',
        'COMMAND_INJECTION': 'critical', 'SCANNER': 'medium',
        'FILE_UPLOAD': 'high',
        'LFI_RFI': 'critical',
        'CSRF': 'medium',
    }
    sev = severity_map.get(attack_type, 'medium')
    sev_enum = {'low': SeverityLevel.LOW, 'medium': SeverityLevel.MEDIUM,
                'high': SeverityLevel.HIGH, 'critical': SeverityLevel.CRITICAL}[sev]

    # SIMULATE_FLOW step 1: INSERT incident langsung (skip log_monitor + DEDUP)
    incident = Incident(
        source_ip=ip,
        attack_type=attack_type,
        severity=sev_enum,
        status=IncidentStatus.NEW,
        raw_payload=payload[:1000],
        request_path=data.get('path', '/simulated'),
        request_method='GET',
        user_agent='Incidentra/Simulator',
    )
    db.session.add(incident)
    db.session.commit()

    # SIMULATE_FLOW step 2: respond() — block/rate-limit sesuai RESPONSE_ACTIONS[severity]
    responder = ResponseManager(db=db, redis_client=get_redis_client(), app=current_app._get_current_object())
    recommended_action = RESPONSE_ACTIONS.get(sev, 'log_and_monitor')
    responder.respond({'ip': ip, 'attack_type': attack_type, 'severity': sev,
                       'recommended_action': recommended_action}, incident.id)

    return jsonify({'message': 'Simulated attack created', 'incident_id': incident.id})
