"""Real client IP resolution behind a reverse proxy (Railway, or any PaaS).

Why this exists: on Railway (and similar PaaS), the app never sees the real client's
TCP connection — Railway's edge proxy terminates it and forwards to the container, so
`request.remote_addr` is one of Railway's own internal/edge IPs (RFC 6598 shared address
space, 100.64.0.0/10), and it can differ per-request depending on which internal hop
served that request. Using it directly breaks anything IP-keyed: brute-force/rate-limit
counters, IP blocking, and audit trail accuracy — the same real client can appear to
"rotate" IPs on every refresh.

Railway's own guidance (as of 2026): `X-Real-IP` is always set/overwritten by their edge
proxy with the true client IP and cannot be spoofed by the client (their proxy is the
only path in — apps can't be reached bypassing it). `X-Forwarded-For` is a documented
fallback. Locally (Docker Compose, no reverse proxy), neither header is present, so this
falls back to `request.remote_addr` exactly as before — zero behavior change there.
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
