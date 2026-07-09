"""
INCIDENTS API — list/detail, status, notes, AI explanation trigger, simulate/export.
SIDANG Ctrl+F: trigger_explanation, simulate
"""
from flask import Blueprint, request, jsonify
import logging
import json
import re
import os

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from sqlalchemy import case
from app import db
from app.models import Incident, IncidentNote, IncidentStatus, SeverityLevel, User
from app.services.audit_service import log_audit

incidents_bp = Blueprint('incidents', __name__)

from app.api.auth_middleware import verify_token, require_role


def _parse_filter_datetime(value: str) -> datetime | None:
    """Parse API date_from/date_to to naive UTC for DB comparison (created_at is naive UTC)."""
    if not value or not str(value).strip():
        return None
    try:
        raw = str(value).strip()
        if raw.endswith('Z'):
            raw = raw[:-1] + '+00:00'
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None

@incidents_bp.before_request
def _check_auth():
    return verify_token()


def _apply_incident_filters(query, args):
    """Apply list/export filters shared between list and CSV export."""
    severity = args.get('severity')
    status = args.get('status')
    attack_type = args.get('attack_type')
    search = args.get('search', '')
    date_from = args.get('date_from')
    date_to = args.get('date_to')

    if severity:
        try:
            query = query.filter(Incident.severity == SeverityLevel(severity))
        except ValueError:
            pass
    if status:
        try:
            query = query.filter(Incident.status == IncidentStatus(status))
        except ValueError:
            pass
    status_in = args.get('status_in')
    if status_in and not status:
        raw_values = [s.strip() for s in status_in.split(',') if s.strip()]
        enums = []
        for val in raw_values:
            try:
                enums.append(IncidentStatus(val))
            except ValueError:
                pass
        if enums:
            query = query.filter(Incident.status.in_(enums))
    # Explicit export/list scope from SOC pages (ongoing vs all archive)
    list_scope = (args.get('list_scope') or '').strip().lower()
    if list_scope == 'ongoing' and not status and not status_in:
        query = query.filter(
            Incident.status.in_([IncidentStatus.NEW, IncidentStatus.INVESTIGATING])
        )
    if attack_type:
        query = query.filter(Incident.attack_type == attack_type)
    if search:
        query = query.filter(
            db.or_(
                Incident.source_ip.ilike(f'%{search}%'),
                Incident.attack_type.ilike(f'%{search}%'),
                Incident.request_path.ilike(f'%{search}%'),
            )
        )
    dt_from = _parse_filter_datetime(date_from)
    if dt_from is not None:
        query = query.filter(Incident.created_at >= dt_from)
    dt_to = _parse_filter_datetime(date_to)
    if dt_to is not None:
        query = query.filter(Incident.created_at <= dt_to)
    return query


@incidents_bp.route('/', methods=['GET'])
def list_incidents():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc')

    query = _apply_incident_filters(Incident.query, request.args)

    # Sorting
    if sort_by == 'severity':
        severity_order = case(
            (Incident.severity == SeverityLevel.CRITICAL, 4),
            (Incident.severity == SeverityLevel.HIGH, 3),
            (Incident.severity == SeverityLevel.MEDIUM, 2),
            (Incident.severity == SeverityLevel.LOW, 1),
            else_=0,
        )
        order = severity_order.asc() if sort_dir == 'asc' else severity_order.desc()
        query = query.order_by(order)
    else:
        col_map = {
            'created_at': Incident.created_at,
            'status': Incident.status,
            'source_ip': Incident.source_ip,
            'attack_type': Incident.attack_type,
        }
        sort_col = col_map.get(sort_by, Incident.created_at)
        if sort_dir == 'asc':
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'incidents': [i.to_dict() for i in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
        'per_page': per_page,
    })


@incidents_bp.route('/bulk-status', methods=['PATCH'])
@require_role('admin', 'analyst')
def bulk_update_status():
    """Update status for multiple incidents. Admin only."""
    data = request.get_json() or {}
    ids = data.get('ids') or []
    new_status = data.get('status')
    if not ids or not new_status:
        return jsonify({'error': 'ids and status are required'}), 400
    if not isinstance(ids, list):
        return jsonify({'error': 'ids must be a list'}), 400
    try:
        status_enum = IncidentStatus(new_status)
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400

    updated = []
    for incident_id in ids:
        try:
            incident_id = int(incident_id)
        except (TypeError, ValueError):
            continue
        incident = Incident.query.get(incident_id)
        if not incident:
            continue
        previous = incident.status.value
        incident.status = status_enum
        if new_status == 'resolved':
            incident.resolved_at = datetime.utcnow()
        updated.append(incident_id)
        log_audit(
            'incident.status_change',
            resource_type='incident',
            resource_id=incident_id,
            details={'status': new_status, 'previous': previous, 'bulk': True},
        )

    db.session.commit()
    return jsonify({
        'message': f'Updated {len(updated)} incident(s)',
        'updated': updated,
        'status': new_status,
    })


@incidents_bp.route('/<int:incident_id>', methods=['GET'])
def get_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    return jsonify(incident.to_dict(include_logs=True))


@incidents_bp.route('/<int:incident_id>/status', methods=['PUT'])
def update_status(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    data = request.get_json()
    new_status = data.get('status')

    try:
        previous = incident.status.value
        incident.status = IncidentStatus(new_status)
        if new_status == 'resolved':
            incident.resolved_at = datetime.utcnow()
        db.session.commit()
        log_audit(
            'incident.status_change',
            resource_type='incident',
            resource_id=incident_id,
            details={'status': new_status, 'previous': previous},
        )
        return jsonify({'message': 'Status updated', 'status': new_status})
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400


@incidents_bp.route('/<int:incident_id>/assign', methods=['PUT'])
def assign_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    data = request.get_json() or {}
    assigned_to = data.get('assigned_to')

    if assigned_to is not None:
        user = User.query.get(assigned_to)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        incident.assigned_to = assigned_to
    else:
        incident.assigned_to = None

    db.session.commit()
    log_audit(
        'incident.assign',
        resource_type='incident',
        resource_id=incident_id,
        details={'assigned_to': assigned_to},
    )
    return jsonify({'message': 'Assignment updated', 'assigned_to': incident.assigned_to})


@incidents_bp.route('/<int:incident_id>/notes', methods=['POST'])
def add_note(incident_id):
    Incident.query.get_or_404(incident_id)
    data = request.get_json()
    note = IncidentNote(
        incident_id=incident_id,
        note_content=data.get('content', ''),
        created_by=request.current_user.get('username', 'unknown'),
    )
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@incidents_bp.route('/<int:incident_id>/explain', methods=['POST'])
def trigger_explanation(incident_id):
    """
    Always runs synchronously — explanation is in the response body.
    No Celery, no polling. Uses Groq with fallback chain.
    Falls back to rich static explanation if GROQ_API_KEY is not set.
    Pass { "force": true } to delete an existing explanation and regenerate.
    """
    incident = Incident.query.get_or_404(incident_id)

    # Read body once — used for both lang and force params
    body = request.get_json(silent=True) or {}
    lang = body.get('language') or request.args.get('lang') or 'en'
    force = body.get('force', False)

    if incident.explanation:
        if not force:
            return jsonify({'message': 'Already exists', 'explanation': incident.explanation.to_dict()})
        # Force regenerate: delete existing and re-generate
        db.session.delete(incident.explanation)
        db.session.commit()
        db.session.refresh(incident)

    from app.services.ai_service import build_prompt, _call_groq_with_fallback, _save_fallback_explanation
    from app.models import IncidentExplanation

    api_key = os.getenv('GROQ_API_KEY', '')
    if not api_key:
        _save_fallback_explanation(incident_id)
        db.session.refresh(incident)
        return jsonify({
            'message': 'Generated (no API key — static fallback).',
            'explanation': incident.explanation.to_dict() if incident.explanation else None,
        })

    try:
        prompt = build_prompt(incident.to_dict(), language=lang)
        raw, model_used = _call_groq_with_fallback(prompt, max_tokens=600)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            data = json.loads(match.group(0)) if match else {}


        explanation = IncidentExplanation(
            incident_id=incident_id,
            ai_summary=data.get('ai_summary', 'Unavailable.'),
            threat_explanation=data.get('threat_explanation', ''),
            recommended_actions=data.get('recommended_actions', ''),
            mitre_technique=data.get('mitre_technique', ''),
            model_used=model_used,
        )
        db.session.add(explanation)
        db.session.commit()
        db.session.refresh(incident)
        return jsonify({
            'message': f'Generated via {model_used}.',
            'explanation': incident.explanation.to_dict(),
        })
    except Exception as e:
        logger.error(f"Groq failed for incident {incident_id}: {e}")
        _save_fallback_explanation(incident_id)
        db.session.refresh(incident)
        return jsonify({
            'message': 'Generated (Groq unavailable — static fallback).',
            'explanation': incident.explanation.to_dict() if incident.explanation else None,
        })


@incidents_bp.route('/export', methods=['GET'])
def export_incidents():
    """Export incidents as CSV. Admin and analyst. Uses same filters as list."""
    if request.current_user.get('role') not in ('admin', 'analyst'):
        return jsonify({'error': 'Insufficient permissions'}), 403
    import csv
    import io
    query = _apply_incident_filters(Incident.query, request.args)
    incidents = query.order_by(Incident.created_at.desc()).limit(10000).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Source IP', 'Attack Type', 'Severity', 'Status', 'Path', 'Country'])
    for i in incidents:
        writer.writerow([i.id, i.created_at, i.source_ip, i.attack_type, i.severity.value, i.status.value, i.request_path, i.country_code or ''])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=incidents.csv'}
    )
