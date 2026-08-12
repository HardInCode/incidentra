"""
VULN-WEB LOGGING — Combined Log + POST_DATA suffix for SOC detection.
Ctrl+F: log_request, POST_DATA, LOG_INGEST_URL, log_extra

Dipanggil dari app.py @after_request — SETELAH route handler selesai.

Hubungan backend (TIDAK import langsung — hanya format string log yang sama):
  logging.py (vuln-web)   → tulis string ke access.log ATAU POST ke LOG_INGEST_URL
  log_monitor.py (backend) → tail file / terima ingest → log_parser.py → detection_engine
"""
import datetime
import logging
import os

from flask import g, request

from config import INTERNAL_API_TIMEOUT, INTERNAL_API_TOKEN, LOG_FILE, LOG_INGEST_URL
from ip_utils import get_client_ip

logger = logging.getLogger(__name__)


def log_request(response):
    """Catat 1 baris access log per HTTP request.

    Dipanggil dari app.py:
      @app.after_request
      def _log(response):
          return log_request(response)

    Dua objek penting (jangan dibalik):
      request  — Flask GLOBAL: data request MASUK (method, path, form POST, user-agent)
      response — PARAMETER fungsi: data response KELUAR (status code, ukuran body)

    POST_DATA suffix selalu dari request.form — BUKAN dari response.
    """
    # ═══════════════════════════════════════════════════════════════════
    # LANGKAH 1 — Kumpulkan body POST jadi suffix POST_DATA (kalau POST)
    # ═══════════════════════════════════════════════════════════════════
    # Kenapa perlu? Access log Nginx standar TIDAK mencatat body HTTP.
    # SQLi/XSS di query string (GET) sudah ada di path — POST butuh suffix ini
    # supaya backend log_parser.py bisa regex baca payload login, form, upload, dll.
    post_data = ''  # default kosong — GET tidak punya suffix

    if request.method == 'POST':
        parts = []  # list string "key=value" sebelum digabung

        if request.form:
            # request.form = dict field form-urlencoded (Flask sudah parse body HTTP)
            # Contoh Burp POST login: username=admin&password=test
            # Hasil: ['username=admin', 'password=test']
            parts.extend(f'{key}={str(value)[:200]}' for key, value in request.form.items())

        if request.files:
            # Upload file: log NAMA file saja (bukan isi binary) — cukup untuk deteksi FILE_UPLOAD
            for key, f in request.files.items():
                if f and f.filename:
                    parts.append(f'{key}={f.filename[:200]}')

        if parts:
            # Gabung jadi suffix literal — backend cari teks " POST_DATA:" di akhir baris
            # Contoh: ' POST_DATA:username=admin&password=test'
            post_data = ' POST_DATA:' + '&'.join(parts)

    # ═══════════════════════════════════════════════════════════════════
    # LANGKAH 2 (opsional) — Route bisa tambah teks extra lewat g.log_extra
    # ═══════════════════════════════════════════════════════════════════
    # g = Flask request context (hidup sepanjang 1 request)
    # Pemakaian: routes/forms.py lab CSRF — set g.log_extra supaya kata "CSRF" ikut ke log
    log_extra = getattr(g, 'log_extra', '')
    if log_extra:
        if post_data:
            post_data = f'{post_data} {log_extra}'       # sudah ada POST_DATA → append
        else:
            post_data = f' POST_DATA:{log_extra}'       # belum ada → buat suffix baru

    # ═══════════════════════════════════════════════════════════════════
    # LANGKAH 3 — Susun 1 string baris log format NCSA (mirip Nginx access log)
    # ═══════════════════════════════════════════════════════════════════
    # Contoh baris lengkap:
    #   172.19.0.1 - - [12/Aug/2026:09:55:00 +0000] "POST /login HTTP/1.1" 200 3144
    #   "-" "Mozilla/5.0" POST_DATA:username=admin&password=test
    log_line = (
        f'{get_client_ip(request)} - - '                                          # IP client (ip_utils.py)
        f'[{datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] '    # timestamp UTC
        f'"{request.method} {request.full_path.rstrip("?")} HTTP/1.1" '           # GET: payload SQLi/XSS ada di sini (query string)
        f'{response.status_code} {response.content_length or 0} '                 # dari response: 200, 403, 500, ukuran bytes
        f'"-" "{request.user_agent.string}"{post_data}'                           # referer dummy + UA + suffix POST (langkah 1)
    )

    # ═══════════════════════════════════════════════════════════════════
    # LANGKAH 4 — Simpan log_line ke backend SOC (2 mode deploy)
    # ═══════════════════════════════════════════════════════════════════
    if LOG_INGEST_URL:
        # ── MODE RAILWAY / service terpisah ──
        # vuln-web & backend TIDAK share file access.log → kirim lewat HTTP POST
        # LOG_INGEST_URL = env, contoh: https://backend.../api/internal/logs
        # Backend: internal.py ingest_logs() → append ke file yang di-tail log_monitor
        try:
            import requests  # lazy import — hanya dipakai kalau LOG_INGEST_URL set (Docker tidak perlu)
            requests.post(
                LOG_INGEST_URL,                        # URL endpoint ingest backend
                json={'line': log_line},               # 1 baris log per request
                headers={'X-Internal-Token': INTERNAL_API_TOKEN},  # auth service-to-service, bukan JWT user SOC
                timeout=INTERNAL_API_TIMEOUT,          # default 2 detik — jangan block response user terlalu lama
            )
            # Tidak perlu cek response body — kalau gagal, masuk except di bawah
        except Exception as e:
            # Log gagal push → request user tetap sukses; baris log hilang untuk deteksi (warning saja)
            logger.warning(f'LOG_INGEST_URL push failed: {e}')
    else:
        # ── MODE DOCKER / shared volume ──
        # Tulis langsung ke access.log — backend LogTailer tail file yang sama di volume shared
        # LOG_FILE default: logs/access.log (env VULN_LOG_FILE)
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)  # buat folder logs/ kalau belum ada
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')  # append 1 baris — tidak overwrite file lama

    return response  # WAJIB return response — after_request Flask expect response ke browser tidak berubah
