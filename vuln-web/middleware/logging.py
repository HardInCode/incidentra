"""
VULN-WEB LOGGING — Combined Log + POST_DATA suffix for SOC detection.
Ctrl+F: log_request, POST_DATA, LOG_INGEST_URL, log_extra

Dipanggil dari app.py @app.after_request — setiap request selesai, tulis 1 baris log.

Hubungan dengan backend (TIDAK import langsung — hanya format string yang sama):
  logging.py (vuln-web)  →  tulis string ke access.log / LOG_INGEST_URL
  log_parser.py (backend) →  baca string itu, parse jadi dict

POST_DATA bukan variable/function — literal teks " POST_DATA:..." di akhir baris log.
Isinya = salinan body form POST (payload Burp di bawah header HTTP).
"""
import datetime
import logging
import os

from flask import g, request

from config import INTERNAL_API_TIMEOUT, INTERNAL_API_TOKEN, LOG_FILE, LOG_INGEST_URL
from ip_utils import get_client_ip

logger = logging.getLogger(__name__)


def log_request(response):
    """Catat 1 baris log per request.

    Parameter:
      response — dari @app.after_request (status code, content_length, dll.)
    Flask global `request` — masih hidup di sini, body POST bisa dibaca via request.form.
    """

    # ─── Langkah 1: salin body POST ke teks (payload Burp: username=hello&password=) ───
    # Nginx access log standar TIDAK menyertakan body — makanya kita tambah suffix custom.
    # request.form = dict field form; Flask sudah parse body HTTP (bukan dari header).
    post_data = ''
    if request.method == 'POST':
        parts = []
        if request.form:
            # Contoh: {'username': 'hello', 'password': ''} → ['username=hello', 'password=']
            parts.extend(f'{key}={str(value)[:200]}' for key, value in request.form.items())
        if request.files:
            # Upload: log nama file saja (bukan isi file), max 200 char
            for key, f in request.files.items():
                if f and f.filename:
                    parts.append(f'{key}={f.filename[:200]}')
        if parts:
            # Hasil: ' POST_DATA:username=hello&password='
            post_data = ' POST_DATA:' + '&'.join(parts)

    # ─── Langkah 2 (opsional): teks extra dari route lewat g.log_extra ───
    # Hook generik — route mana saja boleh set g.log_extra sebelum return.
    # Pemakaian: routes/forms.py — lab CSRF; kata "CSRF" ikut ke log untuk detection.
    log_extra = getattr(g, 'log_extra', '')
    if log_extra:
        post_data = f'{post_data} {log_extra}' if post_data else f' POST_DATA:{log_extra}'

    # ─── Langkah 3: susun 1 string baris log format NCSA (seperti Nginx access log) ───
    # Contoh lengkap:
    #   172.19.0.1 - - [02/Aug/2026:13:00:01 +0000] "POST /login HTTP/1.1" 200 3144
    #   "-" "Mozilla/5.0" POST_DATA:username=hello&password=
    log_line = (
        f'{get_client_ip(request)} - - '                                          # IP client
        f'[{datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] '    # timestamp UTC
        f'"{request.method} {request.full_path.rstrip("?")} HTTP/1.1" '           # method + path (tanpa body!)
        f'{response.status_code} {response.content_length or 0} '                 # status + ukuran response
        f'"-" "{request.user_agent.string}"{post_data}'                           # referer + UA + suffix POST
    )

    # ─── Langkah 4: simpan string log_line ───
    # Manual & Docker: append ke file (volume shared → backend tail file yang sama)
    # Railway: POST json {'line': log_line} ke backend (tidak share file)
    if LOG_INGEST_URL:
        try:
            import requests
            requests.post(
                LOG_INGEST_URL,
                json={'line': log_line},
                headers={'X-Internal-Token': INTERNAL_API_TOKEN},
                timeout=INTERNAL_API_TIMEOUT,
            )
        except Exception as e:
            logger.warning(f'LOG_INGEST_URL push failed: {e}')
    else:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')

    return response  # response ke browser tidak diubah — logging cuma side-effect
