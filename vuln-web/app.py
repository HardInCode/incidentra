"""
VULN-WEB — target lab shop (Flask). NOT production.
SIDANG Ctrl+F: enforce_security (before_request), log_request (after_request)
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
from routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('VULN_SECRET_KEY', 'sme-guard-lab-dev-only')

    @app.before_request
    def _enforce():
        return enforce_security()

    @app.after_request
    def _log(response):
        return log_request(response)

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

    register_blueprints(app)
    return app


app = create_app()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=VULN_PORT, debug=False)
