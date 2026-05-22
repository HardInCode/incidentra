"""
LIVE TRAFFIC API — display-only tags (Attack/Normal/Blocked); NOT the detection engine.
SIDANG Ctrl+F: ATTACK_KEYWORDS, TRAFFIC_ATTACK_PATTERNS, _parse_line, get_recent_traffic
Incidents: detection_engine.analyze (separate pipeline)
"""
import re
import os
from flask import Blueprint, request, jsonify
from urllib.parse import urlparse, unquote_plus

traffic_bp = Blueprint('traffic', __name__)

from app.api.auth_middleware import verify_token

@traffic_bp.before_request
def _check_auth():
    return verify_token()

# Combined Log Format: IP - - [TIME] "METHOD PATH HTTP/1.1" STATUS SIZE "-" "UA"
COMBINED_LOG_PATTERN = re.compile(
    r'(?P<ip>[\d\.a-fA-F:]+)\s+-\s+-\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<path>[^\s"]*)\s+HTTP/[\d\.]+"\s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)\s+'
    r'"[^"]*"\s+"(?P<ua>[^"]*)"'
)

# Extended format (vuln-web with POST data): ... "UA" POST_DATA:key=val&...
POST_DATA_PATTERN = re.compile(r'\s+POST_DATA:(.+)$')

# Lightweight keywords (fallback after regex pass)
ATTACK_KEYWORDS = [
    'union select', 'select ', ' from ', 'insert into', 'drop table',
    'or 1=1', "' or '", "' or \"", 'sleep(', 'benchmark(',
    '<script', 'onerror=', 'javascript:', 'onload=',
    '../', '..\\', '%2e%2e', 'php://', 'cmd=', '; whoami', '; cat',
    'sqlmap', 'nikto', 'nmap',
    'blocked_ips.json', 'rate_limited.json',
]

# Subset aligned with detection_engine (display-only; does not create incidents)
TRAFFIC_ATTACK_PATTERNS = [
    re.compile(r"(?i)(union\s+select|select\s+(\*|[\w]+\s*,\s*[\w\s,`]*|count\s*\([\w\s,*)]*\))\s+from\s+\w)"),
    re.compile(r"(?i)(\bor\b\s+[\'\"]?\d+[\'\"]?\s*=\s*[\'\"]?\d+[\'\"]?)"),
    re.compile(r"(?i)(\'|\")(\s*;\s*|\s+or\s+|\s+and\s+).*?(--|#|/\*)"),
    re.compile(r"(?i)(\'\s+or\s+[\'\"][^\'\"]+[\'\"]\s*=\s*[\'\"][^\'\"]+)"),
    re.compile(r"(?i)(<script[\s>]|</script>|javascript\s*:|onerror\s*=|onload\s*=)"),
    re.compile(r"(?i)(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\/|\.\.%2f)"),
    re.compile(r"(?i)(?:\?file=|[&;\s]file=|file=)[^&\s\"]*\.\."),
    re.compile(r"(?i)(php://input|php://filter|expect://|data://)"),
    re.compile(r"(?i)\bcmd=\s*[^&\s\"]*\b(whoami|id|uname|ls|pwd|cat|ping)\b"),
    re.compile(r"(?i)(nikto|sqlmap|nmap|acunetix|nessus|burpsuite|zaproxy|dirbuster|gobuster)"),
]

DANGEROUS_UPLOAD_EXT = re.compile(
    r'(?i)(?:post_data:)?(?:file|avatar)=[^&\s"]*\.(php\d*|phtml|phar|jsp|asp|aspx|exe|dll|sh|bat|cmd|ps1|htaccess|cgi)\b',
)


def _resolve_log_path():
    """Resolve log file path from env or fallbacks."""
    path = os.getenv('WEB_SERVER_LOG_PATH', '')
    if path and os.path.isfile(path):
        return os.path.abspath(path)
    fallbacks = [
        '../vuln-web/logs/access.log',
        'vuln-web/logs/access.log',
        '/app/watched_logs/access.log',
    ]
    for p in fallbacks:
        if p.startswith('/') and os.path.isfile(p):
            return p
        cwd = os.getcwd()
        candidate = os.path.normpath(os.path.join(cwd, p))
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return None


def _classify_traffic_tag(searchable: str, path: str, status: int) -> str:
    """Heuristic tag for Live Traffic (aligned with detection patterns where practical)."""
    if status in (403, 429):
        return 'blocked'
    if path.startswith('/static/') or path in ('/favicon.ico',):
        return 'normal'
    if DANGEROUS_UPLOAD_EXT.search(searchable):
        return 'attack'
    for pattern in TRAFFIC_ATTACK_PATTERNS:
        if pattern.search(searchable):
            return 'attack'
    if any(kw in searchable for kw in ATTACK_KEYWORDS):
        return 'attack'
    if status >= 400:
        return 'suspicious'
    return 'normal'


def _parse_line(line: str) -> dict | None:
    """Parse a single Combined Log Format line, optionally with POST_DATA suffix."""
    line = line.strip()
    if not line:
        return None

    post_data = ''
    m = POST_DATA_PATTERN.search(line)
    if m:
        post_data = ' ' + m.group(1)
        line = line[:m.start()]

    match = COMBINED_LOG_PATTERN.match(line)
    if not match:
        return None

    full_path = match.group('path')
    try:
        parsed = urlparse(full_path)
        path = unquote_plus(parsed.path)
        query = unquote_plus(parsed.query)
    except Exception:
        path = full_path
        query = ''

    if post_data:
        query = (query + post_data).strip()

    status = int(match.group('status'))
    size = int(match.group('size') or 0)
    ua = (match.group('ua') or '')[:120]
    method = match.group('method')

    searchable = f"{method} {path} {query} {ua}".lower()
    tag = _classify_traffic_tag(searchable, path, status)

    return {
        'ip': match.group('ip'),
        'time': match.group('time'),
        'method': method,
        'path': path,
        'query': query[:500] if query else '',
        'status': status,
        'size': size,
        'ua': ua,
        'tag': tag,
    }


@traffic_bp.route('/recent', methods=['GET'])
def get_recent_traffic():
    """Return last N log entries, newest first. Max 500."""
    limit = min(request.args.get('limit', 100, type=int), 500)
    limit = max(limit, 1)

    log_path = _resolve_log_path()
    if not log_path:
        return jsonify({
            'entries': [],
            'total_lines': 0,
            'summary': {'attack': 0, 'suspicious': 0, 'blocked': 0, 'normal': 0},
            'log_path': None,
            'error': 'Log file not found. Check vuln-web is running and WEB_SERVER_LOG_PATH.',
        }), 200

    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        total_lines = len(lines)
        summary = {'attack': 0, 'suspicious': 0, 'blocked': 0, 'normal': 0}
        entries = []

        for line in reversed(lines[-limit:]):
            entry = _parse_line(line)
            if entry:
                summary[entry['tag']] = summary.get(entry['tag'], 0) + 1
                entries.append(entry)

        return jsonify({
            'entries': entries,
            'total_lines': total_lines,
            'summary': summary,
            'log_path': log_path,
        })
    except Exception as e:
        return jsonify({
            'entries': [],
            'total_lines': 0,
            'summary': {'attack': 0, 'suspicious': 0, 'blocked': 0, 'normal': 0},
            'log_path': log_path,
            'error': str(e),
        }), 200
