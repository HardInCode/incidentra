import json
from flask import request
from app import db
from app.models import AuditLog


def log_audit(action, resource_type=None, resource_id=None, details=None, user=None, ip_address=None):
    """Record an audit log entry. Fails silently on error to avoid breaking main flows."""
    try:
        cu = user or getattr(request, 'current_user', None) or {}
        entry = AuditLog(
            user_id=cu.get('user_id'),
            username=cu.get('username', 'system'),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=json.dumps(details) if details and not isinstance(details, str) else details,
            ip_address=ip_address or (request.remote_addr if request else None),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
