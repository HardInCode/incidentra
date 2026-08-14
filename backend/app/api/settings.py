"""
SETTINGS API — konfigurasi runtime (PostgreSQL app_settings + env fallback).
Ctrl+F: SETTINGS_FLOW, update_settings, test_notification, SETTING_KEYS

SETTINGS_FLOW:
  Settings.js handleSave → PUT /settings/ → AppSetting table
  → detection_engine baca via settings_reader / _get_setting
  → DETECTION_LAB_MODE_UI_ONLY=ON → baseline OWASP OFF, cuma rule UI
  → ubah BRUTE_FORCE/RATE_LIMIT → rules_dirty (engine reload)

Test endpoints (admin):
  /test/notification → notification_service _send_email / _send_telegram
  /test/groq         → Groq API ping (sama provider dengan chatbot + AI explain)
  /test/abuseipdb    → AbuseIPDB key valid

Pasangan frontend: frontend/src/pages/Settings.js
Pasangan baca config: backend/app/core/settings_reader.py
Pasangan notify: backend/app/services/notification_service.py (NOTIFY)
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import AppSetting
import os
import requests as req

settings_bp = Blueprint('settings', __name__)

from app.api.auth_middleware import verify_token, require_role
from app.services.audit_service import log_audit


@settings_bp.before_request
def _check_auth():
    return verify_token()


# Whitelist key yang boleh disimpan — selain ini diabaikan saat PUT
SETTING_KEYS = [
    'GROQ_API_KEY', 'GROQ_MODEL',                    # CHATBOT_FLOW + AI explain
    'ABUSEIPDB_API_KEY',
    'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'ALERT_EMAIL', 'ADMIN_CONTACT_EMAIL',  # NOTIFY email
    'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',          # NOTIFY telegram
    'BRUTE_FORCE_THRESHOLD', 'TEMP_BLOCK_DURATION', 'RATE_LIMIT_WINDOW',  # RATE_LIMIT_FLOW
    'DETECTION_LAB_MODE_UI_ONLY',                      # RULES_FLOW lab mode
    'REPEAT_OFFENDER_THRESHOLD',
    'ESCALATING_HIGH_DURATIONS',                       # ESCALATING tiers
    'ESCALATING_CRITICAL_DURATIONS',
]
SENSITIVE = ['API_KEY', 'PASSWORD', 'TOKEN', 'SECRET']


def _get_raw(key: str) -> str:
    """DB first, env fallback — dipakai test endpoints & notification_service."""
    s = AppSetting.query.filter_by(key=key).first()
    return s.value if (s and s.value) else os.getenv(key, '')


def _mask(key: str, value: str) -> str:
    if value and any(s in key for s in SENSITIVE):
        return value[:4] + '••••••' if len(value) > 4 else '••••••'
    return value


@settings_bp.route('/', methods=['GET'])
def get_settings():
    """Settings.js load — value di-mask untuk API key/password."""
    result = {}
    for key in SETTING_KEYS:
        raw = _get_raw(key)
        s = AppSetting.query.filter_by(key=key).first()
        result[key] = {
            'value': _mask(key, raw),
            'configured': bool(raw),
            'source': 'database' if s else 'env',
        }
    return jsonify(result)


@settings_bp.route('/', methods=['PUT'])
@require_role('admin')
def update_settings():
    """SETTINGS_FLOW step 1: persist ke app_settings — empty value = hapus override DB."""
    data = request.get_json()
    for key, value in data.items():
        if key not in SETTING_KEYS:
            continue
        existing = AppSetting.query.filter_by(key=key).first()
        if not value:
            if existing:
                db.session.delete(existing)
        else:
            if existing:
                existing.value = value
            else:
                db.session.add(AppSetting(key=key, value=value))
    db.session.commit()
    # SETTINGS_FLOW step 2: flag engine reload kalau detection-related berubah
    if 'DETECTION_LAB_MODE_UI_ONLY' in data or any(
        k in data for k in ('BRUTE_FORCE_THRESHOLD', 'RATE_LIMIT_WINDOW', 'TEMP_BLOCK_DURATION')
    ):
        try:
            from app.core.detection_engine import get_redis_client
            r = get_redis_client()
            if r:
                r.set('rules_dirty', '1')
        except Exception:
            pass
    log_audit('settings.update', resource_type='settings', details={'keys': list(data.keys())})
    return jsonify({'message': 'Settings updated'})


@settings_bp.route('/test/notification', methods=['POST'])
@require_role('admin')
def test_notification():
    """NOTIFY test — Settings.js tombol Test Email/Telegram (bukan incident nyata)."""
    from app.services.notification_service import _send_email, _send_telegram
    channel = request.get_json().get('channel', 'both')
    errors = []
    if channel in ('email', 'both'):
        ok, err = _send_email(
            '[Incidentra SOC] Test Notification',
            'This is a test from Incidentra SOC. Email alerts are working.',
        )
        if not ok:
            errors.append(f'Email: {err}')
    if channel in ('telegram', 'both'):
        try:
            _send_telegram('🔔 *Incidentra SOC Test*\nTelegram alerts are working!')
        except Exception as e:
            errors.append(f'Telegram: {e}')
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    return jsonify({'success': True, 'message': 'Test notification sent'})


@settings_bp.route('/test/abuseipdb', methods=['POST'])
@require_role('admin')
def test_abuseipdb():
    key = _get_raw('ABUSEIPDB_API_KEY')
    if not key:
        return jsonify({'success': False, 'error': 'ABUSEIPDB_API_KEY not configured'}), 400
    try:
        r = req.get('https://api.abuseipdb.com/api/v2/check',
                    headers={'Key': key, 'Accept': 'application/json'},
                    params={'ipAddress': '8.8.8.8', 'maxAgeInDays': 90}, timeout=10)
        r.raise_for_status()
        score = r.json().get('data', {}).get('abuseConfidenceScore', 0)
        return jsonify({'success': True, 'message': f'API key valid. 8.8.8.8 abuse score: {score}%'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@settings_bp.route('/test/groq', methods=['POST'])
@require_role('admin')
def test_groq():
    """Test Groq — provider sama untuk CHATBOT_FLOW dan trigger_explanation."""
    data = request.get_json(silent=True) or {}

    key = data.get('api_key')
    if not key or '••••••' in key:
        key = _get_raw('GROQ_API_KEY')

    if not key:
        return jsonify({'success': False, 'error': 'GROQ_API_KEY not configured'}), 400

    selected_model = data.get('model') or _get_raw('GROQ_MODEL') or os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')

    try:
        r = req.post('https://api.groq.com/openai/v1/chat/completions',
                     headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                     json={'model': selected_model,
                           'messages': [{'role': 'user', 'content': 'Say ok'}],
                           'max_tokens': 5}, timeout=15)
        r.raise_for_status()
        return jsonify({
            'success': True,
            'message': f'Groq API key valid. Model "{selected_model}" is working.',
            'model': selected_model,
        })
    except req.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        error_detail = e.response.text if e.response else str(e)
        return jsonify({
            'success': False,
            'error': f'Model "{selected_model}" failed (HTTP {status}): {error_detail}',
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Model "{selected_model}" test failed: {str(e)}',
        }), 400
