"""Railway deployment WSGI entrypoint.

Combines the backend API (default app — keeps its existing /api/... blueprint prefixes
completely unchanged) with vuln-web's lab app (mounted at /lab) into a single WSGI
callable, so both can run as one Railway service sharing one container filesystem.

This exists ONLY for the merged "core" Railway container built by
railway/core/Dockerfile. Local Docker Compose keeps backend and vuln-web as separate
containers/images and never imports this file — see backend/run.py and vuln-web/app.py
for their normal, unmodified entrypoints.
"""
import os
import sys

from werkzeug.middleware.dispatcher import DispatcherMiddleware

from app import create_app as _create_backend_app

backend_app = _create_backend_app(os.getenv('FLASK_ENV', 'production'))

# vuln-web's own modules (config, db, middleware, routes, cart_utils) use bare top-level
# imports, so its directory needs to be on sys.path for `wsgi_entry` to import cleanly.
_VULNWEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vulnweb')
sys.path.insert(0, _VULNWEB_DIR)

from wsgi_entry import app as vulnweb_app  # noqa: E402  (must follow sys.path setup above)

application = DispatcherMiddleware(backend_app, {'/lab': vulnweb_app})
