"""
VULN-WEB LOGGING — Combined Log + POST_DATA suffix for SOC detection.
SIDANG Ctrl+F: log_request, POST_DATA, LOG_INGEST_URL
"""
import datetime
import logging
import os

from flask import g, request

from config import INTERNAL_API_TIMEOUT, INTERNAL_API_TOKEN, LOG_FILE, LOG_INGEST_URL
from ip_utils import get_client_ip

logger = logging.getLogger(__name__)


def log_request(response):
    post_data = ''
    if request.method == 'POST':
        parts = []
        if request.form:
            parts.extend(f'{key}={str(value)[:200]}' for key, value in request.form.items())
        if request.files:
            for key, f in request.files.items():
                if f and f.filename:
                    parts.append(f'{key}={f.filename[:200]}')
        if parts:
            post_data = ' POST_DATA:' + '&'.join(parts)

    log_extra = getattr(g, 'log_extra', '')
    if log_extra:
        post_data = f'{post_data} {log_extra}' if post_data else f' POST_DATA:{log_extra}'

    log_line = (
        f'{get_client_ip(request)} - - '
        f'[{datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] '
        f'"{request.method} {request.full_path.rstrip("?")} HTTP/1.1" '
        f'{response.status_code} {response.content_length or 0} '
        f'"-" "{request.user_agent.string}"{post_data}'
    )
    if LOG_INGEST_URL:
        # Decoupled deployment (own domain, no shared volume) — push the line to the
        # backend instead of appending to a local file it can no longer share.
        try:
            import requests
            requests.post(
                LOG_INGEST_URL,
                json={'line': log_line},
                headers={'X-Internal-Token': INTERNAL_API_TOKEN},
                timeout=INTERNAL_API_TIMEOUT,
            )
        except Exception as e:
            logger.warning(f'LOG_INGEST_URL push failed: {e}')
    else:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    return response
