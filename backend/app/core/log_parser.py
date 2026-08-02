"""
LOG PARSER — NCSA Combined Log + vuln-web POST_DATA suffix.
Ctrl+F: parse_log_line, LogTailer, POST_DATA_PATTERN

Hubungan dengan vuln-web (TIDAK import logging.py — hanya baca string log):
  logging.py menulis  →  "...Mozilla/5.0" POST_DATA:username=hello&password="
  parse_log_line baca →  dict { ip, method, path, query, user_agent, ... }

POST_DATA: = teks literal di log (bukan variable Python). Parser cari dengan regex.
"""
import re
import time
import os
import logging
from typing import Optional, Generator
from urllib.parse import urlparse, unquote_plus  # stdlib Python — bukan file project

logger = logging.getLogger(__name__)

# Regex baris NCSA standar (tanpa suffix POST_DATA).
# Named groups yang diambil: ip, time, method, path, status, size, ua
# Contoh match: 172.19.0.1 - - [...] "POST /login HTTP/1.1" 200 3144 "-" "Mozilla/5.0"
NGINX_PATTERN = re.compile(
    r'(?P<ip>[\d\.a-fA-F:]+)\s+-\s+-\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<path>[^\s"]*)\s+HTTP/[\d\.]+"\s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)\s+"[^"]*"\s+"(?P<ua>[^"]*)"'
)

# Regex suffix custom dari vuln-web/middleware/logging.py baris 32.
# Mencari teks persis " POST_DATA:" + sisa baris (isi form POST).
# Contoh: ' POST_DATA:username=hello&password=' → group(1) = 'username=hello&password='
POST_DATA_PATTERN = re.compile(r'\s+POST_DATA:(.+)$')


def parse_log_line(line: str) -> Optional[dict]:
    """Urai 1 baris log (string) → dict untuk detection engine.

    Input:  line — 1 baris dari access.log atau LOG_INGEST_URL
    Output: dict jika format cocok, None jika baris kosong / tidak match
    """
    line = line.strip()
    if not line:
        return None

    # ─── Langkah A: pisah suffix POST_DATA (jika ada) ───
    # GET attack: biasanya tidak ada POST_DATA → post_data tetap ''
    # POST attack: potong suffix, simpan isinya untuk digabung ke query nanti
    post_data = ''
    m = POST_DATA_PATTERN.search(line)
    if m:
        post_data = ' ' + m.group(1)   # isi body: "username=hello&password="
        line = line[: m.start()]       # sisa = baris NCSA murni (tanpa POST_DATA)

    # ─── Langkah B: parse baris NCSA dengan regex ───
    match = NGINX_PATTERN.match(line)
    if not match:
        return None

    # ─── Langkah C: pecah path vs query string URL (untuk GET attack) ───
    # full_path dari log = "/login" atau "/search?q=%3Cscript%3E"
    # urlparse + unquote_plus = stdlib; decode %3C → <, %3E → >, %20 atau + → spasi, pisah path dari ?query= (menggunakan library urllib untuk memisahkan url dan query contoh /search & q=%3Cscript%3E)
    full_path = match.group('path')
    try:
        parsed = urlparse(full_path)
        path = unquote_plus(parsed.path)    # '/search'
        query = unquote_plus(parsed.query)  # 'q=<script>...' (GET payload ada di sini)
    except Exception:
        path = full_path
        query = ''

    # ─── Langkah D: gabung body POST ke query (untuk POST attack) ───
    # POST /login → query URL kosong; payload dari POST_DATA masuk ke query
    # Detection engine scan: method + path + query + user_agent
    if post_data:
        query = (query + post_data).strip()

    return {
        'ip': match.group('ip'),
        'method': match.group('method'),
        'path': path,
        'query': query,                          # GET: dari URL | POST: dari POST_DATA suffix
        'user_agent': match.group('ua'),
        'status_code': int(match.group('status')),
        'raw': line + (post_data if post_data else ''),  # baris log utuh (audit/debug)
    }


class LogTailer:
    """Baca baris baru dari file log secara real-time (dipakai log_monitor.py).

    Cara kerja singkat: buka file → ingat posisi byte → loop tiap poll_interval detik
    → baca hanya baris baru → yield ke pemanggil → parse_log_line(line).
    """

    def __init__(self, filepath: str, poll_interval: float = 1.0):
        self.filepath = filepath
        self.poll_interval = poll_interval
        self._pos = 0       # posisi byte terakhir yang sudah dibaca
        self._inode = None  # ID file — deteksi log rotation (file diganti baru)

    def _get_inode(self):
        try:
            return os.stat(self.filepath).st_ino
        except FileNotFoundError:
            return None

    def tail(self) -> Generator[str, None, None]:
        """Yield baris log baru satu per satu."""
        # Mulai dari akhir file — jangan re-parse log lama saat startup
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(0, 2)
                self._pos = f.tell()
                self._inode = self._get_inode()
        except FileNotFoundError:
            logger.warning(f"Log file not found: {self.filepath}")

        while True:
            current_inode = self._get_inode()
            if current_inode != self._inode:
                # File log diganti (rotation) — baca dari awal file baru
                self._pos = 0
                self._inode = current_inode
            else:
                try:
                    size = os.stat(self.filepath).st_size
                    if size < self._pos:
                        # File di-truncate — reset posisi
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
    """Log palsu untuk demo/dev tanpa vuln-web — dipakai jika tidak ada file log."""

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
