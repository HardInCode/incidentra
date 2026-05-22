"""
VULN-WEB LOGGING — Combined Log + POST_DATA suffix for SOC detection.
SIDANG Ctrl+F: log_request, POST_DATA
"""
import datetime
import os

from flask import request

from config import LOG_FILE


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

    log_line = (
        f'{request.remote_addr} - - '
        f'[{datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] '
        f'"{request.method} {request.full_path.rstrip("?")} HTTP/1.1" '
        f'{response.status_code} {response.content_length or 0} '
        f'"-" "{request.user_agent.string}"{post_data}'
    )
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')
    return response
