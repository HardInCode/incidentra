"""Real client IP behind Railway's edge proxy — see backend/app/utils/net.py for the
full rationale (same logic, duplicated here since vuln-web has no shared dependency on
the backend package). Locally (Docker Compose), no reverse proxy sits in front of this
app, so neither header is ever present and this falls back to request.remote_addr
exactly as before.
"""


def get_client_ip(request) -> str:
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        first = xff.split(',')[0].strip()
        if first:
            return first
    return request.remote_addr or 'unknown'
