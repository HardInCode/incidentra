"""
LOG PARSER — NCSA Combined Log + vuln-web POST_DATA suffix.
SIDANG Ctrl+F: parse_log_line, LogTailer, POST_DATA_PATTERN
"""
import re
import time
import os
import logging
from typing import Optional, Generator
from urllib.parse import urlparse, unquote_plus

logger = logging.getLogger(__name__)

# Combined Log Format: IP - user [time] "METHOD /path HTTP/1.1" status size "referer" "ua"
# Optional suffix: POST_DATA:key=val&... (vuln-web logs POST body for detection engine)
NGINX_PATTERN = re.compile(
    r'(?P<ip>[\d\.a-fA-F:]+)\s+-\s+-\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<path>[^\s"]*)\s+HTTP/[\d\.]+"\s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)\s+"[^"]*"\s+"(?P<ua>[^"]*)"'
)
POST_DATA_PATTERN = re.compile(r'\s+POST_DATA:(.+)$')


def parse_log_line(line: str) -> Optional[dict]:
    """Parse a single Nginx/Apache combined log line. Appends POST_DATA to query for detection."""
    line = line.strip()
    if not line:
        return None

    post_data = ''
    m = POST_DATA_PATTERN.search(line)
    if m:
        post_data = ' ' + m.group(1)
        line = line[: m.start()]

    match = NGINX_PATTERN.match(line)
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

    return {
        'ip': match.group('ip'),
        'method': match.group('method'),
        'path': path,
        'query': query,
        'user_agent': match.group('ua'),
        'status_code': int(match.group('status')),
        'raw': line + (post_data if post_data else ''),
    }


class LogTailer:
    """Tail a log file in real-time, resuming from where left off."""

    def __init__(self, filepath: str, poll_interval: float = 1.0):
        self.filepath = filepath
        self.poll_interval = poll_interval
        self._pos = 0
        self._inode = None

    def _get_inode(self):
        try:
            return os.stat(self.filepath).st_ino
        except FileNotFoundError:
            return None

    def tail(self) -> Generator[str, None, None]:
        """Yield new lines as they appear."""
        # Seek to end on first open
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(0, 2)  # End of file
                self._pos = f.tell()
                self._inode = self._get_inode()
        except FileNotFoundError:
            logger.warning(f"Log file not found: {self.filepath}")

        while True:
            current_inode = self._get_inode()
            if current_inode != self._inode:
                # Log rotation
                self._pos = 0
                self._inode = current_inode
            else:
                # Cek jika file terpotong (truncated)
                try:
                    size = os.stat(self.filepath).st_size
                    if size < self._pos:
                        logger.info(f"Log file truncated (size {size} < pos {self._pos}). Resetting position.")
                        self._pos = 0
                except Exception:
                    pass

            try:
                with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(self._pos)
                    new_lines = f.readlines()
                    self._pos = f.tell()

                for line in new_lines:
                    yield line
            except FileNotFoundError:
                pass

            time.sleep(self.poll_interval)


class SimulatedLogFeeder:
    """Feeds test log lines for demo/dev without a real log file."""

    SAMPLE_ATTACKS = [
        '192.168.1.100 - - [01/Jan/2026:10:00:01 +0000] "GET /login?user=admin\'%20OR%201=1-- HTTP/1.1" 200 512 "-" "Mozilla/5.0"',
        '10.0.0.50 - - [01/Jan/2026:10:00:05 +0000] "POST /search?q=<script>alert(document.cookie)</script> HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
        '172.16.0.5 - - [01/Jan/2026:10:00:10 +0000] "GET /admin?cmd=cat%20/etc/passwd HTTP/1.1" 403 256 "-" "sqlmap/1.7"',
        '192.168.1.200 - - [01/Jan/2026:10:00:15 +0000] "GET /../../../etc/shadow HTTP/1.1" 404 128 "-" "Nikto/2.1.6"',
        '10.10.0.1 - - [01/Jan/2026:10:00:20 +0000] "GET /index.php?page=php://filter/convert.base64-encode/resource=config HTTP/1.1" 200 2048 "-" "curl/7.68.0"',
        '192.168.1.100 - - [01/Jan/2026:10:00:25 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:26 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:27 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:28 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:29 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:30 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:31 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:32 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:33 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '192.168.1.100 - - [01/Jan/2026:10:00:34 +0000] "POST /login HTTP/1.1" 401 64 "-" "python-requests/2.28"',
        '10.0.0.100 - - [01/Jan/2026:10:01:00 +0000] "GET / HTTP/1.1" 200 4096 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"',
    ]

    def __init__(self, repeat=True, delay=3.0):
        self.repeat = repeat
        self.delay = delay

    def tail(self) -> Generator[str, None, None]:
        while True:
            for line in self.SAMPLE_ATTACKS:
                yield line
                time.sleep(self.delay)
            if not self.repeat:
                break
