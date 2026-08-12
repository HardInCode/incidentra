"""
VULN-WEB — target lab shop (Flask). NOT production.
Ctrl+F: enforce_security (before_request), log_request (after_request)
Hooks: middleware/security.py, middleware/logging.py
"""
import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask

from cart_utils import cart_count
from config import VULN_PORT, VULN_UNSAFE_CMD, VULN_UNSAFE_UPLOAD
from db import init_db
from middleware.logging import log_request
from middleware.security import enforce_security
from routes import register_blueprints  # import fungsi dari routes/__init__.py

# create flask app vuln-web — TIDAK ada @app.route('/login') di file ini; route ada di routes/*.py
def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('VULN_SECRET_KEY', 'incidentra-lab-dev-only')

    # STEP 1 setiap HTTP request: cek block/rate-limit SEBELUM route handler jalan
    @app.before_request
    def _enforce():
        return enforce_security()  # enforce_security dari middleware/security.py — None=lanjut, 403/429=stop

    # STEP 3 setelah route selesai: tulis 1 baris ke access.log (side-effect, response ke user tidak berubah)
    @app.after_request
    def _log(response):
        return log_request(response)  # log_request dari middleware/logging.py — response=hasil route, request=Flask global

    @app.context_processor
    def inject_globals():
        return {
            'cart_count': cart_count(),
            'vuln_unsafe_cmd': VULN_UNSAFE_CMD,
            'vuln_unsafe_upload': VULN_UNSAFE_UPLOAD,
        }

    @app.template_filter('idr')
    def format_idr(value):
        try:
            n = float(value)
            return f'IDR {n:,.0f}'.replace(',', '.')
        except (TypeError, ValueError):
            return value

    # STEP 2 (implisit): daftarkan blueprint auth, shop, files, dll. dari routes/*.py
    register_blueprints(app)  # panggil register_blueprints dari routes/__init__.py, pasangkan ke Flask app
    return app


# call create_app() — instance app dipakai Gunicorn / python app.py
app = create_app()

if __name__ == '__main__':
    init_db()  # initialize database SQLite lab
    app.run(host='0.0.0.0', port=VULN_PORT, debug=False)  # run flask app vuln-web
