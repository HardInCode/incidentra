import jwt
import os
from functools import wraps
from flask import request, jsonify


def verify_token():
    """
    Call from blueprint before_request handlers.
    Returns a 401 Response if auth fails, None if OK.
    """
    if request.method == 'OPTIONS':
        return None  # Allow CORS preflight

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401

    token = auth_header.split(' ', 1)[1]
    try:
        payload = jwt.decode(
            token,
            os.getenv('SECRET_KEY', 'incidentra-secret'),
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired — please log in again'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Re-check live account status on every request — catches accounts that were
    # suspended (or left pending) after a token was already issued.
    from app.models import User
    user = User.query.get(payload.get('user_id'))
    if not user or not user.is_active:
        return jsonify({'error': 'Account is inactive — please log in again'}), 401
    if user.status == 'pending':
        return jsonify({'error': 'Akun menunggu approval admin'}), 403
    if user.status == 'suspended':
        return jsonify({'error': 'Akun Anda disuspend. Silakan hubungi administrator.'}), 403

    request.current_user = payload
    return None  # OK


# REVISI 3A: decorator untuk role-based access control
def require_role(*roles):
    """
    Decorator to enforce role-based access control.
    Usage: @require_role('admin') or @require_role('admin', 'analyst')
    Must be applied AFTER the route decorator, and verify_token must run first
    (via before_request).
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(request, 'current_user', {})
            if user.get('role') not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
