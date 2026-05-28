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


def _make_token(user_id, username, role):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, os.getenv('SECRET_KEY', 'sme-guard-secret'), algorithm='HS256')


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if not user or not check_password_hash(user.password_hash, data.get('password', '')):
        return jsonify({'error': 'Invalid credentials'}), 401
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
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return jsonify([u.to_dict() for u in users])


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'error': 'Username already exists'}), 409
    user = User(
        username=data['username'],
        email=data.get('email', ''),
        password_hash=generate_password_hash(data['password']),
        role='analyst',
    )
    db.session.add(user)
    db.session.commit()
    token = _make_token(user.id, user.username, user.role)
    return jsonify({'token': token, 'user': user.to_dict()}), 201
