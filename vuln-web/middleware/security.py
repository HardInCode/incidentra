"""
VULN-WEB ENFORCEMENT — reads blocked_ips.json / rate_limited.json (no PostgreSQL), or
polls BLOCKLIST_API_URL when deployed as its own service/domain.
Ctrl+F: enforce_security → 403 blocked, 429 rate limited
Ditulis backend: response_manager.py → blocked_ips.json / rate_limited.json
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

# Counter request per IP di memory vuln-web (sliding window) — untuk enforce 429
_request_log: dict = defaultdict(list)

# Cache blocklist dari Railway fetch — supaya tidak HTTP ke backend setiap request user
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
    """Baca JSON dari shared volume (Docker). Backend yang menulis file ini."""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _fetch_blocklist_remote():
    """Railway saja: vuln-web & backend beda service → tidak bisa baca file shared.

    Panggil GET /api/internal/blocklist di backend (internal.py get_blocklist).
    Balikannya sama bentuknya dengan gabungan blocked_ips.json + rate_limited.json:
      { blocked: [...], rate_limited: [...], limits: { ip: { expires_at, ... } } }
    """
    now = time.time()

    # Kalau cache masih fresh (default 3 detik) → pakai data lama, jangan fetch lagi
    if _blocklist_cache['data'] is not None and now - _blocklist_cache['fetched_at'] < BLOCKLIST_CACHE_SECONDS:
        return _blocklist_cache['data']

    try:
        import requests
        resp = requests.get(
            BLOCKLIST_API_URL,  # env: URL backend /api/internal/blocklist
            headers={'X-Internal-Token': INTERNAL_API_TOKEN},  # auth service-to-service, bukan JWT SOC
            timeout=INTERNAL_API_TIMEOUT,
        )
        resp.raise_for_status()  # status HTTP bukan 2xx → masuk except
        data = resp.json()
        _blocklist_cache['data'] = data      # simpan ke cache memori
        _blocklist_cache['fetched_at'] = now
        return data
    except Exception as e:
        logger.warning(f'BLOCKLIST_API_URL fetch failed: {e}')
        # Backend down: pakai cache lama kalau ada; kalau belum pernah fetch → {} (sementara tidak block)
        return _blocklist_cache['data'] or {}


def enforce_security():
    """Gatekeeper — dipanggil dari app.py @before_request SEBELUM route handler jalan.

    Return None     → OK, Flask lanjut ke routes/*.py
    Return (html,403) → IP di blocklist permanent/temporary
    Return (html,429) → IP kena rate limit (terlalu banyak request dalam window)
    """
    # Ambil IP client (prioritas header proxy — lihat ip_utils.py)
    ip = get_client_ip(request)

    # Health check lab — skip enforcement supaya monitoring tidak kena 403
    # endswith (bukan ==) karena Railway mount app di /lab → path jadi /lab/api/status
    if request.path.endswith('/api/status'):
        return None

    # ─── Muat daftar block + rate-limit ───
    if BLOCKLIST_API_URL:
        # Railway: fetch dari backend API
        combined = _fetch_blocklist_remote()
        blocked_data = {'blocked': combined.get('blocked', [])}
        rate_data = {'rate_limited': combined.get('rate_limited', []), 'limits': combined.get('limits', {})}
    else:
        # Docker: baca file JSON yang ditulis response_manager.py ke shared volume
        blocked_data = _load_json_file(BLOCKED_IPS_FILE)   # { blocked: ["1.2.3.4", ...] }
        rate_data = _load_json_file(RATE_LIMITED_FILE)     # { rate_limited: [...], limits: {...} }

    # ─── Cek IP blocked → 403 ───
    if ip in blocked_data.get('blocked', []):
        return render_template_string(FORBIDDEN_HTML, ip=ip), 403

    # ─── Cek IP rate-limited → mungkin 429 ───
    if ip in rate_data.get('rate_limited', []):
        # limits = dict per-IP policy, ditulis backend (response_manager.py) ke rate_limited.json
        # Contoh limits["45.33.32.156"] = { expires_at: 1723456789.0, max_requests: 10, window_seconds: 60 }
        limits = rate_data.get('limits') or {}
        override = limits.get(ip) if isinstance(limits, dict) else None  # entry policy untuk IP ini

        # expires_at = unix timestamp kapan rate limit berakhir (backend yang set saat rate-limit/extend)
        # IP masih ada di array rate_limited[] tapi waktu sudah lewat → loloskan request (return None)
        # Backend/Celery nanti bersihkan entry expired; vuln-web tidak tunggu cleanup itu
        if isinstance(override, dict) and 'expires_at' in override:
            if time.time() > override['expires_at']:
                return None

        # Default dari env vuln-web; admin bisa override per-IP lewat SOC (PATCH /api/rate-limited/<ip>)
        window = RATE_LIMIT_WINDOW    # detik sliding window (default 60)
        max_req = RATE_LIMIT_MAX      # max request dalam window (default dari env)
        if isinstance(override, dict):
            if 'window_seconds' in override:
                window = int(override['window_seconds'])
            if 'max_requests' in override:
                max_req = int(override['max_requests'])

        # Hitung request IP ini dalam window (in-memory di process vuln-web, bukan Redis)
        now = time.time()
        _request_log[ip] = [t for t in _request_log[ip] if now - t < window]  # buang timestamp lama (sliding window)
        _request_log[ip].append(now)  # catat request sekarang
        if len(_request_log[ip]) > max_req:
            retry_after = window - int(now - _request_log[ip][0])
            return render_template_string(
                TOO_MANY_REQUESTS_HTML,
                ip=ip,
                limit=max_req,
                retry=max(retry_after, 1),
            ), 429

    return None  # tidak blocked, tidak rate-limited → route handler di routes/*.py jalan normal
