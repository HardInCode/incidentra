"""
LOG PARSER — baca access.log + urai baris log jadi dict.
Ctrl+F: LogTailer, parse_log_line, POST_DATA_PATTERN

Urutan baca file ini (sesuai alur runtime):
  ① LogTailer.tail()     → yield `line` (string, 1 baris access.log)
  ② parse_log_line(line) → dict `entry` untuk detection engine
  ③ SimulatedLogFeeder   → alternatif demo (tanpa vuln-web)

Hubungan vuln-web (TIDAK import logging.py):
  logging.py menulis string → access.log → LogTailer baca → parse_log_line
"""
import re
import time
import os
import logging
from typing import Optional, Generator
from urllib.parse import urlparse, unquote_plus  # stdlib — pecah URL & decode %3C → <

logger = logging.getLogger(__name__)

# Regex baris NCSA standar — dipakai Langkah B parse_log_line
NGINX_PATTERN = re.compile(
    r'(?P<ip>[\d\.a-fA-F:]+)\s+-\s+-\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<path>[^\s"]*)\s+HTTP/[\d\.]+"\s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)\s+"[^"]*"\s+"(?P<ua>[^"]*)"'
)
# Suffix custom dari logging.py — teks literal " POST_DATA:" + isi form POST
POST_DATA_PATTERN = re.compile(r'\s+POST_DATA:(.+)$')


# ═══════════════════════════════════════════════════════════════════════════════
# ① LogTailer — BACA file access.log, hasilkan `line` (string)
#    Dipanggil dari: log_monitor.start_monitor → for line in feeder.tail()
# ═══════════════════════════════════════════════════════════════════════════════

class LogTailer:
    """Baca baris baru dari file log secara real-time.

    Output: yield `line` — 1 string per baris log (input untuk parse_log_line).
    """

    def __init__(self, filepath: str, poll_interval: float = 1.0):
        self.filepath = filepath            # path access.log (Docker: /app/watched_logs/access.log)
        self.poll_interval = poll_interval  # cek file tiap 1 detik (default)
        self._pos = 0                       # bookmark byte — sudah baca sampai sini
        self._inode = None                  # ID file di disk — deteksi file diganti (log rotation)

    def _get_inode(self):                          # cek apakah file masih file yang sama
        try:
            return os.stat(self.filepath).st_ino   # st_ino = unique ID file di filesystem
        except FileNotFoundError:
            return None

    def tail(self) -> Generator[str, None, None]:  # generator: yield 1 baris per iterasi
        """Yield baris log baru satu per satu."""
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(0, 2)                      # loncat ke EOF — skip log lama saat backend restart
                self._pos = f.tell()              # simpan posisi = ukuran file sekarang
                self._inode = self._get_inode()
        except FileNotFoundError:
            logger.warning(f"Log file not found: {self.filepath}")

        while True:                              # loop selamanya (background thread)
            current_inode = self._get_inode()
            if current_inode != self._inode:     # file diganti (rotation) → baca dari awal file baru
                self._pos = 0
                self._inode = current_inode
            else:
                try:
                    size = os.stat(self.filepath).st_size
                    if size < self._pos:         # file di-truncate (dikosongkan) → reset bookmark
                        logger.info(f"Log file truncated (size {size} < pos {self._pos}). Resetting position.")
                        self._pos = 0
                except Exception:
                    pass

            try:
                with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(self._pos)            # lanjut baca dari bookmark
                    new_lines = f.readlines()    # ambil baris baru saja (bisa 0, 1, atau banyak)
                    self._pos = f.tell()         # update bookmark ke posisi terbaru

                for line in new_lines:
                    yield line                   # kirim string ke _process_log_line(line)
            except FileNotFoundError:
                pass

            time.sleep(self.poll_interval)       # tunggu 1 detik sebelum cek lagi (hemat CPU)


# ═══════════════════════════════════════════════════════════════════════════════
# ② parse_log_line — URAI `line` (string) → `entry` (dict)
#    Dipanggil dari: log_monitor._process_log_line
# ═══════════════════════════════════════════════════════════════════════════════

def parse_log_line(line: str) -> Optional[dict]:
    """Urai 1 baris log → dict untuk detection engine.

    Input:  line — string dari LogTailer / ingest HTTP
    Output: dict { ip, method, path, query, user_agent, status_code, raw } atau None
    """
    line = line.strip()                          # buang \n di ujung baris
    if not line:
        return None                              # baris kosong → skip

    # ── Langkah A: pisah suffix POST_DATA (POST attack — payload dari logging.py) ──
    post_data = ''                               # penampung isi body form
    m = POST_DATA_PATTERN.search(line)           # cari teks " POST_DATA:..." di ujung baris
    if m:
        post_data = ' ' + m.group(1)             # group(1) = username=hello&password= (spasi depan sengaja)
        line = line[: m.start()]                 # potong suffix — sisakan baris NCSA murni

    # ── Langkah B: regex baris NCSA → ambil ip, method, path, status, user_agent ──
    match = NGINX_PATTERN.match(line)
    if not match:
        return None                              # format log tidak cocok → skip

    # ── Langkah C: pecah path vs query URL + decode (GET attack — payload di ?query=) ──
    full_path = match.group('path')              # contoh: /search?q=%3Cscript%3E atau /login
    try:
        parsed = urlparse(full_path)             # stdlib — pisah path dan query
        path = unquote_plus(parsed.path)         # /search
        query = unquote_plus(parsed.query)       # q=<script>... (%3C → <)
    except Exception:
        path = full_path                         # fallback kalau urlparse gagal
        query = ''

    # ── Langkah D: gabung body POST ke query (POST attack — URL tidak punya ?) ──
    if post_data:
        query = (query + post_data).strip()      # query kosong + POST_DATA → detection scan ini

    return {
        'ip': match.group('ip'),                         # IP attacker
        'method': match.group('method'),                 # GET / POST
        'path': path,                                    # /login, /search, ...
        'query': query,                                  # GET: dari URL | POST: dari POST_DATA suffix
        'user_agent': match.group('ua'),                 # Mozilla, sqlmap, ...
        'status_code': int(match.group('status')),       # 200, 403, ...
        'raw': line + (post_data if post_data else ''),  # baris log utuh (audit/debug)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ③ SimulatedLogFeeder — alternatif LogTailer (demo tanpa vuln-web)
#    Interface sama: .tail() → yield `line` — dipakai USE_SIMULATED_LOGS=true
# ═══════════════════════════════════════════════════════════════════════════════

class SimulatedLogFeeder:
    """Log palsu untuk demo — tidak baca file, yield string hardcoded."""

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
        self.repeat = repeat                     # True = loop sample forever; False = sekali lalu stop
        self.delay = delay                       # jeda antar baris (detik)

    def tail(self) -> Generator[str, None, None]:  # interface sama LogTailer — start_monitor tidak peduli sumber
        while True:
            for line in self.SAMPLE_ATTACKS:
                yield line                       # kirim baris sample ke _process_log_line
                time.sleep(self.delay)
            if not self.repeat:
                break
