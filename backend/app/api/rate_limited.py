import os
from urllib.parse import unquote

from flask import Blueprint, request, jsonify

from app.api.auth_middleware import verify_token, require_role
from app.services.audit_service import log_audit
from app.core.response_manager import (
    _read_rate_limited_data,
    clear_rate_limit_entry,
    get_rate_limit_policy_for_ip,
    get_rate_limit_redis_ttl,
    update_rate_limit_entry,
)
from app.core.detection_engine import get_redis_client

rate_limited_bp = Blueprint('rate_limited', __name__)


@rate_limited_bp.before_request
def _check_auth():
    return verify_token()


def _window_seconds():
    return int(os.getenv('RATE_LIMIT_WINDOW', 60))


def _max_requests():
    return int(os.getenv('RATE_LIMIT_MAX_REQUESTS', 10))


def _build_items(ips, data, redis_client):
    updated_at = data.get('updated_at')
    items = []
    for ip in ips:
        policy = get_rate_limit_policy_for_ip(data, ip)
        ttl = get_rate_limit_redis_ttl(redis_client, ip)
        items.append({
            'ip_address': ip,
            'listed_at': updated_at,
            'ttl_seconds': ttl,
            'window_seconds': policy['window_seconds'],
            'max_requests': policy['max_requests'],
        })
    return items


@rate_limited_bp.route('/', methods=['GET'])
def list_rate_limited():
    data = _read_rate_limited_data()
    redis_client = get_redis_client()
    items = _build_items(data.get('rate_limited', []), data, redis_client)

    search = request.args.get('search', '').strip().lower()
    if search:
        items = [i for i in items if search in i['ip_address'].lower()]

    sort_by = request.args.get('sort_by', 'ip_address')
    sort_dir = request.args.get('sort_dir', 'asc')
    reverse = sort_dir == 'desc'

    def sort_key(item):
        if sort_by == 'ttl_seconds':
            return item.get('ttl_seconds', 0)
        return item.get('ip_address', '')

    items.sort(key=sort_key, reverse=reverse)
    return jsonify(items)


@rate_limited_bp.route('/<path:ip_address>', methods=['DELETE'])
@require_role('admin')
def clear_rate_limit(ip_address):
    ip = unquote(ip_address).strip()
    if not ip:
        return jsonify({'error': 'ip_address required'}), 400

    data = _read_rate_limited_data()
    if ip not in data.get('rate_limited', []):
        return jsonify({'error': 'IP not rate limited'}), 404

    redis_client = get_redis_client()
    clear_rate_limit_entry(ip, redis_client)
    log_audit('rate_limit.clear', resource_type='rate_limit', details={'ip': ip})
    return jsonify({'message': 'Rate limit cleared', 'ip_address': ip})


@rate_limited_bp.route('/<path:ip_address>', methods=['PATCH'])
@require_role('admin')
def extend_rate_limit(ip_address):
    ip = unquote(ip_address).strip()
    if not ip:
        return jsonify({'error': 'ip_address required'}), 400

    body = request.get_json() or {}
    seconds = body.get('seconds')
    max_requests = body.get('max_requests')
    window_seconds = body.get('window_seconds')

    try:
        if seconds is not None:
            seconds = int(seconds)
        if max_requests is not None:
            max_requests = int(max_requests)
        if window_seconds is not None:
            window_seconds = int(window_seconds)
    except (TypeError, ValueError):
        return jsonify({'error': 'seconds, max_requests, and window_seconds must be numbers'}), 400

    if seconds is None and max_requests is None and window_seconds is None:
        seconds = _window_seconds()

    redis_client = get_redis_client()
    try:
        update_rate_limit_entry(
            ip,
            redis_client,
            seconds=seconds,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    data = _read_rate_limited_data()
    items = _build_items([ip], data, redis_client)
    log_audit(
        'rate_limit.extend',
        resource_type='rate_limit',
        details={
            'ip': ip,
            'seconds': seconds,
            'max_requests': max_requests,
            'window_seconds': window_seconds,
        },
    )
    return jsonify(items[0] if items else {'ip_address': ip})
