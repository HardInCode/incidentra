from flask import Blueprint, request, jsonify
from app.models import Incident, IncidentStatus

notifications_bp = Blueprint('notifications', __name__)

from app.api.auth_middleware import verify_token


@notifications_bp.before_request
def _check_auth():
    return verify_token()


@notifications_bp.route('/summary', methods=['GET'])
def notifications_summary():
    """
    In-app alert summary (no Telegram/email). unread_count = new incidents with id > since_id.
    Query: since_id (int, default 0) — client last_seen_incident_id from localStorage after mark-all-read.
    """
    since_id = request.args.get('since_id', default=0, type=int) or 0

    unread_count = Incident.query.filter(
        Incident.status == IncidentStatus.NEW,
        Incident.id > since_id,
    ).count()

    recent = (
        Incident.query.filter(Incident.status == IncidentStatus.NEW)
        .order_by(Incident.created_at.desc())
        .limit(8)
        .all()
    )

    max_new_id = (
        Incident.query.filter(Incident.status == IncidentStatus.NEW)
        .with_entities(Incident.id)
        .order_by(Incident.id.desc())
        .limit(1)
        .scalar()
    ) or 0

    return jsonify({
        'unread_count': unread_count,
        'max_new_id': max_new_id,
        'recent': [
            {
                'id': i.id,
                'attack_type': i.attack_type,
                'severity': i.severity.value if hasattr(i.severity, 'value') else i.severity,
                'source_ip': i.source_ip,
                'created_at': i.created_at.isoformat() + 'Z',
            }
            for i in recent
        ],
    })
