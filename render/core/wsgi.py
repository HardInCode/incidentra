"""Render deployment WSGI entrypoint.

Combines the backend API (default app — keeps its existing /api/... blueprint prefixes
completely unchanged) with vuln-web's lab app (mounted at /lab) into a single WSGI
callable, so both can run as one Render service sharing one container filesystem.

This exists ONLY for the Render deployment container built by render/core/Dockerfile.
Local Docker Compose keeps backend and vuln-web as separate containers — see
backend/run.py and vuln-web/app.py for their normal entrypoints.
"""
import os
import sys

from werkzeug.middleware.dispatcher import DispatcherMiddleware

from app import create_app as _create_backend_app

backend_app = _create_backend_app(os.getenv('FLASK_ENV', 'production'))

# Set ENABLE_LAB=false to take the exploitable /lab demo offline without tearing down
# the whole service. Backend /api/... routes are unaffected either way.
_LAB_ENABLED = os.getenv('ENABLE_LAB', 'true').strip().lower() in ('1', 'true', 'yes')

if _LAB_ENABLED:
    # vuln-web's own modules use bare top-level imports, so its directory needs to be
    # on sys.path for `wsgi_entry` to import cleanly.
    _VULNWEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vulnweb')
    sys.path.insert(0, _VULNWEB_DIR)

    from wsgi_entry import app as vulnweb_app  # noqa: E402

    application = DispatcherMiddleware(backend_app, {'/lab': vulnweb_app})
else:
    # vuln-web is never imported — /lab/* falls through to backend_app's own 404 handler.
    application = backend_app
