from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
from datetime import datetime, timedelta
from app import db
from app.models import User
from app.services.audit_service import log_audit
from app.api.auth_middleware import verify_token

auth_bp = Blueprint('auth', __name__)

REGISTER_RATE_LIMIT = 5  # max attempts per IP per hour
REGISTER_RATE_WINDOW = 3600  # seconds

# Messages kept separate from generic "Invalid credentials" — these are account-state
# rejections (not a hint about whether the username/password itself was wrong).
STATUS_MESSAGES = {
    'pending': 'Akun menunggu approval admin. Silakan hubungi administrator.',
    'suspended': 'Akun Anda disuspend. Silakan hubungi administrator.',
}


def _make_token(user_id, username, role):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, os.getenv('SECRET_KEY', 'incidentra-secret'), algorithm='HS256')


def _register_rate_limited(ip):
    """Max REGISTER_RATE_LIMIT attempts per IP per REGISTER_RATE_WINDOW seconds.
    Reuses the same Redis sliding-window pattern as BruteForceTracker (detection_engine.py).
    Fails open (allows the request) if Redis is unavailable, consistent with other Redis usage
    in this codebase (e.g. get_redis_client() callers in blocked_ips.py).
    """
    from app.core.detection_engine import get_redis_client, BruteForceTracker
    tracker = BruteForceTracker(
        redis_client=get_redis_client(),
        window_seconds=REGISTER_RATE_WINDOW,
        threshold=REGISTER_RATE_LIMIT,
    )
    attempts = tracker.record_attempt(ip, '/auth/register')
    return attempts > REGISTER_RATE_LIMIT


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    # Generic error for missing user / wrong password — never reveal which one failed.
    if not user or not check_password_hash(user.password_hash, data.get('password', '')):
        return jsonify({'error': 'Invalid credentials'}), 401
    if user.status in STATUS_MESSAGES:
        return jsonify({'error': STATUS_MESSAGES[user.status]}), 403
    if not user.is_active:
        return jsonify({'error': 'Akun tidak aktif. Silakan hubungi administrator.'}), 403
    token = _make_token(user.id, user.username, user.role)
    log_audit('auth.login', user={'user_id': user.id, 'username': user.username, 'role': user.role})
    return jsonify({'token': token, 'user': user.to_dict()})


@auth_bp.route('/users', methods=['GET'])
def list_users():
    err = verify_token()
    if err:
        return err
    if request.current_user.get('role') not in ('admin', 'analyst'):
        return jsonify({'error': 'Admin or Analyst access required'}), 403
    users = User.query.filter_by(is_active=True, status='active').order_by(User.username).all()
    return jsonify([u.to_dict() for u in users])


@auth_bp.route('/register', methods=['POST'])
def register():
    """Self-registration. New accounts start as status=pending / role=None — no access until
    an admin approves them via the User Management panel (see app/api/users.py)."""
    ip = request.remote_addr or 'unknown'
    if _register_rate_limited(ip):
        return jsonify({'error': 'Too many registration attempts. Please try again later.'}), 429

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'error': 'username, email and password are required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=None,
        status='pending',
    )
    db.session.add(user)
    db.session.commit()

    log_audit(
        'auth.register',
        resource_type='user',
        resource_id=user.id,
        user={'user_id': None, 'username': username, 'role': None},
        details={'status': 'pending'},
        ip_address=ip,
    )

    return jsonify({
        'message': 'Registration submitted. An administrator must approve your account before you can log in.',
        'user': user.to_dict(),
    }), 201
