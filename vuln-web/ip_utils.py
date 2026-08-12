"""Real client IP behind Railway's edge proxy — see backend/app/utils/net.py for the
full rationale (same logic, duplicated here since vuln-web has no shared dependency on
the backend package). Locally (Docker Compose), no reverse proxy sits in front of this
app, so neither header is ever present and this falls back to request.remote_addr
exactly as before.

[vuln-web §4] Prioritas: X-Real-IP → X-Forwarded-For (IP pertama) → remote_addr
Dipakai: security.py (block) + logging.py (IP di access log)
"""

# [vuln-web §4] Bukan backend — file lokal vuln-web; logic mirip backend/app/utils/net.py
def get_client_ip(request) -> str:

    # Prioritas 1: reverse proxy (Nginx/Railway) — IP asli client
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()

    # Prioritas 2: rantai "client, proxy1, proxy2" — ambil client (elemen pertama)
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        first = xff.split(',')[0].strip()
        if first:
            return first

    # Prioritas 3: Docker lokal — tidak ada proxy header
    return request.remote_addr or 'unknown'
