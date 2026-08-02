"""
LOGIN & SELF-REGISTRATION — JWT issue on login, pending-approval signup, anti-spam.
Ctrl+F: login, register, _make_token, _register_rate_limited, LOGIN_ERROR_CODES

Alur login (hulu → hilir):
  Login.js → api.js POST /auth/login → login() di sini → JWT
  Token diverifikasi per-request: auth_middleware.py verify_token()
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
from datetime import datetime, timedelta
from app import db
from app.models import User
from app.services.audit_service import log_audit
from app.api.auth_middleware import verify_token
from app.utils.net import get_client_ip

auth_bp = Blueprint('auth', __name__)

REGISTER_RATE_LIMIT = 5
REGISTER_RATE_WINDOW = 3600  # 1 jam

# Kode error machine-readable → frontend map ke i18n (Login.js AUTH_ERROR_I18N)
# Jangan taruh teks user-facing di sini — hanya kode stabil
LOGIN_ERROR_CODES = {
    'pending': 'account_pending',
    'suspended': 'account_suspended',
}


def _make_token(user_id, username, role):
    """Buat JWT 24 jam, ditandatangani SECRET_KEY."""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, os.getenv('SECRET_KEY', 'incidentra-secret'), algorithm='HS256')


def _register_rate_limited(ip):
    """Anti-spam register: max 5 attempt per IP per jam (Redis sliding window)."""
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
    """POST /api/auth/login — body JSON { username, password } dari Login.js."""
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()

    # Salah user ATAU salah password → error sama (security: jangan bocorkan username valid)
    if not user or not check_password_hash(user.password_hash, data.get('password', '')):
        return jsonify({'error': 'invalid_credentials'}), 401

    if user.status in LOGIN_ERROR_CODES:
        return jsonify({'error': LOGIN_ERROR_CODES[user.status]}), 403
    if not user.is_active:
        return jsonify({'error': 'account_inactive'}), 403

    token = _make_token(user.id, user.username, user.role)
    log_audit('auth.login', user={'user_id': user.id, 'username': user.username, 'role': user.role})
    return jsonify({'token': token, 'user': user.to_dict()})


@auth_bp.route('/users', methods=['GET'])
def list_users():
    """GET /api/auth/users — dropdown assign incident (bukan halaman User Management)."""
    err = verify_token()
    if err:
        return err
    if request.current_user.get('role') not in ('admin', 'analyst'):
        return jsonify({'error': 'Admin or Analyst access required'}), 403
    users = User.query.filter_by(is_active=True, status='active').order_by(User.username).all()
    return jsonify([u.to_dict() for u in users])


@auth_bp.route('/register', methods=['POST'])
def register():
    """POST /api/auth/register — self-signup; status pending sampai admin approve."""
    ip = get_client_ip(request)
    if _register_rate_limited(ip):
        return jsonify({'error': 'register_rate_limited'}), 429

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'error': 'register_fields_required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'register_password_too_short'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'username_exists'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'email_exists'}), 409

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
        'message': 'registered',
        'user': user.to_dict(),
    }), 201
