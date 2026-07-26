"""
INTERNAL SERVICE-TO-SERVICE API — decoupled vuln-web log/state transport.
SIDANG Ctrl+F: ingest_logs, get_blocklist, X-Internal-Token

Only exists for the "separate domain" deployment topology (see railway/README.md,
"Running vuln-web on its own domain"), where vuln-web runs as its own standalone
Railway service/domain instead of being mounted inside the same container as this
backend (railway/core/wsgi.py's DispatcherMiddleware /lab option). In that topology
vuln-web can no longer share a filesystem with this backend, so it pushes/pulls the
exact same state over HTTP instead:

  - POST /logs      — vuln-web pushes each access-log line here instead of appending
                       it to a shared file. Appended to the SAME local file this
                       backend's log monitor already tails (WEB_SERVER_LOG_PATH) — the
                       detection pipeline itself is completely unchanged.
  - GET  /blocklist  — vuln-web polls this instead of reading blocked_ips.json /
                       rate_limited.json off a shared volume.

Not used at all by local Docker Compose or the merged /lab topology — both keep using
the real shared file, zero behavior change. Protected by a shared-secret header
(INTERNAL_API_TOKEN) rather than user JWTs, since the caller is another service, not a
logged-in user. If INTERNAL_API_TOKEN is unset (the default), every request here is
rejected — this endpoint is opt-in only.
"""
import os

from flask import Blueprint, current_app, jsonify, request

internal_bp = Blueprint('internal', __name__)


@internal_bp.before_request
def _check_internal_token():
    expected = current_app.config.get('INTERNAL_API_TOKEN', '')
    if not expected:
        return jsonify({'error': 'Internal API disabled (INTERNAL_API_TOKEN not set)'}), 404
    got = request.headers.get('X-Internal-Token', '')
    if got != expected:
        return jsonify({'error': 'Unauthorized'}), 401


@internal_bp.route('/logs', methods=['POST'])
def ingest_logs():
    """Append raw access-log line(s) pushed by a decoupled vuln-web service to the
    same file this backend's log monitor tails — it picks them up exactly as if they'd
    been written locally (identical to the shared-volume behavior, different transport)."""
    from app.core.log_monitor import resolve_web_log_path

    data = request.get_json(silent=True) or {}
    lines = data.get('lines')
    if lines is None:
        line = data.get('line')
        lines = [line] if line else []
    lines = [ln for ln in lines if isinstance(ln, str) and ln.strip()]

    if not lines:
        return jsonify({'error': 'Provide "line" or "lines"'}), 400

    log_path = resolve_web_log_path()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            for ln in lines:
                f.write(ln + '\n')
    except Exception as e:
        return jsonify({'error': f'Could not write to log file: {e}'}), 500

    return jsonify({'received': len(lines)})


@internal_bp.route('/blocklist', methods=['GET'])
def get_blocklist():
    """Current blocked IPs + rate-limited IPs, read straight from the DB / this
    backend's own local state — the same data vuln-web would otherwise read directly
    off blocked_ips.json / rate_limited.json on a shared volume."""
    from datetime import datetime
    from app.models import BlockedIP
    from app.core.response_manager import _read_rate_limited_data

    now = datetime.utcnow()
    blocked = BlockedIP.query.filter_by(is_whitelist=False).all()
    active_ips = [
        b.ip_address for b in blocked
        if b.block_type == 'permanent' or (b.expire_time and b.expire_time > now)
    ]

    rate_data = _read_rate_limited_data()

    return jsonify({
        'blocked': active_ips,
        'rate_limited': rate_data.get('rate_limited', []),
        'limits': rate_data.get('limits', {}),
        'updated_at': now.isoformat(),
    })
