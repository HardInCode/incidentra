"""Real client IP behind Railway's edge proxy — see backend/app/utils/net.py for the
full rationale (same logic, duplicated here since vuln-web has no shared dependency on
the backend package). Locally (Docker Compose), no reverse proxy sits in front of this
app, so neither header is ever present and this falls back to request.remote_addr
exactly as before.
"""

# get_client_ip — dipakai logging.py (access.log) & security.py (block/rate-limit)
def get_client_ip(request) -> str: #from request Flask object, return client ip

    # Prioritas 1: header dari reverse proxy (Nginx/Railway edge) — IP asli client, bukan IP proxy
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip() 

    # Prioritas 2: X-Forwarded-For bisa berisi rantai IP "client, proxy1, proxy2" — ambil yang pertama (client)
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        first = xff.split(',')[0].strip()
        if first:
            return first

    # Prioritas 3: Docker Compose lokal — tidak ada proxy, langsung IP koneksi TCP ke container
    return request.remote_addr or 'unknown' # 'remote_addr' attribute from request Flask object for local development
