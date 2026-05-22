import json
import os

from flask import Blueprint, jsonify

from config import BLOCKED_IPS_FILE, RATE_LIMITED_FILE

api_bp = Blueprint('api', __name__)


def _load_json_file(path):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


@api_bp.route('/api/status')
def api_status():
    blocked_data = _load_json_file(BLOCKED_IPS_FILE)
    rate_data = _load_json_file(RATE_LIMITED_FILE)
    return jsonify({
        'blocked_ips': blocked_data.get('blocked', []),
        'rate_limited_ips': rate_data.get('rate_limited', []),
        'blocked_ips_updated': blocked_data.get('updated_at'),
        'rate_limited_updated': rate_data.get('updated_at'),
    })
