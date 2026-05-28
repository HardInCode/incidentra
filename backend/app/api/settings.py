from flask import Blueprint, request, jsonify
from app import db
from app.models import AppSetting
import os
import requests as req

settings_bp = Blueprint('settings', __name__)

from app.api.auth_middleware import verify_token
from app.services.audit_service import log_audit

@settings_bp.before_request
def _check_auth():
    return verify_token()

SETTING_KEYS = [
    'GROQ_API_KEY', 'GROQ_MODEL',
    'ABUSEIPDB_API_KEY',
    'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'ALERT_EMAIL',
    'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
    'BRUTE_FORCE_THRESHOLD', 'TEMP_BLOCK_DURATION', 'RATE_LIMIT_WINDOW',
    'DETECTION_LAB_MODE_UI_ONLY',
]
SENSITIVE = ['API_KEY', 'PASSWORD', 'TOKEN', 'SECRET']


def _get_raw(key: str) -> str:
    """Get unmasked value — DB first, then env."""
    s = AppSetting.query.filter_by(key=key).first()
    return s.value if (s and s.value) else os.getenv(key, '')


def _mask(key: str, value: str) -> str:
    if value and any(s in key for s in SENSITIVE):
        return value[:4] + '••••••' if len(value) > 4 else '••••••'
    return value


@settings_bp.route('/', methods=['GET'])
def get_settings():
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
def update_settings():
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
def test_notification():
    from app.services.notification_service import _send_email, _send_telegram
    channel = request.get_json().get('channel', 'both')
    errors = []
    if channel in ('email', 'both'):
        try:
            _send_email('[Incidentra SOC] Test Notification',
                        'This is a test from Incidentra SOC. Email alerts are working.')
        except Exception as e:
            errors.append(f'Email: {e}')
    if channel in ('telegram', 'both'):
        try:
            _send_telegram('🔔 *Incidentra SOC Test*\nTelegram alerts are working!')
        except Exception as e:
            errors.append(f'Telegram: {e}')
    if errors:
        return jsonify({'success': False, 'errors': errors}), 400
    return jsonify({'success': True, 'message': 'Test notification sent'})


@settings_bp.route('/test/abuseipdb', methods=['POST'])
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
def test_groq():
    key = _get_raw('GROQ_API_KEY')
    if not key:
        return jsonify({'success': False, 'error': 'GROQ_API_KEY not configured'}), 400

    primary_model = _get_raw('GROQ_MODEL') or os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    
    # Same fallbacks as ai_service and chatbot
    fallback_models = [
        'llama-3.3-70b-versatile',
        'llama-3.1-8b-instant',
        'meta-llama/llama-4-scout-17b-16e-instruct',
        'meta-llama/llama-guard-4-12b',
    ]
    
    models_to_try = [primary_model] + [m for m in fallback_models if m != primary_model]
    
    last_error = None
    successful_model = None
    
    for model in models_to_try:
        try:
            r = req.post('https://api.groq.com/openai/v1/chat/completions',
                         headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                         json={'model': model,
                               'messages': [{'role': 'user', 'content': 'Say ok'}],
                               'max_tokens': 5}, timeout=15)
            r.raise_for_status()
            successful_model = model
            break
        except req.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (400, 404, 422):
                last_error = e
                continue
            return jsonify({'success': False, 'error': f'HTTP {status}: {e.response.text if e.response else str(e)}'}), 400
        except Exception as e:
            last_error = e
            continue
            
    if successful_model:
        return jsonify({
            'success': True,
            'message': f'Groq API key valid. Tested successfully with model: {successful_model}',
            'model': successful_model,
        })
    else:
        return jsonify({'success': False, 'error': f'All Groq models failed. Last error: {str(last_error)}'}), 400
