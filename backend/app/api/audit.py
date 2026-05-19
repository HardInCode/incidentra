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
@require_role('admin')
def list_audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    username = request.args.get('user')
    action = request.args.get('action')
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
