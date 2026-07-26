"""
VULN-WEB ENFORCEMENT — reads blocked_ips.json / rate_limited.json (no PostgreSQL), or
polls BLOCKLIST_API_URL when deployed as its own service/domain (see BLOCKLIST_API_URL
below). SIDANG Ctrl+F: enforce_security → 403 blocked, 429 rate limited
Written by: backend response_manager
"""
import json
import logging
import os
import time
from collections import defaultdict

from flask import render_template_string, request

from config import (
    BLOCKED_IPS_FILE,
    BLOCKLIST_API_URL,
    BLOCKLIST_CACHE_SECONDS,
    INTERNAL_API_TIMEOUT,
    INTERNAL_API_TOKEN,
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW,
    RATE_LIMITED_FILE,
)
from ip_utils import get_client_ip

logger = logging.getLogger(__name__)
_request_log: dict = defaultdict(list)
_blocklist_cache: dict = {'data': None, 'fetched_at': 0.0}

FORBIDDEN_HTML = """
<!DOCTYPE html><html><head><title>403 Forbidden - Incidentra SOC</title>
<style>body{font-family:sans-serif;background:#0a0e1a;color:#e8eaf6;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
.box{text-align:center;padding:3rem;border:1px solid rgba(255,23,68,0.3);border-radius:16px;background:rgba(255,23,68,0.05);}
h1{color:#ff1744;font-size:3rem;margin:0;}p{color:#8892a4;}</style></head>
<body><div class="box"><h1>🔒 403</h1><h2>Access Forbidden</h2>
<p>Your IP address <strong style="color:#ff6d00;font-family:monospace">{{ ip }}</strong> has been blocked by Incidentra SOC.</p>
<p>Contact your system administrator if you believe this is an error.</p></div></body></html>
"""

TOO_MANY_REQUESTS_HTML = """
<!DOCTYPE html><html><head><title>429 Too Many Requests - Incidentra SOC</title>
<style>body{font-family:sans-serif;background:#0a0e1a;color:#e8eaf6;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
.box{text-align:center;padding:3rem;border:1px solid rgba(255,214,0,0.3);border-radius:16px;background:rgba(255,214,0,0.05);}
h1{color:#ffd600;font-size:3rem;margin:0;}p{color:#8892a4;}</style></head>
<body><div class="box"><h1>⏱ 429</h1><h2>Too Many Requests</h2>
<p>Your IP <strong style="color:#ff6d00;font-family:monospace">{{ ip }}</strong> is rate limited to <strong>{{ limit }} req/min</strong>.</p>
<p>Please retry in <strong>{{ retry }}s</strong>.</p></div></body></html>
"""


def _load_json_file(path):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _fetch_blocklist_remote():
    """GET BLOCKLIST_API_URL (the backend's /api/internal/blocklist), cached for
    BLOCKLIST_CACHE_SECONDS so the hot enforcement path isn't one HTTP round-trip per
    request. Falls back to the last-known-good response (or empty) on error, so a
    transient backend blip fails open rather than crashing every request."""
    now = time.time()
    if _blocklist_cache['data'] is not None and now - _blocklist_cache['fetched_at'] < BLOCKLIST_CACHE_SECONDS:
        return _blocklist_cache['data']
    try:
        import requests
        resp = requests.get(
            BLOCKLIST_API_URL,
            headers={'X-Internal-Token': INTERNAL_API_TOKEN},
            timeout=INTERNAL_API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        _blocklist_cache['data'] = data
        _blocklist_cache['fetched_at'] = now
        return data
    except Exception as e:
        logger.warning(f'BLOCKLIST_API_URL fetch failed: {e}')
        return _blocklist_cache['data'] or {}


def enforce_security():
    ip = get_client_ip(request)
    # endswith (not ==) so this still matches when mounted under a prefix
    # (e.g. Railway deployment mounts this app at /lab -> /lab/api/status).
    if request.path.endswith('/api/status'):
        return None

    if BLOCKLIST_API_URL:
        combined = _fetch_blocklist_remote()
        blocked_data = {'blocked': combined.get('blocked', [])}
        rate_data = {'rate_limited': combined.get('rate_limited', []), 'limits': combined.get('limits', {})}
    else:
        blocked_data = _load_json_file(BLOCKED_IPS_FILE)
        rate_data = _load_json_file(RATE_LIMITED_FILE)

    if ip in blocked_data.get('blocked', []):
        return render_template_string(FORBIDDEN_HTML, ip=ip), 403

    if ip in rate_data.get('rate_limited', []):
        limits = rate_data.get('limits') or {}
        override = limits.get(ip) if isinstance(limits, dict) else None
        
        if isinstance(override, dict) and 'expires_at' in override:
            if time.time() > override['expires_at']:
                return None

        window = RATE_LIMIT_WINDOW
        max_req = RATE_LIMIT_MAX
        if isinstance(override, dict):
            if 'window_seconds' in override:
                window = int(override['window_seconds'])
            if 'max_requests' in override:
                max_req = int(override['max_requests'])
        now = time.time()
        _request_log[ip] = [t for t in _request_log[ip] if now - t < window]
        _request_log[ip].append(now)
        if len(_request_log[ip]) > max_req:
            retry_after = window - int(now - _request_log[ip][0])
            return render_template_string(
                TOO_MANY_REQUESTS_HTML,
                ip=ip,
                limit=max_req,
                retry=max(retry_after, 1),
            ), 429
    return None
