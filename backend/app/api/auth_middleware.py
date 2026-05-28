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
        request.current_user = payload
        return None  # OK
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired — please log in again'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401


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
