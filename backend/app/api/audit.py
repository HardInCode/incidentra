"""
AUDIT LOG API — baca jejak aksi admin/analyst (read-only).
Ctrl+F: AUDIT_FLOW, list_audit_logs

AUDIT_FLOW:
  Tulis: log_audit() dipanggil dari banyak endpoint saat aksi penting
    (login, block IP, ubah settings, approve user, ubah status incident, dll)
  Baca: AuditLog.js → GET /audit/ → list_audit_logs (admin only)

Bukan security log deteksi — itu access.log + PIPELINE.
Audit = "siapa admin melakukan apa kapan" untuk compliance/accountability.

Pasangan frontend: frontend/src/pages/AuditLog.js
Pasangan tulis: app/services/audit_service.py log_audit()
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models import AuditLog
from app.api.auth_middleware import verify_token, require_role

audit_bp = Blueprint('audit', __name__)


@audit_bp.before_request
def _check_auth():
    return verify_token()


@audit_bp.route('/', methods=['GET'])
@require_role('admin')  # cuma admin — analyst tidak lihat audit trail
def list_audit_logs():
    """AUDIT_FLOW read — filter by user, action, date range."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    username = request.args.get('user')
    action = request.args.get('action')  # e.g. auth.login, blocked_ip.unblock, settings.update
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = AuditLog.query

    if username:
        query = query.filter(AuditLog.username.ilike(f'%{username}%'))
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp <= dt_to)
        except ValueError:
            pass

    query = query.order_by(AuditLog.timestamp.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'logs': [log.to_dict() for log in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    })
