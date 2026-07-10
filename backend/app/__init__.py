from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from celery import Celery
import redis
import os

db = SQLAlchemy()
migrate = Migrate()
celery = Celery()

# React dev server on LAN (WiFi / Ethernet "On Your Network" URL)
_LAN_FRONTEND_ORIGINS = [
    r'http://192\.168\.\d{1,3}\.\d{1,3}:3000',
    r'http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:3000',
    r'http://172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}:3000',
]


def _cors_origins():
    origins = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        *_LAN_FRONTEND_ORIGINS,
    ]
    extra = os.getenv('CORS_ORIGINS', '').strip()
    if extra:
        origins.extend(o.strip() for o in extra.split(',') if o.strip())
    return origins


def create_app(config_name=None):
    app = Flask(__name__)

    # Load config
    from app.config import config_by_name
    cfg = config_by_name.get(config_name or os.getenv('FLASK_ENV', 'development'))
    app.config.from_object(cfg)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": _cors_origins()}})

    # Celery
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # Blueprints
    from app.api.incidents import incidents_bp
    from app.api.detection import detection_bp
    from app.api.dashboard import dashboard_bp
    from app.api.blocked_ips import blocked_ips_bp
    from app.api.rate_limited import rate_limited_bp
    from app.api.rules import rules_bp
    from app.api.auth import auth_bp
    from app.api.chatbot import chatbot_bp
    from app.api.traffic import traffic_bp
    from app.api.settings import settings_bp
    # REVISI 2A: blueprint baru untuk IP history
    from app.api.ip_history import ip_history_bp
    from app.api.audit import audit_bp
    from app.api.notifications import notifications_bp
    from app.api.users import users_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(incidents_bp, url_prefix='/api/incidents')
    app.register_blueprint(detection_bp, url_prefix='/api/detection')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(blocked_ips_bp, url_prefix='/api/blocked-ips')
    app.register_blueprint(rate_limited_bp, url_prefix='/api/rate-limited')
    app.register_blueprint(rules_bp, url_prefix='/api/rules')
    app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')
    app.register_blueprint(traffic_bp, url_prefix='/api/traffic')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    # REVISI 2A: register ip_history dengan prefix /api/ip
    app.register_blueprint(ip_history_bp, url_prefix='/api/ip')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

    return app
