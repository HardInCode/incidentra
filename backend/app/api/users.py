"""Admin user management — approve pending self-registrations, assign roles,
suspend/reactivate accounts, force password resets, and full CRUD for admins.
Follows the same blueprint/audit pattern as app/api/blocked_ips.py."""
import secrets
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, Incident
from app.api.auth_middleware import verify_token, require_role
from app.services.audit_service import log_audit

users_bp = Blueprint('users', __name__)

VALID_ROLES = ('admin', 'analyst')
VALID_STATUSES = ('pending', 'active', 'suspended')


@users_bp.before_request
def _check_auth():
    return verify_token()


@users_bp.route('/', methods=['GET'])
@require_role('admin')
def list_users():
    status = request.args.get('status')
    search = request.args.get('search', '')

    query = User.query
    if status:
        if status not in VALID_STATUSES:
            return jsonify({'error': f'status must be one of {VALID_STATUSES}'}), 400
        query = query.filter(User.status == status)
    if search:
        query = query.filter(
            db.or_(User.username.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        )

    users = query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])


@users_bp.route('/', methods=['POST'])
@require_role('admin')
def create_user():
    """Admin directly creates a user — status=active immediately (bypasses the self-registration
    approval flow, for provisioning teammates without going through /auth/register)."""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    role = data.get('role', 'analyst')

    if not username or not email or not password:
        return jsonify({'error': 'username, email and password are required'}), 400
    if role not in VALID_ROLES:
        return jsonify({'error': f'role must be one of {VALID_ROLES}'}), 400
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
        role=role,
        status='active',
    )
    db.session.add(user)
    db.session.commit()

    log_audit('user.create', resource_type='user', resource_id=user.id,
              details={'username': username, 'role': role})
    return jsonify(user.to_dict()), 201


@users_bp.route('/<int:user_id>', methods=['PATCH'])
@require_role('admin')
def update_user(user_id):
    """Approve a pending user (status=active + role), suspend/reactivate, or change role.
    For password resets, use POST /<id>/reset-password instead."""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    current_admin_id = request.current_user.get('user_id')

    changes = {}
    was_pending = user.status == 'pending'

    if 'role' in data:
        role = data['role']
        if role not in VALID_ROLES:
            return jsonify({'error': f'role must be one of {VALID_ROLES}'}), 400
        user.role = role
        changes['role'] = role

    if 'status' in data:
        new_status = data['status']
        if new_status not in VALID_STATUSES:
            return jsonify({'error': f'status must be one of {VALID_STATUSES}'}), 400
        if new_status != 'active' and user.id == current_admin_id:
            return jsonify({'error': 'Cannot change your own account status'}), 400
        if new_status == 'active' and was_pending and not user.role:
            return jsonify({'error': 'role is required to approve a pending user'}), 400
        user.status = new_status
        changes['status'] = new_status

    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
        changes['is_active'] = user.is_active

    if not changes:
        return jsonify({'error': 'No changes provided'}), 400

    db.session.commit()

    action = 'user.approve' if (was_pending and changes.get('status') == 'active') else 'user.update'
    log_audit(action, resource_type='user', resource_id=user.id,
              details={**changes, 'username': user.username})

    return jsonify(user.to_dict())


@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@require_role('admin')
def reset_password(user_id):
    """Force-reset a user's password. Provide 'new_password', or omit it to auto-generate one —
    the generated password is returned ONCE in the response and never stored in plaintext."""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    new_password = data.get('new_password')
    generated = not new_password
    if generated:
        new_password = secrets.token_urlsafe(10)
    elif len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    log_audit('user.reset_password', resource_type='user', resource_id=user.id,
              details={'username': user.username, 'generated': generated})

    response = {'message': f'Password reset for {user.username}', 'user': user.to_dict()}
    if generated:
        response['generated_password'] = new_password
    return jsonify(response)


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@require_role('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    current_admin_id = request.current_user.get('user_id')
    if user.id == current_admin_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    username = user.username
    # Unassign incidents rather than blocking the delete on a FK constraint.
    Incident.query.filter_by(assigned_to=user.id).update({'assigned_to': None})
    db.session.delete(user)
    db.session.commit()

    log_audit('user.delete', resource_type='user', resource_id=user_id, details={'username': username})
    return jsonify({'message': f'User {username} deleted'})
