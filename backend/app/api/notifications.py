"""
IN-APP NOTIFICATIONS — bell icon di Layout (bukan email/Telegram).
Ctrl+F: NOTIFY_INAPP_FLOW, notifications_summary

NOTIFY_INAPP_FLOW:
  PIPELINE INSERT incident (status=new) → NotificationBell poll GET /notifications/summary
  → unread_count = incident.id > last_seen_id (localStorage)
  → toast + sound kalau unread naik

Bedakan dengan NOTIFY (email/Telegram):
  NOTIFY = response_manager → notification_service._do_notify (critical + repeat offender)
  NOTIFY_INAPP = semua incident status=new, cuma di UI bell

Pasangan frontend: frontend/src/components/shared/NotificationBell.js
Pasangan email/Telegram: backend/app/services/notification_service.py (NOTIFY)
"""
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
    NOTIFY_INAPP_FLOW — NotificationBell.js fetchSummary() tiap 30 detik.
    Query since_id = localStorage sme_notif_last_seen_id (mark-all-read).
    """
    since_id = request.args.get('since_id', default=0, type=int) or 0

    # unread = incident NEW dengan id lebih besar dari yang sudah user "lihat"
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
