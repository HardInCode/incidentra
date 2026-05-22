"""
VULN-WEB ENFORCEMENT — reads blocked_ips.json / rate_limited.json (no PostgreSQL).
SIDANG Ctrl+F: enforce_security → 403 blocked, 429 rate limited
Written by: backend response_manager
"""
import json
import os
import time
from collections import defaultdict

from flask import render_template_string, request

from config import (
    BLOCKED_IPS_FILE,
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW,
    RATE_LIMITED_FILE,
)

_request_log: dict = defaultdict(list)

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


def enforce_security():
    ip = request.remote_addr
    if request.path == '/api/status':
        return None

    blocked_data = _load_json_file(BLOCKED_IPS_FILE)
    if ip in blocked_data.get('blocked', []):
        return render_template_string(FORBIDDEN_HTML, ip=ip), 403

    rate_data = _load_json_file(RATE_LIMITED_FILE)
    if ip in rate_data.get('rate_limited', []):
        limits = rate_data.get('limits') or {}
        override = limits.get(ip) if isinstance(limits, dict) else None
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
