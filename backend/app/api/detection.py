from flask import Blueprint, request, jsonify
from app.core.detection_engine import DetectionEngine, get_redis_client
from app.core.log_parser import parse_log_line

detection_bp = Blueprint('detection', __name__)
_engine = None

from app.api.auth_middleware import verify_token

@detection_bp.before_request
def _check_auth():
    return verify_token()


def get_engine():
    global _engine
    if _engine is None:
        _engine = DetectionEngine(redis_client=get_redis_client())
    return _engine


@detection_bp.route('/test', methods=['POST'])
def test_payload():
    """Test a payload or log line against detection engine."""
    data = request.get_json()
    log_line = data.get('log_line', '')
    payload = data.get('payload', '')

    if log_line:
        entry = parse_log_line(log_line)
        if not entry:
            return jsonify({'error': 'Could not parse log line'}), 400
    elif payload:
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

    engine = get_engine()
    result = engine.analyze(entry)

    if result:
        return jsonify({'detected': True, 'threat': result})
    return jsonify({'detected': False, 'message': 'No threat detected'})


@detection_bp.route('/inject-log', methods=['POST'])
def inject_log():
    """
    BUG 5 FIX — MODE B 'Log Injection':
    Write a fake attack log line to the shared log file so the backend log monitor
    picks it up naturally through the full detection pipeline.
    """
    import os
    from datetime import datetime
    from flask import current_app
    from app import db
    from app.core.log_monitor import resolve_web_log_path, ingest_log_lines
    from app.core.detection_engine import get_redis_client

    data = request.get_json()
    attack_type = data.get('attack_type', 'SQL_INJECTION')
    ip = data.get('ip', '45.33.32.156')  # scanme.nmap.org — safe public test IP

    ts = datetime.utcnow().strftime('%d/%b/%Y:%H:%M:%S +0000')
    ATTACK_LOG_LINES = {
        'SQL_INJECTION': f"{ip} - - [{ts}] \"GET /search?q='+OR+1=1+UNION+SELECT+username,password+FROM+users-- HTTP/1.1\" 200 512 \"-\" \"sqlmap/1.7\"",
        'XSS': f"{ip} - - [{ts}] \"GET /search?q=<script>alert(document.cookie)</script> HTTP/1.1\" 200 1024 \"-\" \"Mozilla/5.0\"",
        'BRUTE_FORCE': '\n'.join([
            f"{ip} - - [{ts}] \"POST /login HTTP/1.1\" 401 64 \"-\" \"python-requests/2.28\""
            for _ in range(12)
        ]),
        'PATH_TRAVERSAL': f"{ip} - - [{ts}] \"GET /files?file=../../etc/passwd HTTP/1.1\" 200 256 \"-\" \"curl/7.68.0\"",
        'COMMAND_INJECTION': f"{ip} - - [{ts}] \"GET /cmd?cmd=;+cat+/etc/passwd HTTP/1.1\" 200 512 \"-\" \"Mozilla/5.0\"",
        'SCANNER': f"{ip} - - [{ts}] \"GET / HTTP/1.1\" 200 4096 \"-\" \"Nikto/2.1.6 (Evasions:None)\"",
        'LFI_RFI': f"{ip} - - [{ts}] \"GET /index.php?page=php://filter/convert.base64-encode/resource=config HTTP/1.1\" 200 2048 \"-\" \"curl/7.68.0\"",
        'FILE_UPLOAD': f'{ip} - - [{ts}] "POST /files HTTP/1.1" 302 0 "-" "Mozilla/5.0" POST_DATA:file=shell.php',
    }

    log_block = ATTACK_LOG_LINES.get(attack_type, ATTACK_LOG_LINES['SCANNER'])
    log_lines = [ln for ln in log_block.split('\n') if ln.strip()]
    log_path = resolve_web_log_path()

    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            for ln in log_lines:
                f.write(ln + '\n')
    except Exception as e:
        return jsonify({'error': f'Could not write to log file: {e}'}), 500

    app = current_app._get_current_object()
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
def simulate_attack():
    """Inject a simulated attack into the detection pipeline."""
    from app import db
    from app.models import Incident, SeverityLevel, IncidentStatus
    from app.core.response_manager import ResponseManager

    data = request.get_json()
    attack_type = data.get('attack_type', 'SQL_INJECTION')
    ip = data.get('ip', '45.33.32.156')  # scanme.nmap.org — safe public test IP

    ATTACK_PAYLOADS = {
        'SQL_INJECTION': "' OR 1=1 UNION SELECT username,password FROM users--",
        'XSS': '<script>alert(document.cookie)</script>',
        'BRUTE_FORCE': 'Multiple failed login attempts',
        'PATH_TRAVERSAL': '../../../etc/passwd',
        'COMMAND_INJECTION': '; cat /etc/passwd',
        'SCANNER': 'sqlmap/1.7 (https://sqlmap.org)',
        'FILE_UPLOAD': 'POST_DATA:file=webshell.php',
    }

    payload = ATTACK_PAYLOADS.get(attack_type, data.get('payload', 'test'))
    severity_map = {
        'SQL_INJECTION': 'critical', 'XSS': 'high',
        'BRUTE_FORCE': 'high', 'PATH_TRAVERSAL': 'high',
        'COMMAND_INJECTION': 'critical', 'SCANNER': 'medium',
        'FILE_UPLOAD': 'high',
        'LFI_RFI': 'critical',
    }
    sev = severity_map.get(attack_type, 'medium')
    sev_enum = {'low': SeverityLevel.LOW, 'medium': SeverityLevel.MEDIUM,
                'high': SeverityLevel.HIGH, 'critical': SeverityLevel.CRITICAL}[sev]

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

    from app.core.response_manager import ResponseManager
    from app.core.detection_engine import get_redis_client, RESPONSE_ACTIONS
    from flask import current_app
    responder = ResponseManager(db=db, redis_client=get_redis_client(), app=current_app._get_current_object())
    # BUG 6 FIX: Use the correct severity → action mapping, not hardcoded 'temporary_block'
    recommended_action = RESPONSE_ACTIONS.get(sev, 'log_and_monitor')
    responder.respond({'ip': ip, 'attack_type': attack_type, 'severity': sev,
                       'recommended_action': recommended_action}, incident.id)

    return jsonify({'message': 'Simulated attack created', 'incident_id': incident.id})
