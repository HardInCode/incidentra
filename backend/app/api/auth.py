"""
LOGIN & SELF-REGISTRATION — JWT issue on login, pending-approval signup, anti-spam.
Ctrl+F: LOGIN_FLOW, REGISTER_FLOW, FORGOT_PASSWORD_FLOW, login, register, _make_token

LOGIN_FLOW:
  Login.js → POST /auth/login → login() → JWT → auth_middleware verify_token()

REGISTER_FLOW:
  Login.js register → POST /auth/register → status=pending, role=null
  → admin Users.js PATCH /users/:id { status:active, role:analyst } → bisa login

FORGOT_PASSWORD_FLOW:
  Login.js forgot → POST /auth/forgot-password → email reset link
  → /reset-password?token=… → POST /auth/reset-password

GET /auth/users = dropdown assign incident (bukan User Management — itu users.py)
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from app import db
from app.models import User, PasswordResetToken
from app.services.audit_service import log_audit
from app.api.auth_middleware import verify_token
from app.utils.net import get_client_ip
from app.utils.password_policy import validate_password

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

REGISTER_RATE_LIMIT = 5
REGISTER_RATE_WINDOW = 3600  # 1 jam
FORGOT_RATE_LIMIT = 5
FORGOT_RATE_WINDOW = 3600
RESET_TOKEN_TTL = timedelta(hours=1)

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


def _forgot_rate_limited(ip):
    """Anti-spam forgot-password: max 5 attempt per IP per jam."""
    from app.core.detection_engine import get_redis_client, BruteForceTracker
    tracker = BruteForceTracker(
        redis_client=get_redis_client(),
        window_seconds=FORGOT_RATE_WINDOW,
        threshold=FORGOT_RATE_LIMIT,
    )
    attempts = tracker.record_attempt(ip, '/auth/forgot-password')
    return attempts > FORGOT_RATE_LIMIT


def _hash_reset_token(raw_token: str) -> str:
    pepper = os.getenv('SECRET_KEY', 'incidentra-secret')
    return hashlib.sha256(f'{pepper}:{raw_token}'.encode()).hexdigest()


def _frontend_reset_url(raw_token: str) -> str:
    from app.services.notification_service import _frontend_base_url
    base = _frontend_base_url().rstrip('/')
    return f'{base}/reset-password?token={raw_token}'


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
    """
    REGISTER_FLOW step 1 — self-signup; tidak bisa login sampai admin approve.
    Rate limit 5/IP/jam via BruteForceTracker (Redis).
    """
    ip = get_client_ip(request)
    if _register_rate_limited(ip):
        return jsonify({'error': 'register_rate_limited'}), 429

    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'error': 'register_fields_required'}), 400
    ok, policy_err = validate_password(password)
    if not ok:
        return jsonify({'error': policy_err}), 400
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


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    FORGOT_PASSWORD_FLOW step 1 — kirim reset link ke email terdaftar.
    Selalu return 200 generik (jangan bocorkan apakah email ada).
    """
    ip = get_client_ip(request)
    if _forgot_rate_limited(ip):
        return jsonify({'error': 'forgot_rate_limited'}), 429

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'forgot_email_required'}), 400

    user = User.query.filter(db.func.lower(User.email) == email).first()
    if user and user.is_active and user.status == 'active':
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_reset_token(raw_token)
        PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).delete()
        reset_row = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + RESET_TOKEN_TTL,
        )
        db.session.add(reset_row)
        db.session.commit()

        reset_url = _frontend_reset_url(raw_token)
        from app.services.notification_service import send_password_reset_email
        ok, err = send_password_reset_email(user.email, reset_url, user.username)
        if not ok:
            logger.warning(f"Password reset email failed for {user.username}: {err}")
            if os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG', '').lower() == 'true':
                return jsonify({
                    'message': 'reset_email_sent',
                    'dev_reset_url': reset_url,
                    'email_error': err,
                })

        log_audit(
            'auth.forgot_password',
            resource_type='user',
            resource_id=user.id,
            user={'user_id': None, 'username': user.username, 'role': user.role},
            ip_address=ip,
        )

    return jsonify({'message': 'reset_email_sent'})


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """FORGOT_PASSWORD_FLOW step 2 — token + password baru."""
    data = request.get_json() or {}
    raw_token = (data.get('token') or '').strip()
    password = data.get('password') or ''

    if not raw_token:
        return jsonify({'error': 'reset_token_required'}), 400
    ok, policy_err = validate_password(password)
    if not ok:
        return jsonify({'error': policy_err}), 400

    token_hash = _hash_reset_token(raw_token)
    reset_row = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
    if not reset_row or reset_row.used_at or reset_row.expires_at < datetime.utcnow():
        return jsonify({'error': 'reset_token_invalid'}), 400

    user = User.query.get(reset_row.user_id)
    if not user or not user.is_active or user.status != 'active':
        return jsonify({'error': 'reset_token_invalid'}), 400

    user.password_hash = generate_password_hash(password)
    reset_row.used_at = datetime.utcnow()
    PasswordResetToken.query.filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != reset_row.id,
        PasswordResetToken.used_at.is_(None),
    ).delete()
    db.session.commit()

    log_audit(
        'auth.reset_password',
        resource_type='user',
        resource_id=user.id,
        user={'user_id': user.id, 'username': user.username, 'role': user.role},
    )
    return jsonify({'message': 'password_reset_success'})


@auth_bp.route('/support-contact', methods=['GET'])
def support_contact():
    """Public email for login-page help icon — reads core env/DB, no auth required."""
    from app.services.notification_service import _get_setting
    email = (
        _get_setting('ADMIN_CONTACT_EMAIL')
        or _get_setting('ALERT_EMAIL')
        or os.getenv('DEMO_ADMIN_EMAIL', 'admin@incidentra.local')
    ).strip()
    return jsonify({'email': email})
